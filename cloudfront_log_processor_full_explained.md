# 📘 CloudFront Log Processor – `process_log_object()` Deep Dive

This Python code defines a CloudFront log processor used in the Dynatrace AWS S3 log forwarder Lambda function. It downloads, parses, enriches, and forwards CloudFront logs from S3 to Dynatrace — one structured record at a time.

Here’s a detailed line-by-line breakdown with explanations grouped by logical sections:

---

## 🧱 Imports and Setup

```python
import logging, gzip, json, boto3, sys, time
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from log.processing.log_processing_rule import LogProcessingRule
from utils.helpers import ENCODING
```

- **Standard imports**: Used for log processing, AWS access, and metric reporting.
- **Metrics**: Used to emit custom CloudWatch metrics for observability.
- **LogProcessingRule**: Provides per-source settings like `log_format`, `skip_header_lines`, etc.
- **ENCODING**: Usually `'utf-8'`, imported from helpers.

---

## 📍 Constants and Logging Setup

```python
logger = logging.getLogger()
metrics = Metrics()
EXECUTION_REMAINING_TIME_LIMIT = 10000
```

- `logger`: Standard logger for writing to CloudWatch logs.
- `metrics`: Used to track performance metrics (processing time, size, count).
- `EXECUTION_REMAINING_TIME_LIMIT`: Defines a 10-second safety margin to avoid timeout before Lambda ends.

---

## 🧩 Helper Functions

### `_get_context_log_attributes`

```python
def _get_context_log_attributes(bucket: str, key: str):
    return {
        'log.source.aws.s3.bucket.name': bucket,
        'log.source.aws.s3.key.name': key,
        'cloud.log_forwarder': os.environ['FORWARDER_FUNCTION_ARN']
    }
```

Returns metadata about the source log file — bucket, key, and Lambda name — for tagging logs in Dynatrace.

---

### `normalize_field_name`

```python
def normalize_field_name(name: str) -> str:
    return name.lower().replace('-', '_').replace('.', '_')
```

Ensures log field names are compatible with Dynatrace by replacing `-` and `.` with underscores (e.g., `cs-uri-stem` → `cs_uri_stem`).

---

## 🧠 Main Function: `process_log_object(...)`

This function is the heart of CloudFront log handling.

---

### 🔽 1. Setup and S3 Download

```python
if not session:
    session = boto3.Session()
s3_client = session.client('s3')
obj = s3_client.get_object(Bucket=bucket, Key=key)
body = obj['Body']
```

- Uses Boto3 to download the log file from S3.

---

### 🗜 2. Decompression

```python
if key.endswith('.gz'):
    log_stream = gzip.GzipFile(fileobj=body)
else:
    log_stream = body
```

- If it’s a `.gz` file, decompress it
- Else, process it as a plain text stream

---

### 🏷 3. Build Metadata Context

```python
context_log_attributes.update(user_defined_annotations)
context_log_attributes.update(_get_context_log_attributes(bucket, key))
context_log_attributes.update(log_processing_rule.get_attributes_from_s3_key_name(key))
context_log_attributes.update(log_processing_rule.get_processing_log_annotations())
```

Combines:
- Forwarding rule annotations
- Static S3 metadata (bucket/key)
- Dynamic attributes from key name or rule

---

### 🎯 4. Sinks Setup

```python
for log_sink in log_sinks:
    log_sink.set_s3_source(bucket, key)
```

- Prepares each Dynatrace sink to associate the source info

---

### 🔁 5. Log Parsing Loop

```python
for line in log_stream:
```

- Reads one line at a time from the log stream
- Each line is decoded, stripped, and processed

---

### 📜 6. Header Handling

```python
if line.startswith('#'):
    if line.lower().startswith('# fields:'):
        cloudfront_fields = [normalize_field_name(f) for f in line.split(":", 1)[1].strip().split()]
```

- Detects `#Fields:` line (2nd line in CloudFront logs)
- Extracts and normalizes field names like `cs_uri_stem`, `sc_status`, etc.

---

### 🛑 7. Header Skipping

```python
if log_processing_rule.skip_header_lines and num_processed < log_processing_rule.skip_header_lines:
    num_processed += 1
    continue
```

- Skips the first 2 lines (version + fields), as instructed by `skip_header_lines`

---

### 🔍 8. Log Line Parsing

```python
values = line.split('\t')
...
for i, field_name in enumerate(cloudfront_fields):
    if i < len(values):
        log_entry[field_name] = values[i]
```

- Splits the log line by tab
- Maps each field name to the corresponding value

---

### 🏷 9. Add Metadata

```python
log_entry.update(context_log_attributes)
log_entry['content'] = line
if "aws.region" not in log_entry:
    log_entry["aws.region"] = bucket_region
```

- Adds annotations (e.g., team, region, bucket)
- `content`: raw line preserved optionally for audit/debug

---

### 🚀 10. Push to Dynatrace

```python
for log_sink in log_sinks:
    log_sink.push(log_entry)
```

- Sends the structured log to Dynatrace via Log Ingest API

---

### ⏱ 11. Timeout Safety Check

```python
if num_processed % 1000 == 0 and lambda_context.get_remaining_time_in_millis() < EXECUTION_REMAINING_TIME_LIMIT:
    raise NotEnoughExecutionTimeRemaining
```

- If you’ve processed 1000+ lines and Lambda is near timeout, safely exit

---

### 📊 12. Metrics and Logging

```python
logger.info(...)
metrics.add_metric(...)
```

- Tracks performance for monitoring in CloudWatch

---

### 🚫 Class: NotEnoughExecutionTimeRemaining

```python
class NotEnoughExecutionTimeRemaining(Exception):
    pass
```

- Raised to exit early and avoid Lambda timeout

---

## 🧩 Summary Table

| Section             | Purpose                             |
|---------------------|-------------------------------------|
| Download from S3    | Uses Boto3 to stream file           |
| Decompress          | Handles `.gz` logs                  |
| Detect `#Fields:`   | Dynamically parses CloudFront headers |
| Build structured log| Maps values to field names          |
| Add metadata        | Includes bucket, region, annotations|
| Send to Dynatrace   | One structured event per line       |
| Track metrics       | For observability                   |
| Handle timeout      | Protects large files from failing   |

---

## 🧩 Execution Flow – Text Diagram

```
START: process_log_object()
        │
        ▼
[ Create or reuse boto3 S3 session ]
        │
        ▼
[ Download object from S3 using bucket + key ]
        │
        ▼
[ Decompress if .gz else use raw stream ]
        │
        ▼
[ Build context attributes (bucket, key, annotations) ]
        │
        ▼
[ Initialize Dynatrace log sinks ]
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ For each line in the stream:                                │
│  • Decode & strip                                            │
│  • Skip empty lines                                          │
│  • If '#Fields:', parse and normalize field names            │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ For each valid log line:                                    │
│  • Split line by tab                                         │
│  • Map values to parsed field names                          │
│  • Add context metadata (region, bucket, annotations)        │
│  • Add original line as 'content' (optional)                 │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
[ Push structured log entry to each Dynatrace log sink ]
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│ Every 1000 lines:                                            │
│  • Check Lambda remaining time                               │
│  • If < 10 seconds → raise NotEnoughExecutionTimeRemaining  │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
[ Log total lines processed + emit metrics ]
        │
        ▼
        END → return num_processed
```
