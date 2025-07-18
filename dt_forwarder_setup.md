# 🛡️ InfoSec → EMS Log Forwarding via EventBridge (Full Documentation with Terraform)

This document defines the complete Terraform configuration and AWS account mappings to enable **S3 EventBridge log forwarding** from the InfoSec account to EMS environments using **Amazon EventBridge** (not CloudWatch).

---

## 📌 Key AWS Account IDs

| Purpose        | AWS Account Name | Account ID     |
|----------------|------------------|----------------|
| Source         | InfoSec          | `808693921418` |
| Destination    | EMS Prod         | `125232492988` |
| Destination    | EMS Test         | `351454108853` |

---

## 📦 S3 Buckets and EMS Target Buses

| S3 Bucket Name                              | EMS Target Account | Target Event Bus ARN                                              |
|---------------------------------------------|---------------------|-------------------------------------------------------------------|
| `sf-prod-event-trail`                       | sf-ems-prod         | `arn:aws:events:us-east-1:125232492988:event-bus/default`         |
| `aws-waf-logs-sf-mgmt-prod-us-east-1`       | sf-ems-prod         | `arn:aws:events:us-east-1:125232492988:event-bus/default`         |
| `sf-infosec-cloudfront-logs`                | sf-ems-prod         | `arn:aws:events:us-east-1:125232492988:event-bus/default`         |
| `sf-test-event-trail`                       | sf-ems-test         | `arn:aws:events:us-east-1:351454108853:event-bus/default`         |

---

## 🖼️ Architecture Flow (Text Diagram)

```
          InfoSec AWS Account (808693921418)
          ┌─────────────────────────────────────┐
          │ S3 Buckets:                         │
          │  - sf-prod-event-trail              │
          │  - sf-test-event-trail              │
          │  - aws-waf-logs-sf-mgmt-prod-us-east-1 │
          │  - sf-infosec-cloudfront-logs       │
          └────────────┬────────────────────────┘
                       │
                       ▼ (EventBridge enabled in S3 bucket)
          ┌─────────────────────────────────────┐
          │ EventBridge Rule (InfoSec)          │
          │ - Matches "Object Created" events   │
          │ - Filters by bucket name            │
          └────────────┬────────────────────────┘
                       │
                       ▼
          ┌─────────────────────────────────────┐
          │ EventBridge Target (Cross-Account)  │
          │ - EMS PROD Bus (125232492988)       │
          │ - EMS TEST Bus (351454108853)       │
          └────────────┬────────────────────────┘
                       │
                       ▼
          EMS Account (default event bus receives)
          ┌─────────────────────────────────────┐
          │ EventBridge Rule (in EMS)           │
          │ - Sends to SQS Queue or Lambda      │
          └────────────┬────────────────────────┘
                       ▼
          ┌─────────────────────────────────────┐
          │ Dynatrace S3 Forwarder Lambda       │
          │ - Pulls from SQS                    │
          │ - Sends to Dynatrace API            │
          └─────────────────────────────────────┘
```

---

## ✅ Terraform Configuration

```hcl
// -------------------------------
// Terraform: InfoSec EventBridge Forwarding to EMS
// -------------------------------

variable "region" {
  default = "us-east-1"
}

provider "aws" {
  region = var.region
}

// 1. S3 EventBridge Notification

resource "aws_s3_bucket_notification" "enable_eventbridge_notifications" {
  for_each = toset([
    "sf-prod-event-trail",
    "sf-test-event-trail",
    "aws-waf-logs-sf-mgmt-prod-us-east-1",
    "sf-infosec-cloudfront-logs"
  ])

  bucket = each.key

  eventbridge {}
}

// 2. EventBridge Rules & Targets

resource "aws_cloudwatch_event_rule" "s3_logs_to_ems_prod" {
  name = "forward-s3-logs-to-ems-prod"
  event_pattern = jsonencode({
    "source": ["aws.s3"],
    "detail-type": ["Object Created"],
    "detail": {
      "bucket": {
        "name": [
          "sf-prod-event-trail",
          "aws-waf-logs-sf-mgmt-prod-us-east-1",
          "sf-infosec-cloudfront-logs"
        ]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "target_ems_prod" {
  rule     = aws_cloudwatch_event_rule.s3_logs_to_ems_prod.name
  arn      = "arn:aws:events:us-east-1:125232492988:event-bus/default"
  role_arn = aws_iam_role.allow_put_events_to_ems.arn
}

resource "aws_cloudwatch_event_rule" "s3_logs_to_ems_test" {
  name = "forward-s3-logs-to-ems-test"
  event_pattern = jsonencode({
    "source": ["aws.s3"],
    "detail-type": ["Object Created"],
    "detail": {
      "bucket": {
        "name": ["sf-test-event-trail"]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "target_ems_test" {
  rule     = aws_cloudwatch_event_rule.s3_logs_to_ems_test.name
  arn      = "arn:aws:events:us-east-1:351454108853:event-bus/default"
  role_arn = aws_iam_role.allow_put_events_to_ems.arn
}

// 3. IAM Role for PutEvents

resource "aws_iam_role" "allow_put_events_to_ems" {
  name = "AllowPutEventsToEMS"

  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy" "allow_put_events_policy" {
  name = "AllowPutEventsPolicy"
  role = aws_iam_role.allow_put_events_to_ems.id

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": "events:PutEvents",
        "Resource": [
          "arn:aws:events:us-east-1:125232492988:event-bus/default",
          "arn:aws:events:us-east-1:351454108853:event-bus/default"
        ]
      }
    ]
  })
}
```

---

## 🧠 Terraform Naming Note

Although the resource types begin with `cloudwatch`, they actually configure **EventBridge**:

| Terraform Resource                   | Manages                        |
|--------------------------------------|--------------------------------|
| `aws_cloudwatch_event_rule`          | EventBridge **Rule**           |
| `aws_cloudwatch_event_target`        | EventBridge **Target**         |
| `aws_cloudwatch_event_permission`    | Cross-account EventBridge auth |
