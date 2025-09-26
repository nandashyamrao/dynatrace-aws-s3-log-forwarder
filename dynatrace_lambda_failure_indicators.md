# 🧾 Dynatrace Lambda Failure – Evidence & Indicators

When the failure originated deep within Dynatrace's internal infrastructure (HAProxy + connection pool), you **still had clues** visible in AWS and Dynatrace dashboards. The key is knowing **where to look** for symptoms when you cannot see the root cause.

---

## 1️⃣ On Your AWS Lambda Side (The Symptoms) 🚨

These are the immediate, customer-facing effects of the bottleneck, visible in **CloudWatch Metrics** and **CloudWatch Logs**.

| **Indicator** | **Metric / Log Location** | **Why It Happens** |
|---------------|--------------------------|--------------------|
| **Duration Spikes to Limit** | CloudWatch Metric: `Duration` | The Lambda functions hang during the Dynatrace agent's initialization network call. The function sits idle, consuming time until it hits the configured Timeout limit. |
| **High Timeout Rate** | CloudWatch Metric: `Errors` / Log Message: `Task timed out` | Confirms the hang. Since your code never runs, the container is killed by AWS for exceeding the duration limit. |
| **Low Invocation Count** | CloudWatch Metric: `Invocations` | As functions fail to start and time out, the overall rate of successful work drops — indicating a total service degradation. |

---

## 2️⃣ In Your Dynatrace Dashboards (The Missing Data) 📉

Even if you cannot see HAProxy's internal queue, the failure of the Dynatrace agent to connect is **visible in your monitoring data — or the lack of it.**

| **Indicator** | **Dashboard / Analysis** | **Why It Happens** |
|---------------|------------------------|--------------------|
| **Loss of Lambda Data** | Dynatrace Service View for Lambda Functions | The most obvious sign: During the outage, the Dynatrace agent cannot phone home. You see a sudden, near-total drop to zero in metrics (Response Time, Error Rate, Invocation Count). |
| **Connection Errors in Lambda Logs** | Dynatrace Log Viewer (from CloudWatch logs) | With debug logging enabled, you might see specific messages about connection failures or network timeouts attempting to reach the Dynatrace SaaS endpoint. |

---

## 3️⃣ On Your Traffic Gateway (The Backpressure) 🛑

If Lambdas are invoked via **API Gateway** or **ALB**, you’ll see the impact upstream as well.

| **Indicator** | **Log Location** | **Why It Happens** |
|---------------|----------------|--------------------|
| **Gateway Timeout Response** | AWS WAF Logs / ALB Access Logs: Many HTTP 504 codes | The front-end gateway times out because the Lambda is hung waiting for the Dynatrace connection. |
| **WAF Rate Limit Block** | AWS WAF Logs: High HTTP 429 codes from Rate-Based Rules | Client retries (due to 504s) spike so high that WAF starts blocking them to defend other parts of the app. |

---

## 🏁 Conclusion

By assembling evidence from **AWS metrics**, **Lambda logs**, and **Dynatrace dashboards**, you can deduce that the root issue was a **third-party network dependency failure** (HAProxy saturation) during the cold start phase, even if you cannot directly see Dynatrace’s internal queues.


---

## 4️⃣ What to Ask Dynatrace to Confirm 🔍

Even though the issue originated inside Dynatrace SaaS (HAProxy + downstream connection pool), you can **ask Dynatrace Support** for internal evidence to confirm the diagnosis. This helps separate root cause (SaaS bottleneck) from your own Lambda/ActiveGate setup.

| **Area** | **What to Request** | **Why It Matters** |
|---------|--------------------|--------------------|
| **HAProxy & Ingest Metrics** | Connection pool utilization, queue depth, 5xx counts, p95/p99 response times | Confirms front-door saturation at the time of incident |
| **Backend Log Ingest Health** | Queue size, processing latency, autoscaler events, dropped batch count | Shows whether there was a backlog or delayed processing |
| **Environment-Specific Stats** | Request count, payload size trend, latency per request, failure rate | Confirms your requests were received but delayed/dropped server-side |
| **Incident Report** | Internal RCA, maintenance history, or status update for your cluster | Provides evidence of a known SaaS-side degradation |
| **Cross-Customer Correlation** | Whether other tenants on the same cluster saw similar spikes | Proves this was not isolated to your configuration |
| **Auth/Token Logs** | Verification that your API token was accepted and not rejected | Rules out configuration error on your side |

### Example Request to Dynatrace Support
> **Subject:** Request for Backend Metrics – Log Ingest & HAProxy Saturation (Environment `<ENV-ID>`)
>
> **Description:** During `[timestamp range UTC]`, we observed severe Lambda slowdowns, timeout spikes, and 5xx errors from the `/api/v2/logs/ingest` endpoint (via ActiveGate).
> 
> Could you please provide:
> 1. HAProxy connection pool usage, queue depth, and 5xx count during that time.
> 2. Log ingest backend queue sizes and processing latency.
> 3. Environment-specific ingest metrics (request count, payload size, error breakdown).
> 4. Any incident reports, rolling maintenance, or RCA for the cluster during that window.
> 5. Whether other customers were impacted at the same time.
> 
> This will help us tune our retries/concurrency and confirm our setup is healthy.

