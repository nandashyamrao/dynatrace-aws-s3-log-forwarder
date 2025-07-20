
# Updated CloudFront log parsing version of processing.py with relaxed field check

import logging
from os import environ
import sys
import time
import json
import gzip
import boto3
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

from utils.helpers import ENCODING

logger = logging.getLogger()
metrics = Metrics()

EXECUTION_REMAINING_TIME_LIMIT = 10000

cloudfront_fields = [
    "date", "time", "x-edge-location", "sc-bytes", "c-ip", "cs-method", "cs(Host)",
    "cs-uri-stem", "sc-status", "cs(Referer)", "cs(User-Agent)", "cs-uri-query",
    "cs(Cookie)", "x-edge-result-type", "x-edge-request-id", "x-host-header",
    "cs-protocol", "cs-bytes", "time-taken", "x-forwarded-for", "ssl-protocol",
    "ssl-cipher", "x-edge-response-result-type", "cs-protocol-version", "fle-status",
    "fle-encrypted-fields", "c-port", "time-to-first-byte", "x-edge-detailed-result-type",
    "sc-content-type", "sc-content-len", "sc-range-start", "sc-range-end"
]

def _get_context_log_attributes(bucket: str, key: str):
    return {
        'log.source.aws.s3.bucket.name': bucket,
        'log.source.aws.s3.key.name': key,
        'cloud.log_forwarder': environ['FORWARDER_FUNCTION_ARN']
    }

def get_log_entry_size(log_entry):
    if isinstance(log_entry, dict):
        size = sys.getsizeof(json.dumps(log_entry).encode(ENCODING))
    elif isinstance(log_entry, bytes):
        size = sys.getsizeof(log_entry)
    else:
        logger.warning("Can't determine the size of the log entry")
        size = 0
    return size

def process_log_object(
    log_processing_rule,
    bucket: str,
    key: str,
    bucket_region: str,
    log_sinks: list,
    lambda_context,
    user_defined_annotations: dict = None,
    session: boto3.Session = None
):
    start_time = time.time()

    if not session:
        session = boto3._get_default_session()

    if user_defined_annotations is None:
        user_defined_annotations = {}

    s3_client = session.client('s3')
    log_obj_http_response = s3_client.get_object(Bucket=bucket, Key=key)
    log_obj_http_response_body = log_obj_http_response['Body']
    log_obj_http_response_content_encoding = log_obj_http_response.get('ContentEncoding', '').lower()

    logger.debug("s3://%s/%s Object size: %i KB", bucket, key, log_obj_http_response['ContentLength'] / 1024)

    if key.endswith('.gz') or log_obj_http_response_content_encoding == 'gzip':
        log_stream = gzip.GzipFile(mode='rb', fileobj=log_obj_http_response_body)
    else:
        log_stream = log_obj_http_response_body

    log_entries = log_stream if hasattr(log_stream, 'readline') else log_stream.iter_lines()

    context_log_attributes = {}
    context_log_attributes.update(user_defined_annotations)
    context_log_attributes.update(_get_context_log_attributes(bucket, key))

    for log_sink in log_sinks:
        log_sink.set_s3_source(bucket, key)

    num_log_entries = 0
    decompressed_log_object_size = 0

    for log_entry in log_entries:
        dt_log_message = {}
        if isinstance(log_entry, bytes):
            log_entry = log_entry.decode(ENCODING)
        if not log_entry or log_entry.startswith('#'):
            continue

        decompressed_log_object_size += len(log_entry.encode(ENCODING))
        parts = log_entry.split('\t')
        cloudfront_log_dict = dict(zip(cloudfront_fields, parts))

        dt_log_message['content'] = log_entry
        dt_log_message.update(context_log_attributes)

        # Map fields if available
        dt_log_message["http.status_code"] = cloudfront_log_dict.get("sc-status")
        dt_log_message["http.url.path"] = cloudfront_log_dict.get("cs-uri-stem")
        dt_log_message["user.agent"] = cloudfront_log_dict.get("cs(User-Agent)")
        dt_log_message["duration.ms"] = float(cloudfront_log_dict.get("time-taken", 0)) * 1000
        dt_log_message["bytes.sent"] = int(cloudfront_log_dict.get("sc-bytes", 0))
        dt_log_message["client.ip"] = cloudfront_log_dict.get("c-ip")
        dt_log_message["x-edge-location"] = cloudfront_log_dict.get("x-edge-location")
        dt_log_message["cloudfront.request_id"] = cloudfront_log_dict.get("x-edge-request-id")
        dt_log_message["aws.region"] = bucket_region

        for log_sink in log_sinks:
            log_sink.push(dt_log_message)

        num_log_entries += 1

        if num_log_entries % 1000 == 0 and lambda_context.get_remaining_time_in_millis() <= EXECUTION_REMAINING_TIME_LIMIT:
            raise NotEnoughExecutionTimeRemaining

    logger.info("Total CloudFront log entries processed: %s", str(num_log_entries))

    end_time = time.time()
    metrics.set_default_dimensions(dimensions={"bucket": bucket})
    metrics.add_metric(name='LogProcessingTime', unit=MetricUnit.Seconds, value=(end_time - start_time))
    metrics.add_metric(name='ReceivedUncompressedLogFileSize', unit=MetricUnit.Bytes, value=decompressed_log_object_size)
    metrics.add_metric(name='LogEntriesProcessed', unit=MetricUnit.Count, value=num_log_entries)

    return num_log_entries

class NotEnoughExecutionTimeRemaining(Exception):
    pass
