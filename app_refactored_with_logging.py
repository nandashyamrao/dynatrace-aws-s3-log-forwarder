import logging
import os
import json
import re
import boto3
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

from log.processing import log_processing_rules
from log.processing import processing
from log.forwarding import log_forwarding_rules
from log.sinks import dynatrace
from utils import aws_appconfig_extension_helpers as aws_appconfig_helpers
from version import get_version

# ------------------- Logger Setup ------------------- #
logger = logging.getLogger()
logger.setLevel(os.getenv("LOGGING_LEVEL", "INFO"))

# Suppress noisy boto logs
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)

# ------------------- Boto3 and Metrics ------------------- #
boto3_session = boto3.Session()
metrics = Metrics()
metrics.set_default_dimensions(deployment=os.environ['DEPLOYMENT_NAME'])

# ------------------- Load Rules ------------------- #
defined_log_forwarding_rules, current_log_forwarding_rules_version = log_forwarding_rules.load()
logger.info("✅ Loaded log-forwarding-rules version %s from %s",
            current_log_forwarding_rules_version, os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION'))

defined_log_processing_rules, current_log_processing_rules_version = log_processing_rules.load()
logger.info("✅ Loaded log-processing-rules version %s from %s",
            current_log_processing_rules_version, os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION'))

# ------------------- Load Sinks ------------------- #
dynatrace_sinks = dynatrace.load_sinks()

# ------------------- Helper Functions ------------------- #
def generate_execution_timeout_batch_item_failures(index: int, batch_item_failures: dict, messages: list):
    for message in messages[index:]:
        batch_item_failures['batchItemFailures'].append({'itemIdentifier': message['messageId']})
    return batch_item_failures

def reload_rules(rules_type: str):
    if os.environ['LOG_FORWARDER_CONFIGURATION_LOCATION'] == "aws-appconfig":
        glob = globals()
        try:
            rules_configuration_profile = aws_appconfig_helpers.get_configuration_from_aws_appconfig(f"log-{rules_type}-rules")
            if rules_configuration_profile['Configuration-Version'] != glob[f"current_log_{rules_type}_rules_version"]:
                logger.info("🔄 New log-%s-rules version found: %s. Reloading...",
                            rules_type, rules_configuration_profile['Configuration-Version'])
                glob[f"defined_log_{rules_type}_rules"], glob[f"current_log_{rules_type}_rules_version"] = glob[f"log_{rules_type}_rules"].load()
                return True
        except aws_appconfig_helpers.ErrorAccessingAppConfig:
            logger.exception("❌ Unable to reload log-%s-rules from AWS AppConfig", rules_type)
    return False

# ------------------- Lambda Handler ------------------- #
@metrics.log_metrics
def lambda_handler(event, context):
    logger.info("🚀 dynatrace-aws-s3-log-forwarder version: %s", get_version())
    logger.debug("🔍 Raw Event:
%s", json.dumps(event, indent=2))
    os.environ['FORWARDER_FUNCTION_ARN'] = context.invoked_function_arn

    # Reload AppConfig if enabled
    reload_rules('forwarding')
    reload_rules('processing')

    batch_item_failures = {'batchItemFailures': []}
    event_records = event.get('Records', [])
    if not isinstance(event_records, list):
        logger.error("❌ Invalid event structure: 'Records' field is missing or not a list.")
        return batch_item_failures

    for index, message in enumerate(event_records):
        dynatrace.empty_sinks(dynatrace_sinks)

        try:
            # Step 1: Parse the message body
            sns_message = json.loads(message['body'])
            if 'Message' in sns_message:
                payload = json.loads(sns_message['Message'])
                logger.info("📨 Received SNS-wrapped EventBridge or S3 message.")
            else:
                payload = sns_message
                logger.info("📨 Received direct S3 or EventBridge message.")
        except json.decoder.JSONDecodeError as e:
            logger.warning("❌ Invalid JSON in message body: %s", str(e))
            continue

        # Step 2: Extract bucket/key
        try:
            if 'detail' in payload:
                bucket_name = payload['detail']['bucket']['name']
                key_name = payload['detail']['object']['key']
                region = payload.get('region', 'unknown')
                source_context = payload['detail'].get('requester', 'unknown')
                logger.info("🧭 Found bucket/key from EventBridge: s3://%s/%s", bucket_name, key_name)
            elif 'Records' in payload and 's3' in payload['Records'][0]:
                record = payload['Records'][0]
                bucket_name = record['s3']['bucket']['name']
                key_name = record['s3']['object']['key']
                region = record.get('awsRegion', 'unknown')
                source_context = record.get('eventSource', 'aws:s3')
                logger.info("🧭 Found bucket/key from S3 Record: s3://%s/%s", bucket_name, key_name)
            else:
                logger.warning("⚠️ Unsupported event format, skipping.")
                continue
        except Exception:
            logger.exception("❌ Failed to extract bucket/key from event.")
            batch_item_failures['batchItemFailures'].append({'itemIdentifier': message['messageId']})
            continue

        # Step 3: Match forwarding rule
        try:
            matched_log_forwarding_rule = log_forwarding_rules.get_matching_log_forwarding_rule(
                bucket_name, key_name, defined_log_forwarding_rules)

            if matched_log_forwarding_rule is None:
                logger.info("⛔ Dropping s3://%s/%s — No matching forwarding rule found.", bucket_name, key_name)
                metrics.add_metric(name='DroppedObjectsNotMatchingFwdRules', unit=MetricUnit.Count, value=1)
                continue

            logger.info("✅ Matched forwarding rule '%s' for s3://%s/%s",
                        matched_log_forwarding_rule.name, bucket_name, key_name)
            user_defined_log_annotations = matched_log_forwarding_rule.annotations

            # Step 4: Match processing rule
            matched_log_processing_rule = log_processing_rules.lookup_processing_rule(
                matched_log_forwarding_rule.source,
                matched_log_forwarding_rule.source_name,
                defined_log_processing_rules,
                key_name)

            if matched_log_processing_rule is None:
                logger.warning("⚠️ No processing rule matched for source %s and key %s",
                               matched_log_forwarding_rule.source, key_name)
                metrics.add_metric(name="LogFilesSkipped", unit=MetricUnit.Count, value=1)
                continue

            # Step 5: Validate sink(s)
            log_object_destination_sinks = []
            for sink_id in matched_log_forwarding_rule.sinks:
                try:
                    log_object_destination_sinks.append(dynatrace_sinks[sink_id])
                except KeyError:
                    logger.warning("⚠️ Invalid sink ID '%s' in rule '%s'", sink_id, matched_log_forwarding_rule.name)

            if not log_object_destination_sinks:
                logger.error("❌ No valid sinks in rule '%s' for bucket %s", matched_log_forwarding_rule.name, bucket_name)
                metrics.add_metric(name="LogFilesSkipped", unit=MetricUnit.Count, value=1)
                continue

            # Step 6: Process and flush
            processing.process_log_object(
                matched_log_processing_rule, bucket_name, key_name, region,
                log_object_destination_sinks, context,
                user_defined_annotations=user_defined_log_annotations,
                session=boto3_session)

            for sink in log_object_destination_sinks:
                sink.flush()

            metrics.add_metric(name='LogFilesProcessed', unit=MetricUnit.Count, value=1)

        except Exception:
            logger.exception("❌ Error processing message %s", message['messageId'])
            batch_item_failures['batchItemFailures'].append({'itemIdentifier': message['messageId']})

    metrics.add_metric(name='LogProcessingFailures', unit=MetricUnit.Count, value=len(batch_item_failures['batchItemFailures']))
    return batch_item_failures
