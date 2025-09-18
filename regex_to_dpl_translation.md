# 📘 Regex → DPL (Dynatrace) Translation Guide with Log Examples

## 1️⃣ Anchors & “Starts with / Ends with”  

**Log**  
```
ERROR Connection reset
INFO  Service started
WARN  Disk low
```

| Intent | Regex | DPL | DQL Example | Output |
|--------|-------|-----|-------------|--------|
| Starts with ERROR | `^ERROR.*$` | `WORD:level TEXT:*` | ```dql fetch logs \| filter matchesPattern(content,"WORD:level TEXT:*") and level=="ERROR"``` | `ERROR Connection reset` |
| Ends with number | `\d+$` | `INT:last` | ```dql fetch logs \| parse content, "* INT:last" \| fields last``` | `last=404` (if line ends with 404) |

---

## 2️⃣ Character Classes & Tokens  

**Log**  
```
2025-09-17 User=alice Error=404 Amount=250.50
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `User=(?<u>\w+)` | `WORD:user` | ```dql fetch logs \| parse content, "User=WORD:user"``` | `user=alice` |
| `Error=(\d+)` | `INT:code` | ```dql fetch logs \| parse content, "Error=INT:code"``` | `code=404` |
| `Amount=\d+\.\d+` | `FLOAT:amt` | ```dql fetch logs \| parse content, "Amount=FLOAT:amt"``` | `amt=250.50` |

---

## 3️⃣ Optional & Skip  

**Log**  
```
OrderId=1001 User=alice Amount=250.50
OrderId=1002 User=bob
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `(Amount=\d+\.\d+)?` | `FLOAT:amount?` | ```dql fetch logs \| parse content, "OrderId=INT:order User=WORD:user Amount=FLOAT:amount?"``` | Row1: `order=1001, user=alice, amount=250.50` <br> Row2: `order=1002, user=bob, amount=null` |

---

## 4️⃣ Grouping & Captures  

**Log**  
```
User=charlie Error=500
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `User=(?<user>\w+) Error=(?<code>\d+)` | `WORD:user INT:code` | ```dql fetch logs \| parse content, "User=WORD:user Error=INT:code"``` | `user=charlie, code=500` |

---

## 5️⃣ Alternation (OR)  

**Log**  
```
ERROR DB down
WARN  Disk usage high
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `^(ERROR|WARN)` | Extract then filter | ```dql fetch logs \| parse content, "WORD:level TEXT:*" \| filter level in ["ERROR","WARN"]``` | Both lines returned with `level` extracted |

---

## 6️⃣ Boundaries & Lookarounds  

**Log**  
```
response=200ms
response=400ms
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `\d+(?=ms)` (lookahead) | (no DPL equivalent) → regex | ```dql fetch logs \| filter matches(content, /\d+(?=ms)/)``` | Matches `200`, `400` |

---

## 7️⃣ CSV & Lists  

**Log**  
```
123,John,Admin,Chicago
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `^([^,]*),([^,]*),([^,]*),(.*)$` | Use `TEXT` for last | ```dql fetch logs \| parse content, "WORD:id , WORD:name , WORD:role , TEXT:city"``` | `id=123, name=John, role=Admin, city=Chicago` |

---

## 8️⃣ JSON (don’t regex it!)  

**Log**  
```json
{"user":"alice","action":"purchase","amount":49.99,"success":true}
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| Complex regex | `JSON:j` | ```dql fetch logs \| parse content, "JSON:j" \| fields j.user, j.amount``` | `user=alice, amount=49.99` |

---

## 9️⃣ Multi-value Extraction  

**Log**  
```
Items: Item=pen Item=book Item=bag
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `Item=(?<item>\w+)` with `max_match=0` | `parseAll` | ```dql fetch logs \| parseAll content, "Item=WORD:item" \| expand item``` | Rows: `pen`, `book`, `bag` |

---

## 🔟 Masking / Replace  

