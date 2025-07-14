# ✅ AWS API Gateway Logs – Purpose and Architecture

---

## 🎯 Purpose of API Gateway Logs

API Gateway access logs provide detailed information about every request and response processed by your API. These logs help you:

- 🧭 Trace incoming requests for debugging
- 🚨 Monitor API errors, throttles, and latency
- 📈 Track usage patterns and client behavior
- 🔐 Audit identity context and request origin
- 📊 Feed insights to Dynatrace or SIEM platforms

---

## 🔁 Flow Overview

```
🌐 Client calls API endpoint (HTTPS)
     ↓
🛡️ API Gateway receives request and logs metadata
     ↓
🪣 Access logs are written to CloudWatch Logs or Kinesis Firehose (if configured)
     ↓
🔁 Optional: Export logs to S3 via subscription
     ↓
🧠 Lambda log forwarder reads the logs and parses them
     ↓
📬 Logs are enriched and sent to Dynatrace Logs API
```

---

## 🧠 Example Use Case in Dynatrace

```dql
fetch logs
| filter log.source == "apigateway"
| filter status >= 500
| summarize count(), avg(latency)
```

Use it to:
- Detect API failures and client spikes
- Measure performance bottlenecks
- Monitor integration time from upstream services

---

## 🧭 Summary of Key Components

| Component            | Role                                                             |
|----------------------|------------------------------------------------------------------|
| **API Gateway**      | Handles request routing, logging, and authorization              |
| **CloudWatch Logs**  | Default destination for access logs                              |
| **S3 or Kinesis**    | Optional destination for access logs for external processing     |
| **Lambda Forwarder** | Parses, enriches, and forwards logs to Dynatrace                 |
| **Dynatrace**        | Visualizes and alerts on request, latency, and error patterns    |
---

# 📋 API Gateway Log Fields – Categorized with Real-World Sample Values

### 📅 Request Timing

| Field | Description | Sample Value |
|-------|-------------|---------------|
| requestTime | The time at which the request was received | 13/Jul/2025:14:23:00 +0000 |

### 🌐 Request Context

| Field | Description | Sample Value |
|-------|-------------|---------------|
| httpMethod | The HTTP method used in the request | POST |
| resourcePath | The path of the requested resource | /prod/user |
| requestId | Unique identifier for the request | c4z4azazazc1= |
| sourceIp | The IP address from which the request was received | 198.51.100.24 |
| userAgent | The user agent of the caller | curl/7.79.1 |
| protocol | The request protocol version | HTTP/1.1 |

### 📤 Response Details

| Field | Description | Sample Value |
|-------|-------------|---------------|
| status | The HTTP status code returned to the client | 200 |
| responseLength | The number of bytes returned in the response | 350 |
| integrationStatus | The status returned from the backend integration | 200 |
| latency | The total request latency in ms | 120 |
| integrationLatency | The backend integration latency in ms | 80 |

### 🔒 Authorization & Identity

| Field | Description | Sample Value |
|-------|-------------|---------------|
| caller | The IAM caller (if any) | 123456789012 |
| user | The user identity (IAM or Cognito) | AIDAEXAMPLEID |
| accountId | The AWS account ID | 123456789012 |
| apiId | The API Gateway ID | abc123def4 |
| stage | The deployment stage | prod |
