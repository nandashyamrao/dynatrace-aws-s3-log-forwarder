
import logging
import gzip
import json
import boto3
import sys
import time
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

from log.processing.log_processing_rule import LogProcessingRule
from utils.helpers import ENCODING

logger = logging.getLogger()
metrics = Metrics()

EXECUTION_REMAINING_TIME_LIMIT = 10000

def _get_context_log_attributes(bucket: str, key: str):
    return {
        'log.source.aws.s3.bucket.name': bucket,
        'log.source.aws.s3.key.name': key,
        'cloud.log_forwarder': os.environ.get('FORWARDER_FUNCTION_ARN', 'undefined')
    }

def normalize_field_name(name: str) -> str:
    return name.lower().replace('-', '_').replace('.', '_')

def process_log_object(log_processing_rule: LogProcessingRule, bucket: str, key: str, bucket_region: str, log_sinks: list,
                       lambda_context, user_defined_annotations: dict = None, session: boto3.Session = None):
    start_time = time.time()
    if not session:
        session = boto3.Session()

    if user_defined_annotations is None:
        user_defined_annotations = {}

    s3_client = session.client('s3')
    obj = s3_client.get_object(Bucket=bucket, Key=key)
    body = obj['Body']

    if key.endswith('.gz'):
        log_stream = gzip.GzipFile(fileobj=body)
    else:
        log_stream = body

    context_log_attributes = {}
    context_log_attributes.update(user_defined_annotations)
    context_log_attributes.update(_get_context_log_attributes(bucket, key))
    context_log_attributes.update(log_processing_rule.get_attributes_from_s3_key_name(key))
    context_log_attributes.update(log_processing_rule.get_processing_log_annotations())

    for log_sink in log_sinks:
        log_sink.set_s3_source(bucket, key)

    cloudfront_fields = []
    num_processed = 0
    decompressed_size = 0

    for line in log_stream:
        if isinstance(line, bytes):
            line = line.decode(ENCODING)
        line = line.strip()

        if not line:
            continue

        if line.startswith('#'):
            if line.lower().startswith('# fields:'):
                cloudfront_fields = [normalize_field_name(f) for f in line.split(":", 1)[1].strip().split()]
                logger.debug(f"Parsed CloudFront fields: {cloudfront_fields}")
            continue

        if log_processing_rule.skip_header_lines and num_processed < log_processing_rule.skip_header_lines:
            num_processed += 1
            continue

        values = line.split('\t')
        if not cloudfront_fields or len(values) < len(cloudfront_fields):
            logger.warning("Skipping log line due to missing fields or unparsed header: %s", line)
            continue

        log_entry = {}
        for i, field_name in enumerate(cloudfront_fields):
            if i < len(values):
                log_entry[field_name] = values[i]

        log_entry.update(context_log_attributes)
        log_entry['content'] = line

        if "aws.region" not in log_entry:
            log_entry["aws.region"] = bucket_region

        for log_sink in log_sinks:
            log_sink.push(log_entry)

        decompressed_size += sys.getsizeof(line)
        num_processed += 1

        if num_processed % 1000 == 0 and lambda_context.get_remaining_time_in_millis() < EXECUTION_REMAINING_TIME_LIMIT:
            logger.warning("Not enough time left to process large object s3://%s/%s", bucket, key)
            raise NotEnoughExecutionTimeRemaining

    logger.info("Processed %d CloudFront log lines from s3://%s/%s", num_processed, bucket, key)

    end_time = time.time()
    metrics.add_metric(name='LogProcessingTime', unit=MetricUnit.Seconds, value=(end_time - start_time))
    metrics.add_metric(name='ReceivedUncompressedLogFileSize', unit=MetricUnit.Bytes, value=decompressed_size)
    metrics.add_metric(name='LogFilesProcessed', unit=MetricUnit.Count, value=1)

    return num_processed

class NotEnoughExecutionTimeRemaining(Exception):
    pass
