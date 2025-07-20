
# 🪣 AWS S3 Access Log Fields Cheat Sheet

Use this cheat sheet to understand S3 access log fields for monitoring, auditing, and security insights.

---

## 👤 Requester Identity

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🆔 `requester`       | Canonical user ID or IAM user                | Who made the request                    |
| 👤 `request-id`      | S3-generated request ID                      | Troubleshooting, AWS support            |
| 🪪 `host-id`         | Extended request ID                          | AWS internal trace                      |
| 🧑‍💻 `operation`       | API action name (e.g., `REST.GET.OBJECT`)    | Action classification                   |

---

## 🕒 Request Timing

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 📅 `time`           | Request timestamp (in UTC)                   | Temporal correlation                    |
| ⏳ `turn-around-time` | Time taken in ms to serve request           | Performance metric                      |

---

## 🌐 Client Info

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🌍 `remote-ip`      | IP address of the requester                  | Geo-location, anomaly detection         |
| 🧠 `user-agent`     | Requesting tool or browser                   | Bot detection, pattern analysis         |
| 🌐 `referrer`       | Referring page or host                       | Source tracing                          |

---

## 🪣 Bucket & Object Info

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🪣 `bucket-owner`   | Canonical ID of bucket owner                 | Multi-account audit                     |
| 📦 `bucket`         | Name of the bucket                          | Request scoping                         |
| 📄 `key`            | Object key path                             | Determine accessed object               |
| 🔒 `request-uri`    | Full HTTP request line                      | Includes method, object, version        |
| 🔗 `uri`            | Request-URI only                            | URI tracking                            |

---

## 📤 Response Info

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🎯 `http-status`    | HTTP status code                            | Error rate tracking                     |
| 📊 `error-code`     | Internal S3 error (if any)                  | Identify failures                       |
| 🔢 `bytes-sent`     | Bytes returned to client                    | Data transfer cost                      |
| 🧮 `object-size`    | Size of object served                       | Cost/bandwidth correlation              |
| 🧾 `total-time`     | Total request duration                      | End-to-end performance                  |

---

## 🔐 Auth & Signature

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🛡️ `auth-type`      | Auth method used (e.g., REST-HEADER)         | Signature enforcement                   |
| 🔑 `sig-version`    | Signature version (e.g., SigV2, SigV4)       | Identify insecure usage                 |
| 🧾 `access-key-id`  | AWS Access Key used                         | Audit API key usage                     |
| 🧪 `tls-version`    | TLS version used                            | Security compliance                     |
| 🔐 `cipher-suite`   | Cipher used                                 | Weak encryption detection               |

---

## 📊 Observability Metrics

| Metric                        | From Fields                     | Purpose                                 |
|------------------------------|----------------------------------|-----------------------------------------|
| 📈 Total Requests             | Count of all lines              | Volume tracking                         |
| 🚫 Error Rate                 | `http-status`, `error-code`     | Alerting on failures                    |
| 💰 High Data Transfer         | `bytes-sent`, `object-size`     | Bandwidth cost spike detection          |
| 🐢 Latency Analysis           | `total-time`, `turn-around-time`| Performance debugging                   |
| 🕵️ Insecure TLS or Signature | `tls-version`, `sig-version`    | Compliance enforcement                  |

---

## 🚨 Suggested Alerts

| Alert Description                | Trigger Condition                              |
|---------------------------------|-------------------------------------------------|
| 🚨 High 5xx/4xx Error Rate      | `http-status` in 4xx/5xx range                 |
| 🧪 Insecure Sig Version Used    | `sig-version` = SigV2                          |
| 🐢 Slow Object Downloads        | `total-time` > 2s                              |
| 💾 Large Object Accessed        | `object-size` > threshold                      |
| 🔓 Public Unauthenticated Access| `auth-type` = Anonymous                        |
| 🌍 Access From New Geo/IP       | Unknown `remote-ip`                            |

---

Would you like this exported as `.md`, `.pdf`, or combined with CloudTrail/WAF/CloudFront into one master doc?
