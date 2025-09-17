# 📊 Splunk → Dynatrace Grail Migration Reference

This sheet helps map Splunk’s common metadata fields and query patterns into Dynatrace (with Owning Area Buckets).

---

## 🔑 Field Mapping

| Splunk        | Dynatrace (your setup)                          | Notes                                                                                                                                                                                                 |
|---------------|-------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Index**     | **Owning Area Bucket** (custom attribute)       | Logical container/grouping. In DT, you enrich logs with `log.bucket=ClaimsApps`, `log.bucket=ITSM`, etc.                                                                                              |
| **Sourcetype**| **Source Type Attribute** (e.g., `source.type`) | Identifies log format/type. Same role as Splunk sourcetype.                                                                                                                                           |
| **Source**    | **log.source / dt.source**                      | Original source (e.g., file path, log stream, S3 bucket).                                                                                                                                             |
| **Host**      | **dt.entity.host / host.name**                  | Host or entity producing the log. Useful for infra-level correlations.                                                                                                                                |
| **_time**     | **timestamp**                                   | Event time, parsed by Grail. DT always uses `timestamp` as standard.                                                                                                                                  |
| **_raw**      | **content**                                     | Raw event body in Splunk = `content` field in DT. All extractions/regex happen here.                                                                                                                  |
| **eventtype** | **Custom Attribute (e.g., log.eventType)**      | Splunk “eventtype” is a saved search or tag. In DT, represent it as an enrichment tag (e.g., `log.eventType="IncidentClosed"`).                                                                       |
| **host/ip**   | **network.client.ip / network.server.ip**       | Splunk’s `host`/`ip` fields → DT’s structured network attributes (if logs contain IPs).                                                                                                               |
| **sourceapp** | **dt.entity.process_group / service.name**      | App or service that generated the log. DT automatically enriches if entity detection works; else set a custom attribute.                                                                              |
| **user**      | **user.name**                                   | If Splunk logs include `user=...`, you can map to `user.name` in DT for analytics.                                                                                                                    |
| **fields**    | **extracted attributes**                        | In Splunk, KV pairs often become fields. In DT, you use log processing rules to extract into structured attributes.                                                                                    |
| **tag::xxx**  | **log.tag.xxx / dt.tag.xxx**                    | Splunk “tag” system → represented as log attributes or Grail tags.                                                                                                                                    |
| **linecount** | **Not needed**                                  | Splunk field for multiline events. DT handles multi-line automatically; no separate field.                                                                                                            |
| **event_id**  | **dt.event.id (or custom)**                     | Splunk may create `_cd` or unique ID. In DT, you can retain as custom attribute if needed for deduplication or correlation.                                                                            |

---

## 🔄 Side-by-Side Query Examples

### Example 1: ITSM Incidents

**Splunk**  
```spl
index=itsm sourcetype=sm9_incident "Ticket Closed"
```

**Dynatrace DQL**  
```dql
fetch logs
| filter log.bucket == "itsm"
| filter source.type == "sm9_incident"
| filter contains(content, "Ticket Closed")
```

---

### Example 2: Filter by Host and Time

**Splunk**  
```spl
index=app_logs sourcetype=web host=web01 earliest=-15m
```

**Dynatrace DQL**  
```dql
fetch logs
| filter log.bucket == "app_logs"
| filter source.type == "web"
| filter dt.entity.host == "web01"
| filter timestamp > now() - 15m
```

---

### Example 3: Extracting Fields

**Splunk**  
```spl
index=security sourcetype=aws:cloudtrail | rex "userName=(?<user>[^ ]+)"
```

**Dynatrace DQL**  
```dql
fetch logs
| filter log.bucket == "security"
| filter source.type == "aws:cloudtrail"
| parse content, "userName=* user:LD"
```

---

## ✅ Key Takeaways
- Splunk **Index** → DT **Owning Area Bucket**.  
- Splunk **Sourcetype** → DT **Source Type Attribute**.  
- Splunk **_raw** → DT **content**.  
- Splunk **_time** → DT **timestamp**.  
- Everything else becomes a **log attribute** in DT.  

---
