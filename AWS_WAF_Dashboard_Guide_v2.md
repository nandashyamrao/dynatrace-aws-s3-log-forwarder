# 🛡️ AWS WAF Dashboard Guide (Dynatrace Logs + DQL)

This guide is designed for building a clear, user-friendly **AWS WAF** dashboard in Dynatrace.  
All queries below use your ingestion routing filter:

✅ **`dt.system.bucket == "aws_waf"`**

---

## ✅ Global Notes (applies to every tile)

- **Data source**: Dynatrace Logs (WAF events parsed into fields like `waf_action`, `waf_uri`, `waf_client_ip`, etc.)
- **Filter convention** (use in every tile):
  ```dql
  fetch logs
  | filter dt.system.bucket == "aws_waf"
  ```
- **Common WAF action values**: `ALLOW`, `BLOCK`, `COUNT`

---

# 🧭 Section 1 — Executive Summary (Top-line posture)

## 1. Action Distribution (Counts + %)

**Purpose of tile:**  
Show the overall traffic decision breakdown (how much is allowed vs blocked).

**What this indicates:**  
A quick health/security posture view. A sudden rise in **BLOCK %** can indicate an attack, misconfiguration, or new rule rollout.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| summarize requests = count() by waf_action
| fieldsAdd total = sum(requests) over ()
| fieldsAdd percentage = round(100.0 * requests / total, 2)
| sort percentage desc
```

**Recommended visualization:** Donut or stacked bar.

---

## 2. Total Requests (Single Value)

**Purpose of tile:**  
Show total WAF-observed requests in the selected timeframe.

**What this indicates:**  
A baseline “traffic volume” indicator. Use it to compare with blocked volume spikes.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| summarize total_requests = count()
```

**Recommended visualization:** Single value.

---

## 3. Blocked Requests (Single Value)

**Purpose of tile:**  
Show total blocked requests in the selected timeframe.

**What this indicates:**  
Absolute block volume. Pair it next to total requests to interpret scale.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count()
```

**Recommended visualization:** Single value.

---

## 4. Block Rate % (Single Value)

**Purpose of tile:**  
Show the percentage of requests blocked.

**What this indicates:**  
The primary exec metric: “What % of traffic is hostile or rejected?”

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| summarize requests = count() by waf_action
| fieldsAdd total = sum(requests) over ()
| fieldsAdd blocked = sum(if(waf_action == "BLOCK", requests, 0)) over ()
| fieldsAdd block_rate_pct = round(100.0 * blocked / total, 2)
| fields block_rate_pct
```

**Recommended visualization:** Single value (with threshold coloring if desired).

---

# 🧱 Section 2 — Endpoint Abuse (What’s being targeted)

## 5. Top Blocked URIs (Endpoint Abuse)

**Purpose of tile:**  
Identify which endpoints are being attacked/abused.

**What this indicates:**  
If one URI dominates blocks, it may indicate scraping, brute force, injection attempts, or bot activity aimed at that endpoint.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count() by waf_uri
| sort blocked_requests desc
| limit 20
```

**Recommended visualization:** Table or bar chart.

---

## 6. URI Allow vs Block (Per Endpoint)

**Purpose of tile:**  
Compare allowed vs blocked traffic per endpoint.

**What this indicates:**  
Which endpoints are both heavily used and heavily attacked. Useful for prioritizing protection and tuning rules.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| summarize requests = count() by waf_uri, waf_action
| sort requests desc
```

**Recommended visualization:** Stacked bar (waf_action as series) or table.

---

## 7. URI Block Rate % (Per Endpoint)

**Purpose of tile:**  
Show which endpoints have the highest **block percentage**, not just raw counts.

**What this indicates:**  
Helps highlight “high risk” endpoints even if total traffic is smaller.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| summarize requests = count() by waf_uri, waf_action
| summarize
    total = sum(requests),
    blocked = sum(if(waf_action == "BLOCK", requests, 0))
  by waf_uri
| fieldsAdd block_rate_pct = round(100.0 * blocked / total, 2)
| sort block_rate_pct desc
| limit 20
```

**Recommended visualization:** Table.

---

# 🔧 Section 3 — Rule Effectiveness (Why did it block?)

## 8. Top Terminating Rule IDs (Blocked)

**Purpose of tile:**  
Show which rule is actually making the decision to block.

**What this indicates:**  
Whether managed rules vs custom rules are doing most of the work; helps validate policy and reduce false positives.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count() by waf_terminating_rule_id
| sort blocked_requests desc
| limit 20
```

