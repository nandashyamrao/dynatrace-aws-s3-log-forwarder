## 🔁 WAF Log Flow – Purpose and Architecture

### 🎯 Purpose of WAF Logs

AWS WAF logs capture every request inspected by your WebACL, including which rule matched, what action was taken, and request metadata.

**Main purposes include:**

- 🔍 Detecting and investigating malicious activity
- 📊 Monitoring rule behavior (allow, block, count)
- ⚠️ Alerting and automated responses in Dynatrace, SIEMs, etc.
- 📈 Tuning managed rules and custom rule sets

---

### 🔁 Flow Overview

```
🔴 Client Request
     ↓
🌐 CloudFront / ALB / API Gateway (with WAF attached)
     ↓
🛡️ AWS WAF evaluates request via WebACL
     ↓
📤 WAF sends log (if enabled) to Kinesis Firehose
     ↓
🪣 Firehose writes JSON logs to S3 bucket
     ↓
🔔 S3 triggers EventBridge/SNS/SQS
     ↓
🧠 Lambda (Dynatrace Log Forwarder) processes log
     ↓
📬 Log is enriched and sent to Dynatrace Logs API
```

---

### 🧠 Example Use Case in Dynatrace

Query:

```dql
fetch logs
| filter log.source == "waf"
| filter action == "BLOCK"
| filter labels contains "sql-database"
```

Create dashboards to monitor:
- 🔝 Top blocked IPs
- 📍 Blocked requests by country
- 🛡️ Rules triggering most actions

---

### 🧭 Summary of Key Components

| Component              | Role                                                                 |
|------------------------|----------------------------------------------------------------------|
| **AWS WAF WebACL**     | Evaluates HTTP requests based on defined rules                       |
| **Kinesis Firehose**   | Delivers logs to S3                                                  |
| **S3 Bucket**          | Stores log data in JSON format                                       |
| **SQS/EventBridge/SNS**| Triggers downstream processing (e.g., Lambda)                        |
| **Lambda Forwarder**   | Parses, enriches, and sends logs to Dynatrace                        |
| **Dynatrace**          | Analyzes and visualizes WAF security data                           |

---

# ✅ AWS WAF Log Fields – Categorized with Real-World Sample Values

### 📅 Request Timing

| Field | Description | Sample Value |
|-------|-------------|---------------|
| timestamp | The time when AWS WAF received the request | 2025-07-13T14:23:00Z |

### 🌐 Request Context

| Field | Description | Sample Value |
|-------|-------------|---------------|
| httpRequest.clientIp | The IP address that sent the request | 198.51.100.23 |
| httpRequest.country | The country of origin for the request | US |
| httpRequest.method | The HTTP method of the request | POST |
| httpRequest.uri | The URI of the request | /api/login |
| httpRequest.args | The query arguments of the request | user=admin |
| httpRequest.headers | The headers included in the request | [{"name":"User-Agent","value":"curl/7.79.1"}] |
| httpRequest.httpVersion | The HTTP version of the request | HTTP/1.1 |

### 🛡️ Rule Evaluation

| Field | Description | Sample Value |
|-------|-------------|---------------|
| ruleGroupList | List of rule groups that matched | [{"ruleGroupId":"AWS#DefaultRuleSet","terminatingRuleId":"SQLi_BODY"}] |
| terminatingRuleId | The ID of the rule that terminated evaluation | SQLi_BODY |
| terminatingRuleType | Type of rule that terminated the evaluation | REGULAR |
| action | Final action taken on the request | BLOCK |

### 📊 Labels and Tags

| Field | Description | Sample Value |
|-------|-------------|---------------|
| labels | Labels added to the request during evaluation | ["awswaf:managed:aws:sql-database"] |
| rateBasedRuleList | List of rate-based rules that evaluated the request | [] |

### 🧾 Metadata

| Field | Description | Sample Value |
|-------|-------------|---------------|
| formatVersion | The version of the log format | 1.0 |
| webaclId | The ID of the WebACL associated with the request | arn:aws:wafv2:us-east-1:123456789012:regional/webacl/my-waf |
| terminatingRuleMatchDetails | Details on the rule that matched | [{"conditionType":"SQL_INJECTION","location":"BODY"}] |

---