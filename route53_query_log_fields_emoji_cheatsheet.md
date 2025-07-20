
# 🛰️ AWS Route 53 Resolver Query Log Fields Cheat Sheet

Use this cheat sheet to analyze Route 53 DNS query logs for security, troubleshooting, and traffic visibility.

---

## 🌐 DNS Query Details

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🕒 `queryTimestamp` | Timestamp of query in UTC                    | Time-based analysis                     |
| 🧾 `queryName`      | Domain name queried                          | Domain popularity, investigation        |
| 📛 `queryType`      | Record type (A, AAAA, MX, etc.)              | DNS record analysis                     |
| 🔄 `rcode`          | DNS response code                            | Detect resolution issues                |
| ✅ `answers`        | List of returned IPs or records              | Forensics, threat intel mapping         |

---

## 📍 Source Info

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🧍 `srcIP`          | IP of the querying device                    | Client identification                   |
| 🧑‍🤝‍🧑 `vpcId`        | VPC ID of the source                        | Multi-VPC query tracing                 |
| 🧪 `queryClass`     | Class (IN = Internet, etc.)                  | Rarely used; mostly IN                  |

---

## 🔄 Resolver & Endpoint Info

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| 🌎 `resolverEndpointId` | ID of resolver endpoint used           | Track traffic through specific endpoints|
| 🧭 `region`         | AWS region of the resolver                  | Geo-localize DNS flows                  |
| 🔐 `firewallRuleAction` | `ALLOW`, `BLOCK`, `ALERT` from DNS firewall | Security enforcement               |
| 🧱 `firewallDomainListId` | ID of domain list in rule             | Threat list mapping                     |

---

## 🧠 DNS Behavior Insights

| Field               | Description                                  | Use Case                                |
|--------------------|----------------------------------------------|-----------------------------------------|
| ❓ `isTruncated`    | Whether the DNS response was truncated       | Potential for follow-up TCP query       |
| 🔁 `protocol`       | `UDP` or `TCP`                               | TCP fallback detection                  |
| 📡 `srcPort`        | Source port of the DNS query                 | Anomaly detection                       |

---

## 📊 Observability Metrics

| Metric                      | From Fields                     | Purpose                                 |
|----------------------------|----------------------------------|-----------------------------------------|
| 🔥 NXDOMAIN Volume          | `rcode = 3`                     | Domain typo/spam/attack detection       |
| ⛔ Blocked Domains          | `firewallRuleAction = BLOCK`    | DNS firewall enforcement                |
| 🧾 Popular Domain Requests  | Frequency of `queryName`        | Top domains tracked                     |
| 🚩 Alerted DNS Requests     | `firewallRuleAction = ALERT`    | Review for manual escalation            |
| 🐢 DNS Latency              | Derived from timing (if enabled) | Resolver performance                    |

---

## 🚨 Suggested Alerts

| Alert Description                    | Trigger Condition                              |
|-------------------------------------|------------------------------------------------|
| 🚨 Excessive NXDOMAINs              | `rcode = 3` threshold exceeded                 |
| 🧟 Known Bad Domain Queried         | `queryName` in threat list                    |
| 🔁 High TCP DNS Usage               | `protocol = TCP` unusual spike                 |
| 🔐 Unexpected Region Querying       | New `region` or unknown `resolverEndpointId`   |
| 📈 Spike in DNS Queries from Host   | Same `srcIP` rate-limited                      |

---

Would you like to include this in a bundled cheat sheet for DNS, CDN, logging, and firewall services?
