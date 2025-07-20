
# 🛡️ AWS WAF Log Fields Cheat Sheet

Understand AWS WAF logs field-by-field, and use them to build dashboards, alerts, and security insights.

---

## 🔐 Request Identity & Source

| Field               | Description                                      | Use Case                                  |
|--------------------|--------------------------------------------------|-------------------------------------------|
| 🆔 `requestId`       | Unique request ID assigned by WAF               | Correlation across logs                   |
| 🌍 `httpSourceName` | Source (ALB, CloudFront, API Gateway, etc.)     | Identify integration point                |
| 🌎 `httpSourceId`   | Resource ID (e.g., ALB ARN or CF distribution)  | Trace request origin                      |
| 🌐 `clientIp`       | Client's IP address                             | Geo, bot, abuse detection                 |

---

## 🌐 HTTP Request Metadata

| Field               | Description                                      | Use Case                                  |
|--------------------|--------------------------------------------------|-------------------------------------------|
| 🚀 `httpMethod`     | Method used in the request (GET, POST, etc.)     | Track usage patterns                      |
| 🧾 `uri`            | Full URI requested                               | Monitor endpoints under attack            |
| 🔍 `args`           | Query string parameters                          | Injection attack surface detection        |
| 🧳 `headers`        | Full header map                                  | User-Agent, Referer, Host filtering       |
| 📦 `body`           | Request payload (base64)                         | Decode for inspection                     |

---

## 🧠 Rule Matching

| Field               | Description                                      | Use Case                                  |
|--------------------|--------------------------------------------------|-------------------------------------------|
| 🧩 `ruleGroupList`  | List of rule groups evaluated                    | Analysis of triggered rule paths          |
| 🎯 `terminatingRuleId` | Final rule that blocked/allowed request       | Enforcement visibility                    |
| 🧱 `terminatingRuleType` | Rule type (`REGULAR`, `RATE_BASED`, etc.)   | Policy-type detection                     |
| 🧰 `rateBasedRuleList` | List of matched rate-based rules              | Rate limiting effectiveness               |
| 🧰 `nonTerminatingMatchingRules` | Matched rules that didn’t stop flow | Logging/mirroring policy insights         |

---

## ⏱️ Timing and Processing

| Field               | Description                                      | Use Case                                  |
|--------------------|--------------------------------------------------|-------------------------------------------|
| 🕒 `timestamp`       | Time the request was evaluated                   | Temporal correlation                      |
| 🧮 `action`          | Action taken (`ALLOW`, `BLOCK`, `COUNT`)         | Alerting on BLOCK or excessive COUNT      |
| 📈 `ruleSetType`     | Scope (`REGIONAL` or `CLOUDFRONT`)               | Determine scope of enforcement            |
| ⚖️ `wafEvaluationTime` | Evaluation time in ms                         | Performance benchmarking                  |

---

## 📊 Observability Metrics

| Metric                       | From Fields                         | Purpose                                    |
|-----------------------------|--------------------------------------|--------------------------------------------|
| 🔥 Block Count              | `action = BLOCK`                    | Alert on blocked threats                   |
| 🐢 High WAF Latency         | `wafEvaluationTime > 100ms`         | Detect evaluation lag                      |
| 📈 Rate Limit Triggered     | `rateBasedRuleList not empty`       | Monitor bot or DDoS mitigation             |
| 🧠 Rule Trigger Analysis    | `terminatingRuleId` + `ruleGroupList` | Track noisy or misfiring rules           |
| 🛑 Top URIs Blocked         | `uri where action = BLOCK`          | Identify abused endpoints                  |
| 🛂 Top IPs Blocked          | `clientIp where action = BLOCK`     | Geo/blocklist enrichment                   |

---

## 🚨 Suggested Alerts

| Alert Description                    | Trigger Condition                                  |
|-------------------------------------|---------------------------------------------------|
| 🚨 High Block Rate                  | > X BLOCKs in 5 minutes                           |
| 🕵️ Suspicious Repeated COUNTs      | COUNT rules hit > Y times/IP                     |
| 🐢 WAF Lagging Evaluation           | `wafEvaluationTime > 200ms`                      |
| 🧱 Rate-Based Rule Hit              | `rateBasedRuleList.length > 0`                   |
| 🌐 Top URI under attack             | Same `uri` with high BLOCK/COUNT                 |
| 🔗 Attack From Same IP              | Same `clientIp` hits COUNT/BLOCK repeatedly       |

---

Would you like this exported as a `.md` or `.pdf` as well?
