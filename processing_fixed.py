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
