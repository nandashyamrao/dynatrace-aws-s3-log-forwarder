# 🛡️ PostgreSQL Observability in Dynatrace SaaS — Enterprise Checklist

This document provides a **step-by-step, enterprise-ready plan** to enable **PostgreSQL monitoring** in Dynatrace SaaS using an **ActiveGate** and (optional) **OneAgent**.

It is intended for **two collaborating teams**:  
👥 **Postgres Team (DBA)** + 🖥️ **Dynatrace Team (Monitoring/Infra)**

---

## 0️⃣ 🗂️ Scope & Planning (Shared)

- [ ] **📋 Inventory & Scope**  
  *List DBs (hostname, port, TLS setup, on-prem vs RDS), AG host(s), network zones, and success criteria.*  
  **Purpose:** Avoid missing DBs and prevent rework in firewall and credential requests.

- [ ] **🔍 Decide Visibility Level**  
  Dynatrace PostgreSQL Extension 2.0 supports multiple levels of visibility.  
  Pick which ones you want to enable **up front**, as they define required privileges and change approvals:

  ### 🔹 Level A — **Basic DB Metrics (Always Recommended)**
  - **What You Get:** 📊
    - Active connections, blocked queries, deadlocks
    - Transactions committed/rolled back
    - Cache hit ratio, WAL activity, replication lag
    - Checkpoint & buffer statistics
  - **Dynatrace Views:** 🖥️
    - "PostgreSQL" tile in **Databases**
    - Metrics usable in dashboards and alerting
  - **Privileges Needed:** 🔑
    - DB user with `pg_monitor`
    - `CONNECT` privilege on monitored DB
  - **Change Scope:** ✅ Safe for production, read-only monitoring

  ### 🔹 Level B — **+ Top Queries (Performance Hotspots)**
  - **What You Get:** 🔥
    - Top 100 queries by total execution time
    - Query count, average runtime, normalized text
    - Correlation with DB load in Dynatrace Problems
  - **Dynatrace Views:**
    - "Top queries" section in Database screen
    - Query performance drilldowns over time
  - **Privileges Needed:**
    - Everything from Level A
    - `pg_stat_statements` enabled & `GRANT SELECT` to `dynatrace`
  - **Change Scope:** ⚠️ May require Postgres reload/restart (`shared_preload_libraries`)

  ### 🔹 Level C — **+ Execution Plans (Deep Diagnostics)**
  - **What You Get:** 🧠
    - Full EXPLAIN plan (JSON)
    - Index usage visibility, cost vs actual rows
    - Root cause hints (e.g., Seq Scan vs Index Scan)
  - **Dynatrace Views:**
    - "Execution plan" tab per slow query
    - Visual plan tree in Problems view
  - **Privileges Needed:**
    - Everything from Level B
    - Helper schema + SECURITY DEFINER function
      ```sql
      CREATE SCHEMA IF NOT EXISTS dynatrace;
      CREATE OR REPLACE FUNCTION dynatrace.dynatrace_execution_plan(query TEXT)
      RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
      DECLARE r JSON;
      BEGIN
        EXECUTE 'EXPLAIN (FORMAT JSON) ' || query INTO r;
        RETURN r;
      END $$;
      GRANT EXECUTE ON FUNCTION dynatrace.dynatrace_execution_plan(TEXT) TO dynatrace;
      ```
  - **Change Scope:** 📜 Requires change control + security review

**Purpose:**  
This choice determines **what data you will see** in Dynatrace, **what privileges are granted**, and the **security/change management steps** required.

---

### 📋 Dynatrace Documentation Verification Checklist

| ✅ Area | 🔍 What to Verify | 🎯 Why |
|--------|------------------|--------|
| **ActiveGate** | Version ≥ 1.269, outbound HTTPS to `*.live.dynatrace.com`, proxy configured | Needed for Extension 2.0 & TLS |
| **Certificates** | DB TLS enabled, CA trusted on AG | Prevents SSL errors, secures credentials |
| **Postgres Version** | PostgreSQL ≥ 11 | Ensures compatibility |
| **pg_stat_statements** | Installed & loaded in `shared_preload_libraries` | Needed for Top Queries |
| **Credential Vault** | Used for DB credentials | Prevents plaintext passwords |
| **Feature Sets** | Decide which metrics sets to enable | Controls data volume & DDU usage |
| **Execution Plan Function** | Created & EXECUTE granted to `dynatrace` | Required for Level C |
| **Audit Logging** | Log DB connections for `dynatrace` user | Compliance & troubleshooting |
| **Scaling** | Endpoints per config < 20k | Avoid hitting Dynatrace limits |

