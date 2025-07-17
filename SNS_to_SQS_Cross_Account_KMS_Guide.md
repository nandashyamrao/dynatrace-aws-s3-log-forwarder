# 🔐 SNS → SQS Cross-Account Behavior: Encrypted vs. Non-Encrypted

## ✅ Scenario Overview

- **SNS Topic Owner**: Infosec team  
  → Account: `808693921418`  
  → Topic: `sf-mgmt-prod-s3-infosec-events`

- **SQS Queue Subscriber**: EMS team  
  → Account: `190731337505`  
  → Queue: `dts3fwd`  
  → Queue is **either non-encrypted or KMS-encrypted**

---

## 🧾 Behavior Comparison

| Feature / Setup                        | Without KMS (unencrypted or AWS-managed) | With KMS CMK encryption |
|----------------------------------------|------------------------------------------|--------------------------|
| ✅ SQS Queue Policy allows SNS          | ✔️ Required                               | ✔️ Required               |
| 🔐 KMS Key Policy needed                | ❌ No                                     | ✔️ Yes – SNS must call `kms:GenerateDataKey` |
| 🧾 SNS Topic Policy needed              | ❌ Usually not (even cross-account)       | ✔️ Yes – publish explicitly allowed |
| 📨 Message Delivery to SQS              | ✔️ Works if SQS policy is correct         | ❌ **Fails silently** without KMS + SNS topic policy |
| 🔎 Common failure symptom               | —                                        | SQS receives nothing; no visible error |

---

## 🧠 Why SNS Topic Policy Is Needed with KMS

When SQS is encrypted using a **customer-managed KMS key**:

1. **SNS must first call KMS** to get a temporary data encryption key (`kms:GenerateDataKey`)
2. **SNS must encrypt the message**
3. **SNS must then publish it** to your queue
4. If the **SNS topic policy does not allow this** (especially cross-account), **SNS fails silently**

> 🧩 AWS documentation:  
> “When SNS delivers messages to a KMS-encrypted resource in another account,  
> the topic owner must grant explicit permission in the topic policy.”

---

## ✅ Required Policy Additions (When SQS is KMS-encrypted)

### 🔐 EMS Account – KMS Key Policy

```json
{
  "Sid": "AllowSNSFromMgmtToEncrypt",
  "Effect": "Allow",
  "Principal": {
    "Service": "sns.amazonaws.com"
  },
  "Action": [
    "kms:GenerateDataKey",
    "kms:Encrypt"
  ],
  "Resource": "*",
  "Condition": {
    "StringEquals": {
      "aws:SourceAccount": "808693921418"
    }
  }
}
```

### 📬 EMS Account – SQS Queue Policy

```json
{
  "Sid": "AllowSNSFromInfosecToSendToSQS",
  "Effect": "Allow",
  "Principal": {
    "Service": "sns.amazonaws.com"
  },
  "Action": "sqs:SendMessage",
  "Resource": "arn:aws:sqs:us-east-1:190731337505:dts3fwd",
  "Condition": {
    "ArnEquals": {
      "aws:SourceArn": "arn:aws:sns:us-east-1:808693921418:sf-mgmt-prod-s3-infosec-events"
    }
  }
}
```

### 📣 Infosec Account – SNS Topic Policy

```json
{
  "Sid": "AllowSNSPublishToEMS_SQS",
  "Effect": "Allow",
  "Principal": {
    "Service": "sns.amazonaws.com"
  },
  "Action": "sns:Publish",
  "Resource": "arn:aws:sns:us-east-1:808693921418:sf-mgmt-prod-s3-infosec-events",
  "Condition": {
    "ArnEquals": {
      "aws:SourceArn": "arn:aws:sqs:us-east-1:190731337505:dts3fwd"
    }
  }
}
```

---

## ✅ Conclusion

- 🔓 **Without KMS**: Cross-account delivery works with just SQS queue policy.
- 🔐 **With KMS**: You must add:
  - KMS key policy (in EMS)
  - SNS topic policy (in Infosec)
  - SQS queue policy (in EMS)
- ❗ Otherwise, **SNS will silently fail to deliver messages**, even if subscriptions are "Confirmed."

---