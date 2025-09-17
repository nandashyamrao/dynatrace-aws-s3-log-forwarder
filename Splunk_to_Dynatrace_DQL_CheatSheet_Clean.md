
# 📊 Splunk → Dynatrace (DQL / DPL) Translation Aide

This consolidated reference sheet maps **Splunk concepts & commands** to **Dynatrace DQL/DPL equivalents** with **compact inline examples**.  
Full multi-line query examples are provided below the table.

| **Splunk Concept / Keyword** | **Purpose** | **Dynatrace DQL / DPL Equivalent** | **Example (Inline)** |
|-----------------------------|-------------|----------------------------------|----------------------|
| `index=foo` | Data namespace selector | `from logs` + filter | `from logs filter dt.system.bucket == "foo"` |
| `sourcetype=eventing` | Source format classifier | `matchesValue(log.source,"eventing")` | `filter matchesValue(log.source,"eventing")` |
| `source=/path/app.log` | File origin | `filter log.file.path` | `filter log.file.path == "/path/app.log"` |
| `host=web123` | Host filter | `filter host.name` | `filter host.name == "web123"` |
| `_time` | Event timestamp | `timestamp` field | `fields timestamp, message` |
| `earliest=-1h latest=now` | Time window | `filter timestamp between` | `filter timestamp between now()-1h and now()` |
| `field=value` | Exact match | `filter field == "value"` | `filter status == "ERROR"` |
| `NOT field=value` | Negation | `filter field != "value"` | `filter status != "OK"` |
| `AND / OR` | Boolean logic | Same operators | `filter (service=="A" or service=="B") and status=="ERROR"` |
| `rex` | Regex extraction | `fieldsAdd ...=regex_extract(...)` | `fieldsAdd user=regex_extract(body,"user=(.*?) ")` |
| `eval` | Create / transform | `fieldsAdd new=expr` | `fieldsAdd sev=if(status>=500,"CRIT","OK")` |
| `coalesce(a,b)` | Replace nulls | `coalesce(a,b)` | `fieldsAdd region=coalesce(region,"unknown")` |
| `substr(field,1,3)` | Substring | `substring(field, start,len)` | `fieldsAdd prefix=substring(userId,0,3)` |
| `round(field,2)` | Rounding | `round(field,n)` | `fieldsAdd latency=round(duration,2)` |
| `stats count by f` | Group aggregate | `summarize count() by f` | `summarize count() by service` |
| `stats avg(field)` | Aggregation | `summarize avg(field)` | `summarize avg(duration) by endpoint` |
| `timechart span=5m` | Time buckets | `makeTimeseries ... interval 5m` | `makeTimeseries count() interval 5m` |
| `fillnull` | Fill missing | `coalesce()` | `fieldsAdd errors=coalesce(errors,0)` |
| `dedup field` | Deduplicate | `summarize take_any(*) by field` | `summarize take_any(*) by requestId` |
| `mvexpand` | Expand multi-value | `unfold fieldName` | `unfold tags` |
| `lookup table.csv` | Enrichment | Ingest enrichment or join | `join on userId (from datasetB)` |
| `join` | Join datasets | `join` | `join on sessionId (from otherDataset)` |
| `transaction` | Session stitching | `makeGroup()` | `summarize count() by sessionId` |
| `where condition` | Post-filter | `filter condition` | `filter count > 10` |
| `sort -count` | Ordering | `sort count desc` | `sort count desc` |
| `head 10` | Limit rows | `limit 10` | `limit 10` |
| `upper(field)` | Uppercase | `upper(field)` | `fieldsAdd name=upper(user)` |
| `lower(field)` | Lowercase | `lower(field)` | `fieldsAdd path=lower(file)` |
| `spath` | JSON extract | `parse json(...)` | `fieldsAdd traceId=json:body.trace.id` |
| `table f1,f2` | Projection | `fields f1,f2` | `fields timestamp, service, status` |
| `tags` | Log tags | Prefer ingest tagging | `fieldsAdd env="prod"` |
| `alert threshold` | Alert condition | `filter + summarize` | `filter status>=500 summarize count() by service filter count>10` |

---

## 🔧 Full Example Queries

### 1️⃣ **Basic Filter + Count**
```dql
from logs
| filter dt.system.bucket == "foo" and status == "ERROR"
| summarize count() by service
| sort count desc
| limit 10
```

### 2️⃣ **Time Series (Splunk `timechart`)**
```dql
from logs
| filter matchesValue(log.source, "eventing")
| makeTimeseries count() interval 5m
```

### 3️⃣ **Field Extraction + Aggregation**
```dql
from logs
| fieldsAdd user=regex_extract(body,"user=(.*?) "), ip=regex_extract(body,"ip=(.*?) ")
| summarize count() by user, ip
```

### 4️⃣ **Alert Condition**
```dql
from logs
| filter status >= 500
| summarize error_count = count() by service
| filter error_count > 10
```

---

### 🔑 Key Tips
- ✅ **Always prefer ingest-time normalization** (sourcetype, host, tags).
- ✅ Use `makeTimeseries` for time-based analysis (gap-filling included).
- ✅ Use `fieldsAdd` to replicate Splunk `eval` logic.
- ✅ `unfold` is your friend for array fields (Splunk `mvexpand`).

