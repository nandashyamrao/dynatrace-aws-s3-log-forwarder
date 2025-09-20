# 📘 LD Cheat Sheet for Dynatrace DQL Parsing

This guide maps **common log patterns** (often extracted in Splunk with `rex`) into **Dynatrace DQL `parse` patterns** using the `LD` (Literal Delimiter) operator.  

---

## 🔎 What is `LD`?
- **LD = Literal Delimiter**  
- It anchors on **fixed text in a log message**.  
- It does not capture itself — only the value **after** the literal is extracted.  

---

## 🧩 Syntax
```dql
parse content, "LD '<literal>' <TYPE:fieldname>"
```

- `LD '<literal>'` → the anchor string to locate.  
- `<TYPE:fieldname>` → extract the following token into a new field.  

Types:  
- `STRING` → free text values (usernames, IPs, paths)  
- `INT` → integers (status codes, IDs)  
- `FLOAT` → decimals (latency, response time)  

---

## 📝 Examples

| **Log Example** | **Goal** | **DQL Parse Pattern** | **Resulting Fields** |
|-----------------|----------|-----------------------|-----------------------|
| `INFO Request finished HTTP_STATUS 404 path=/login` | Extract HTTP status | `| parse content, "LD 'HTTP_STATUS ' INT:httpstatus"` | `httpstatus = 404` |
| `DEBUG login success UserID=john.doe Session=xyz123` | Extract user ID | `| parse content, "LD 'UserID=' STRING:user"` | `user = "john.doe"` |
| `Transaction completed response_time=12.37 ms` | Extract response time | `| parse content, "LD 'response_time=' FLOAT:resp_time"` | `resp_time = 12.37` |
| `2025-09-20 ERROR Payment failed ErrorCode: 503 Retry` | Extract error code | `| parse content, "LD 'ErrorCode:' INT:error"` | `error = 503` |
| `INFO status=200 duration=15.62ms` | Extract status & duration | `| parse content, "LD 'status=' INT:status LD ' duration=' FLOAT:duration"` | `status = 200`, `duration = 15.62` |
| `INFO User alice logged in from 192.168.0.12` | Extract username & IP | `| parse content, "LD 'User ' STRING:user LD ' logged in from ' STRING:ip"` | `user = "alice"`, `ip = "192.168.0.12"` |
| `INFO login User=jane SessionID=abc123`<br>`INFO logout SessionID=xyz987` | Extract session IDs | `| parse content, "LD 'SessionID=' STRING:session"` | `session = "abc123"`<br>`session = "xyz987"` |
| `WARN OrderID=78432 CustomerID=9981 Status=FAILED` | Extract multiple fields | `| parse content, "LD 'OrderID=' INT:order LD ' CustomerID=' INT:customer LD ' Status=' STRING:status"` | `order = 78432`, `customer = 9981`, `status = "FAILED"` |
| `GET /api/v1/orders 200 123ms` | Extract path, status, duration | `| parse content, "LD 'GET ' STRING:path STRING:status STRING:duration"` | `path = "/api/v1/orders"`, `status = "200"`, `duration = "123ms"` |
| `user=admin action=delete resource=server01` | Extract user, action, resource | `| parse content, "LD 'user=' STRING:user LD ' action=' STRING:action LD ' resource=' STRING:resource"` | `user = "admin"`, `action = "delete"`, `resource = "server01"` |

---

## ✅ Best Practices
1. Anchor on **stable text** like `status=`, `UserID=`, `ErrorCode:`.  
2. Choose the right **type** (`INT`, `FLOAT`, `STRING`).  
3. Chain multiple `LD`s to capture multiple fields in one pass.  
4. Start small (one field), then expand your parse pattern.  

---

⚡ Use this cheat sheet when converting **Splunk `rex` extractions** to **Dynatrace `parse` with LD** during Splunk → Dynatrace migration.


---

## 🔁 Splunk `rex` vs Dynatrace `parse` (Side‑by‑Side)

This section helps you convert common **Splunk `rex`** patterns into **Dynatrace `parse` with `LD`**.

> **Rule of thumb**:  
> - `rex field=_raw "prefix(?<field>pattern)"` ⟶ `parse content, "LD 'prefix' <TYPE:field>"`  
> - Use `INT`, `FLOAT`, or `STRING` based on the value you need.

### 1) HTTP Status Extraction
**Splunk**
```spl
| rex field=_raw "HTTP_STATUS\s+(?<httpstatus>\d+)"
```
**Dynatrace**
```dql
| parse content, "LD 'HTTP_STATUS ' INT:httpstatus"
```

### 2) Key=Value (UserID)
**Splunk**
```spl
| rex field=_raw "UserID=(?<user>[^\s]+)"
```
**Dynatrace**
```dql
| parse content, "LD 'UserID=' STRING:user"
```

### 3) Duration with Units
**Splunk**
```spl
| rex field=_raw "duration=(?<duration>\d+(?:\.\d+)?)ms"
```
**Dynatrace**
```dql
| parse content, "LD 'duration=' FLOAT:duration"
```

### 4) Multiple Captures on One Line
**Splunk**
```spl
| rex field=_raw "status=(?<status>\d+)\s+duration=(?<duration>\d+(?:\.\d+)?)ms"
```
**Dynatrace**
```dql
| parse content, "LD 'status=' INT:status LD ' duration=' FLOAT:duration"
```

### 5) IP After a Phrase
**Splunk**
```spl
| rex field=_raw "logged in from\s+(?<ip>\S+)"
```
**Dynatrace**
```dql
| parse content, "LD 'logged in from ' STRING:ip"
```

### 6) Session IDs in Different Messages
**Splunk**
```spl
| rex field=_raw "SessionID=(?<session>\S+)"
```
**Dynatrace**
```dql
| parse content, "LD 'SessionID=' STRING:session"
```

### 7) Order/Customer/Status Trio
**Splunk**
```spl
| rex field=_raw "OrderID=(?<order>\d+)\s+CustomerID=(?<customer>\d+)\s+Status=(?<status>\S+)"
```
**Dynatrace**
```dql
| parse content, "LD 'OrderID=' INT:order LD ' CustomerID=' INT:customer LD ' Status=' STRING:status"
```

### 8) Generic Key=Value Triplet
**Splunk**
```spl
| rex field=_raw "user=(?<user>\S+)\s+action=(?<action>\S+)\s+resource=(?<resource>\S+)"
```
**Dynatrace**
```dql
| parse content, "LD 'user=' STRING:user LD ' action=' STRING:action LD ' resource=' STRING:resource"
```

### 9) Path + Status + Time (Simple Access Log)
**Splunk**
```spl
| rex field=_raw "GET\s+(?<path>\S+)\s+(?<status>\d{3})\s+(?<duration>\d+ms)"
```
**Dynatrace**
```dql
| parse content, "LD 'GET ' STRING:path STRING:status STRING:duration"
```

### 10) Error Code with Label
**Splunk**
```spl
| rex field=_raw "ErrorCode:\s*(?<error>\d+)"
```
**Dynatrace**
```dql
| parse content, "LD 'ErrorCode:' INT:error"
```

---

### Tips for Accurate Conversions
- Prefer **stable anchors** (e.g., `status=`, `UserID=`, `ErrorCode:`).  
- If values may be non‑numeric (e.g., `status=OK`), use `STRING` instead of `INT`.  
- Chain `LD` segments to extract multiple fields from a single line.  
- If the anchor text can vary, consider multiple `parse` statements or pre‑normalize logs in **OpenPipeline**.  
- Validate with a quick **`| take 20`** to spot formatting quirks before rolling out broadly.

