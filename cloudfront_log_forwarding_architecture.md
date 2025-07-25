
# 📦 CloudFront Log Forwarding Architecture (Text Diagram)

## ✅ Overview

This document outlines the architecture and data flow for forwarding **AWS CloudFront logs** from an S3 bucket to **Dynatrace**, using **SNS, SQS, and Lambda** for processing and enrichment.

---

## 🧱 Architecture Flow

```
1️⃣ CloudFront (Distribution)
   └── Logs are delivered to:
       S3 Bucket: sf-infosec-cloudfront-logs
       Object Key Format:
         cloudfront/<account_id>/<distribution>/<date>/<time>.gz
         e.g., cloudfront/123456789012/login-oidc-ui/EPDWCOJZCBQDAL.2025-07-24-22-e8d85d8.gz

2️⃣ Amazon S3 (sf-infosec-cloudfront-logs)
   └── S3 Event Notification on object creation
       ├── Event Type: s3:ObjectCreated:Put
       └── Target: SNS Topic (e.g., arn:aws:sns:us-east-1:...:cloudfront-log-topic)
       └── Payload:
           {
             "Records": [
               {
                 "eventTime": "...",
                 "s3": {
                   "bucket": { "name": "sf-infosec-cloudfront-logs" },
                   "object": { "key": "cloudfront/..." }
                 }
               }
             ]
           }

3️⃣ Amazon SNS Topic (cloudfront-log-topic)
   └── Publishes notification to subscribed SQS queue
       └── Message sent as plain JSON to SQS

4️⃣ Amazon SQS Queue (e.g., cloudfront-log-queue)
   └── Receives SNS message
   └── Payload is stored as one SQS message

5️⃣ AWS Lambda (Dynatrace Log Forwarder)
   └── Triggered by SQS
   └── Steps:
       🔹 Parses the SNS-wrapped S3 event
       🔹 Downloads the `.gz` file from S3
       🔹 Decompresses and parses CloudFront log lines (tab-delimited)
       🔹 Extracts fields like:
           - `date`, `time`, `x-edge-location`, `sc-status`, `cs-uri-stem`, etc.
           - Extracts distribution ID from S3 key (e.g., `EPDWCOJZCBQDAL`)
           - Parses AWS Account ID and maps alias (if rules configured)
       🔹 Enriches with metadata:
           - `log.source.aws.s3.bucket.name`
           - `log.source.aws.s3.key.name`
           - `log.cloudfront.distribution_id`
           - `aws.account.id`, `aws.account.alias` (from lookup)

6️⃣ Dynatrace (via Log Ingest API v2)
   └── Ingested log structure per record:
       {
         "timestamp": "...",
         "content": "CloudFront log line raw",
         "attributes": {
           "log.source.aws.s3.bucket.name": "sf-infosec-cloudfront-logs",
           "log.source.aws.s3.key.name": "...gz",
           "log.cloudfront.distribution_id": "EPDWCOJZCBQDAL",
           "sc-status": "200",
           "cs-uri-stem": "/index.html",
           "aws.account.id": "123456789012",
           "aws.account.alias": "aws-prod"
         }
       }
```

---

## 🔄 Data Flow Summary

| Stage         | Source                               | Destination                    | Payload Content                          |
|---------------|--------------------------------------|--------------------------------|-------------------------------------------|
| S3 Trigger    | CloudFront → S3                      | SNS                            | S3 Event JSON                             |
| SNS Fanout    | SNS                                  | SQS                            | Same S3 Event wrapped in SNS message      |
| SQS Trigger   | SQS                                  | Lambda                         | Wrapped SNS message with original S3 info |
| Lambda        | Lambda                               | Dynatrace                      | Parsed & enriched CloudFront logs         |
