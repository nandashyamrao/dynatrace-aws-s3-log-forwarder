# ✅ AWS CloudTrail Log Flow – Purpose and Architecture

---

## 🎯 Purpose of CloudTrail Logs

AWS CloudTrail records **every API call and management event** made within your AWS account.

**Main purposes include:**

- 🕵️ Auditing user activity and API usage
- 🔐 Security forensics and incident response
- 📜 Compliance tracking (PCI, HIPAA, SOC 2, etc.)
- 🔔 Real-time alerting and detection with Dynatrace, SIEMs, etc.

---

## 🔁 Flow Overview

```
🔧 AWS API Activity (Console, SDK, CLI)
     ↓
📓 AWS CloudTrail captures event
     ↓
🪣 CloudTrail writes log file to S3 bucket (in .json.gz format)
     ↓
🔔 S3 triggers EventBridge / SNS / SQS notification
     ↓
🧠 Lambda (Dynatrace Log Forwarder) reads and parses event
     ↓
📬 Log is enriched and sent to Dynatrace Logs API
```

---

## 🧠 Example Use Case in Dynatrace

Query:

```dql
fetch logs
| filter log.source == "cloudtrail"
| filter eventName == "TerminateInstances"
| filter userIdentity.userName == "alice"
```

Use it to:
- Detect dangerous actions (e.g. root access, policy changes)
- Build dashboards of user activity
- Track resource usage across accounts and regions

---

## 🧭 Summary of Key Components

| Component              | Role                                                                 |
|------------------------|----------------------------------------------------------------------|
| **AWS CloudTrail**     | Captures API calls and user actions                                  |
| **S3 Bucket**          | Stores the CloudTrail logs in gzip-compressed JSON format            |
| **EventBridge/SNS/SQS**| Sends notifications of new logs to trigger downstream processing     |
| **Lambda Forwarder**   | Parses, enriches, and forwards logs to Dynatrace                     |
| **Dynatrace**          | Stores, analyzes, and visualizes the CloudTrail logs                 |

---

# ✅ CloudTrail Log Fields – Categorized with Real-World Sample Values

### 🧾 Event Metadata

| Field | Description | Sample Value |
|-------|-------------|---------------|
| eventTime | The time the event occurred | 2025-07-13T14:23:45Z |
| eventName | The name of the API operation | RunInstances |
| eventSource | The AWS service that the request was made to | ec2.amazonaws.com |
| eventVersion | The CloudTrail event version | 1.08 |
| eventID | Unique ID for the event | abc12345-6789-0123-4567-abcdefabcdef |

### 👤 Identity Information

| Field | Description | Sample Value |
|-------|-------------|---------------|
| userIdentity.type | The type of user (IAMUser, Root, AssumedRole, etc.) | AssumedRole |
| userIdentity.arn | The Amazon Resource Name (ARN) of the principal | arn:aws:sts::123456789012:assumed-role/AdminRole/AWSCLI-Session |
| userIdentity.accountId | The AWS account ID of the user | 123456789012 |
| userIdentity.userName | The username of the IAM user | jdoe |

### 🌐 Request Context

| Field | Description | Sample Value |
|-------|-------------|---------------|
| sourceIPAddress | The IP address from which the request was made | 203.0.113.45 |
| userAgent | The agent used to make the request | aws-cli/2.0 |
| awsRegion | The AWS region where the request was made | us-east-1 |

### 🔧 Request Parameters

| Field | Description | Sample Value |
|-------|-------------|---------------|
| requestParameters | The parameters sent with the request | {"instanceType":"t2.micro"} |
| requestID | The AWS request ID | 12345678-abcd-1234-abcd-123456abcdef |

### 📤 Response Elements

| Field | Description | Sample Value |
|-------|-------------|---------------|
| responseElements | The elements returned in the response | {"instancesSet":{"items":[{"instanceId":"i-1234567890abcdef0"}]}} |

### 📁 Resources Accessed

| Field | Description | Sample Value |
|-------|-------------|---------------|
| resources | The AWS resources impacted by the request | [{"ARN":"arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0"}] |

### 🔒 Authorization

| Field | Description | Sample Value |
|-------|-------------|---------------|
| userIdentity.sessionContext.attributes.mfaAuthenticated | Whether MFA was used | true |
| userIdentity.sessionContext.attributes.creationDate | When the session was created | 2025-07-13T13:50:30Z |