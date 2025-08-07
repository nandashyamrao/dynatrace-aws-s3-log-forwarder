
# 📘 Dynatrace CloudFront Dashboard (Simple Version)

This is a minimal dashboard setup to monitor CloudFront logs with interactive filters.

---

## 🎛️ Dashboard Variables

### 🔹 aws_account_id
```dql
fetch logs
| summarize by aws_account_id
```

### 🔹 distribution_id
```dql
fetch logs
| summarize by distribution_id
```

### 🔹 distribution_name
```dql
fetch logs
| summarize by distribution_name
```

Use these variables in queries like:

```dql
fetch logs
| filter (isNull("$aws_account_id") or aws_account_id == "$aws_account_id")
      and (isNull("$distribution_id") or distribution_id == "$distribution_id")
      and (isNull("$distribution_name") or distribution_name == "$distribution_name")
| summarize count() by bin(timestamp, 5m)
```

---

## 📊 Sample Panel: Total CloudFront Requests

### DQL
```dql
fetch logs
| filter (isNull("$aws_account_id") or aws_account_id == "$aws_account_id")
      and (isNull("$distribution_id") or distribution_id == "$distribution_id")
      and (isNull("$distribution_name") or distribution_name == "$distribution_name")
| summarize count() as total_requests by bin(timestamp, 5m)
```

---

Next: Expand with latency, errors, geo, and cache hit ratio panels.
