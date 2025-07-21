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
from version import get_version

# Set up the root logger for the Lambda function
logger = logging.getLogger()
logger.setLevel(os.getenv("LOGGING_LEVEL", "INFO"))

# Reduce verbosity of boto3 and botocore logs to warnings only
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)

# Create a reusable boto3 session for AWS calls (avoids cold start penalty)
boto3_session = boto3.Session()

# Initialize the Metrics object from Lambda Powertools for custom CloudWatch metrics
metrics = Metrics()
# Set default metric dimensions for all metrics sent in this Lambda invocation
metrics.set_default_dimensions(deployment=os.environ['DEPLOYMENT_NAME'])

# Load log forwarding rules (which buckets/keys to process and where to send them)
defined_log_forwarding_rules, current_log_forwarding_rules_version = log_forwarding_rules.load()
logger.info(
    "Loaded log-forwarding-rules version %s from %s",
    current_log_forwarding_rules_version,
    os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION')
)

# Load log processing rules (how to process logs based on source/source_name/key)
defined_log_processing_rules, current_log_processing_rules_version = log_processing_rules.load()
logger.info(
    "Loaded log-processing-rules version %s from %s",
    current_log_forwarding_rules_version,
    os.environ.get('LOG_FORWARDER_CONFIGURATION_LOCATION')
)

# Load all Dynatrace sinks (where logs will be forwarded after processing)
dynatrace_sinks = dynatrace.load_sinks()