---

## 1️⃣ 🌐 Network & Firewall (Dynatrace Team + Security)

- [ ] **Allow ActiveGate → Dynatrace SaaS (443)**  
  **Purpose:** Enables AG to upload metrics/config to SaaS.

- [ ] **Allow ActiveGate → PostgreSQL (5432)**  
  **Purpose:** Extension polls DB stats over SQL.

- [ ] **Configure Corporate Proxy (if required)**  
  `/var/lib/dynatrace/gateway/config/custom.properties`
  ```ini
  [http.client]
  proxy-server=<proxy-host>:<proxy-port>
  proxy-user=<svc_proxy_user>
  proxy-password=<svc_proxy_password>
  ```
  Restart ActiveGate: `sudo systemctl restart dynatracegateway`  
  **Purpose:** Ensures traffic egresses via enterprise proxy.

- [ ] **Restrict Inbound Access**  
  SSH/RDP only via jump host + MFA.  
  **Purpose:** Hardens AG.

---

## 2️⃣ 🔒 Certificates & TLS (Shared)

- [ ] **Enforce TLS on Postgres** (`ssl = on`, TLS1.2+)
- [ ] **Import DB CA Certs into AG Truststore**
- [ ] **Verify NTP/Clock Sync**

**Purpose:** Prevent MITM, handshake issues, timestamp drift.

---

## 3️⃣ 🗝️ Database User & Permissions (Postgres Team)

- [ ] **Create Monitoring User**
  ```sql
  CREATE USER dynatrace WITH PASSWORD '<STRONG_PASSWORD>' INHERIT;
  GRANT pg_monitor TO dynatrace;
  ```
- [ ] **Enable pg_stat_statements (if Level B/C)**
- [ ] **Restrict `pg_hba.conf` to AG Subnet**
- [ ] **Smoke Test**
  ```bash
  psql -h <db-host> -U dynatrace -d <db> "sslmode=require" -c "select 1;"
  ```

**Purpose:** Least-privilege, secure, validated connectivity.

---

## 4️⃣ 🖥️ ActiveGate Readiness (Dynatrace Team)

- [ ] Patch & harden OS
- [ ] Verify AG shows **Connected/Healthy** in Dynatrace
- [ ] Assign to **Network Zone** (`onprem-db`)

**Purpose:** Ensure stable and secure metric polling.

---

## 5️⃣ 🧩 OneAgent on DB Host (Optional)

*(Skip for RDS/Aurora)*  
Install OneAgent for host metrics & log ingestion.

---

## 6️⃣ 🛠️ Dynatrace Hub — PostgreSQL Extension

- [ ] Install **PostgreSQL Extension 2.0**
- [ ] Assign to AG group
- [ ] Store DB creds in **Credential Vault**
- [ ] Add endpoints & **Test Connection**

**Purpose:** Start collecting DB metrics.

---

## 7️⃣ ✅ Validation & Dashboards (Shared)

- [ ] Confirm metrics visible in Dynatrace → Databases
- [ ] Validate Top Queries & Execution Plans (if enabled)
- [ ] Create dashboards & alerting rules

**Purpose:** Operationalize observability.

---

## 8️⃣ 🔁 Security & Compliance

- [ ] Rotate passwords & update Vault
- [ ] Quarterly privilege review (`pg_monitor`, SELECT on pg_stat_statements)
- [ ] Keep AG + extension versions updated

**Purpose:** Stay compliant & secure.

---

✅ **End State:**  
- AG → SaaS + DB traffic works through proxy/firewall  
- DB user least-privilege, TLS enforced  
- Metrics, Top Queries, Execution Plans (if enabled) visible in Dynatrace  
- Dashboards + alerts live, runbook documented

