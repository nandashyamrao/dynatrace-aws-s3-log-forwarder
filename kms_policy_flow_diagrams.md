
# 🔐 AWS KMS Key Policy Deep Dive: SNS and S3 Integration

This document explains the purpose, flow, and technical behavior of the two KMS key policy blocks used in your AWS setup. These blocks support current and future message encryption workflows across SNS, S3, SQS, Lambda, and EventBridge.

---

## 🛡️ Policy Block 1: `AllowSNS`

### 🔧 Policy JSON

```json
{
  "Sid": "AllowSNS",
  "Effect": "Allow",
  "Principal": {
    "Service": "sns.amazonaws.com"
  },
  "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
  "Resource": "*",
  "Condition": {
    "ArnLike": {
      "aws:SourceArn": "arn:aws:sns:us-east-1:808609321418:sf-mgmt-prod-s3-infosec-events-v2"
    }
  }
}
```

### 🎯 Purpose

This block allows **direct SNS topic publishing with encryption**, where:
- The KMS key can be used **by the SNS service**
- Only for a specific topic: `sf-mgmt-prod-s3-infosec-events-v2`
- No intermediate service like S3 is required
- No `kms:ViaService` condition applies

### 🧭 Flow Diagram

```
┌──────────────────────────────┐
│ External AWS Account (MGMT) │
│ Publishes to SNS Topic       │
│ ARN: arn:aws:sns:...:events-v2 │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│    SNS Topic (events-v2)     │
│  - Needs to encrypt payload  │
│  - Calls AWS KMS             │
│  - Caller: sns.amazonaws.com │
│  - Source ARN: topic ARN     │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│   AWS KMS Validates Request  │
│   ✔ Matches Source ARN       │
│   ✔ Principal is SNS         │
│   ✔ Allows Encrypt/Decrypt   │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│ Encrypted Message Delivered  │
│     to SQS Queue             │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│     Lambda Forwarder         │
│   - Reads SQS message        │
│   - Decrypts using KMS key   │
└──────────────────────────────┘
```

---

## 🌉 Policy Block 2: `AllowS3AndSNSViaService`

### 🔧 Policy JSON

```json
{
  "Sid": "AllowS3AndSNSViaService",
  "Effect": "Allow",
  "Principal": {
    "Service": [
      "s3.amazonaws.com",
      "sns.amazonaws.com"
    ]
  },
  "Action": [
    "kms:GenerateDataKey",
    "kms:Decrypt",
    "kms:ReEncrypt*"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "kms:ViaService": "s3.us-east-1.amazonaws.com",
      "kms:CallerAccount": "808609321418"
    }
  }
}
```

### 🎯 Purpose

This block supports **S3-originated notifications** that are encrypted via KMS before being sent to SNS or EventBridge.

The condition:
- `kms:ViaService: s3.us-east-1.amazonaws.com` ensures only S3 in that region can use this key
- `kms:CallerAccount: 808609321418` restricts to the InfoSec account

### 🧭 Flow Diagram

```
┌──────────────────────────────┐
│     S3 Bucket (CloudTrail)   │
│  e.g., sf-infosec-cloudfront │
└────────────┬─────────────────┘
             │ S3 Object Created Event (e.g., log uploaded)
             │
             ▼
┌──────────────────────────────┐
│    S3 Notification Trigger   │
│ (EventBridge or SNS Target)  │
└────────────┬─────────────────┘
             │ Prepare message payload (JSON)
             │ Encrypt with customer-managed KMS key
             │
             ▼
┌──────────────────────────────┐
│     AWS KMS Encryption Call  │
│  - Called by: `s3.amazonaws.com`           │
│  - Region: `us-east-1`                     │
│  - KMS Condition Triggered:                │
│     "kms:ViaService": "s3.us-east-1.amazonaws.com"  │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│ Encrypted message delivered  │
│ to SNS or EventBridge Rule   │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│     SQS Queue (EMS Account)  │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│     Lambda Forwarder         │
│  - Decrypts using same KMS   │
│  - No ViaService restriction │
└──────────────────────────────┘
```

---

## 🔍 Comparison Table

| Feature                     | `AllowSNS` Block                          | `AllowS3AndSNSViaService` Block            |
|----------------------------|-------------------------------------------|--------------------------------------------|
| ✅ Current SNS → SQS use case | ✔ Supported                             | ❌ Not triggered (no S3 context)           |
| ✅ Future S3 → EventBridge flow | ❌ Not triggered (no ViaService)       | ✔ Required to allow encryption by S3       |
| Condition Type             | `aws:SourceArn`                          | `kms:ViaService` + `kms:CallerAccount`     |
| Grants KMS Decrypt         | ✔ Yes                                     | ✔ Yes                                      |
| Limited to a topic or service | ✔ Topic-specific                        | ✔ Service and region specific              |

---

## ✅ Summary

- Use **`AllowSNS` block** for today's setup
- Keep **`AllowS3AndSNSViaService` block** for future S3 → EventBridge integration
- Together, these policies cover both direct SNS publishing and S3-triggered encrypted events
