
# 🧾 AWS CloudTrail Log Fields Cheat Sheet

Understand AWS CloudTrail fields for security auditing, compliance, and governance. Use these for alerts, investigations, and automated responses.

---

## 👤 Identity & User Context

| Field               | Description                                      | Use Case                                  |
|--------------------|--------------------------------------------------|-------------------------------------------|
| 🆔 `userIdentity.type`    | Type of identity (IAMUser, AssumedRole, etc.) | Track human vs programmatic access       |
| 👤 `userIdentity.userName`| IAM user name                               | Audit individual users                    |
| 🛡️ `userIdentity.arn`     | Full ARN of the identity                     | Uniquely identify actor                   |
| 👥 `userIdentity.sessionContext` | Session info for temporary creds       | Investigate role assumption               |
| 🗝️ `accessKeyId`          | AWS access key used                         | Key leakage detection                     |

---

## 📍 Source & IP Information

| Field               | Description                                      | Use Case                                  |
|--------------------|--------------------------------------------------|-------------------------------------------|
| 🌐 `sourceIPAddress`  | IP address of request origin                    | Geo-location, anomalous access detection  |
| 📱 `userAgent`        | Calling tool or browser info                    | Identify automated/scripted access        |

---

## 🔧 Event Information

| Field               | Description                                      | Use Case                                  |
|--------------------|--------------------------------------------------|-------------------------------------------|
| 🔨 `eventName`       | API action name (e.g., `RunInstances`)          | Track sensitive API activity              |
| 📦 `eventSource`     | AWS service (`ec2.amazonaws.com`, etc.)         | Service-level breakdown                   |
| ⏱️ `eventTime`       | Timestamp in UTC                                | Timeline correlation                      |
| 🆕 `eventVersion`    | Event record schema version                     | Backward compatibility                    |
| 🔑 `requestParameters` | Parameters passed in request                   | Data exposure investigation               |
| 📤 `responseElements`  | Output of the API call                         | Forensics, access success/failure         |

---

## 📁 Resources Accessed

| Field               | Description                                      | Use Case                                  |
|--------------------|--------------------------------------------------|-------------------------------------------|
| 📚 `resources`       | List of ARNs/IDs impacted by the request         | Impact scoping, dependency analysis       |
| 🔗 `recipientAccountId` | Account ID that owns the resource             | Cross-account action visibility           |

---

## 🧠 Advanced Context

| Field                      | Description                                | Use Case                             |
|---------------------------|---------------------------------------------|--------------------------------------|
| 🧭 `awsRegion`            | AWS region of the activity                  | Geographically localize events       |
| 📄 `requestID`            | Internal request UUID                       | Traceability                         |
| 🧬 `sharedEventID`        | Link across multiple records in a chain     | Event chain tracing                  |
| 🪪 `managementEvent`      | True if this is a control plane API         | Filter management vs data plane      |
| 🧮 `readOnly`             | True if the API is non-mutating             | Distinguish read vs write access     |
| 📂 `eventType`            | Type of event (e.g., AwsApiCall)            | Alert filtering                      |

---

## 📊 Observability Metrics

| Metric                        | From Fields                    | Purpose                                |
|------------------------------|--------------------------------|----------------------------------------|
| 🔥 Unauthorized Actions       | `errorCode = AccessDenied`     | Permission issues, potential attacks   |
| 🛑 Failed Login Attempts       | `eventName = ConsoleLogin` + `responseElements.success = false` | Brute force detection  |
| 🗑️ Resource Deletions         | `eventName starts with Delete` | Risky behavior alerting                |
| 🧾 Sensitive APIs Used        | e.g., `CreateUser`, `PutBucketPolicy` | Security impact monitoring         |
| 🧍 Privilege Escalation Paths | `AssumeRole`, `AttachPolicy`   | IAM privilege escalation detection     |

---

## 🚨 Suggested Alerts

| Alert Description                        | Trigger Condition                                         |
|-----------------------------------------|----------------------------------------------------------|
| 🔐 Multiple Failed Console Logins       | `eventName = ConsoleLogin` + failure count threshold     |
| 🚫 Access Denied Spike                  | `errorCode = AccessDenied` for multiple actions          |
| 📤 Resource Shared Publicly             | `PutBucketPolicy` or `ModifySnapshotAttribute` opens to all |
| 🧍 Privilege Escalation Detected        | `AttachUserPolicy`/`PutRolePolicy` with admin access     |
| 🌍 New Geo/IP Detected                  | Unusual `sourceIPAddress` for same user                  |
| 🔁 Repeated Role Assumptions            | `AssumeRole` loops within short window                   |

---

Would you like this exported as `.md`, `.pdf`, or GitHub-ready version?
