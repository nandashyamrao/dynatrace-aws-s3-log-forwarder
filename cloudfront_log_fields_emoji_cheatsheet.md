
# 📘 CloudFront Access Log Field Cheat Sheet

Understand every field. Use it for observability, metrics, and alerting.

---

## 🕒 Request Timing & Identification

| Field              | Description                                  | Use Case                           |
|-------------------|----------------------------------------------|------------------------------------|
| 🗓️ `date`          | Date of the request (UTC)                    | Daily usage trends                 |
| ⏰ `time`          | Time of the request (UTC)                    | Peak load identification           |
| 🧭 `x-edge-location` | AWS POP that served the request             | Geo-load distribution              |
| 🆔 `x-edge-request-id` | Unique request identifier                   | Log correlation                    |
| 🧠 `cs-protocol-version` | HTTP protocol used (1.1/2.0)              | Protocol performance monitoring    |

---

## 🌐 Client Info

| Field              | Description                                  | Use Case                           |
|-------------------|----------------------------------------------|------------------------------------|
| 🌍 `c-ip`         | Client IP address                             | Unique visitors, geo-mapping       |
| 🌐 `x-forwarded-for` | Original client IP (behind proxy)           | True source identification         |
| 🔠 `cs(User-Agent)` | Browser or bot info                          | Bot detection, UX targeting        |
| 📲 `cs(Cookie)`   | Client cookies                                | Session/correlation                |
| 🔗 `cs(Referer)`  | Referrer URL                                  | Traffic source analytics           |

---

## 🔓 Request Details

| Field              | Description                                  | Use Case                           |
|-------------------|----------------------------------------------|------------------------------------|
| 🚀 `cs-method`     | HTTP method (GET/POST/etc.)                  | Detect misuse (e.g., DELETE/PUT)   |
| 🧾 `cs-uri-stem`   | Requested path                                | Top URL analysis, 404s             |
| 🔍 `cs-uri-query`  | Query parameters                              | Behavior tracking                  |
| 🧳 `cs(Host)`      | Host header used                              | Multi-tenant or domain routing     |
| 🔒 `cs-protocol`   | Protocol (http/https)                         | Enforce HTTPS                      |
| 📦 `cs-bytes`      | Bytes received from client                   | POST/PAYLOAD tracking              |

---

## 📤 Response Info

| Field              | Description                                  | Use Case                           |
|-------------------|----------------------------------------------|------------------------------------|
| 📥 `sc-bytes`      | Bytes returned to client                     | Bandwidth cost tracking            |
| 🔢 `sc-status`     | HTTP response code                           | Error tracking (4xx/5xx)           |
| 🧩 `sc-range-start`| Start byte for partial content               | Streaming/debug                    |
| 🧩 `sc-range-end`  | End byte for partial content                 | Streaming/debug                    |
| 📄 `sc-content-type` | MIME type returned                         | Content profiling                  |
| 🔢 `sc-content-len` | Size of response body                       | Download insights                  |

---

## ⚙️ Cache & Delivery Outcome

| Field                     | Description                             | Use Case                            |
|--------------------------|------------------------------------------|-------------------------------------|
| 🧠 `x-edge-result-type`   | How CF processed request (Hit/Miss)      | Cache hit ratio                     |
| ✅ `x-edge-response-result-type` | Final outcome (Error, Hit, Miss)       | Reliability/QoS                     |
| 🔁 `time-taken`           | Total time to serve request              | Latency & performance tracking      |

---

## 🔐 TLS / Security

| Field              | Description                                  | Use Case                           |
|-------------------|----------------------------------------------|------------------------------------|
| 🔐 `ssl-protocol`  | TLS version used                             | Enforce TLS 1.2+                   |
| 🔑 `ssl-cipher`    | Cipher suite                                 | Weak cipher detection              |
| 🛡️ `fle-status`    | Field-level encryption (Encrypted/Decrypted) | Data protection monitoring         |
| 🔢 `fle-encrypted-fields` | # of encrypted fields                   | Sensitive data flow visibility     |

---

## ⚠️ Top Observability Metrics

| Metric                     | Built From Fields                 | Purpose                             |
|----------------------------|-----------------------------------|-------------------------------------|
| 💥 Error Rate              | `sc-status`                       | Detect 4xx/5xx surge                |
| 🎯 Cache Hit Ratio         | `x-edge-result-type`              | CDN efficiency                      |
| 📶 Bandwidth               | `sc-bytes`, `cs-bytes`            | Cost and usage tracking             |
| 🐌 Latency (p95/p99)       | `time-taken`                      | Performance measurement             |
| 🧠 TLS Compliance          | `ssl-protocol`                    | Security enforcement                |
| 🧭 Protocol Adoption       | `cs-protocol-version`             | HTTP/2 visibility                   |

---

## 🚨 Suggested Alerts

| Alert                              | Condition                                          |
|-----------------------------------|---------------------------------------------------|
| 🔥 High 5xx error rate             | > 5% 5xx from total requests in 5-minute window   |
| ❌ Surge in 4xx errors             | > threshold rate for 4xx codes                    |
| 🐢 High latency                    | `time-taken` > 2s for > 5% requests               |
| 📉 Drop in cache hit ratio         | More `Miss` than `Hit` in `x-edge-result-type`   |
| 🔓 Weak TLS Detected               | TLSv1.0 or weak ciphers in use                   |
| 🔗 Too many HTTP requests          | `cs-protocol` = http (not https)                 |