**Recommended visualization:** Table.

---

## 9. Terminating Rule Types (Blocked)

**Purpose of tile:**  
Show what “type” of terminating rules are responsible (e.g., REGULAR, etc.)

**What this indicates:**  
High-level classification of enforcement behavior; helpful when multiple rule-set strategies exist.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count() by waf_terminating_rule_type
| sort blocked_requests desc
```

**Recommended visualization:** Bar chart.

---

# 🧑‍💻 Section 4 — Attacker / Client Insights (Who is doing it?)

## 10. Top Attacking Client IPs (Blocked)

**Purpose of tile:**  
Identify IPs with the most blocked requests.

**What this indicates:**  
Repeat offenders, bot nodes, or abusive clients. Useful for triage and allow/deny lists.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count() by waf_client_ip, waf_country
| sort blocked_requests desc
| limit 20
```

**Recommended visualization:** Table.

---

## 11. Blocked Requests by Country

**Purpose of tile:**  
High-level geographic concentration of blocked traffic.

**What this indicates:**  
If a single region spikes, it may indicate region-specific abuse or botnet distribution.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count() by waf_country
| sort blocked_requests desc
| limit 20
```

**Recommended visualization:** Table or bar chart (or map if available).

---

# 🌐 Section 5 — HTTP Characteristics (How are they hitting?)

## 12. Blocked Requests by Method

**Purpose of tile:**  
See which HTTP methods are associated with blocks.

**What this indicates:**  
- High `GET` blocks → scraping/scanning  
- High `POST` blocks → injection/login brute force, etc.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count() by waf_method
| sort blocked_requests desc
```

**Recommended visualization:** Bar chart.

---

## 13. Blocked Requests by Host

**Purpose of tile:**  
Show which hostnames are getting blocked activity.

**What this indicates:**  
Pinpoints which apps/domains are under attack (or misconfigured).

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count() by waf_host
| sort blocked_requests desc
| limit 20
```

**Recommended visualization:** Table.

---

# 🕒 Section 6 — Trend & Spike Detection (When did it happen?)

## 14. Requests Over Time (All Actions)

**Purpose of tile:**  
Trend total request volume across time.

**What this indicates:**  
Traffic surges, baseline changes, or sudden drops (pipeline/ingestion issues).

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| summarize requests = count(), interval: 1m
```

**Recommended visualization:** Time series.

---

## 15. Blocked Requests Over Time

**Purpose of tile:**  
Trend block activity across time.

**What this indicates:**  
Attack windows, bot bursts, or new rule deployments.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| filter waf_action == "BLOCK"
| summarize blocked_requests = count(), interval: 1m
```

**Recommended visualization:** Time series.

---

# 🧪 Section 7 — Troubleshooting / Data Quality (Is parsing working?)

## 16. Quick Field Presence Check

**Purpose of tile:**  
Confirm key parsed fields are present (non-null) for recent logs.

**What this indicates:**  
Validates pipeline/processor parsing. If this drops, your processor may have stopped matching new log formats.

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| summarize
    total = count(),
    uri_present = sum(if(isNotNull(waf_uri), 1, 0)),
    ip_present  = sum(if(isNotNull(waf_client_ip), 1, 0)),
    rule_present = sum(if(isNotNull(waf_terminating_rule_id), 1, 0))
```

**Recommended visualization:** Table (single row) or single values.

---

# ✅ Suggested Dashboard Layout (Practical)

1. **Executive Summary** (tiles 1–4)  
2. **Endpoint Abuse** (tiles 5–7)  
3. **Rule Effectiveness** (tiles 8–9)  
4. **Attacker Insights** (tiles 10–11)  
5. **HTTP Characteristics** (tiles 12–13)  
6. **Trends** (tiles 14–15)  
7. **Data Quality** (tile 16)

---

## 📝 Optional: “Definition” blurb for users (copy/paste)

- **ALLOW**: Request permitted by WAF evaluation  
- **BLOCK**: Request denied by WAF evaluation  
- **COUNT**: Rule matched but only counted (not enforced)

---


## 🔄 Updated WAF Action Percentage Query (Validated)

```dql
fetch logs
| filter dt.system.bucket == "aws_waf"
| summarize requests = count(), by:{waf_action}
| summarize total = sum(requests), data = collectArray(record(waf_action, requests))
| expand data
| fieldsAdd waf_action = data[waf_action], requests = data[requests]
| fieldsAdd percentage = round(100.0 * requests / total, 2)
| sort percentage desc
```