# 📘 Dynatrace AWS S3 Log Forwarder – `app.py` Handler Deep Dive

This document provides a detailed breakdown of the `app.py` Lambda handler used in the Dynatrace AWS S3 log forwarder. It explains the structure, logic, and flow used to receive SQS events (from EventBridge or SNS), match rules, and process logs.

---

## ✅ Purpose

The `lambda_handler()` in `app.py` is responsible for:

- Receiving SQS messages from SNS or EventBridge
- Parsing the event to extract the S3 bucket and key
- Matching log-forwarding and log-processing rules
- Invoking `process_log_object()` for valid log files
- Emitting metrics and safely handling failures

---

## 🧱 Imports and Setup

```python
import logging, os, json, boto3
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit
from log.processing import log_processing_rules, processing
from log.forwarding import log_forwarding_rules
from log.sinks import dynatrace
from utils import aws_appconfig_extension_helpers as aws_appconfig_helpers
from version import get_version
```

- Loads all required components: rules, sinks, AWS clients, metrics
- `get_version()` reports current forwarder version for logging

---

## 📍 Constants and Initialization

```python
logger = logging.getLogger()
logger.setLevel(os.getenv("LOGGING_LEVEL", "INFO"))
boto3_session = boto3.Session()
metrics = Metrics()
```

- Sets up logging and a reusable boto3 session
- Initializes a metrics object used for tracking event handling
- Also suppresses noisy Boto logs

---

## 🔁 Load Forwarding and Processing Rules

```python
defined_log_forwarding_rules, current_log_forwarding_rules_version = log_forwarding_rules.load()
defined_log_processing_rules, current_log_processing_rules_version = log_processing_rules.load()
```

- Loads AppConfig-based forwarding and processing rules at startup

---

## 🔄 reload_rules()

```python
def reload_rules(rules_type: str):
    ...
```

- Re-checks AppConfig to see if there is a new version of the rule configuration
- Reloads forwarding or processing rules if version has changed

---

## 🧠 Main Entry Point: lambda_handler()

```python
@metrics.log_metrics
def lambda_handler(event, context):
    ...
```

- Main function executed by Lambda on each trigger
- Decorated with `@log_metrics` to automatically publish CloudWatch metrics

---

### 🔽 1. Event Setup

```python
os.environ['FORWARDER_FUNCTION_ARN'] = context.invoked_function_arn
```

- Sets environment variable used for tagging logs with the function name

---

### 📦 2. SQS Message Loop

```python
for index, message in enumerate(event_records):
```

- Iterates over each message received from SQS
- Each message may contain SNS-wrapped or EventBridge-wrapped JSON payloads

---

### 🔍 3. Event Parsing (SNS or EventBridge)

```python
sns_message = json.loads(message['body'])
if 'Message' in sns_message:
    payload = json.loads(sns_message['Message'])  # SNS-wrapped
else:
    payload = sns_message  # direct EventBridge or S3
```

- Detects if the incoming message is an SNS-wrapped EventBridge payload
- Extracts the inner message for processing

---

### 🪣 4. Bucket and Key Extraction

Handles both formats:

```python
if 'detail' in payload:  # EventBridge
    bucket = payload['detail']['bucket']['name']
elif 'Records' in payload and 's3' in payload['Records'][0]:  # S3
    bucket = payload['Records'][0]['s3']['bucket']['name']
```

- Supports both EventBridge and direct S3 notifications
- Extracts `bucket`, `key`, `region`, and `source_context`

---

### 🧾 5. Forwarding Rule Match

```python
matched_log_forwarding_rule = log_forwarding_rules.get_matching_log_forwarding_rule(bucket, key, defined_log_forwarding_rules)
```

- Uses regex-based matching from AppConfig rules
- If no match, the message is dropped

---

### ⚙️ 6. Processing Rule Match

```python
matched_log_processing_rule = log_processing_rules.lookup_processing_rule(...)
```

- Uses `source`, `source_name`, and `key_name` to identify how to parse the file
- If not matched, the message is skipped

