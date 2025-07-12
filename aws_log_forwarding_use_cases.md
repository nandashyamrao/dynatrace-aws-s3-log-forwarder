
# 📘 AWS Log Forwarding: Dual Use Case Architecture

This document explains two real-world AWS log ingestion use cases handled by a single Lambda forwarder function. It describes how messages are wrapped and unwrapped from different AWS sources.

---

## ✅ Use Case 1: CloudTrail → S3 → SNS → SQS → Lambda

### 🏗 Architecture Flow

```
📄 CloudTrail Event
   ↓
📦 S3 Bucket (CloudTrail writes log file)
   ↓
📣 SNS Topic (triggered on PutObject)
   ↓
📬 SQS Queue (subscribed to SNS)
   ↓
🧠 Lambda Function (Dynatrace forwarder)
```

### 🧾 Payload Format (Step by Step)

1. **S3 Event**
```json
{
  "Records": [
    {
      "eventSource": "aws:s3",
      "s3": {
        "bucket": { "name": "cloudtrail-logs" },
        "object": { "key": "AWSLogs/.../CloudTrail/..." }
      }
    }
  ]
}
```

2. **SNS Wraps It**
```json
{
  "Type": "Notification",
  "Message": "{ \"Records\": [ { ... } ] }"
}
```

3. **SQS Wraps SNS**
```json
{
  "body": "{ \"Type\": \"Notification\", \"Message\": \"{ \\\"Records\\\": [ ... ] }\" }"
}
```

### 🔓 Lambda Handling Logic

```python
sns_message = json.loads(message['body'])
payload = json.loads(sns_message['Message'])  # unwrap SNS
bucket_name = payload['Records'][0]['s3']['bucket']['name']
key_name = payload['Records'][0]['s3']['object']['key']
```

---

## ✅ Use Case 2: S3 PutObject → EventBridge → SQS → Lambda

### 🏗 Architecture Flow

```
📦 S3 Bucket (object uploaded)
   ↓
📅 EventBridge Rule (triggers on PutObject)
   ↓
📬 SQS Queue (target of EventBridge rule)
   ↓
🧠 Lambda Function (Dynatrace forwarder)
```

### 🧾 Payload Format (EventBridge)

```json
{
  "source": "aws.s3",
  "region": "us-east-1",
  "detail": {
    "bucket": { "name": "app-logs" },
    "object": { "key": "logs/2025/07/11/app.json" },
    "requester": "..."
  }
}
```

### 🔓 Lambda Handling Logic

```python
payload = json.loads(message['body'])  # no SNS layer
bucket_name = payload['detail']['bucket']['name']
key_name = payload['detail']['object']['key']
```

---

## 🔄 Comparison Table

| Feature                     | Use Case 1: CloudTrail + SNS       | Use Case 2: S3 + EventBridge         |
|----------------------------|-------------------------------------|--------------------------------------|
| Trigger Type               | SNS → SQS                           | EventBridge → SQS                    |
| Payload Structure          | SNS → S3 → JSON                     | Direct JSON                          |
| Unwrapping Required        | ✅ SNS → Message → Records          | 🚫 Only message['body']              |
| Detection in Lambda        | `'Records' in payload`              | `'detail' in payload`                |

---

## 🧠 Unified Lambda Logic Summary

```python
sns_message = json.loads(message['body'])

if 'Message' in sns_message:
    payload = json.loads(sns_message['Message'])  # SNS-wrapped
else:
    payload = sns_message  # EventBridge

if 'detail' in payload:
    # EventBridge style
elif 'Records' in payload and 's3' in payload['Records'][0]:
    # S3 via SNS
else:
    logger.warning("Unsupported format")
```

---

## 📌 Visual Architecture

![CloudTrail and EventBridge Flow](https://user-images.githubusercontent.com/123456789/diagram-usecase-flow.png)

> 📝 *Replace with your actual architecture diagram if needed.*

---
