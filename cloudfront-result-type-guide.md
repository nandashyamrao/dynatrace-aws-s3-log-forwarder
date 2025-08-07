
# 🚦 CloudFront `result_type` Filtering — User Guide

This guide explains how to use the `result_type` field from CloudFront logs to understand how requests were handled — whether they were cache hits, misses, errors, or redirects — and how to filter on these values in Dynatrace or other observability platforms.

---

## 🔍 What is `result_type`?

The `result_type` field indicates how CloudFront handled a request — **whether it was served from the edge cache, forwarded to the origin, or returned with an error**.

---

## 📖 Common `result_type` Values

| `result_type`       | Meaning                          | Description                                                                 |
|---------------------|----------------------------------|-----------------------------------------------------------------------------|
| `Hit` ✅             | Cache Hit                        | The object was served from the CloudFront edge cache                       |
| `Miss` 🔄            | Cache Miss                       | CloudFront had to forward the request to the origin                        |
| `Error` ❌           | Error                            | An error occurred either at CloudFront or the origin                       |
| `Redirect` 🔁        | Redirect                         | A redirection response was returned (like 3xx)                             |
| `LimitExceeded` ⛔   | Limit Exceeded                   | CloudFront rejected the request because of rate/size/throttle limits       |
| `InvalidRequest` 🚫 | Invalid Request                  | Request was malformed or unauthorized                                      |
| `RefreshHit` ♻️      | Cache Refresh Hit                | The object was in cache but had to be revalidated with the origin          |
| `OriginShieldHit` 🛡️ | Origin Shield Hit                | Request served from Origin Shield (if enabled) instead of main origin      |

---

## 🧠 How to Use It

You can use `result_type` to:
- 📊 Measure cache efficiency
- 🔍 Detect error types (alongside `status`)
- 🧼 Identify excessive origin fetches (misses)
- 🧱 Build dashboards for performance metrics

---

## 🔎 DQL Filters by `result_type`

### ✅ Cache Hits Only

```dql
fetch logs
| filter result_type == "Hit"
```

### 🔄 Cache Misses Only

```dql
fetch logs
| filter result_type == "Miss"
```

### ❌ Errors Only

```dql
fetch logs
| filter result_type == "Error"
```

### 🔁 Redirects

```dql
fetch logs
| filter result_type == "Redirect"
```

### ⛔ Limit Exceeded

```dql
fetch logs
| filter result_type == "LimitExceeded"
```

---

## 📊 Suggested Dashboard Tiles

| Tile Title                      | Filter Example                                        |
|--------------------------------|--------------------------------------------------------|
| Cache Hit Rate %               | `summarize hits = countIf(result_type == "Hit")`      |
| Cache Miss Rate %              | `summarize misses = countIf(result_type == "Miss")`   |
| Errors by Result Type          | `summarize count(), by: result_type where status >= 400` |
| Top Origins Triggering Misses  | `filter result_type == "Miss" | summarize count(), by: domain` |
| Result Type Trend Over Time    | `summarize count(), by: result_type, bin(timestamp, 1h)` |

---

## 🛡️ Best Practices

- ♻️ **Monitor RefreshHits** to evaluate origin validation pressure.
- 🛑 Use `LimitExceeded` and `InvalidRequest` to detect abusive patterns or misconfigurations.
- 📉 High `Miss` rates may indicate **low cache hit efficiency** — consider tuning TTLs or cache policies.
