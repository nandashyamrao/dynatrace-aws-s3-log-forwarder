
# 📊 Splunk → Dynatrace (DQL / DPL) Translation Aide (with Notes/Tips)

This sheet maps **common Splunk commands** to **Dynatrace DQL/DPL** with compact inline examples **and a Notes/Tips column** to guide migration choices.  
Full multi‑line examples follow the table.

| **Splunk Concept / Keyword** | **Purpose** | **Dynatrace DQL / DPL Equivalent** | **Example (inline)** | **Notes / Tips** |
|---|---|---|---|---|
| `index=foo` | Data namespace selector | `from logs` + bucket filter | `from logs filter dt.system.bucket=="foo"` | Prefer **buckets** or **data sources** over hardcoding in every query. |
| `sourcetype=eventing` | Source format classifier | `matchesValue(log.source,"eventing")` | `filter matchesValue(log.source,"eventing")` | Normalize to a canonical attribute at **ingest** to keep queries simple. |
| `source=/path/app.log` | File origin | `filter log.file.path` | `filter log.file.path=="/path/app.log"` | Use ingestion metadata; avoid path fragments when possible. |
| `host=web123` | Host filter | `filter host.name` | `filter host.name=="web123"` | Also consider `entity.host.name` depending on ingest. |
| `_time` | Event timestamp | `timestamp` | `fields timestamp,message` | UI time picker sets `timestamp` range automatically. |
| `earliest=-1h latest=now` | Time window | `filter timestamp between` | `filter timestamp between now()-1h and now()` | Prefer UI scope; add filter only for embedded snippets. |
| `field=value` | Exact match | `filter field == "value"` | `filter status=="ERROR"` | String compares are **case-sensitive** by default. |
| `NOT field=value` | Negation | `filter field != "value"` | `filter status!="OK"` | For regex negation use `!matchesValue(field,"pattern")`. |
| `AND / OR` | Boolean logic | same operators | `filter (svc=="A" or svc=="B") and status=="ERROR"` | Parentheses to control precedence—same as Splunk. |
| `rex` (single) | Regex extract | `fieldsAdd f=regex_extract(...)` | `fieldsAdd user=regex_extract(body,"user=(.*?) ")` | Avoid leading `.*`; anchor patterns for speed. |
| `rex` (multi) | Extract multiple | `fieldsAdd f1=regex_extract(...), f2=...` | `fieldsAdd u=regex_extract(b,"u=(\w+)"), ip=regex_extract(b,"ip=(\S+)")` | You can add **multiple** fields in one `fieldsAdd`. |
| `eval` if/case | Create/transform | `fieldsAdd new = if(cond,a,b)` | `fieldsAdd sev=if(status>=500,"CRIT","OK")` | Chain with commas: `fieldsAdd a=..., b=...`. |
| `coalesce(a,b)` | Replace nulls | `coalesce(a,b)` | `fieldsAdd region=coalesce(region,"unknown")` | Works across many args: `coalesce(a,b,c,...)`. |
| `substr(field,1,3)` | Substring | `substring(field,start,len)` | `fieldsAdd pfx=substring(userId,0,3)` | 0‑based index. |
| `round(field,2)` | Rounding | `round(field,n)` | `fieldsAdd latency=round(duration,2)` | Use numeric casts if needed (see `toNumber`). |
| `upper/lower` | Case change | `upper() / lower()` | `fieldsAdd name=upper(user)` | Locale‑agnostic transforms. |
| `tostring/tonumber` | Cast | `toString() / toNumber()` | `fieldsAdd size_num=toNumber(size)` | Validate with `isNull()` after cast. |
| `stats count by f` | Group aggregate | `summarize count() by f` | `summarize count() by service` | Add metrics with commas: `count(), avg(x)`. |
| `stats avg(field)` | Aggregation | `summarize avg(field)` | `summarize avg(duration) by endpoint` | Also `min()`, `max()`, `sum()`, `percentile(x,95)`. |
| `dc(field)` | Distinct count | `countDistinct(field)` | `summarize countDistinct(user) by service` | High cardinality—**prefilter** first. |
| `values(field)` | Set of values | `collectDistinct(field)` | `summarize collectDistinct(error) by service` | Limit output size; for reports only. |
| `timechart span=5m` | Time buckets | `makeTimeseries ... interval 5m` | `makeTimeseries count() interval 5m` | `makeTimeseries` **fills gaps** automatically. |
| `bin span=1h` (time) | Bucket size | `bin(timestamp, 1h)` | `bin(timestamp,1h)` | Aligns to query window. |
| `bin field 10` (num) | Numeric bucketing | `bin(field, 10)` | `bin(bytes,10)` | Use for histograms on numeric fields. |
| `fillnull` | Fill missing | `coalesce()` | `fieldsAdd errors=coalesce(errors,0)` | Fill per‑field; no global fill. |
| `dedup field` | De‑duplicate | `summarize take_any(*) by field` | `summarize take_any(*) by requestId` | For **latest per key**, compute `max(timestamp)` then filter on it. |
| `mvexpand` | Expand multivalue | `unfold field` | `unfold tags` | Pre‑explode at ingest if arrays are huge. |
| `lookup table.csv` | Enrichment | Ingest enrichment or `join` | `join on userId (from ref_users)` | Prefer **ingest‑time** enrichment for scale. |
| `join type=inner/left` | Join datasets | `join` | `join left on sessionId (from B)` | Keep keys small; avoid many‑to‑many explosions. |
| `transaction` | Session stitching | Group by session id | `summarize count() by sessionId` | Model sessions at ingest when possible. |
| `where condition` | Post‑filter | `filter condition` | `filter count > 10` | Works before/after `summarize`. |
| `sort - count` | Ordering | `sort count desc` | `sort count desc` | Sorting is memory‑heavy; limit first when possible. |
| `head 10` | Limit rows | `limit 10` | `limit 10` | Use early to reduce payload. |
| `spath` | JSON extract | `parse json(...)` | `fieldsAdd traceId=json:body.trace.id` | Parse early; **flatten** selectively for speed. |
| `table f1,f2` | Projection | `fields f1, f2` | `fields timestamp, service, status` | Shrinks payload; do it early. |
| `rename a AS b` | Rename | `fieldsRename a as b` | `fieldsRename service as svc` | Keep final names consistent across dashboards. |
| `tags` | Log tags | Ingest or `fieldsAdd` | `fieldsAdd env="prod"` | Prefer tagging centrally (OpenPipeline / rules). |
| Alert (Splunk) | Alert threshold | `filter + summarize + filter` | `filter status>=500 summarize c=count() by svc filter c>10` | Convert to **Metric Event** or **Workflow** for automation. |

