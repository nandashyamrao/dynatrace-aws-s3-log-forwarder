
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
        batch_item_failures['batchItemFailures'].append(
            {'itemIdentifier': message['messageId']})
    return batch_item_failures

def reload_rules(rules_type: str):
    if os.environ['LOG_FORWARDER_CONFIGURATION_LOCATION'] == "aws-appconfig":
        glob = globals()
        try:
            rules_configuration_profile = aws_appconfig_helpers.get_configuration_from_aws_appconfig(
                f"log-{rules_type}-rules")
            if rules_configuration_profile['Configuration-Version'] != glob[f"current_log_{rules_type}_rules_version"]:
                logger.info("New log-%s-rules configuration version found. Loading version %s ...",
                            str(rules_configuration_profile['Configuration-Version']), rules_type)
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
                s3_notification = json.loads(sns_message['Message'])
            else:
                s3_notification = sns_message
        except json.decoder.JSONDecodeError as exception:
            logging.warning('Dropping message %s, body is not valid JSON', exception.doc)
            continue)

    logger.debug(json.dumps(batch_item_failures, indent=2))
    metrics.add_metric(name='LogProcessingFailures', unit=MetricUnit.Count, value=len(batch_item_failures['batchItemFailures']))
    return batch_item_failures
