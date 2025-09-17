
# 📊 Splunk → Dynatrace (DQL / DPL) Translation Aide

This consolidated reference sheet maps **Splunk concepts & commands** to **Dynatrace DQL/DPL equivalents** with simple examples.  
Use it as a quick guide during migration.

| **Splunk Concept / Keyword** | **Purpose** | **Dynatrace DQL / DPL Equivalent** | **Example** |
|-----------------------------|-------------|----------------------------------|-------------|
| `index=foo` | Data namespace selector | `from logs` with filter on `dt.system.bucket` | ```dql
from logs
filter dt.system.bucket == "foo"
``` |
| `sourcetype=eventing` | Source format classifier | Normalize via ingest rule, or use `matchesValue()` | ```dql
filter matchesValue(log.source, "eventing")
``` |
| `source=/path/app.log` | File origin | `filter log.file.path` | ```dql
filter log.file.path == "/path/app.log"
``` |
| `host=web123` | Host filter | `filter host.name` | ```dql
filter host.name == "web123"
``` |
| `_time` | Event timestamp | `timestamp` field | ```dql
fields timestamp, message
``` |
| `earliest=-1h latest=now` | Time window | UI time picker or `filter timestamp between` | ```dql
filter timestamp between now()-1h and now()
``` |
| `field=value` | Exact match | `filter field == "value"` | ```dql
filter status == "ERROR"
``` |
| `NOT field=value` | Negation | `filter field != "value"` | ```dql
filter status != "OK"
``` |
| `AND / OR` | Boolean logic | Same operators in DQL | ```dql
filter (service == "A" or service == "B") and status=="ERROR"
``` |
| `rex` | Regex extraction | `fieldsAdd field=regex_extract()` | ```dql
fieldsAdd user=regex_extract(body, "user=(.*?) ")
``` |
| `eval` | Create / transform fields | `fieldsAdd newfield = expression` | ```dql
fieldsAdd severity = if(status >= 500, "CRITICAL", "OK")
``` |
| `coalesce(a,b)` | Replace nulls | `coalesce(a,b)` | ```dql
fieldsAdd region = coalesce(region, "unknown")
``` |
| `substr(field,1,3)` | Substring | `substring(field, start, length)` | ```dql
fieldsAdd prefix = substring(userId,0,3)
``` |
| `round(field,2)` | Rounding | `round(field, 2)` | ```dql
fieldsAdd latency_ms = round(duration,2)
``` |
| `stats count by field` | Group aggregate | `summarize count() by field` | ```dql
summarize count() by service
``` |
| `stats avg(field)` | Aggregation | `summarize avg(field)` | ```dql
summarize avg(duration) by endpoint
``` |
| `timechart span=5m` | Time buckets | `makeTimeseries count() interval 5m` | ```dql
makeTimeseries count() interval 5m
``` |
| `fillnull` | Fill missing | `coalesce()` | ```dql
fieldsAdd errorCount = coalesce(errorCount, 0)
``` |
| `dedup field` | Deduplicate events | `summarize take_any(*) by field` | ```dql
summarize take_any(*) by requestId
``` |
| `mvexpand` | Expand multivalue | `unfold fieldName` | ```dql
unfold tags
``` |
| `lookup table.csv` | Enrichment | Ingest-time enrichment or `lookup join` | ```dql
enrichment lookup / join preview
``` |
| `join` | Join datasets | `lookup / join` | ```dql
join on requestId (from datasetB)
``` |
| `transaction` | Session stitching | `makeGroup()` or `summarize sessionId` | ```dql
summarize count() by sessionId
``` |
| `where condition` | Filter after aggregation | `filter condition` | ```dql
filter count > 10
``` |
| `sort - count` | Ordering | `sort count desc` | ```dql
sort count desc
``` |
| `head 10` | Limit rows | `limit 10` | ```dql
limit 10
``` |
| `upper(field)` | Uppercase | `upper(field)` | ```dql
fieldsAdd user_upper = upper(user)
``` |
| `lower(field)` | Lowercase | `lower(field)` | ```dql
fieldsAdd path_lower = lower(path)
``` |
| `spath` | JSON extract | `parse json(body)` | ```dql
fieldsAdd traceId = json:body.trace.id
``` |
| `table field1,field2` | Projection | `fields field1, field2` | ```dql
fields timestamp, service, status
``` |
| `tags` | Log tags | Prefer ingest-time tagging | ```dql
fieldsAdd env="prod"
``` |
| `alert threshold` | Alert condition | `filter + summarize` | ```dql
filter status >= 500
summarize count() by service
filter count > 10
``` |

---

### 🔑 Key Takeaways
- ✅ **Prefer ingest-time enrichment** for sourcetype, host, tags — simplifies queries.
- ✅ Use `makeTimeseries` for gap-filled time charts.
- ✅ Use `fieldsAdd` to create derived attributes (Splunk `eval`).

---

