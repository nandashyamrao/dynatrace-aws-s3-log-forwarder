
# 📘 CloudFront Logs - Dynatrace Dashboard (Parsed Fields)

This dashboard assumes you have parsed all CloudFront log fields like `sc_status`, `time_taken`, `cs_uri_stem`, `x_edge_result_type`, etc. It focuses on traffic, latency, cache efficiency, errors, geo-distribution, and data volume.

---

## 🔹 Section 1: Traffic Overview

### 📌 Total Requests Over Time
```dql
fetch logs
| filter dt.system.bucket == "aws_cloudfront"
| summarize count() as total_requests by bin(timestamp, 5m)
```

### 📌 Top 10 Requested URIs
```dql
fetch logs
| filter dt.system.bucket == "aws_cloudfront"
| summarize count() by cs_uri_stem
| sort count desc
| limit 10
```

---

## 🔹 Section 2: Performance Metrics

### 📌 Average Latency (time-taken)
```dql
fetch logs
| filter dt.system.bucket == "aws_cloudfront"
| summarize avg(toDouble(time_taken)) as avg_latency by bin(timestamp, 5m)
```

### 📌 Top Slow URIs
```dql
fetch logs
| filter dt.system.bucket == "aws_cloudfront"
| summarize avg(toDouble(time_taken)) as avg_latency by cs_uri_stem
| sort avg_latency desc
| limit 10
```

---

## 🔹 Section 3: Cache Efficiency

### 📌 Cache Hit Ratio Over Time
```dql
fetch logs
| filter dt.system.bucket == "aws_cloudfront"
| summarize
    hits = countIf(x_edge_result_type == "Hit"),
    misses = countIf(x_edge_result_type != "Hit")
    by bin(timestamp, 5m)
| extend hit_ratio = hits * 100.0 / (hits + misses)
```

### 📌 Top Missed URIs
```dql
fetch logs
| filter dt.system.bucket == "aws_cloudfront" and x_edge_result_type != "Hit"
| summarize count() by cs_uri_stem
| sort count desc
| limit 10
```

---

## 🔹 Section 4: Errors & Status Codes

### 📌 4xx and 5xx Error Count
```dql
fetch logs
| filter matchesValue(sc_status, "4*") or matchesValue(sc_status, "5*")
| summarize count() by sc_status, bin(timestamp, 5m)
```

### 📌 Error Rate (%)
```dql
fetch logs
| summarize
    error_count = countIf(matchesValue(sc_status, "4*") or matchesValue(sc_status, "5*")),
    total = count()
| extend error_rate = error_count * 100.0 / total
```

---

## 🔹 Section 5: Geo & Client Info

### 📌 Requests by Edge Location
```dql
fetch logs
| summarize count() by x_edge_location
| sort count desc
| limit 10
```

### 📌 Top Client IPs
```dql
fetch logs
| summarize count() by c_ip
| sort count desc
| limit 10
```

---

## 🔹 Optional: Cost Awareness

### 📌 Total Bytes Transferred (Egress)
```dql
fetch logs
| summarize total_bytes = sum(toLong(sc_bytes)) by bin(timestamp, 5m)
```

---

**Next step**: If you'd like, I can provide a `.json` Dynatrace dashboard for import based on these DQL panels.


---

## 🎛️ Dashboard Variables for Interactive Filtering

To enable dynamic filtering of CloudFront logs by key attributes, add the following dashboard variables in Dynatrace:

---

### 🔹 1. `aws_account_id`

- **Name**: `aws_account_id`
- **Type**: Query value (from logs)
- **DQL**:
  ```dql
  fetch logs
  | summarize by aws_account_id
  ```

---

### 🔹 2. `distribution_id`

- **Name**: `distribution_id`
- **Type**: Query value (from logs)
- **DQL**:
  ```dql
  fetch logs
  | summarize by distribution_id
  ```

---

### 🔹 3. `distribution_name`

- **Name**: `distribution_name`
- **Type**: Query value (from logs)
- **DQL**:
  ```dql
  fetch logs
  | summarize by distribution_name
  ```

---

### 🧪 Example DQL Using Variables

```dql
fetch logs
| filter aws_account_id == "$aws_account_id"
      and distribution_id == "$distribution_id"
      and distribution_name == "$distribution_name"
| summarize count() by sc_status, bin(timestamp, 5m)
```

For optional filters:

```dql
| filter (isNull("$aws_account_id") or aws_account_id == "$aws_account_id")
```

---

### ⚙️ Steps to Add Variables in Dynatrace Dashboard

1. Open your dashboard.
2. Click the **gear icon** and choose **"Manage variables"**.
3. Add each variable:
   - Type: `Query value`
   - Source: `Logs`
   - Use the DQL from above.
4. Reference variables in panels using `$variable_name`.
5. Save and test the filtering.

---