💡 **Explanation:** By combining your AWS CloudWatch evidence (duration spikes, Lambda timeouts) with Dynatrace's backend telemetry, you can build a clear case that the outage was SaaS-related, not a misconfiguration in your Lambda or ActiveGate.



---

## 5️⃣ ActiveGate – What to Watch & How to Verify 🛰️

ActiveGate (AG) is your **relay**: it accepts traffic on **:9999**, briefly buffers, and forwards to Dynatrace SaaS on **:443**. If SaaS is slow or AG is resource‑constrained, you’ll see symptoms here first. Use this checklist to separate **AG issues** from **SaaS issues**.

### 🔍 Health & Status (UI + Host)
- **Dynatrace UI:** *Deployment status → ActiveGates* — check the AG is **online**, version, last heartbeat, and assigned capabilities (Log/OTLP ingest).  
- **Host health:** CPU, memory, disk, and network — spikes here correlate with ingest delays.

### 📁 Logs to Tail on the AG Host
- **Gateway logs:** `/var/log/dynatrace/gateway/gateway.log` (primary), plus recent rotated files.  
  - Look for: TLS errors, 5xx from upstream, queue/space warnings, connection resets, DNS failures.  
- **Startup/config:** `/var/log/dynatrace/gateway/config/` (if present) — confirms effective settings on restart.

### 💾 Buffer / Queue (Burst Absorption)
- Ensure the AG has **sufficient disk** and queue configured for ingest spikes.  
- Watch for messages like “**usable space limit reached**” or “**queue full**” — these indicate local backpressure.  
- Place the queue directory on a volume with ample free space and IOPS.

### 🔐 TLS / Hostname
- Use the **FQDN** that matches the AG certificate (avoid raw IPs). Cert mismatches cause failed handshakes and retries.  
- If you rotate certs, confirm clients see the updated chain.

### 🌐 Connectivity Checks
- **Inbound:** Port **9999/TCP** open from senders (Lambdas, shippers).  
- **Outbound:** Port **443/TCP** open from AG to Dynatrace SaaS (egress proxy rules if used).  
- **DNS:** AG can resolve the SaaS cluster endpoints; transient DNS failures present as intermittent 5xx/timeouts.

### ✅ Endpoint & Path Sanity
- Correct path for logs JSON:  
  `https://<ag-fqdn>:9999/e/<ENV-ID>/api/v2/logs/ingest`  
- Correct path for OTLP logs:  
  `https://<ag-fqdn>:9999/e/<ENV-ID>/api/v2/otlp/v1/logs`  
- Missing `/e/<ENV-ID>` or wrong path will yield 404/5xx at AG.

### 🧪 Fast Probes (from a bastion or admin box)
```bash
# 1) Minimal JSON ingest probe
curl -ik -X POST "https://<AG_FQDN>:9999/e/<ENV-ID>/api/v2/logs/ingest"   -H "Authorization: Api-Token <TOKEN_WITH_logs.ingest>"   -H "Content-Type: application/json"   --data '[{"timestamp": 1710000000000, "content":"ag probe", "severity":"INFO"}]'

# 2) OTLP path probe (if you use OTLP)
curl -ik -X POST "https://<AG_FQDN>:9999/e/<ENV-ID>/api/v2/otlp/v1/logs"   -H "Authorization: Api-Token <TOKEN_WITH_logs.ingest>"   -H "Content-Type: application/json"   --data-binary '[]'   # send a tiny, valid batch
```

**Interpretation:**  
- `200/202` → AG path/token/TLS OK; problems likely downstream or volume-related.  
- `404` → path/env-id wrong.  
- `5xx` with space/queue wording → increase AG buffer / disk.  
- `5xx` generic / timeouts → check AG → SaaS connectivity or upstream saturation.

### 🧩 Version, Capabilities, and Scale
- Keep AG **up to date**; newer builds include ingest fixes and better buffering.  
- If sustained throughput is high, **add a second AG** and distribute senders (simple DNS round-robin).  
- Verify **capabilities** (Log ingest, OTLP) are enabled on the intended AG nodes.

### 📈 Suggested Alarms (practical starting points)
- **AG process up/heartbeat**: missing > 2 intervals.  
- **Gateway 5xx rate**: >1% over 5 min.  
- **Disk free on AG queue volume**: < 20%.  
- **AG queue depth / backlog**: growing for > 10–15 min.  
- **Outbound failures to SaaS**: any sustained spike.

### 🧠 Quick Root‑Cause Hints
- **AG healthy, queue stable, but 5xx from SaaS** → SaaS/edge congestion (respect backoff).  
- **AG shows queue full / space limit** → increase disk/queue and throttle senders.  
- **TLS/DNS errors in `gateway.log`** → fix certs/hostname or name resolution.  
- **Frequent 404 at AG** → fix client path to include `/e/<ENV-ID>`.
