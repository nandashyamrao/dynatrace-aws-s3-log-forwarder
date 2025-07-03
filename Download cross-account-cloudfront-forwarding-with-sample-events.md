
# ✅ Cross-Account CloudFront Log Forwarding to Dynatrace via EventBridge & SQS

## 🧭 Objective

Forward CloudFront S3 log object events from **Account B** ➜ into **Account A**, where a centralized Dynatrace Lambda forwarder processes the logs.

---

## 🧱 Component Roles

| Component | 🅰️ Account A (Forwarder) | 🅱️ Account B (S3 Logs) |
|-----------|--------------------------|------------------------|
| 🪣 S3 Log Bucket | ❌ | ✅ Stores CloudFront logs |
| 📡 EventBridge Rule | ❌ | ✅ Sends S3 PUT events to A |
| 🐍 Lambda Forwarder | ✅ | ❌ |
| 🔐 IAM Role Permissions | ✅ | ✅ |
| 📄 Template Used | [`eventbridge-cross-region-or-account-forward-rules.yaml`](https://github.com/dynatrace-oss/dynatrace-aws-s3-log-forwarder/blob/main/eventbridge-cross-region-or-account-forward-rules.yaml) | ✅ |

---

## 🔄 Data Flow Overview

```text
[1] CloudFront logs written ➜ [🪣 S3 Bucket in Account B]
       ↓
[2] S3 triggers 📡 EventBridge event in Account B
       ↓
[3] EventBridge forwards event ➜ 🅰️ Account A EventBus
       ↓
[4] 📨 SQS Queue in Account A receives the message
       ↓
[5] Lambda in Account A is triggered
       ↓
[6] Lambda fetches object from Account B's S3
       ↓
[7] Lambda parses and sends logs to Dynatrace
```

---

## 🛠️ Setup Guide

### 🟪 Step 1: Account B — S3 Bucket Notification

Enable EventBridge notifications:

```bash
aws s3api put-bucket-notification-configuration \
  --bucket <your-cloudfront-logs-bucket> \
  --notification-configuration '{{"EventBridgeConfiguration": {{}}}}'
```

---

### 🟪 Step 2: Account B — Deploy the EventBridge Rule Template

Use the Dynatrace CloudFormation template:

```bash
aws cloudformation deploy \
  --template-file eventbridge-cross-region-or-account-forward-rules.yaml \
  --stack-name forward-to-account-a-stack \
  --parameter-overrides \
    DestinationAccountId=<AccountA_ID> \
    EventBusArn=arn:aws:events:<region>:<AccountA_ID>:event-bus/default \
    RuleName=ForwardToAccountA \
    SourceBucketName=<your-bucket-name> \
  --capabilities CAPABILITY_NAMED_IAM
```

---

### 🟩 Step 3: Account A — Grant EventBridge Permission

Attach this permission to Account A's EventBridge default bus:

```json
{{
  "Sid": "AllowAccountBToPutEvents",
  "Effect": "Allow",
  "Principal": {{
    "AWS": "arn:aws:iam::<ACCOUNT_B_ID>:root"
  }},
  "Action": "events:PutEvents",
  "Resource": "arn:aws:events:<region>:<ACCOUNT_A_ID>:event-bus/default"
}}
```

---

### 🟩 Step 4: Account A — SQS Queue Setup

1. Create an SQS queue.
2. Add a policy to allow EventBridge from Account B:

```json
{{
  "Version": "2012-10-17",
  "Statement": [
    {{
      "Sid": "AllowEventBridgeFromAccountB",
      "Effect": "Allow",
      "Principal": {{
        "Service": "events.amazonaws.com"
      }},
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:<region>:<ACCOUNT_A_ID>:<queue-name>",
      "Condition": {{
        "ArnEquals": {{
          "aws:SourceArn": "arn:aws:events:<region>:<ACCOUNT_B_ID>:rule/<RuleName>"
        }}
      }}
    }}
  ]
}}
```

---

### 🟩 Step 5: Account A — Lambda Setup

Lambda must:

- Be triggered by the SQS queue
- Extract `bucket` and `key` from message
- Read from S3 in Account B (via cross-account IAM role)
- Forward logs to Dynatrace

IAM Role should include:

- `s3:GetObject`, `s3:ListBucket` for Account B’s S3
- `sqs:ReceiveMessage`, `DeleteMessage` for SQS

---

## ✅ Final Architecture Diagram (Text)

```text
🅱️ Account B:
[CloudFront] ➜ [S3 Bucket] ➜ [EventBridge Rule] ➜ [Account A EventBus]

🅰️ Account A:
[EventBus] ➜ [SQS Queue] ➜ [Lambda] ➜ [Dynatrace]
```

---

## 📋 Summary Checklist

| Component | Setup |
|-----------|-------|
| 🪣 S3 Bucket (B) | CloudFront logs written here |
| 📡 EventBridge Rule (B) | Forwards PUT events |
| 📬 SQS Queue (A) | Receives forwarded messages |
| 🐍 Lambda (A) | Processes and sends to Dynatrace |
| 🔐 IAM Role | Cross-account S3 + SQS access |
| 📜 SQS Policy | Allows B’s EventBridge to write |

---

Let me know if you'd like Terraform equivalents or a zipped bundle for these!


# 📦 Sample Messages in the Flow

## `S3 PUT Event (Account B)`
```json
{
  "version": "0",
  "id": "abc12345",
  "detail-type": "Object Created",
  "source": "aws.s3",
  "account": "ACCOUNT_B",
  "detail": {
    "bucket": {
      "name": "cf-logs-bucket-b"
    },
    "object": {
      "key": "cloudfront/E12345678.gz"
    }
  }
}
```

## `EventBridge Rule Match (Account B)`
```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {
      "name": ["cf-logs-bucket-b"]
    },
    "object": {
      "key": [{"prefix": "cloudfront/"}]
    }
  }
}
```

## `Forwarded Event to Account A’s Event Bus`
```json
{
  "account": "ACCOUNT_A",
  "region": "us-east-1",
  "resources": ["arn:aws:s3:::cf-logs-bucket-b/cloudfront/E12345678.gz"],
  "source": "aws.s3",
  "detail-type": "Object Created",
  "detail": {
    "bucket": {
      "name": "cf-logs-bucket-b"
    },
    "object": {
      "key": "cloudfront/E12345678.gz"
    }
  }
}
```

## `SQS Message Triggering Lambda (Account A)`
```json
{
  "Records": [
    {
      "body": "{\"version\":\"0\",\"id\":\"abc12345\",\"detail-type\":\"Object Created\",\"source\":\"aws.s3\",\"account\":\"ACCOUNT_B\",\"detail\":{\"bucket\":{\"name\":\"cf-logs-bucket-b\"},\"object\":{\"key\":\"cloudfront/E12345678.gz\"}}}"
    }
  ]
}
```