**Log**  
```
Card=1234-5678-9999-0000 User=alice
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `\d` → `X` | `replacePattern` | ```dql fetch logs \| fieldsAdd masked = replacePattern(content, "INT:n", "X")``` | `Card=X-XXXX-XXXX-XXXX User=alice` |

---

## 11️⃣ Phrase Search vs Regex  

**Log**  
```
2025-09-17 User login failed for alice
2025-09-17 User logout ok
```

| Regex | DPL | DQL Example | Output |
|-------|-----|-------------|--------|
| `.*User login failed.*` | `matchesPhrase` | ```dql fetch logs \| filter matchesPhrase(content, "User login failed")``` | Only first line |

---

## ✅ Summary Rules  

- Use **DPL tokens** (`WORD`, `INT`, `TEXT`, `FLOAT`, `JSON`, etc.) whenever possible.  
- Use `?` to make fields optional.  
- Use `TEXT:*` to discard rest of the line.  
- Use **regex (`matches(field, /.../)`)** only when you need advanced features (lookarounds, alternation inside token, boundary checks).  
- **Always filter early** (`from:` and `filter`) before parsing.  


---

# ✅ Extended Summary Rules for Regex & DPL in Dynatrace DQL  

## 🔹 General Parsing Strategy
- **Prefer DPL tokens (`WORD`, `INT`, `TEXT`, `FLOAT`, `JSON`) over regex.**  
  → They’re faster, easier to read, and more robust.  
- **Regex (`matches`) is still PCRE.** Use it only when DPL cannot express the pattern (lookahead, boundaries, complex alternation).  
- **Filter before parsing.** Always use `from:` and `filter` first to cut data volume.  

## 🔹 Token Usage
- Use **`WORD`** for single tokens without spaces (e.g., usernames, codes).  
- Use **`TEXT`** for free text that may contain spaces (e.g., messages, error descriptions).  
- Use **`INT`** and **`FLOAT`** for numeric fields.  
- Use **`?`** to make fields optional → avoids dropped lines when data is missing.  
- Use **`*`** or `TEXT:*` to skip irrelevant portions of a log line.  

## 🔹 JSON Logs
- If logs are JSON → **always use `JSON:j`**, never regex.  
- Drill into fields with `j.fieldname`.  
- Example:  
  ```dql
  | parse content, "JSON:j"
  | fields j.user, j.action
  ```

## 🔹 Multi-value Data
- Use `parseAll` when a pattern repeats (`Item=WORD:item`).  
- Always follow with `expand` to flatten lists.  
- Example:  
  ```dql
  | parseAll content, "Item=WORD:item"
  | expand item
  ```

## 🔹 String & Phrase Matching
- For **simple wildcards** → use `like` (`content like "ERROR*"`).  
- For **phrase search** → use `matchesPhrase` (`"User login failed"`).  
- For **pattern-based matching** → use `matchesPattern`.  
- For **complex regex** → use `matches(field, /regex/)`.  

## 🔹 Robustness & Reliability
- If you’re not sure a field always exists → make it **optional** (`INT:code?`).  
- If the log format is mixed, **parse only what you need** (skip the rest).  
- For CSV or delimited logs → use `split` or `parse` with `TEXT` for the last column.  

## 🔹 Joins & Enrichment
- Logs often have `dt.entity.host` or `dt.entity.service` → join with entity metadata.  
- Use `entityName()` for human-readable names instead of IDs.  
- Example:  
  ```dql
  | lookup [ fetch entities | fields host=entityId, os=entityAttr("osType") ] on dt.entity.host
  ```

## 🔹 Performance Considerations
- `matchesPhrase` and `like` are cheaper than regex.  
- `matchesPattern` (with tokens) is faster than raw regex.  
- Avoid `parseAll` unless you really need multiple matches—it expands results.  
- Narrow with `from:` (time window) first.  

## 🔹 Migration Mindset
- Splunk regex groups → map to DPL tokens (`(?<user>\w+)` → `WORD:user`).  
- Splunk wildcards (`.*error.*`) → map to `matchesPhrase(content, "error")`.  
- Splunk optional groups (`(foo)?`) → map to `WORD:foo?`.  
- Splunk key-value parsing → map to `parse "Key=WORD:field"`.  

---

# 🚀 Quick Migration Checklist

✅ Start every query with **`fetch logs, from:`** and a **filter**.  
✅ Use **tokens (`WORD`, `TEXT`, `INT`)** for parsing, not regex, unless unavoidable.  
✅ Add `?` to make parsing **fault-tolerant**.  
✅ Use **`parseAll` + `expand`** for repeating keys.  
✅ Prefer **`matchesPhrase`** or **`like`** for searches instead of regex.  
✅ **Enrich logs with entities** (`entityName()`, `entityAttr`) for better dashboards.  
✅ Use regex (`matches(field, /regex/)`) only for advanced cases (lookbehind, lookahead, word boundaries).  

---
