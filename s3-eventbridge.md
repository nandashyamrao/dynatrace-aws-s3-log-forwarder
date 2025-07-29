# 🛡️ S3 EventBridge Forwarding: `sf-infosec-cloudfront-logs` → `sf-ems-prod`

## 🎯 Objective

Forward S3 object creation events from the bucket **`sf-infosec-cloudfront-logs`** (owned by InfoSec) to the **default EventBridge bus** in the **`sf-ems-prod` account**, where the events are routed to an SQS queue and picked up by a Lambda that forwards logs to **Dynatrace**.

---

## 🖼️ Architecture Flow Diagram

```
📂 S3 Bucket: sf-infosec-cloudfront-logs (InfoSec Account)
         │
         ▼
🛎️ EventBridge Notification (enabled in S3)
         │
         ▼
📤 EventBridge Rule (in InfoSec)
- Matches: ObjectCreated + bucket name
- Target: EMS event bus (cross-account)
         │
         ▼
🎯 EventBridge Bus (in sf-ems-prod)
         │
         ▼
📨 SQS Queue: cloudfront-log-queue
         │
         ▼
🧠 Lambda: Dynatrace S3 Log Forwarder
         │
         ▼
🌐 Dynatrace Ingest API
```

---

## ✅ Terraform Configuration (InfoSec Account)

### 1. Create S3 Bucket & Enable EventBridge Notification

```hcl
resource "aws_s3_bucket" "cloudfront_logs" {
  bucket = "sf-infosec-cloudfront-logs"
}

resource "aws_s3_bucket_notification" "enable_eventbridge" {
  bucket = aws_s3_bucket.cloudfront_logs.id

  eventbridge {}
}
```

---

### 2. Create EventBridge Rule to Forward S3 Events

```hcl
resource "aws_cloudwatch_event_rule" "s3_cloudfront_rule" {
  name        = "Forward-CloudFront-to-EMS"
  description = "Forward S3 events from sf-infosec-cloudfront-logs to EMS"

  event_pattern = jsonencode({
    "source": ["aws.s3"],
    "detail-type": ["Object Created"],
    "detail": {
      "bucket": {
        "name": ["sf-infosec-cloudfront-logs"]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "to_ems_prod_bus" {
  rule      = aws_cloudwatch_event_rule.s3_cloudfront_rule.name
  arn       = "arn:aws:events:us-east-1:190731337505:event-bus/default"
  role_arn  = aws_iam_role.put_events_to_ems.arn
}
```

---

### 3. IAM Role for EventBridge to Assume

```hcl
resource "aws_iam_role" "put_events_to_ems" {
  name = "PutEventsToEMS"

  assume_role_policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "sts:AssumeRole",
        "Principal": {
          "Service": "events.amazonaws.com"
        },
        "Effect": "Allow"
      }
    ]
  })
}

resource "aws_iam_role_policy" "allow_put_events" {
  name = "AllowPutEventsToEMS"
  role = aws_iam_role.put_events_to_ems.id

  policy = jsonencode({
    "Version": "2012-10-17",
    "Statement": [
      {
        "Action": "events:PutEvents",
        "Effect": "Allow",
        "Resource": "arn:aws:events:us-east-1:190731337505:event-bus/default"
      }
    ]
  })
}
```

---

## ✅ Configuration (EMS Account – `sf-ems-prod`)

### 4. Allow InfoSec to Put Events into Default Bus

```hcl
resource "aws_cloudwatch_event_permission" "allow_infosec_to_put" {
  principal    = "<INFOSEC_ACCOUNT_ID>"
  statement_id = "AllowInfoSecToPutEvents"
  action       = "events:PutEvents"
}
```

> Replace `<INFOSEC_ACCOUNT_ID>` with the actual AWS account ID of the InfoSec source account.

---

## 📝 Summary

- S3 bucket `sf-infosec-cloudfront-logs` sends events via EventBridge.
- EventBridge rule in InfoSec forwards these to EMS default bus.
- EMS EventBridge rules match and deliver to SQS.
- Lambda reads from SQS, parses logs, and sends to Dynatrace.
