
# 🚦 AWS ALB Access Log Fields Cheat Sheet

Use this guide to interpret AWS Application Load Balancer (ALB) logs for performance, security, and traffic analysis.

---

## 📍 Request Source & Metadata

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 📅 `type`           | Type of request log (always `http` or `https`) | Log format indicator                   |
| 🕒 `timestamp`      | Request completion time (ISO 8601)            | Time correlation                        |
| 🌐 `elb`            | Load balancer name                           | For multi-ALB deployments               |
| 🧑‍💻 `client:port`   | Source IP and port                           | Geo/IP analysis, bot detection          |
| 🎯 `target:port`    | Destination IP and port                      | Target tracing                          |

---

## 🧠 Request Context

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🚀 `request_processing_time` | Time to receive request header    | Front-end performance metric            |
| ⌛ `target_processing_time`  | Time target took to generate response | Back-end health & latency             |
| 📤 `response_processing_time` | Time to send response to client  | Egress bottleneck analysis              |
| 📈 `elb_status_code` | Status from load balancer (e.g., 200, 502)  | Health monitoring                       |
| 🏁 `target_status_code` | Response code from target               | Detect application errors               |
| 🔁 `received_bytes`   | Bytes from client                          | Traffic measurement                     |
| 📦 `sent_bytes`       | Bytes to client                            | Bandwidth monitoring                    |

---

## 🌍 Request Details

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🧾 `request`        | Full request line: method, path, protocol    | URL, method visibility                  |
| 🧑‍🚀 `user_agent`    | Client user agent                            | Bot/user profiling                      |
| 🔗 `ssl_cipher`     | TLS cipher suite used                        | TLS hardening checks                    |
| 🛡️ `ssl_protocol`   | TLS version used                             | Compliance & deprecated protocol alerts |

---

## 📛 Authentication & Targeting

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🧾 `target_group_arn` | ARN of the target group                     | Routing layer tracing                   |
| 🧍 `trace_id`       | X-Amzn-Trace-Id for X-Ray                    | End-to-end trace correlation            |
| 🔐 `domain_name`    | SNI hostname from TLS                        | Cert-based filtering                    |
| 🪪 `chosen_cert_arn`| ACM cert used for HTTPS                      | Cert audit/compliance                   |
| 📦 `matched_rule_priority` | Rule priority that matched             | Rule effectiveness review               |
| 🎯 `rule_action`    | ALB action taken (`forward`, `redirect`, etc.)| Traffic routing decision               |
| ⚖️ `redirect_url`   | URL where request was redirected             | Debugging routing logic                 |

---

## 📊 Observability Metrics

| Metric                      | From Fields                        | Purpose                                 |
|----------------------------|-------------------------------------|-----------------------------------------|
| 🧍 Active Targets           | `target_processing_time > 0`        | Healthy traffic                         |
| 🚫 Target Error Rate        | `target_status_code >= 500`         | App-level error alerting                |
| 🏃 Slow Backend Response    | `target_processing_time > 1s`       | Performance degradation                 |
| 🛑 Load Balancer Failures   | `elb_status_code = 5xx`             | Infrastructure-level failure            |
| 🧪 Deprecated TLS Used      | `ssl_protocol = TLSv1`              | Security alert                          |

---

## 🚨 Suggested Alerts

| Alert Description                  | Trigger Condition                                |
|-----------------------------------|--------------------------------------------------|
| 🚨 High 5xx Errors from Target     | `target_status_code >= 500`                      |
| ⚖️ Redirect Loops                 | Same `redirect_url` called repeatedly            |
| 🐢 Backend Latency Spike          | `target_processing_time > 2000ms`                |
| 🔐 Deprecated TLS Detected        | `ssl_protocol = TLSv1 or TLSv1.1`                |
| 🚧 Unexpected Rule Action         | `rule_action != forward` in default case         |
| 📉 Missing Target Response        | `target_status_code = "-"`                       |

---

Let me know if you'd like this as `.md`, `.pdf`, or merged into a full cheat sheet set.