---

### 🎯 7. Destination Sink Resolution

```python
for sink_id in matched_log_forwarding_rule.sinks:
    log_object_destination_sinks.append(dynatrace_sinks[sink_id])
```

- Maps sink IDs to actual Dynatrace log sink instances

---

### 🚀 8. Call process_log_object()

```python
processing.process_log_object(...)
```

- Main handoff to the parsing logic in `processing.py`
- All matching logs go through this function

---

### ⏱ 9. Execution Time Safeguards

If `process_log_object()` raises `NotEnoughExecutionTimeRemaining`, remaining messages are preserved in `batchItemFailures`.

---

### 📊 10. Emit Final Metrics

```python
metrics.add_metric(name='LogProcessingFailures', unit=MetricUnit.Count, value=len(batch_item_failures['batchItemFailures']))
```

- Tracks how many messages failed in this invocation

---

## 🧩 Summary Table

| Section                 | Purpose                                  |
|-------------------------|------------------------------------------|
| Event parsing           | SNS-wrapped or direct EventBridge/S3     |
| Bucket/key extraction   | Reads S3 object path                     |
| Forwarding rule check   | Matches configured regex + source        |
| Processing rule check   | Determines how to parse the log format   |
| Sink resolution         | Maps to Dynatrace log ingestors          |
| Log processing call     | Invokes `process_log_object()`           |
| Timeout + retries       | Handles long-running files safely        |
| Metrics tracking        | CloudWatch observability                 |

---

## 📘 Execution Flow (Text Diagram)

```
START: lambda_handler()
        │
        ▼
[ Reload forwarding + processing rules if AppConfig updated ]
        │
        ▼
[ Loop through each SQS message ]
        │
        ▼
[ Unwrap SNS → EventBridge or S3 payload ]
        │
        ▼
[ Extract bucket, key, region from payload ]
        │
        ▼
[ Match against forwarding rules (AppConfig regex) ]
        │
        ▼
[ If no match → skip message ]
        │
        ▼
[ Match processing rule (based on source + key) ]
        │
        ▼
[ Resolve Dynatrace log sinks from rule ]
        │
        ▼
[ Call process_log_object(...) to parse + forward logs ]
        │
        ▼
[ Flush sinks + emit metrics ]
        │
        ▼
END → Return batchItemFailures for retry (if any)
```

---

## ✅ Best Practices

- Use `log.source`, `environment`, `team` annotations in AppConfig rules
- Prefer `bucket + prefix` rules to limit which logs are picked
- Enable AppConfig versioning to safely rollback changes
- Use structured logs + `@metrics.log_metrics` for CloudWatch visibility



---

## 🧩 Lambda Handler Flow – Text Diagram

```
START: lambda_handler()
        │
        ▼
[ Load and reload AppConfig rules (forwarding & processing) ]
        │
        ▼
[ Extract SQS 'Records' list from incoming event ]
        │
        ▼
┌──────────────────────────────────────────────────────────────┐
│ For each record in SQS:                                      │
│  • Clear previous sink states                                 │
│  • Parse message body (SNS-wrapped or EventBridge JSON)       │
│  • Identify if it's an EventBridge or S3-type event           │
└──────────────────────────────────────────────────────────────┘
        │
        ▼
[ Extract S3 bucket name, object key, region from payload ]
        │
        ▼
[ Match forwarding rule from AppConfig (based on bucket/key) ]
        │
        ├── If no match → log & skip
        ▼
[ Match processing rule (based on source & key) ]
        │
        ├── If no match → log & skip
        ▼
[ Identify Dynatrace sink(s) from forwarding rule ]
        │
        ▼
[ Call process_log_object() to parse and forward the log ]
        │
        ▼
[ Flush logs to all configured sinks ]
        │
        ▼
[ Track metrics: processed, skipped, failures ]
        │
        ▼
[ Return batchItemFailures for any unprocessed messages ]
        │
        ▼
END
```

---
