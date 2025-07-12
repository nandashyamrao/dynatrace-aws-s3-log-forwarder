
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

logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)

boto3_session = boto3.Session()

metrics = Metrics()
metrics.set_default_dimensions(deployment=os.environ['DEPLOYMENT_NAME'])

defined_log_forwarding_rules, current_log_forwarding_rules_version = log_forwarding_rules.load()
logger.info("Loaded log-forwarding-rules version %s from %s",
            current_log_forwarding_rules_version, os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION'))

defined_log_processing_rules, current_log_processing_rules_version = log_processing_rules.load()
logger.info("Loaded log-processing-rules version %s from %s",
            current_log_processing_rules_version, os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION'))

dynatrace_sinks = dynatrace.load_sinks()

def generate_execution_timeout_batch_item_failures(index: int, batch_item_failures: dict, messages: list):
    for message in messages[index:]:
        batch_item_failures['batchItemFailures'].append({'itemIdentifier': message['messageId']})
    return batch_item_failures

def reload_rules(rules_type: str):
    if os.environ['LOG_FORWARDER_CONFIGURATION_LOCATION'] == "aws-appconfig":
        glob = globals()
        try:
            rules_configuration_profile = aws_appconfig_helpers.get_configuration_from_aws_appconfig(
                f"log-{rules_type}-rules")
            if rules_configuration_profile['Configuration-Version'] != glob[f"current_log_{rules_type}_rules_version"]:
                logger.info("New log-%s-rules configuration version found. Loading version %s ...",
                            rules_type, str(rules_configuration_profile['Configuration-Version']))
                glob[f"defined_log_{rules_type}_rules"], glob[f"current_log_{rules_type}_rules_version"] = glob[f"log_{rules_type}_rules"].load()
                return True
        except aws_appconfig_helpers.ErrorAccessingAppConfig:
            logger.exception("Unable to reload log-%s-rules from AWS AppConfig", rules_type)
    return False

@metrics.log_metrics
def lambda_handler(event, context):
    logging.info("dynatrace-aws-s3-log-forwarder version: %s", get_version())

    reload_rules('forwarding')
    reload_rules('processing')

    logger.debug(json.dumps(event, indent=2))

    os.environ['FORWARDER_FUNCTION_ARN'] = context.invoked_function_arn
    batch_item_failures = {'batchItemFailures': []}

    event_records = event.get('Records')
    if not isinstance(event_records, list):
        logger.error('Received invalid event (missing or invalid "Records" field)')
        logger.error(json.dumps(event, indent=2))
        event_records = []

    for index, message in enumerate(event_records):
        dynatrace.empty_sinks(dynatrace_sinks)

        try:
            sns_message = json.loads(message['body'])
            if 'Message' in sns_message:
                payload = json.loads(sns_message['Message'])
            else:
                payload = sns_message
        except json.decoder.JSONDecodeError as exception:
            logging.warning('Dropping message %s, body is not valid JSON', exception.doc)
            continue

        try:
            # Handle both EventBridge-like and S3-style formats
            if 'detail' in payload:
                bucket_name = payload['detail']['bucket']['name']
                key_name = payload['detail']['object']['key']
                source_context = payload['detail'].get('requester', 'unknown')
                region = payload.get('region', 'unknown')
            elif 'Records' in payload and 's3' in payload['Records'][0]:
                bucket_name = payload['Records'][0]['s3']['bucket']['name']
                key_name = payload['Records'][0]['s3']['object']['key']
                source_context = payload['Records'][0].get('eventSource', 'aws:s3')
                region = payload['Records'][0].get('awsRegion', 'unknown')
            else:
                logger.warning("Unsupported event structure. Skipping message.")
                continue

            logger.info('Processing object s3://%s/%s; source: %s',
                        bucket_name, key_name, source_context)

            matched_log_forwarding_rule = log_forwarding_rules.get_matching_log_forwarding_rule(
                bucket_name, key_name, defined_log_forwarding_rules)

            if matched_log_forwarding_rule is None:
                logger.info('Dropping object. s3://%s/%s doesn\'t match any forwarding rule',
                            bucket_name, key_name)
                metrics.add_metric(name='DroppedObjectsNotMatchingFwdRules', unit=MetricUnit.Count, value=1)
                continue

            logger.debug('Object s3://%s/%s matched log forwarding rule %s',
                         bucket_name, key_name, matched_log_forwarding_rule.name)

            user_defined_log_annotations = matched_log_forwarding_rule.annotations
            logger.debug('User defined annotations: %s', user_defined_log_annotations)

            matched_log_processing_rule = log_processing_rules.lookup_processing_rule(
                matched_log_forwarding_rule.source,
                matched_log_forwarding_rule.source_name,
                defined_log_processing_rules,
                key_name)

            if matched_log_processing_rule is not None:
                log_object_destination_sinks = []

                for sink_id in matched_log_forwarding_rule.sinks:
                    try:
                        log_object_destination_sinks.append(dynatrace_sinks[sink_id])
                    except KeyError:
                        logger.warning('Invalid sink id %s defined on log forwarding rule %s in bucket %s.',
                                       sink_id, matched_log_forwarding_rule.name, bucket_name)

                if not log_object_destination_sinks:
                    logger.error('There are no valid sinks defined in log forwarding rule %s in bucket %s.',
                                 matched_log_forwarding_rule.name, bucket_name)
                    metrics.add_metric(name="LogFilesSkipped", unit=MetricUnit.Count, value=1)
                    continue

                processing.process_log_object(
                    matched_log_processing_rule, bucket_name, key_name, region,
                    log_object_destination_sinks, context,
                    user_defined_annotations=user_defined_log_annotations,
                    session=boto3_session
                )

                for dynatrace_sink in log_object_destination_sinks:
                    dynatrace_sink.flush()

                metrics.add_metric(name='LogFilesProcessed', unit=MetricUnit.Count, value=1)
            else:
                logger.warning('Could not find a matching log processing rule for source %s and key %s. Skipping...',
                               matched_log_forwarding_rule.source, key_name)
                metrics.add_metric(name="LogFilesSkipped", unit=MetricUnit.Count, value=1)

        except UnicodeDecodeError:
            logger.exception('Error decoding log object. Log contains non-UTF-8 characters. Dropping object s3://%s/%s', bucket_name, key_name)
            metrics.add_metric(name='DroppedObjectsDecodingErrors', unit=MetricUnit.Count, value=1)

        except processing.NotEnoughExecutionTimeRemaining:
            logger.exception(
                'Unable to process log file s3://%s/%s with remaining Lambda execution time. %s total non-processed log files in batch',
                bucket_name, key_name, (len(event['Records']) - index))
            metrics.add_metric(name='NotEnoughExecutionTimeRemainingErrors', unit=MetricUnit.Count, value=1)

            total_batch_item_failures = generate_execution_timeout_batch_item_failures(
                index, batch_item_failures, event['Records'])

            metrics.add_metric(name='LogProcessingFailures', unit=MetricUnit.Count, value=len(
                total_batch_item_failures['batchItemFailures']))
            logger.debug(json.dumps(batch_item_failures, indent=2))
            return total_batch_item_failures

        except Exception:
            logger.exception('Error processing message %s', message['messageId'])
            batch_item_failures['batchItemFailures'].append({'itemIdentifier': message['messageId']})

    logger.debug(json.dumps(batch_item_failures, indent=2))
    metrics.add_metric(name='LogProcessingFailures', unit=MetricUnit.Count, value=len(batch_item_failures['batchItemFailures']))
    return batch_item_failures