@metrics.log_metrics  # Automatically sends custom metrics at the end of Lambda execution
def lambda_handler(event, context):
    """
    AWS Lambda entry point. Handles SQS-triggered events containing S3 notifications, uses
    rule-based matching to determine whether and how to process log objects, and forwards processed logs to Dynatrace sinks.
    """
    # Log the version of the forwarder for traceability
    logging.info("dynatrace-aws-s3-log-forwarder version: %s", get_version())
    # Dump the event payload for debugging
    logger.debug(json.dumps(event, indent=2))

    # Set the ARN of the current Lambda function in the environment for downstream use
    os.environ['FORWARDER_FUNCTION_ARN'] = context.invoked_function_arn
    # Prepare response structure for SQS batch item failures (partial batch success)
    batch_item_failures = {'batchItemFailures': []}

    # Extract SQS records from the event payload
    event_records = event.get('Records')
    if not isinstance(event_records, list):
        logger.error('Received invalid event (missing or invalid "Records" field)')
        logger.error(json.dumps(event, indent=2))
        event_records = []  # Prevents errors if the event is malformed

    # Loop through each SQS message in the batch
    for index, message in enumerate(event_records):
        # Empty all sinks before processing the next message to prevent cross-message contamination
        dynatrace.empty_sinks(dynatrace_sinks)

        # Try to parse the SQS message body as JSON
        try:
            sns_message = json.loads(message['body'])
            # If the message has a nested "Message" field (SNS-wrapped), parse it again
            if 'Message' in sns_message:
                payload = json.loads(sns_message['Message'])
            else:
                payload = sns_message
        except json.decoder.JSONDecodeError as exception:
            # If the message body is not valid JSON, skip this message and log a warning
            logging.warning('Dropping message %s, body is not valid JSON', exception.doc)
            continue

        # Extract bucket/key info and other metadata depending on event structure
        if 'detail' in payload:
            # EventBridge-style
            bucket_name = payload['detail']['bucket']['name']
            key_name = payload['detail']['object']['key']
            source_context = payload['detail'].get('requester', 'unknown')
            region = payload.get('region', 'unknown')
            logger.info(
                f"Bucket name and key found in EventBridge message: bucket='{bucket_name}', key='{key_name}'"
            )
        elif 'Records' in payload and 's3' in payload['Records'][0]:
            # SNS-wrapped S3 notification style
            bucket_name = payload['Records'][0]['s3']['bucket']['name']
            key_name = payload['Records'][0]['s3']['object']['key']
            source_context = payload['Records'][0].get('eventSource', 'aws:s3')
            region = payload['Records'][0].get('awsRegion', 'unknown')
            logger.info(
                f"Bucket name and key found in SQS/SNS message: bucket='{bucket_name}', key='{key_name}'"
            )
        else:
            # If the event structure is unsupported, skip this message and log a warning
            logger.warning("Unsupported event structure. Skipping message.")
            continue

        # Start rule-based processing for this bucket/key
        try:
            # Find a matching forwarding rule for this bucket/key
            matched_log_forwarding_rule = log_forwarding_rules.get_matching_log_forwarding_rule(
                bucket_name, key_name, defined_log_forwarding_rules
            )

            # If no forwarding rule matches, skip processing for this log object and record a metric
            if matched_log_forwarding_rule is None:
                logger.info(
                    'Dropping object. s3://%s/%s does not match any forwarding rule',
                    bucket_name, key_name)
                metrics.add_metric(
                    name='DroppedObjectsNotMatchingFwdRules', unit=MetricUnit.Count, value=1)
                continue

            # Log the name of the matched forwarding rule
            logger.debug('Object s3://%s/%s matched log forwarding rule %s',
                         bucket_name, key_name, matched_log_forwarding_rule.name)

            # Get any custom log annotations defined by the forwarding rule (for enrichment)
            user_defined_log_annotations = matched_log_forwarding_rule.annotations
            logger.debug('User defined annotations: %s',
                         user_defined_log_annotations)

            # Find a matching log processing rule for the log source
            matched_log_processing_rule = log_processing_rules.lookup_processing_rule(
                matched_log_forwarding_rule.source,
                matched_log_forwarding_rule.source_name,
                defined_log_processing_rules,
                key_name
            )

            if matched_log_processing_rule is not None:
                # Prepare the list of sinks (destinations) for this log object based on the rule
                log_object_destination_sinks = []

                # Match sinks by ID, warn if a sink is missing
                for sink_id in matched_log_forwarding_rule.sinks:
                    try:
                        log_object_destination_sinks.append(
                            dynatrace_sinks[sink_id])
                    except KeyError:
                        logger.warning(
                            'Invalid sink id %s defined on log forwarding rule %s in bucket %s.',
                            sink_id, matched_log_forwarding_rule.name, bucket_name
                        )

                # If there are no valid sinks for this rule, skip processing and record a metric
                if not log_object_destination_sinks:
                    logger.error(
                        'There are no valid sinks defined in log forwarding rule %s in bucket %s.',
                        matched_log_forwarding_rule.name, bucket_name
                    )
                    metrics.add_metric(name="LogFilesSkipped",
                                       unit=MetricUnit.Count, value=1)
                    continue

                # Process the log object using the matched processing rule and sinks
                processing.process_log_object(
                    matched_log_processing_rule, bucket_name, key_name, region,
                    log_object_destination_sinks, context,
                    user_defined_annotations=user_defined_log_annotations,
                    session=boto3_session
                )

                # Flush (send) all processed logs to their respective sinks
                for dynatrace_sink in log_object_destination_sinks:
                    dynatrace_sink.flush()

                # Record a metric for successful log file processing
                metrics.add_metric(name='LogFilesProcessed',
                                   unit=MetricUnit.Count, value=1)

            else:
                # If no processing rule matches, skip processing and record a metric
                logger.warning(
                    'Could not find a matching log processing rule for source %s and key %s. Skipping...',
                    matched_log_forwarding_rule.source, key_name
                )
                metrics.add_metric(name="LogFilesSkipped",
                                   unit=MetricUnit.Count, value=1)

        except Exception:
            # Catch all exceptions during processing, log the error, and add the message to batch failures
            logger.exception('Error processing message %s', message.get('messageId', 'unknown'))
            batch_item_failures['batchItemFailures'].append({'itemIdentifier': message.get('messageId', 'unknown')})

    # Log the batch failures for debugging
    logger.debug(json.dumps(batch_item_failures, indent=2))
    # Record a metric for the number of log processing failures in this batch
    metrics.add_metric(name='LogProcessingFailures', unit=MetricUnit.Count, value=len(batch_item_failures['batchItemFailures']))
    # Return the batch item failures for SQS partial batch response
    return batch_item_failures
