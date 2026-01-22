
# Splunk → Dynatrace Migration

## Telemetry, Alerting & System-of-Record Decision Matrix

> **Purpose**
> Provide a single, authoritative view of:
>
> * **What each sourcetype becomes** (Logs / Events / Metrics / Drop)
> * **Eventually where alerting comes from** (Davis AI vs Workflow)
> * **Where the data lives post-Splunk**
>
> This enables **one-time review** with Security, Risk, and Infrastructure — not per app.

---

## 🧭 Allowed Dynatrace Targets

* **Logs** – diagnostic text engineers search
* **Events** – state changes, failures, notable conditions
* **Metrics** – counts, rates, durations, capacity
* **Drop** – no future value
* **TBD** – decision pending

---

## 🚨 Alerting Source (Definitions)

| Alerting Source | When used                                                     |
| --------------- | ------------------------------------------------------------- |
| **Davis AI**    | Health, anomalies, infra/app failures, causality-based alerts |
| **Workflow**    | Deterministic logic, batch jobs, SLAs, security signals       |
| **None**        | Informational or audit-only events                            |
| **TBD**         | Alerting decision not finalized                               |

---

## 📘 Application Telemetry

| Splunk Sourcetype         | What it REALLY is            | OpenPipeline Action | Dynatrace Target | Decision Status         | **Alerting Source** | Post-Splunk System of Record |
| ------------------------- | ---------------------------- | ------------------- | ---------------- | ----------------------- | ------------------- | ---------------------------- |
| `linux:app:log`           | Linux application behavior   | Ingest              | Logs             | **Final**               | Workflow            | Dynatrace                    |
| `pega:log`                | BPM / workflow execution     | Ingest              | Logs + Events    | **TBD (needs samples)** | Workflow            | Dynatrace                    |
| `systemout`               | App server stdout            | Ingest              | Logs             | **Final**               | None                | Dynatrace                    |
| `systemerr`               | App server stderr (errors)   | Ingest              | Logs + Events    | **Final**               | Davis AI            | Dynatrace                    |
| `WinEventLog:Application` | Windows app runtime          | Ingest              | Logs + Events    | **Final**               | Davis AI            | Dynatrace                    |
| `eventing`                | App / platform state changes | Route               | Events           | **Final**               | None                | Dynatrace                    |
| `jira_eventing`           | ITSM workflow transitions    | Route               | Events           | **Final**               | Workflow            | Dynatrace                    |

---

## 🧱 Infrastructure & Platform Telemetry

| Splunk Sourcetype    | What it REALLY is            | OpenPipeline Action | Dynatrace Target | Decision Status          | **Alerting Source** | Post-Splunk System of Record |
| -------------------- | ---------------------------- | ------------------- | ---------------- | ------------------------ | ------------------- | ---------------------------- |
| `linux:crit:log`     | Linux OS critical failures   | Route               | Events           | **Final**                | Davis AI            | Dynatrace + S3 Archive       |
| `linux:hardware:log` | Hardware faults              | Route               | Metrics + Events | **Final**                | Davis AI            | Dynatrace + S3 Archive       |
| `WinEventLog:System` | Windows OS failures          | Route               | Events           | **Final**                | Davis AI            | Dynatrace + S3 Archive       |
| `Syslog:network`     | Network device syslog        | Route               | Metrics + Events | **TBD (Infra review)**   | Davis AI            | Dynatrace + S3 Archive       |
| `Syslog:dell_bmc`    | Server BMC / hardware mgmt   | Route               | Metrics + Events | **Final**                | Davis AI            | Dynatrace + S3 Archive       |
| `Syslog:capacity`    | Infra capacity thresholds    | Route               | Metrics + Events | **Final**                | Davis AI            | Dynatrace + S3 Archive       |
| `Syslog:srm_lfm`     | Storage lifecycle & capacity | Route               | Metrics + Events | **Final**                | Davis AI            | Dynatrace + S3 Archive       |
| `Syslog:tsm_storage` | Backup storage infra         | Route               | Metrics + Events | **Final**                | Davis AI            | Dynatrace + S3 Archive       |
| `Syslog:uc`          | Generic shared infra syslog  | Route               | Events           | **TBD (needs samples)**  | None                | S3 Archive                   |
| `Syslog:adcl`        | Vendor / controller syslog   | Route               | Events           | **TBD (vendor context)** | None                | S3 Archive                   |

---

## 💾 Backup & Data-Protection Telemetry

| Splunk Sourcetype | What it REALLY is      | OpenPipeline Action | Dynatrace Target | Decision Status | **Alerting Source** | Post-Splunk System of Record |
| ----------------- | ---------------------- | ------------------- | ---------------- | --------------- | ------------------- | ---------------------------- |
| `tsm:log`         | Unix/Linux backup jobs | Route               | Metrics + Events | **Final**       | Workflow            | Dynatrace + S3 Archive       |
| `tsm-win:log`     | Windows backup jobs    | Route               | Metrics + Events | **Final**       | Workflow            | Dynatrace + S3 Archive       |

---

## 🔐 Security, Audit & Control-Plane Telemetry

| Splunk Sourcetype   | What it REALLY is             | OpenPipeline Action | Dynatrace Target      | Decision Status             | **Alerting Source** | Post-Splunk System of Record |
| ------------------- | ----------------------------- | ------------------- | --------------------- | --------------------------- | ------------------- | ---------------------------- |
| `qpasa:log`         | Authn / authz audit           | Route               | Events (signals only) | **TBD (Security sign-off)** | Workflow            | Security Platform (SIEM)     |
| `commandcenter:log` | Ops control-plane audit       | Route               | Events                | **TBD (Risk/IRP)**          | None                | S3 Archive                   |
| `controlm:log`      | Batch scheduling & SLA        | Route               | Metrics + Events      | **Final**                   | Workflow            | Dynatrace + S3 Archive       |
| `script_events:log` | Automation execution results  | Route               | Events                | **Final**                   | Workflow            | Dynatrace                    |
| `atm:log`           | Ingest / pipeline audit noise | Drop                | Drop                  | **Final**                   | None                | None (Dropped)               |

---

## 🧠 OpenPipeline Action Rules

```text
Ingest → Store logs in Dynatrace Logs
Route  → Convert to Events and/or Metrics (no raw log retention)
Drop   → Explicit exclusion from Dynatrace ingestion
```

---

## 🏛️ Governance Model 

* **Ingestion** is decided once (OpenPipeline)
* **Storage** is explicit (Logs vs Events vs Metrics vs Archive)
* **Alerting** is intentional (Davis AI vs Workflow vs None)
* **Ownership** is clear (Dynatrace, SIEM, S3, or Drop)

❌ No per-app alert debates
❌ No “everything alerts” noise
✅ Central policy, centrally enforced

---

## 🎯 Key Takeaway

> **Alerting is not an automatic consequence of ingestion.
> In Dynatrace, you must decide *who* alerts (Davis vs Workflow) just as deliberately as *what* you ingest.**

