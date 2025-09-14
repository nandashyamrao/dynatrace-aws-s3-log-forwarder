# 🛡️ Enterprise Checklist — PostgreSQL Observability in Dynatrace SaaS

This checklist is for **two teams** — **Postgres Team** (DBA) and **Dynatrace Team** (Monitoring/Infra) — to enable full PostgreSQL monitoring in Dynatrace SaaS via ActiveGate.

---

## 0️⃣ Scope & Planning (Shared)

- [ ] **Inventory & Scope**  
  *List DBs (hostname, port, TLS setup, on-prem vs RDS), AG host(s), network zones, and success criteria.*  
  **Purpose:** Avoid missing DBs and prevent rework in firewall and credential requests.

- [ ] **Decide Visibility Level**  
  - **A:** Basic DB metrics (connections, locks, cache hit ratio)  
  - **B:** + Top Queries (`pg_stat_statements`)  
  - **C:** + Execution Plans (schema + helper function)  
  **Purpose:** Defines required privileges and change scope.

---

## 1️⃣ Network & Firewall (Dynatrace Team + Security)

- [ ] **Allow ActiveGate → Dynatrace SaaS (443)**  
  - Destination: `*.live.dynatrace.com` (or specific SaaS FQDN)  
  - Protocol: `HTTPS`  
  **Purpose:** AG needs outbound to upload metrics/config.

- [ ] **Allow ActiveGate → PostgreSQL (5432)**  
  - Destination: Each DB host on `tcp/5432`  
  **Purpose:** Extension queries DB metrics.

- [ ] **Corporate Proxy Configuration**  
  Add to `/var/lib/dynatrace/gateway/config/custom.properties`:
  ```ini
  [http.client]
  proxy-server=<proxy-host>:<proxy-port>
  proxy-user=<svc_proxy_user>
  proxy-password=<svc_proxy_password>
  ```
  Then restart ActiveGate:
  ```bash
  sudo systemctl restart dynatracegateway
  ```
  **Purpose:** Route all AG outbound traffic via corporate proxy.

- [ ] **Restrict Inbound**  
  Only allow SSH/RDP from jump host with MFA.  
  **Purpose:** Harden AG and reduce attack surface.

---

## 2️⃣ Certificates & TLS (Shared)

- [ ] **Enforce TLS on Postgres**  
  `ssl = on` and `ssl_min_protocol_version = 'TLSv1.2'` in `postgresql.conf`.  
  **Purpose:** Secure transport for credentials and data.

- [ ] **Trust DB Certificates on AG**  
  Import corporate CA or RDS CA to AG OS trust store:
  ```bash
  sudo cp mycorp-ca.pem /etc/pki/ca-trust/source/anchors/
  sudo update-ca-trust extract
  sudo systemctl restart dynatracegateway
  ```
  **Purpose:** Allow AG to validate DB certs.

- [ ] **NTP/Time Sync**  
  Ensure AG and DB host clocks are in sync.  
  **Purpose:** Avoid TLS handshake errors and timestamp drift.

---

## 3️⃣ Database User & Permissions (Postgres Team)

- [ ] **Create Least-Privilege User**
  ```sql
  CREATE USER dynatrace WITH PASSWORD '<STRONG_PASSWORD>' INHERIT;
  GRANT pg_monitor TO dynatrace;
  ```
  **Purpose:** Grants read-only access to system views without superuser.

