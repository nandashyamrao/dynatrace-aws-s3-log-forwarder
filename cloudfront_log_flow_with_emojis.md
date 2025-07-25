
# 🌐 CloudFront Log Flow to Dynatrace (with Emojis)

This document illustrates how **CloudFront logs** are processed and forwarded to **Dynatrace**, highlighting each component’s role in the flow with activity emojis 🚀⚙️📥📤

---

## 🚦 Full Component Flow: CloudFront → S3 → SNS → SQS → Lambda → Dynatrace

```
📡 1. CloudFront (🚀 Generates Logs)
   └── Delivers logs to:
       🪣 S3 Bucket: sf-infosec-cloudfront-logs
       📄 Object Format: 
           cloudfront/<account_id>/<distribution>/<date>/<timestamp>.gz

📥 2. Amazon S3 (📦 Receives Log File)
   └── Trigger: ObjectCreated:Put event
   └── 🔔 Sends Event Notification to:
       📣 SNS Topic: cloudfront-log-topic
       📤 Payload:
           {
             "Records": [
               {
                 "s3": {
                   "bucket": { "name": "sf-infosec-cloudfront-logs" },
                   "object": { "key": "cloudfront/..." }
                 }
               }
             ]
           }

📣 3. SNS Topic (📤 Broadcasts Event)
   └── Fan-out pattern to one or more subscribers
   └── Subscribed:
       📬 SQS Queue: cloudfront-log-queue

📬 4. Amazon SQS (📨 Stores Notification)
   └── Receives SNS message
   └── Stores it as a message

⚙️ 5. AWS Lambda: Dynatrace Log Forwarder (Triggered by SQS)
   └── 📥 Reads message from SQS
   └── 🔍 Parses SNS-wrapped S3 event
   └── 📂 Downloads .gz log file from S3
   └── 🧹 Decompresses & parses CloudFront log lines
   └── 🧠 Enriches with:
       - log.source.aws.s3.bucket.name
       - log.cloudfront.distribution_id
       - aws.account.id → aws.account.alias
   └── 📤 Forwards structured log lines to Dynatrace

🧠 6. Dynatrace (📊 Observability Platform)
   └── Receives logs via:
       🔗 Log Ingest API v2
   └── Example Enriched Log Entry:
       {
         "timestamp": "...",
         "content": "...",
         "attributes": {
           "sc-status": "200",
           "cs-uri-stem": "/index.html",
           "log.cloudfront.distribution_id": "EPDWCOJZCBQDAL",
           "aws.account.id": "123456789012",
           "aws.account.alias": "aws-prod"
         }
       }
```

---

## 🔄 Summary Table: Data Flow per Component

| 🔢 Step | Component         | Role Description                           | Emoji | Output Sent To        |
|--------|-------------------|---------------------------------------------|-------|------------------------|
| 1      | CloudFront        | Generates access logs                        | 📡🚀  | Amazon S3              |
| 2      | Amazon S3         | Stores logs and sends event                 | 🪣📥  | SNS Topic              |
| 3      | SNS Topic         | Publishes event to subscribers              | 📣📤  | SQS Queue              |
| 4      | SQS Queue         | Queues SNS notification                     | 📬📨  | Lambda Trigger         |
| 5      | Lambda Function   | Parses, enriches, and forwards logs         | ⚙️📂🧠 | Dynatrace API          |
| 6      | Dynatrace         | Stores searchable, enriched log entries     | 🧠📊  | Dynatrace Logs Storage |

---

## 🧠 Extra Notes

- All logs are parsed **line-by-line** from the decompressed `.gz` file.
- Fields are extracted using tab-delimited parsing for CloudFront format.
- You can enhance further with distribution ID parsing or AWS account alias mapping.

