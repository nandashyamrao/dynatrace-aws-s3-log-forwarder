# ✅ AWS ALB (Application Load Balancer) Logs – Purpose and Architecture

---

## 🎯 Purpose of ALB Logs

ALB access logs provide detailed insight into traffic going through your load balancer. These logs are essential for:

- 🕵️ Diagnosing backend latency and target failures
- 🔐 Monitoring HTTP/TLS status codes
- 📈 Traffic analysis and user-agent trends
- 📊 Feeding observability tools like Dynatrace

---

## 🔁 Flow Overview

```
🌐 Client sends request to ALB
     ↓
📥 ALB receives request, routes to target
     ↓
📝 ALB writes access log to S3 bucket (in .log format)
     ↓
🔔 S3 event triggers Lambda / EventBridge / SQS
     ↓
🧠 Lambda (Dynatrace Log Forwarder) processes and enriches log
     ↓
📬 Sends to Dynatrace Logs API
```

---

## 🧠 Example Use Case in Dynatrace

```dql
fetch logs
| filter log.source == "alb"
| filter elb_status_code >= 500
| summarize count(), avg(target_processing_time)
```

Common dashboards include:
- 🔥 Target 5xx spikes
- 🐢 Slowest backends by target group
- 📍 Top paths and user agents

---

## 🧭 Summary of Key Components

| Component               | Role                                                              |
|-------------------------|-------------------------------------------------------------------|
| **ALB**                 | Handles HTTP/HTTPS traffic routing                                |
| **S3 Bucket**           | Stores access logs in space-delimited text format                 |
| **EventBridge/SNS/SQS** | Triggers log processing workflows                                 |
| **Lambda Forwarder**    | Parses logs, enriches metadata, sends to Dynatrace                |
| **Dynatrace**           | Provides dashboards, alerting, and traffic insight                |
---

# 📋 ALB Log Fields – Categorized with Real-World Sample Values

### 📅 Request Timing

| Field | Description | Sample Value |
|-------|-------------|---------------|
| type | The type of request | http |
| timestamp | Time when the load balancer received the request | 2025-07-13T14:23:00.123456Z |

### 🌐 Request Context

| Field | Description | Sample Value |
|-------|-------------|---------------|
| elb | The name of the load balancer | app/my-alb/50dc6c495c0c9188 |
| client:port | The IP address and port of the requesting client | 198.51.100.1:54321 |
| target:port | The IP address and port of the target | 192.0.2.10:80 |
| request_processing_time | Time (s) the load balancer spent receiving the request | 0.00002 |
| target_processing_time | Time (s) the target spent processing the request | 0.045 |
| response_processing_time | Time (s) the load balancer spent sending the response | 0.00003 |

### 📤 Response Details

| Field | Description | Sample Value |
|-------|-------------|---------------|
| elb_status_code | The status code sent from the load balancer to the client | 200 |
| target_status_code | The status code sent from the target to the load balancer | 200 |
| received_bytes | The size of the request (bytes) | 512 |
| sent_bytes | The size of the response (bytes) | 2048 |
| request | The HTTP request line | "GET https://myalb.example.com:443/index.html HTTP/1.1" |
| user_agent | The user agent header value | "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" |

### 🔒 TLS & Security

| Field | Description | Sample Value |
|-------|-------------|---------------|
| ssl_cipher | The SSL cipher used for HTTPS requests | ECDHE-RSA-AES128-GCM-SHA256 |
| ssl_protocol | The SSL protocol used | TLSv1.2 |
| authentication_status | Result of client authentication | - |
| target_group_arn | The full ARN of the target group | arn:aws:elasticloadbalancing:region:123456789012:targetgroup/my-targets/73e2d6bc24d8a067 |

### 📌 Metadata

| Field | Description | Sample Value |
|-------|-------------|---------------|
| trace_id | Trace ID for request tracing (if enabled) | Root=1-5e9f5e48-bd862a5d29c6c82e9a7a9b36 |
| domain_name | Domain name of the request | myalb.example.com |
| chosen_cert_arn | The ARN of the certificate used for SSL | arn:aws:acm:region:account:certificate/12345678 |
| matched_rule_priority | Priority of the matched listener rule | 1 |
| actions_executed | List of actions executed by the rule | ["forward"] |
| redirect_url | URL for redirection (if action was redirect) | - |
