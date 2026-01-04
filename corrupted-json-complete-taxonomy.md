# Corrupted JSON — Complete Taxonomy (Dynatrace-centric)

## Definition (Practical)
**“Corrupted JSON”** — Any JSON input that prevents Dynatrace’s JSON parser from successfully building a valid in-memory JSON object.

---

### 1️⃣ **Truncated JSON (Most Common & Most Dangerous)**  
#### What it looks like:
```json
{"action":"BLOCK","clientIp":"10.1.1.1"
```
(missing closing `}`)

#### Why it happens:
- Log line size limits
- Network buffering
- Application crash mid-write
- Multi-line JSON cut into pieces

#### What Dynatrace does:
- **JSON parser fails**
- `jsonField` / `jsonPath` → `null`
- `parse content,json` → no JSON object created

#### What works:
- ❌ **jsonPath**
- ❌ **jsonField**
- ❌ **parse content,json**

#### Only salvage option:
- **Regex for partial recovery:**
  ```regex
  extract(content, "\"clientIp\":\"([^\"]+)\"", 1)
  ```

📌 **Best practice:** Detect and drop these early.

---

### 2️⃣ **Multiple JSON Objects in One Log Line**  
#### What it looks like:
```json
{"action":"BLOCK"} {"clientIp":"10.1.1.1"}
```

#### Why it happens:
- Poor logging frameworks
- Concatenated payloads
- Multiple libraries writing to the same log stream

#### What Dynatrace does:
- Without `seek=true` → ❌ **fails**
- With `seek=true` → ✅ Parses **only the first JSON**

#### Behavior:
```json
jsonPath(content, "$.action", seek=true) ✔ → "BLOCK"
jsonPath(content, "$.clientIp", seek=true) ❌ → null
```

#### What does NOT exist:
- ❌ No loop
- ❌ No multi-JSON extraction

---

### 3️⃣ **JSON Embedded Inside Text (but otherwise valid)**  
#### What it looks like:
```
INFO event payload={"action":"BLOCK","clientIp":"10.1.1.1"}
```

#### Why it happens:
- Structured logging + prefixes (e.g., Logback / Log4j patterns)

#### What Dynatrace does:
- **Normal JSON parse** → ❌
- With `seek=true`: Scans for `{` and parses until closing `}`

#### What works:
- `jsonPath(content, "$.action", seek=true)` ✔

#### What fails:
- `jsonPath(content, "$.action")` ❌

---

### 4️⃣ **Single Quotes Instead of Double Quotes**  
#### What it looks like:
```json
{'action':'BLOCK','clientIp':'10.1.1.1'}
```

#### Why it happens:
- Python dict logging
- Bad serialization
- Debug prints

#### JSON Standard Says:
- ❌ **Invalid JSON**

#### Dynatrace Behavior:
- JSON parser rejects it
- `seek=true` does not resolve ❌

#### What works:
- **Regex workaround:**
  ```regex
  extract(content, "'action':'([^']+)'", 1)
  ```

📌 No native Dynatrace JSON function can parse this.

---

(Include all other examples detailed in previous messages, expanding where necessary.)