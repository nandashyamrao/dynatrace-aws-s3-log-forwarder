# Dynatrace AWS S3 Log Forwarder Configuration

## ✅ Processing Rules (`processing-rules.yaml`)

```yaml
- id: aws.cloudtrail
  version: 1
  matches:
    - bucketName: "sf-prod-event"  # CloudTrail bucket
      keyPrefix: "AWSLogs/"
  processors:
    - type: cloudtrail

- id: aws.cloudfront
  version: 1
  matches:
    - bucketName: "sf-iaeeast-test-us-east-1-eligibqcloudfront-logs"
      keyPrefix: "807000099195/eligibqapi/"
  processors:
    - type: cloudfront

- id: generic.log
  version: 1
  matches:
    - bucketName: "*"
  processors:
    - type: json
      detectTimeField: true
      timeFieldName: timestamp
      timeFieldFormat: iso
```

---

## 🚀 Forwarding Rules (`forwarding-rules.yaml`)

```yaml
rules:
  - id: forward.cloudtrail
    enabled: true
    match:
      bucketName: "sf-prod-event"
      keyPrefix: "AWSLogs/"
    forwardTo: logs

  - id: forward.cloudfront
    enabled: true
    match:
      bucketName: "sf-iaeeast-test-us-east-1-eligibqcloudfront-logs"
      keyPrefix: "807000099195/eligibqapi/"
    forwardTo: logs

  - id: forward.generic
    enabled: true
    match:
      bucketName: "*"
    forwardTo: logs
```
