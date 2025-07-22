# 📘 CloudFront Log Processor – `process_log_object()` Deep Dive

This document provides a full breakdown of the `process_log_object()` function used in the Dynatrace AWS S3 log forwarder. It explains the logic, flow, and structure used to safely parse, enrich, and forward CloudFront log lines from AWS S3 to Dynatrace.

---

## ✅ Purpose

The `process_log_object()` function is responsible for:

- Downloading `.gz`-compressed CloudFront logs from S3
- Detecting the header fields dynamically from the `#Fields:` line
- Parsing each log line into a structured JSON object
- Attaching metadata (bucket name, region, annotations)
- Forwarding logs to Dynatrace via configured sinks
- Emitting metrics and avoiding Lambda timeouts

---

## 🧠 How CloudFront Logs Look

Example decompressed log file:

```
#Version: 1.0
#Fields: date time x-edge-location sc-bytes c-ip cs-method cs(Host) cs-uri-stem sc-status ...
2025-07-21 17:55:56 IAD89 1234 203.0.113.1 GET d111111abcdef8.cloudfront.net /index.html 200 ...
```

- **Tab-delimited** values
- First 2 lines are headers (`#Version`, `#Fields`)
- Format may change over time

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

---

## 🧩 Key Features

| Feature                          | Description |
|----------------------------------|-------------|
| Dynamic header parsing           | Uses `#Fields:` line to extract field names |
| Normalized attribute names       | Converts `cs-uri-stem` → `cs_uri_stem` |
| Metadata tagging                 | Adds S3 bucket, key, region, function ARN |
| Structured log export            | Sends each log line as structured JSON to Dynatrace |
| Safe timeout detection           | Stops if less than 10s remain in Lambda |
| CloudWatch metrics               | Reports processing time, object size, success/failure count |

---

## ✅ CloudFront Log Rule (AppConfig Example)

```yaml
- name: cloudfront
  source: aws
  log_format: text
  skip_header_lines: 2
  known_key_path_pattern: '^cloudfront/.*/.*\.gz$'
  annotations:
    cloud.provider: aws
    aws.service: cloudfront
    aws.region: global
```

---

## 🔚 Summary

This processor allows you to parse CloudFront logs safely, with complete field visibility, dynamic flexibility, and Dynatrace-compatible output.

