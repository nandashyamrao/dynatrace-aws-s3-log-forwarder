import logging
import os
import json
import boto3
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from log.processing import log_processing_rules
from log.processing import processing
from log.forwarding import log_forwarding_rules
from log.sinks import dynatrace
from utils import aws_appconfig_extension_helpers as aws_appconfig_helpers
from version import get_version

logger = logging.getLogger()
logger.setLevel(os.getenv("LOGGING_LEVEL", "INFO"))

# Adjust boto log verbosity
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)

# Create a boto3 session to reuse
boto3_session = boto3.Session()

# initialize Metrics
metrics = Metrics()
metrics.set_default_dimensions(deployment=os.environ['DEPLOYMENT_NAME'])

# Load log-forwarding-rules
defined_log_forwarding_rules, current_log_forwarding_rules_version = log_forwarding_rules.load()
logger.info("Loaded log-forwarding-rules version %s from %s",
            current_log_forwarding_rules_version, os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION'))

# Load log-processing-rules
defined_log_processing_rules, current_log_processing_rules_version = log_processing_rules.load()
logger.info("Loaded log-processing-rules version %s from %s",
            current_log_forwarding_rules_version, os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION'))

# load sinks
dynatrace_sinks = dynatrace.load_sinks()


def generate_execution_timeout_batch_item_failures(index: int, batch_item_failures: dict, messages: list):
    '''
    Gets the current batch_item_failures dict and adds the messages that were left unprocessed due
    to execution timeout
    '''
    for message in messages[index:]:
        batch_item_failures['batchItemFailures'].append(
            {'itemIdentifier': message['messageId']})
    return batch_item_failures


def reload_rules(rules_type: str):
    if os.environ['LOG_FORWARDER_CONFIGURATION_LOCATION'] == "aws-appconfig":
        # load globals
        glob = globals()

        try:
            # Check if we need to reload log forwarding rules
            rules_configuration_profile = aws_appconfig_helpers.get_configuration_from_aws_appconfig(
                f"log-{rules_type}-rules")

            if rules_configuration_profile['Configuration-Version'] != glob[f"current_log_{rules_type}_rules_version"]:
                logger.info("New log-%s-rules configuration version found. Loading version %s ...",
                            str(rules_configuration_profile['Configuration-Version']), rules_type)
                glob[f"defined_log_{rules_type}_rules"], glob[f"current_log_{rules_type}_rules_version"] = glob[f"log_{rules_type}_rules"].load(
                )
                return True

        except aws_appconfig_helpers.ErrorAccessingAppConfig:
            logger.exception(
                "Unable to reload log-%s-rules from AWS AppConfig", rules_type)

    return False


@metrics.log_metrics
def lambda_handler(event, context):

    logging.info("dynatrace-aws-s3-log-forwarder version: %s", get_version())

    # If we're using AWS AppConfig and there's a new config version available, reload
    reload_rules('forwarding')
    reload_rules('processing')

    logger.debug(json.dumps(event, indent=2))

    os.environ['FORWARDER_FUNCTION_ARN'] = context.invoked_function_arn

    # List for SQS messages that failed processing
    batch_item_failures = {
        'batchItemFailures': []
    }

    # Iterate through the messages in the event
    for index, message in enumerate(event['Records']):
        dynatrace.empty_sinks(dynatrace_sinks)

        try:
            # Check if the message is SNS or SQS format
            if 'Sns' in message:
                # SNS message
                sns_message = json.loads(message['Sns']['Message'])
                bucket_name = sns_message['Records'][0]['s3']['bucket']['name']
                key_name = sns_message['Records'][0]['s3']['object']['key']

            elif 'body' in message:
                # SQS message
                sqs_message = json.loads(message['body'])
                bucket_name = sqs_message['Records'][0]['s3']['bucket']['name']
                key_name = sqs_message['Records'][0]['s3']['object']['key']

            else:
                logger.warning("Unrecognized message format. Skipping message.")
                continue

            logger.info('Processing object s3://%s/%s', bucket_name, key_name)

            process_s3_object(bucket_name, key_name)

        except Exception as ex:
            logger.error("Failed processing message for bucket: %s, key: %s due to %s",
                         bucket_name if 'bucket_name' in locals() else "unknown",
                         key_name if 'key_name' in locals() else "unknown",
                         str(ex))

            batch_item_failures['batchItemFailures'].append({
                'itemIdentifier': message['messageId']
            })

    return batch_item_failures


# Catch all exception. If anything fails, add messageId to batchItemFailures
try:
    matched_log_forwarding_rule = log_forwarding_rules.get_matching_log_forwarding_rule(
        bucket_name, key_name, defined_log_forwarding_rules)

    # if no matching forwarding rules, drop message
    if matched_log_forwarding_rule is None:
        logger.info(
            'Dropping object. s3://%s/%s doesn\'t match any forwarding rule',
            bucket_name, key_name)
        metrics.add_metric(
            name='DroppedObjectsNotMatchingFwdRules', unit=MetricUnit.Count, value=1)
        continue

    logger.debug('Object s3://%s/%s matched log forwarding rule %s',
                 bucket_name, key_name, matched_log_forwarding_rule.name)

    user_defined_log_annotations = matched_log_forwarding_rule.annotations
    logger.debug('User defined annotations: %s',
                 user_defined_log_annotations)

    matched_log_processing_rule = log_processing_rules.lookup_processing_rule(
        matched_log_forwarding_rule.source,
        matched_log_forwarding_rule.source_name,
        defined_log_processing_rules,
        key_name)

    if matched_log_processing_rule is not None:
        log_object_destination_sinks = []

        for sink_id in matched_log_forwarding_rule.sinks:
            try:
                log_object_destination_sinks.append(
                    dynatrace_sinks[sink_id])
            except KeyError:
                logger.warning('Invalid sink id %s defined on log forwarding rule %s in bucket %s.',
                               sink_id, matched_log_forwarding_rule.name, bucket_name)

        if not log_object_destination_sinks:
            logger.error('There are no valid sinks defined in log forwarding rule %s in bucket %s.',
                         matched_log_forwarding_rule.name, bucket_name)
            metrics.add_metric(name="LogFilesSkipped",
                               unit=MetricUnit.Count, value=1)
            continue

        processing.process_log_object(
            matched_log_processing_rule, bucket_name, key_name, sns_message['region'],
            log_object_destination_sinks, context,
            user_defined_annotations=user_defined_log_annotations,
            session=boto3_session
        )

        # Iterate through all sinks and flush
        for dynatrace_sink in log_object_destination_sinks:
            dynatrace_sink.flush()

        metrics.add_metric(name='LogFilesProcessed',
                           unit=MetricUnit.Count, value=1)

    else:
        logger.warning('Could not find a matching log processing rule for source %s and key %s. Skipping...',
                       matched_log_forwarding_rule.source, key_name)
        metrics.add_metric(name="LogFilesSkipped",
                           unit=MetricUnit.Count, value=1)

except UnicodeDecodeError:
    logger.exception(
        'Error decoding log object. Log contains non-UTF-8 characters. Dropping object s3://%s/%s', bucket_name, key_name
    )
    metrics.add_metric(
        name='DroppedObjectsDecodingErrors', unit=MetricUnit.Count, value=1)

except processing.NotEnoughExecutionTimeRemaining:
    logger.exception(
        'Unable to process log file s3://%s/%s with remaining Lambda execution time. %s total non-processed log files in batch',
        bucket_name, key_name, (len(event['Records']) - index)
    )

    metrics.add_metric(
        name='NotEnoughExecutionTimeRemainingErrors', unit=MetricUnit.Count, value=1)

    total_batch_item_failures = generate_execution_timeout_batch_item_failures(
        index, batch_item_failures, event['Records'])

    metrics.add_metric(name='LogProcessingFailures', unit=MetricUnit.Count, value=len(
        total_batch_item_failures['batchItemFailures']))

    logger.debug(json.dumps(batch_item_failures, indent=2))

    return total_batch_item_failures

except Exception:
    logger.exception(
        'Error processing message %s', message['messageId'])

    batch_item_failures