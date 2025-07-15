# 📦 Understanding How S3 → EventBridge → SQS → Lambda Wrapping Works

This document explains how an **S3 event notification**, when routed through **EventBridge** to **SQS**, and then to a **Lambda function**, gets **wrapped at each stage**. The goal is to clearly understand **where the original S3 event data is buried**, and how to extract it properly in your Lambda code.

---

## ✅ High-Level Flow Overview

```
[S3 Bucket]
   │
   │  (1) PutObject triggers
   ▼
[EventBridge (S3 → EventBridge enabled)]
   │
   │  (2) Matches a rule
   ▼
[EventBridge Rule Target → SQS]
   │
   │  (3) SQS receives EventBridge event as body
   ▼
[Lambda triggered by SQS]
   │
   │  (4) Parses SQS message body
   ▼
[Extracts S3 bucket & key from .detail.bucket.name / .detail.object.key]
```

---

## 🧱 Detailed Breakdown of Each Step

### 🔹 1. S3 → EventBridge Notification

When you enable **EventBridge notifications** on your bucket, every supported event (like `PutObject`) goes to EventBridge.

**Example S3-originated EventBridge event:**

```json
{
  "version": "0",
  "id": "abc123",
  "detail-type": "Object Created",
  "source": "aws.s3",
  "account": "123456789012",
  "time": "2025-07-15T20:15:35Z",
  "region": "us-east-1",
  "resources": ["arn:aws:s3:::my-bucket"],
  "detail": {
    "bucket": {
      "name": "my-bucket"
    },
    "object": {
      "key": "logs/filename.json.gz",
      "size": 2048
    },
    "request-id": "REQ123456789",
    "source-ip-address": "192.0.2.1",
    "reason": "PutObject"
  }
}
```

➡️ This is the **raw EventBridge message**.

---

### 🔹 2. EventBridge Rule → SQS

When EventBridge sends this event to an SQS queue, it **wraps the entire JSON as a string** in the `body` of the SQS message.

**SQS receives this format:**

```json
{
  "Records": [
    {
      "messageId": "...",
      "body": "{
        \"version\": \"0\",
        \"id\": \"abc123\",
        \"detail-type\": \"Object Created\",
        ...
        \"detail\": {
          \"bucket\": {
            \"name\": \"my-bucket\"
          },
          \"object\": {
            \"key\": \"logs/filename.json.gz\",
            \"size\": 2048
          }
        }
      }"
    }
  ]
}
```

💡 **Where is the original message?**
> **Inside `body` as a stringified JSON.**

---

### 🔹 3. Lambda Triggered by SQS

When the Lambda is triggered by SQS:

- The outer `event` object has:
```python
event = {
  "Records": [
    {
      "body": "{...JSON STRING...}"  # Stringified EventBridge event
    }
  ]
}
```

- You must parse it like this:
```python
import json

def lambda_handler(event, context):
    for record in event['Records']:
        body_str = record['body']
        eventbridge_event = json.loads(body_str)

        bucket = eventbridge_event['detail']['bucket']['name']
        key = eventbridge_event['detail']['object']['key']
        print(f"New file in {bucket}: {key}")
```

---

## 📌 Summary Table: Where Is the Original Message?

| Step | Location | Wrapping |
|------|----------|----------|
| S3 sends to EventBridge | As native EventBridge event | ✅ Fully structured JSON |
| EventBridge sends to SQS | Inside `body` string | ✅ JSON serialized to string |
| Lambda receives | `event['Records'][i]['body']` | ✅ Stringified JSON (needs `json.loads`) |
| Final access | `body.detail.bucket.name`, `body.detail.object.key` | ✅ After parsing string |

---

## 🧠 Key Insight

> The original S3 object info (bucket and key) lives in `event['Records'][i]['body']`, but you **must parse it from a string back into JSON** in your Lambda. This is the "buried" part.

---

Let me know if you need a **Lambda function that supports both EventBridge and native S3 → SQS formats**.