- [ ] **Enable Top Queries (Optional but Recommended)**
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
  GRANT SELECT ON pg_stat_statements TO dynatrace;
  ```
  **Purpose:** Provides query-level performance data.

- [ ] **Execution Plan Function (Optional)**
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
  **Purpose:** Allows Dynatrace to fetch query execution plans securely.

- [ ] **Restrict Source in `pg_hba.conf`**
  ```
  hostssl all dynatrace 10.50.0.0/24 md5
  ```
  **Purpose:** Enforces access from AG subnet only.

- [ ] **Test Connectivity**
  ```bash
  psql "host=<db-host> port=5432 user=dynatrace dbname=<db> sslmode=require" -c "select 1;"
  ```
  **Purpose:** Validate network and credentials before moving to Dynatrace.

---

## 4️⃣ ActiveGate Readiness (Dynatrace Team)

- [ ] **Harden & Patch AG OS**
  Keep OS at enterprise baseline (CIS or equivalent).  
  **Purpose:** Reduce vulnerabilities.

- [ ] **Verify Connection to SaaS**
  Check AG in Dynatrace → Deployment Status → should show **Connected**.  
  **Purpose:** Confirms proxy/firewall setup is correct.

- [ ] **Network Zone**
  Assign network zone (e.g., `onprem-db`) for routing clarity:
  ```bash
  sudo /var/lib/dynatrace/gateway/agent/tools/gatewayctl --set-network-zone=onprem-db
  ```
  **Purpose:** Isolate DB monitoring traffic and control AG assignment.

---

## 5️⃣ OneAgent on DB Host (Dynatrace Team)

*(Skip for RDS/Aurora)*

```bash
curl -o Dynatrace-OneAgent-Linux.sh "<download-url>"
sudo /bin/sh Dynatrace-OneAgent-Linux.sh APP_LOG_CONTENT_ACCESS=1 INFRA_ONLY=0 --set-network-zone=onprem-db
sudo /opt/dynatrace/oneagent/agent/tools/oneagentctl --set-host-tag=role=db --set-host-tag=env=prod
```

**Purpose:** Collect host/process metrics and optionally tail Postgres logs.

---

## 6️⃣ Dynatrace Hub — PostgreSQL Extension (Dynatrace Team)

- [ ] **Install Extension 2.0**
  Hub → **PostgreSQL** → *Install* → Assign to AG group.  
  **Purpose:** Enables server-side metric polling.

- [ ] **Credential Vault**
  Store `dynatrace` DB credentials here (no plaintext).  
  **Purpose:** Secure password management & rotation.

- [ ] **Add Endpoint Config**
  Enter host, port, dbname, and select Credential Vault entry.  
  **Purpose:** Creates monitored target.

- [ ] **Test Endpoint**
  Use extension test button or check AG logs for successful connection.  
  **Purpose:** Early validation before production rollout.

---

## 7️⃣ Validation & Dashboards (Shared)

- [ ] **Metrics Visible**
  Check Dynatrace → Databases → PostgreSQL entity shows connections, locks, cache hit.  
  **Purpose:** Confirms data flow.

- [ ] **Top Queries Visible**
  Ensure `pg_stat_statements` output is appearing.  
  **Purpose:** Validates query-level insights.

- [ ] **Optional: Execution Plan**
  Trigger slow query and confirm plan view works.  
  **Purpose:** Root-cause analysis readiness.

- [ ] **Dashboards & Alerts**
  Build dashboard + alerting (connections > N, deadlocks > 0).  
  **Purpose:** Turn observability into actionable insights.

---

## 8️⃣ Security & Compliance (Shared)

- [ ] **Password Rotation**
  Update DB password per policy, refresh Credential Vault.  
  **Purpose:** Credential hygiene.

- [ ] **Audit & Review**
  Quarterly review of `dynatrace` user privileges and AG firewall rules.  
  **Purpose:** Meet compliance (SOC2/ISO).

- [ ] **Patch & Upgrade**
  Keep AG and Extension versions current (via Dynatrace Hub).  
  **Purpose:** Get latest security fixes & features.

---

✅ **End State:**  
- AG → SaaS + DB traffic allowed through proxy/firewall  
- DB user least-privilege + TLS enforced  
- Extension deployed & healthy  
- Metrics, top queries, (optional) execution plans visible in Dynatrace  
- Alerts/dashboard + runbook ready for operations