---

## 🔧 Full Multi‑line Examples

### 1️⃣ Basic Filter + Count
```dql
from logs
| filter dt.system.bucket == "foo" and status == "ERROR"
| summarize error_count = count() by service
| sort error_count desc
| limit 10
```

### 2️⃣ Time Series (Splunk `timechart span=5m`)
```dql
from logs
| filter matchesValue(log.source, "eventing")
| makeTimeseries count() interval 5m
```

### 3️⃣ Field Extraction + Aggregation
```dql
from logs
| fieldsAdd user = regex_extract(body, "user=(\w+)")
         , ip   = regex_extract(body, "ip=(\S+)")
| summarize count() by user, ip
```

### 4️⃣ Distinct Users per Service (dc / values)
```dql
from logs
| filter status == "OK"
| summarize users = countDistinct(user), samples = collectDistinct(endpoint) by service
```

### 5️⃣ Session‑like Grouping (transaction analogue)
```dql
from logs
| filter timestamp between now()-1h and now()
| fieldsAdd sess = coalesce(sessionId, trace.id)
| summarize events=count(), first_ts=min(timestamp), last_ts=max(timestamp) by sess
| filter events > 10
```

---

### 🔑 Tips Recap
- ✅ **Normalize at ingest** (source/sourcetype/host/tags) to simplify queries.
- ✅ Use `makeTimeseries` for charts; it **fills gaps**.
- ✅ Use `unfold` for arrays (Splunk `mvexpand`).
- ✅ Do heavy operations (`join`, `countDistinct`) **after prefilters**.
- ✅ Keep result sets small with early `fields`, `limit`, and selective filters.

