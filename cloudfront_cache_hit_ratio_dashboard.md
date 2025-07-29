# 📊 Dynatrace Dashboard: Cache Hit Ratio for CloudFront

## ✅ Objective
Visualize what percentage of requests are served from cache (hits, refresh hits) vs. errors or misses from CloudFront logs ingested in Dynatrace.

---

## 🧱 DQL Query to Calculate Cache Hit Ratio

```dql
fetch logs
| filter matchesValue(log.source.aws.s3.bucket.name, "sf-infosec-cloudfront-logs")
| parse content, "LD:date SPACE LD:time SPACE LD:edge_location SPACE INT:sc_bytes SPACE IP:client_ip SPACE WORD:method SPACE LD:host SPACE LD:uri_stem SPACE INT:status_code SPACE LD:referer SPACE LD:user_agent SPACE INT:cs_bytes SPACE FLOAT:time_taken SPACE WORD:ssl_protocol SPACE LD:protocol_version SPACE WORD:response_result_type"
| summarize count() by response_result_type
```

---

## 📈 Recommended Visualization

- **Type**: Pie Chart or Column Chart
- **Metric**: Count of each `response_result_type`
- **Grouping**: `response_result_type`
- **Color Hints**:
  - `Hit` → 🟢
  - `RefreshHit` → 🔵
  - `Miss/Error` → 🔴

---

## ✏️ Optional – Derived Cache Hit Percentage Tile

If you want to compute the percentage in DQL:

```dql
fetch logs
| filter matchesValue(log.source.aws.s3.bucket.name, "sf-infosec-cloudfront-logs")
| parse content, "LD:date SPACE LD:time SPACE LD:edge_location SPACE INT:sc_bytes SPACE IP:client_ip SPACE WORD:method SPACE LD:host SPACE LD:uri_stem SPACE INT:status_code SPACE LD:referer SPACE LD:user_agent SPACE INT:cs_bytes SPACE FLOAT:time_taken SPACE WORD:ssl_protocol SPACE LD:protocol_version SPACE WORD:response_result_type"
| summarize total = count(), hits = countIf(response_result_type in ("Hit", "RefreshHit"))
| fieldsAdd cache_hit_ratio = hits * 100.0 / total
```

🎯 This produces a **single number tile** for cache hit ratio, which you can format as a **percentage** display tile.

---

## 🧩 Add to Dashboard

1. Go to your Dynatrace Dashboard.
2. Click ➕ "Add tile" → choose **"Custom chart"** or **"Data explorer"**.
3. Select **"Logs"** as data source.
4. Paste the **DQL** in the Query section.
5. Choose **"Pie"**, **"Column"**, or **"Single Value"** based on your preference.
6. Save the tile with a name like **“CloudFront Cache Hit Ratio”**.
