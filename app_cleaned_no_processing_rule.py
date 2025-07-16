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

def lambda_handler(event, context):
    batch_item_failures = {'batchItemFailures': []}

    for index, message in enumerate(event["Records"]):
        dynatrace.empty_sinks(dynatrace_sinks)

        try:
            sns_message = json.loads(message['body'])
            if 'Message' in sns_message:
                payload = json.loads(sns_message['Message'])
            else:
                payload = sns_message
            logger.info("SNS message received: %s", json.dumps(payload))
        except json.decoder.JSONDecodeError as exception:
            logging.warning('Dropping message %s, body is not valid JSON', exception.doc)
            continue

        try:
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
                continue

            logger.info("Reading file from bucket: %s, key: %s", bucket_name, key_name)

            matched_log_forwarding_rule = log_forwarding_rules.get_matching_log_forwarding_rule(
                bucket_name, key_name, defined_log_forwarding_rules)

            if matched_log_forwarding_rule is None:
                logger.info("Dropping object. s3://%s/%s doesn't match any forwarding rule",
                            bucket_name, key_name)
                metrics.add_metric(name="DroppedObjectNoMatchingRule", unit=MetricUnit.Count, value=1)
                continue

            object_records, metadata = processing.process_log_file(
                boto3_session,
                bucket_name,
                key_name,
                matched_log_forwarding_rule
            )

            total_log_entries = len(object_records)
            logger.info(f"Total log entries processed: {total_log_entries}")
            logger.info("Log data sent to Dynatrace successfully for %d records", total_log_entries)

            metrics.add_metric(name="LogEntriesProcessed", unit=MetricUnit.Count, value=total_log_entries)
            metrics.publish()

            log_forwarding_rules.send_records_to_sinks(
                object_records,
                metadata,
                dynatrace_sinks,
                matched_log_forwarding_rule,
                source_context,
                region
            )

        except Exception as e:
            logger.exception("Failed processing message: %s", str(e))
            generate_execution_timeout_batch_item_failures(index, batch_item_failures, event["Records"])
            continue

    return batch_item_failures