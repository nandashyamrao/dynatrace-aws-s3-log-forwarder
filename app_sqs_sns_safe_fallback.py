
# Copyright 2022 Dynatrace LLC

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
            current_log_forwarding_rules_version, os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION'))

dynatrace_sinks = dynatrace.load_sinks()

def generate_execution_timeout_batch_item_failures(index: int, batch_item_failures: dict, messages: list):
    for message in messages[index:]:
        batch_item_failures['batchItemFailures'].append({'itemIdentifier': message.get('messageId', 'UNKNOWN')})
    return batch_item_failures

def reload_rules(rules_type: str):
    if os.environ['LOG_FORWARDER_CONFIGURATION_LOCATION'] == "aws-appconfig":
        glob = globals()
        try:
            profile = aws_appconfig_helpers.get_configuration_from_aws_appconfig(f"log-{rules_type}-rules")
            if profile['Configuration-Version'] != glob[f"current_log_{rules_type}_rules_version"]:
                logger.info("New log-%s-rules config version found. Reloading...", rules_type)
                glob[f"defined_log_{rules_type}_rules"], glob[f"current_log_{rules_type}_rules_version"] = glob[f"log_{rules_type}_rules"].load()
                return True
        except aws_appconfig_helpers.ErrorAccessingAppConfig:
            logger.exception("Unable to reload %s rules from AWS AppConfig", rules_type)
    return False

@metrics.log_metrics
def lambda_handler(event, context):
    logging.info("dynatrace-aws-s3-log-forwarder version: %s", get_version())
    reload_rules('forwarding')
    reload_rules('processing')
    logger.debug("Full event:
%s", json.dumps(event, indent=2))

    os.environ['FORWARDER_FUNCTION_ARN'] = context.invoked_function_arn
    batch_item_failures = {'batchItemFailures': []}

    event_records = event.get('Records', [])
    if not isinstance(event_records, list):
        logger.error("Invalid or missing 'Records' in event:
%s", json.dumps(event, indent=2))
        return batch_item_failures

    for index, message in enumerate(event_records):
        dynatrace.empty_sinks(dynatrace_sinks)

        try:
            logger.debug("Raw message body:
%s", message.get('body', 'NO BODY'))
            s3_notification = json.loads(message['body'])

            if "Records" not in s3_notification:
                logger.warning("Message body missing 'Records' key. Skipping.
%s", json.dumps(s3_notification, indent=2))
                continue

            bucket_name = s3_notification['Records'][0]['s3']['bucket']['name']
            key_name = s3_notification['Records'][0]['s3']['object']['key']

        except Exception as e:
            logger.warning("Failed to parse S3 message structure: %s", str(e))
            logger.debug("Failed message body:
%s", message.get('body', 'NO BODY'))
            continue

        logger.info("Processing object s3://%s/%s", bucket_name, key_name)

        try:
            matched_log_forwarding_rule = log_forwarding_rules.get_matching_log_forwarding_rule(
                bucket_name, key_name, defined_log_forwarding_rules)

            if matched_log_forwarding_rule is None:
                logger.info("Skipping unmatched object: s3://%s/%s", bucket_name, key_name)
                metrics.add_metric(name="DroppedObjectsNotMatchingFwdRules", unit=MetricUnit.Count, value=1)
                continue

            matched_log_processing_rule = log_processing_rules.lookup_processing_rule(
                matched_log_forwarding_rule.source,
                matched_log_forwarding_rule.source_name,
                defined_log_processing_rules,
                key_name)

            if not matched_log_processing_rule:
                logger.warning("No processing rule matched for key: %s", key_name)
                metrics.add_metric(name="LogFilesSkipped", unit=MetricUnit.Count, value=1)
                continue

            log_object_destination_sinks = []
            for sink_id in matched_log_forwarding_rule.sinks:
                try:
                    log_object_destination_sinks.append(dynatrace_sinks[sink_id])
                except KeyError:
                    logger.warning("Invalid sink ID %s in rule %s", sink_id, matched_log_forwarding_rule.name)

            if not log_object_destination_sinks:
                logger.error("No valid sinks configured for rule %s", matched_log_forwarding_rule.name)
                metrics.add_metric(name="LogFilesSkipped", unit=MetricUnit.Count, value=1)
                continue

            processing.process_log_object(
                matched_log_processing_rule, bucket_name, key_name,
                s3_notification['Records'][0].get('awsRegion', 'us-east-1'),
                log_object_destination_sinks, context,
                user_defined_annotations=matched_log_forwarding_rule.annotations,
                session=boto3_session)

            for dynatrace_sink in log_object_destination_sinks:
                dynatrace_sink.flush()

            metrics.add_metric(name="LogFilesProcessed", unit=MetricUnit.Count, value=1)

        except processing.NotEnoughExecutionTimeRemaining:
            logger.exception("Not enough time left to process s3://%s/%s", bucket_name, key_name)
            batch_item_failures = generate_execution_timeout_batch_item_failures(index, batch_item_failures, event_records)
            metrics.add_metric(name="LogProcessingFailures", unit=MetricUnit.Count, value=len(batch_item_failures['batchItemFailures']))
            return batch_item_failures

        except Exception:
            logger.exception("Unhandled error processing message")
            batch_item_failures['batchItemFailures'].append({'itemIdentifier': message.get('messageId', 'UNKNOWN')})

    metrics.add_metric(name="LogProcessingFailures", unit=MetricUnit.Count, value=len(batch_item_failures['batchItemFailures']))
    return batch_item_failures
