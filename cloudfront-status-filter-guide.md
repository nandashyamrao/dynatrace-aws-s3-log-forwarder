
# 🌐 CloudFront Status Code Filtering — User Guide

This guide helps you understand, interpret, and **filter CloudFront logs** using `status` codes, commonly used in dashboards and observability platforms like Dynatrace.

---

## 🧾 What is the `status` field?

The `status` field in CloudFront logs represents the **HTTP response code** returned by CloudFront to the client. These codes help you:

- ✅ Identify success or failure of requests
- 🔍 Filter logs by errors (4xx, 5xx)
- 📊 Build visualizations in dashboards

---

## 📖 Common CloudFront Status Codes

| Status Code | Meaning | Category | Description |
|-------------|---------|----------|-------------|
| `200` ✅ | OK | Success | Request was successfully fulfilled |
| `206` 🧩 | Partial Content | Success | Only part of the resource was delivered (e.g., video streaming) |
| `301` 🔁 | Moved Permanently | Redirect | Resource moved to another location |
| `302` 🔁 | Found (Temporary Redirect) | Redirect | Temporary redirect |
| `304` 🧼 | Not Modified | Cache | Resource not modified, served from browser cache |
| `400` ❌ | Bad Request | Client Error | Malformed request |
| `403` 🔒 | Forbidden | Client Error | Access to the resource is denied |
| `404` 🚫 | Not Found | Client Error | Resource does not exist |
| `500` 💥 | Internal Server Error | Server Error | Generic server error |
| `502` 🛑 | Bad Gateway | Server Error | CloudFront received invalid response from origin |
| `503` 💤 | Service Unavailable | Server Error | Origin is overloaded or unavailable |
| `504` ⏱️ | Gateway Timeout | Server Error | Origin did not respond in time |

---

## 🔎 Filtering by Status Code in Dynatrace (DQL)

### ✅ Successful Requests

```dql
fetch logs
| filter status == 200
```

### ❌ Client Errors (4xx)

```dql
fetch logs
| filter status >= 400 and status < 500
```

### 💥 Server Errors (5xx)

```dql
fetch logs
| filter status >= 500
```

### 🔍 Specific Status (e.g., 404)

```dql
fetch logs
| filter status == 404
```

---

## 📊 Suggested Dashboard Tiles

- **Success Rate Gauge** → `status == 200`
- **Top 4xx Errors** → `status >= 400 and status < 500 | summarize count(), by: status`
- **Top 5xx Errors** → `status >= 500 | summarize count(), by: status`
- **Time Series** of 4xx/5xx → Group by timestamp + status

---

## 📁 Sample Log Fields (for reference)

| Field | Example |
|-------|---------|
| `log.source` | `cloudfront` |
| `status` | `200`, `403`, `502` |
| `client_ip` | `192.0.2.10` |
| `distribution_name` | `my-cdn.example.com` |
| `timestamp` | `2025-08-07T12:00:00Z` |

---

## 🧠 Best Practices

- 🔄 Use variables like `$status_filter` in dashboards for dynamic filtering
- 🧱 Combine status filtering with `aws_account_id` or `distribution_name`
- 📈 Monitor spikes in 4xx/5xx errors to detect anomalies or outages
