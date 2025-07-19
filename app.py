
import logging
import os
import json
import boto3
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from log.processing import processing
from log.sinks import dynatrace
from version import get_version

logger = logging.getLogger()
logger.setLevel(os.getenv("LOGGING_LEVEL", "INFO"))

logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)

boto3_session = boto3.Session()

metrics = Metrics()
metrics.set_default_dimensions(deployment=os.environ['DEPLOYMENT_NAME'])

dynatrace_sinks = dynatrace.load_sinks()

@metrics.log_metrics
def lambda_handler(event, context):
    logging.info("dynatrace-aws-s3-log-forwarder version: %s", get_version())

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
            # 🟡 Step 1: SNS-wrapped SQS Message
            logger.info("Now processing SNS message received in SQS queue")
            sns_message = json.loads(message['body'])
            if 'Message' in sns_message:
                payload = json.loads(sns_message['Message'])
            else:
                payload = sns_message
        except json.decoder.JSONDecodeError as exception:
            logging.warning('Dropping message %s, body is not valid JSON', exception.doc)
            continue

        try:
            # 🟢 Step 2: EventBridge S3-style detail-based payload
            if 'detail' in payload:
                logger.info("This appears to be an EventBridge-style message with 'detail.bucket.name'")
                bucket_name = payload['detail']['bucket']['name']
                key_name = payload['detail']['object']['key']
                source_context = payload['detail'].get('requester', 'unknown')
                region = payload.get('region', 'unknown')

            # 🔵 Step 3: Normal S3 PUT notifications from SNS
            elif 'Records' in payload and 's3' in payload['Records'][0]:
                logger.info("S3 notification-style message detected with Records -> s3.bucket.name")
                bucket_name = payload['Records'][0]['s3']['bucket']['name']
                key_name = payload['Records'][0]['s3']['object']['key']
                source_context = payload['Records'][0].get('eventSource', 'aws:s3')
                region = payload['Records'][0].get('awsRegion', 'unknown')

            else:
                logger.warning("Unsupported event structure. Skipping message.")
                continue

            if bucket_name != "sf-infosec-cloudfront-logs":
                logger.info('Skipping object s3://%s/%s; bucket not whitelisted.', bucket_name, key_name)
                continue

            logger.info('Processing object s3://%s/%s; source: %s',
                        bucket_name, key_name, source_context)

            log_object_destination_sinks = list(dynatrace_sinks.values())

            if not log_object_destination_sinks:
                logger.error('There are no valid sinks available for bucket %s.', bucket_name)
                metrics.add_metric(name="LogFilesSkipped", unit=MetricUnit.Count, value=1)
                continue

            user_defined_log_annotations = {
                "source.service": "cloudfront",
                "team": "infosec",
                "environment": "prod"
            }

            processing.process_log_object(
                log_processing_rule=None,
                bucket=bucket_name,
                key=key_name,
                bucket_region=region,
                log_sinks=log_object_destination_sinks,
                lambda_context=context,
                user_defined_annotations=user_defined_log_annotations,
                session=boto3_session
            )

            for dynatrace_sink in log_object_destination_sinks:
                dynatrace_sink.flush()

            metrics.add_metric(name='LogFilesProcessed', unit=MetricUnit.Count, value=1)

        except Exception:
            logger.exception('Error processing message %s', message['messageId'])
            batch_item_failures['batchItemFailures'].append({'itemIdentifier': message['messageId']})

    logger.debug(json.dumps(batch_item_failures, indent=2))
    metrics.add_metric(name='LogProcessingFailures', unit=MetricUnit.Count, value=len(batch_item_failures['batchItemFailures']))
    return batch_item_failures
