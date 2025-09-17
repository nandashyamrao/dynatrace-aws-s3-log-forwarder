
# 🚀 Splunk → Dynatrace Migration Guidance (Improved)

This section provides **actionable, clear steps** to migrate Splunk searches to Dynatrace DQL/DPL.

---

## 🔧 **Improved Migration Guidance (Actionable)**

### 1️⃣ **Classify Searches Before Migration**
Break each Splunk search into **use case types** — so you know what Dynatrace construct it should map to:
- **📊 Dashboards / Timecharts** → `makeTimeseries` + `summarize` → *Dashboards & Notebooks*
- **🔔 Alerts / Monitors** → DQL + `filter` + `summarize` → *Metric Events* or *Workflow triggers*
- **🕵️‍♂️ Ad-hoc Investigations** → Direct `from logs` queries → *Exploratory Queries*

---

### 2️⃣ **Handle Time-based Searches**
- Convert `timechart` + `span` to `makeTimeseries ... interval`.
- Use **bin()** only for aggregations, avoid where time functions can be pushed to UI picker.
- Replace Splunk `rolling windows` with DQL metrics + alert rules.

---

### 3️⃣ **Translate Session or Transaction Logic**
- Splunk `transaction` → derive a session key (`trace.id`, `session.id`) at ingest.
- Use `summarize ... by sessionId` and calculate `min(timestamp), max(timestamp), count()`.

---

### 4️⃣ **Ingest Enrichment & Lookups**
- Move Splunk `lookup` tables to **Dynatrace Grail lookup datasets**.
- Join at query time only if absolutely necessary (`join` is expensive).
- Normalize key fields (host, env, app) at ingest so you can filter fast.

---

### 5️⃣ **Canonicalize & Normalize Early**
- Map Splunk `sourcetype`, `index`, `source` → DQL attributes (`log.source`, `dt.system.bucket`).
- Standardize field names across data sources (`status`, `env`, `team`).

---

### 6️⃣ **Guard Against Cardinality Explosion**
- Replace `values(field)` with `collectDistinct(field)` only for reporting.
- Use `countDistinct(field)` sparingly and pre-filter logs.

---

### 7️⃣ **Best Practices for Alert Conversion**
- Always `filter` first, then `summarize`, then final `filter` (threshold).
- Convert to **Metric Events** where possible (cheaper, faster).
- Keep thresholds as variables in workflows (easy to tune).

---

## 🚫 **Common Pitfalls to Avoid**
| Pitfall | Why It’s Problematic | Fix |
|--------|--------------------|-----|
| Using `matchesValue(".*text.*")` broadly | Regex scan on every event = slow | Normalize fields and filter on exact match |
| Large unfiltered `summarize by` | Memory heavy, slow queries | Pre-filter on env, service, timeframe |
| Carrying over hidden macros | Loss of transparency | Expand macros before migration |
| Recreating Splunk `transaction` 1:1 | Dynatrace uses trace/session context differently | Redesign with session keys and summarize logic |

---

## 🎯 **Migration Priorities**
1. **Correlate IDs** early (session, trace, user) → enable DQL joins & groupings.
2. **Normalize fields** at ingest (source, host, env).
3. **Push enrichment to ingest phase** — avoid runtime joins when possible.
4. **Convert recurring searches to metricization** → saves cost + improves alert speed.
5. **Test performance** with `limit` before scaling query for production dashboards.

---

## ✅ **Improved Sample Migration Pattern**

```dql
from logs
| filter log.level == "ERROR"
| filter matchesValue(body, ".*StaleConnectionException.*")
| summarize per_minute = count() by bin(timestamp, 1m)
| fieldsAdd minuteHasError = per_minute > 0
| summarize error_minutes = count() by bin(timestamp, 3m)
| filter error_minutes >= 3
```

🔑 **What’s Happening:**
- First `summarize` buckets logs per minute.
- Then we derive a flag (`minuteHasError`) for each minute.
- Final aggregation counts minutes with errors over 3-min windows (like Splunk rolling window).
