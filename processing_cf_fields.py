# Copyright 2022 Dynatrace LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#      https://www.apache.org/licenses/LICENSE-2.0

#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import logging
from os import environ
import sys
import time
import json
import gzip
import boto3
import jmespath
from datetime import datetime
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
import jsonslicer

from log.processing.log_processing_rule import LogProcessingRule
from utils.helpers import ENCODING

logger = logging.getLogger()
metrics = Metrics()

EXECUTION_REMAINING_TIME_LIMIT = 10000

def _get_context_log_attributes(bucket: str, key: str):
    return {
        'log.source.aws.s3.bucket.name': bucket,
        'log.source.aws.s3.key.name': key,
        'cloud.log_forwarder': environ.get('FORWARDER_FUNCTION_ARN', 'undefined')
    }

def get_jsonslicer_path_prefix_from_jmespath_path(jmespath_expr: str):
    jsonslicer_tuple = tuple(jmespath_expr.split('.'))
    jsonslicer_tuple += (None,)
    return jsonslicer_tuple

def get_log_entry_size(log_entry):
    if isinstance(log_entry, dict):
        size = sys.getsizeof(json.dumps(log_entry).encode(ENCODING))
    elif isinstance(log_entry, bytes):
        size = sys.getsizeof(log_entry)
    else:
        logger.warning("Can't determine the size of the log entry")
        size = 0
    return size

def parse_cloudfront_log_line(log_line: str) -> dict:
    fields = log_line.strip().split("\t")
    if len(fields) < 33:
        raise ValueError(f"Expected 33 fields, got {len(fields)}")

    try:
        return {
            "timestamp": datetime.strptime(f"{fields[0]} {fields[1]}", "%Y-%m-%d %H:%M:%S").isoformat() + "Z",
            "edge_location": fields[2],
            "sc_bytes": int(fields[3]),
            "client_ip": fields[4],
            "method": fields[5],
            "host": fields[6],
            "uri_stem": fields[7],
            "status_code": int(fields[8]),
            "referer": fields[9],
            "user_agent": fields[10],
            "uri_query": fields[11],
            "cookie": fields[12],
            "edge_result_type": fields[13],
            "request_id": fields[14],
            "host_header": fields[15],
            "protocol": fields[16],
            "cs_bytes": int(fields[17]),
            "time_taken": float(fields[18]),
            "forwarded_for": fields[19],
            "ssl_protocol": fields[20],
            "ssl_cipher": fields[21],
            "response_result_type": fields[22],
            "protocol_version": fields[23],
            "fle_status": fields[24],
            "fle_encrypted_fields": int(fields[25]) if fields[25].isdigit() else None,
            "c_port": int(fields[26]),
            "time_to_first_byte": float(fields[27]),
            "detailed_result_type": fields[28],
            "content_type": fields[29],
            "content_len": int(fields[30]) if fields[30].isdigit() else None,
            "range_start": int(fields[31]) if fields[31].isdigit() else None,
            "range_end": int(fields[32]) if fields[32].isdigit() else None,
        }
    except Exception as e:
        logger.warning("Failed to parse CloudFront log line: %s", e)
        return {"content": log_line}

def process_log_object(log_processing_rule: LogProcessingRule, bucket: str, key: str, bucket_region: str, log_sinks: list,
                       lambda_context, user_defined_annotations: dict = None, session: boto3.Session = None):
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

    if log_processing_rule.log_format == 'json':
        if log_processing_rule.log_entries_key is not None:
            json_slicer_path_prefix = get_jsonslicer_path_prefix_from_jmespath_path(log_processing_rule.log_entries_key)
        else:
            json_slicer_path_prefix = (None,)
        log_entries = jsonslicer.JsonSlicer(log_stream, json_slicer_path_prefix)

    elif log_processing_rule.log_format == 'json_stream':
        if log_processing_rule.name == "cwl_to_fh":
            json_stream = gzip.GzipFile(mode='rb', fileobj=log_stream)
        else:
            json_stream = log_stream
        json_slicer_path_prefix = []
        log_entries = jsonslicer.JsonSlicer(json_stream, json_slicer_path_prefix, yajl_allow_multiple_values=True)

    elif log_processing_rule.log_format == 'text':
        if isinstance(log_stream, gzip.GzipFile):
            log_entries = log_stream
        else:
            log_entries = log_stream.iter_lines()
    else:
        log_entries = []

    context_log_attributes = {}
    context_log_attributes.update(user_defined_annotations)
    context_log_attributes.update(_get_context_log_attributes(bucket, key))
    context_log_attributes.update(log_processing_rule.get_attributes_from_s3_key_name(key))
    context_log_attributes.update(log_processing_rule.get_processing_log_annotations())

    for log_sink in log_sinks:
        log_sink.set_s3_source(bucket, key)

    num_log_entries = 0
    decompressed_log_object_size = 0

    for log_entry in log_entries:
        dt_log_message = {}
        decompressed_log_object_size += get_log_entry_size(log_entry)

        if log_processing_rule.log_format == 'text':
            if num_log_entries + 1 <= log_processing_rule.skip_header_lines:
                num_log_entries += 1
                continue
            if isinstance(log_entry, bytes):
                log_entry = log_entry.decode(ENCODING)
                if log_entry == '':
                    logger.debug('skipping empty log line')
                    continue
                try:
                    structured_record = parse_cloudfront_log_line(log_entry)
                    dt_log_message.update(structured_record)
                except Exception as e:
                    logger.warning("Falling back to raw content due to parse error: %s", e)
                    dt_log_message['content'] = log_entry
            else:
                metrics.add_metric(name='FilesWithInvalidLogEntries', unit=MetricUnit.Count, value=1)
                raise ValueError(f'Log entry was expected to be bytes, but is {type(log_entry)}')

        elif log_processing_rule.log_format in ['json', 'json_stream'] and not log_processing_rule.log_entries_key:
            if isinstance(log_entry, dict):
                dt_log_message['content'] = json.dumps(log_entry)
            else:
                metrics.add_metric(name='FilesWithInvalidLogEntries', unit=MetricUnit.Count, value=1)
                raise ValueError(f'Log entry was expected to be dict, but is {type(log_entry)}')

        dt_log_message.update(context_log_attributes)
        dt_log_message.update(log_processing_rule.get_extracted_log_attributes(log_entry))
        if "aws.region" not in dt_log_message:
            dt_log_message['aws.region'] = bucket_region

        for log_sink in log_sinks:
            log_sink.push(dt_log_message)

        num_log_entries += 1

        if num_log_entries % 1000 == 0:
            logger.debug("Processed %s entries", str(num_log_entries))
            if lambda_context.get_remaining_time_in_millis() <= EXECUTION_REMAINING_TIME_LIMIT:
                raise NotEnoughExecutionTimeRemaining

    logger.info("Total log entries processed: %s", str(num_log_entries))

    end_time = time.time()
    metrics.add_metric(name='LogProcessingTime', unit=MetricUnit.Seconds, value=(end_time - start_time))
    metrics.add_metric(name='ReceivedUncompressedLogFileSize', unit=MetricUnit.Bytes, value=decompressed_log_object_size)

    return num_log_entries

class NotEnoughExecutionTimeRemaining(Exception):
    pass
