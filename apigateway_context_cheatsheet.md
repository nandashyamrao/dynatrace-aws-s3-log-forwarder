
# 🚀 AWS API Gateway `$context` Variables Cheat Sheet

Use this sheet to understand the `$context` variables available in API Gateway Access Logs, Mapping Templates, and integrations.

---

## 👤 Caller Identity

| Variable | Description | Use Case |
|----------|-------------|----------|
| `$context.identity.sourceIp` | IP address of the caller | Geolocation, traffic source analysis |
| `$context.identity.userAgent` | User agent string | Device or client type |
| `$context.identity.caller` | IAM principal (if signed) | IAM tracing |
| `$context.identity.user` | IAM user ID | Authenticated call identification |

---

## 🌐 Request Info

| Variable | Description | Use Case |
|----------|-------------|----------|
| `$context.httpMethod` | HTTP method (GET, POST, etc.) | API behavior |
| `$context.path` | Full path of the request | Route tracing |
| `$context.domainName` | Domain name used | Multi-domain support |
| `$context.protocol` | HTTP protocol used | TLS/HTTP version debugging |

---

## 📄 Response Info

| Variable | Description | Use Case |
|----------|-------------|----------|
| `$context.status` | HTTP response status code | Error rate alerting |
| `$context.responseLength` | Bytes returned in the response | Bandwidth cost analysis |

---

## ⏱️ Timing

| Variable | Description | Use Case |
|----------|-------------|----------|
| `$context.requestTime` | Formatted request time | Readable logs |
| `$context.requestTimeEpoch` | Epoch timestamp in ms | Metric correlation |
| `$context.responseLatency` | Time taken in ms to respond | Latency SLOs |

---

## 🧾 API Metadata

| Variable | Description | Use Case |
|----------|-------------|----------|
| `$context.apiId` | API Gateway ID | API-specific filtering |
| `$context.stage` | Deployed stage name | Stage-level debugging |
| `$context.requestId` | Unique ID for each request | Distributed tracing |
| `$context.routeKey` | Route match key (HTTP APIs) | Routing validation |

---

## 🔐 Authorization Data

| Variable | Description | Use Case |
|----------|-------------|----------|
| `$context.authorizer.claims` | JWT or Cognito claims | Authorization logic |
| `$context.authorizer.<key>` | Custom authorizer return values | Custom RBAC or enrichment |

---

## 📊 Sample Log Format

```text
$context.requestId - $context.identity.sourceIp - $context.httpMethod $context.path - $context.status - $context.responseLatency ms
```

**Example output:**
```
f9bc3a12-0c4b-11ee-83a7-8d67bca892f3 - 203.0.113.42 - GET /api/v1/items - 200 - 132 ms
```

---

Would you like to combine this into a single observability reference with WAF, CloudFront, S3, CloudTrail, ALB, and Route 53 logs?
