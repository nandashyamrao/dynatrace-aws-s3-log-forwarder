# 🛡️ Enterprise Checklist — PostgreSQL Observability in Dynatrace SaaS

This end‑to‑end guide combines everything we discussed into **one complete, enterprise‑ready Markdown** you can share with both teams:
- 👥 **Postgres Team (DBA)**
- 🖥️ **Dynatrace Team (Monitoring/Infra)**

It covers **planning → network/proxy → certs → DB privileges → ActiveGate → OneAgent → Extension 2.0 → validation → security/compliance**, with copy‑pasteable snippets and clear *Purpose* for each step.

> **Applies to:** On‑prem PostgreSQL and cloud (e.g., Amazon RDS/Aurora; skip OneAgent on RDS).  
> **Goal:** Make PostgreSQL metrics, top queries, and (optionally) execution plans visible in **Dynatrace → Databases** with least privilege and enterprise controls.

---

## 🧭 Table of Contents

1. [Scope & Planning (Shared)](#-scope--planning-shared)  
2. [Dynatrace Documentation Verification Checklist](#-dynatrace-documentation-verification-checklist)  
3. [Network & Firewall (Dynatrace + Security)](#-network--firewall-dynatrace--security)  
4. [Certificates & TLS (Shared)](#-certificates--tls-shared)  
5. [Database User & Permissions (Postgres Team)](#-database-user--permissions-postgres-team)  
6. [ActiveGate Readiness (Dynatrace Team)](#-activegate-readiness-dynatrace-team)  
7. [OneAgent on DB Host (Optional / On‑prem only)](#-oneagent-on-db-host-optional--onprem-only)  
8. [Dynatrace Hub — PostgreSQL Extension 2.0](#-dynatrace-hub--postgresql-extension-20)  
9. [Execution Plans (Optional Deep Diagnostics)](#-execution-plans-optional-deep-diagnostics)  
10. [Validation, Dashboards, Alerts](#-validation-dashboards-alerts)  
11. [Runbook, Ownership, Troubleshooting](#-runbook-ownership-troubleshooting)  
12. [Security & Compliance Lifecycle](#-security--compliance-lifecycle)  
13. [Acceptance Criteria](#-acceptance-criteria)  
14. [Appendix — Scripts & Snippets](#-appendix--scripts--snippets)

---

## 0️⃣ Scope & Planning (Shared)

- [ ] **📋 Inventory & Scope**  
  *List DBs (hostname, port, TLS setup, on‑prem vs RDS), ActiveGate host(s), network zones, and success criteria.*  
  **Purpose:** Avoid missed systems; inform firewall, proxy, and credential design.

- [ ] **🔍 Decide Visibility Level**  
  Dynatrace PostgreSQL Extension 2.0 supports multiple levels of visibility.  
  Pick which ones you want to enable **up front** — these drive privileges and change controls:

  ### 🔹 Level A — Basic DB Metrics (Always Recommended)
  - **What You Get:**  
    - Active connections; waiting/blocked queries; deadlocks  
    - Transactions committed/rolled back; cache hit ratio  
    - Replication status & lag; WAL activity & disk usage  
    - Checkpoint stats; buffer stats
  - **Dynatrace Views:**  
    - “PostgreSQL” tile in **Databases**; metrics available in **DQL/dashboards**  
    - Alerting on connections, replication lag, deadlocks
  - **Privileges Needed:**  
    - User with `pg_monitor` and `CONNECT` on the target DB
  - **Change Scope:** Safe for prod; read‑only; no schema changes.

  ### 🔹 Level B — + Top Queries (Performance Hotspots)
  - **What You Get:**  
    - Top 100 queries by total runtime (from `pg_stat_statements`)  
    - Query count, average duration, total runtime; normalized SQL text  
    - Correlate query spikes with Problems
  - **Dynatrace Views:**  
    - “Top queries” panel; drill‑downs over time
  - **Privileges Needed:**  
    - Level A + `pg_stat_statements` enabled  
    - `GRANT SELECT ON pg_stat_statements TO dynatrace;`
  - **Change Scope:** May require reload/restart if `shared_preload_libraries` change is needed.

  ### 🔹 Level C — + Execution Plans (Deep Diagnostics)
  - **What You Get:**  
    - EXPLAIN plan (JSON) for slow/top queries; index usage; row estimates vs costs  
    - Root‑cause hints (Seq Scan vs Index Scan, etc.)
  - **Dynatrace Views:**  
    - “Execution plan” tab per query; plan tree in Problems
  - **Privileges Needed:**  
    - Level B + schema & SECURITY DEFINER helper function (DBA‑owned)
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
  - **Change Scope:** Schema/function rollout requires change control + security review.

**Purpose:** Your selection defines **what data appears** in Dynatrace and the **minimum privileges** and **approvals** needed.

---

## 📋 Dynatrace Documentation Verification Checklist

| ✅ Area | 🔍 What to Verify | 🎯 Why |
|---|---|---|
| **ActiveGate** | Version ≥ 1.269; outbound HTTPS to `*.live.dynatrace.com`; proxy configured if required | Needed for Extension 2.0 + TLS |
| **Certificates** | DB TLS enabled; DB CA trusted by AG; hostname validation if verify‑full | Avoid SSL failures; secure creds |
| **Postgres Version** | PostgreSQL ≥ 11 | Compatibility |
| **pg_stat_statements** | Installed & loaded in `shared_preload_libraries` | Required for *Top Queries* |
| **Credential Vault** | Store DB credentials in Vault (not plaintext) | Secret hygiene & rotation |
| **Feature Sets** | Choose metric feature sets consciously | Controls data volume & DDU usage |
| **Execution Plan Function** | Created by DBA; EXECUTE granted only to `dynatrace` | Needed for Level C |
| **Audit Logging** | Log DB connections for `dynatrace` user | Compliance & troubleshooting |
| **Scaling** | Endpoints/config scale within limits | Avoid hitting platform limits |

---

## 1️⃣ Network & Firewall (Dynatrace + Security)

- [ ] **🌐 Allow AG → Dynatrace SaaS (TCP/443)**  
  **What:** Permit outbound HTTPS from ActiveGate to your SaaS FQDN (e.g., `*.live.dynatrace.com`). When FQDN rules aren’t possible, request SaaS IP ranges via vendor.  
  **Purpose:** AG sends metrics/config; connection is agent‑initiated — no inbound from internet.

- [ ] **🔌 Allow AG → PostgreSQL (TCP/5432)**  
  **What:** Permit AG to reach each DB host on 5432; consider per‑subnet rules.  
  **Purpose:** Extension polls DB stats via SQL.

- [ ] **🧭 Corporate Proxy (if required)**  
  **What:** Configure AG to egress via HTTPS proxy.  
  **Purpose:** Conform to enterprise egress policies.  
  **Snippet:** `/var/lib/dynatrace/gateway/config/custom.properties`
  ```ini
  [http.client]
  proxy-server=<proxy-host>:<proxy-port>
  proxy-user=<svc_proxy_user>
  proxy-password=<svc_proxy_password>
  ```
  Restart: `sudo systemctl restart dynatracegateway`

- [ ] **🚫 Inbound Restrictions**  
  **What:** No internet‑facing inbound to AG; admin access only via jump hosts + MFA.  
  **Purpose:** Minimize attack surface.

- [ ] **🧪 Network Tests**  
  **What:**  
  ```bash
  curl -I https://<your-env>.live.dynatrace.com
  nc -vz <db-host> 5432
  openssl s_client -connect <db-host>:5432 -starttls postgres
  ```
  **Purpose:** Quick verify of egress and DB reachability/TLS.

---

## 2️⃣ Certificates & TLS (Shared)

- [ ] **🔒 Enforce TLS to DB**  
  **What:** `ssl = on` and `ssl_min_protocol_version = 'TLSv1.2'` (or higher). For RDS/Aurora, use AWS CA bundle.  
  **Purpose:** Protect credentials and data in transit.

- [ ] **🧾 Trust Chain on ActiveGate**  
  **What:** Import your DB CA into AG OS trust store.  
  **RHEL/CentOS:**
  ```bash
  sudo cp mycorp-ca.pem /etc/pki/ca-trust/source/anchors/
  sudo update-ca-trust extract
  sudo systemctl restart dynatracegateway
  ```
  **Debian/Ubuntu:**
  ```bash
  sudo cp mycorp-ca.pem /usr/local/share/ca-certificates/mycorp-ca.crt
  sudo update-ca-certificates
  sudo systemctl restart dynatracegateway
  ```
  **Purpose:** Allow AG to validate DB certs; avoid self‑signed issues.

- [ ] **⏱️ NTP / Clock Sync**  
  **What:** Ensure AG and DB clocks are accurate.  
  **Purpose:** Prevent TLS and Problem timeline anomalies.

---

## 3️⃣ Database User & Permissions (Postgres Team)

- [ ] **🗝️ Create Least‑Privilege Monitoring User**  
  ```sql
  CREATE USER dynatrace WITH PASSWORD '<STRONG_PASSWORD>' INHERIT;
  GRANT pg_monitor TO dynatrace;
  ```
  **Purpose:** `pg_monitor` = read‑only access to `pg_stat_*` and config views.

- [ ] **📈 Enable Top Queries (Level B/C)**  
  ```sql
  CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
  GRANT SELECT ON pg_stat_statements TO dynatrace;
  -- On many installs, also ensure:
  -- ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
  -- SELECT pg_reload_conf();  -- restart if required by platform
  ```
  **Purpose:** Enables query performance insights.

- [ ] **🧠 (Optional) Execution Plan Helper (Level C)**  
  See [Execution Plans](#-execution-plans-optional-deep-diagnostics).  
  **Purpose:** Securely fetch EXPLAIN JSON without superuser.

- [ ] **🛡️ Restrict Source in `pg_hba.conf`**  
  ```
  hostssl all dynatrace 10.50.0.0/24 md5
  ```
  **Purpose:** Only allow AG subnet; require SSL. For RDS/Aurora, set equivalent parameter/security rules.

- [ ] **🧪 Smoke Test Credentials**  
  ```bash
  psql -h <db-host> -p 5432 -U dynatrace -d <db> "sslmode=require" -c "select 1;"
  ```
  **Purpose:** Validate connectivity and privileges before configuring Dynatrace.

> **Do not grant:** SUPERUSER, CREATEROLE, CREATEDB, or write privileges to `dynatrace`.

---

## 4️⃣ ActiveGate Readiness (Dynatrace Team)

- [ ] **🛠️ Provision / Harden AG**  
  **What:** Patch OS; CIS baseline; minimal packages; restrict SSH; locate in “monitoring” subnet.  
  **Purpose:** Reduce risk; ensure stability.

- [ ] **🔗 Network Zone**  
  **What:** Assign AG to a zone (e.g., `onprem-db`) for routing/visibility.
  ```bash
  sudo /var/lib/dynatrace/gateway/agent/tools/gatewayctl --set-network-zone=onprem-db
  ```
  **Purpose:** Logical isolation and policy control.

- [ ] **📶 Health Check**  
  **What:** Dynatrace UI → Deployment Status → AG shows **Connected/Healthy**.  
  **Purpose:** Confirms egress, proxy, and certs are correct.

- [ ] **🗂️ Key Paths**  
  - Config: `/var/lib/dynatrace/gateway/config/`  
  - Logs: `/var/log/dynatrace/gateway/`  
  **Purpose:** Where to troubleshoot.

---

## 5️⃣ OneAgent on DB Host (Optional / On‑prem only)

> Skip for RDS/Aurora.

- [ ] **⬇️ Download & Install (Silent)**  
  ```bash
  ENV_ID="<your-env-id>"
  PAAS_TOKEN="dt0c01.xxxxx"
  curl -o Dynatrace-OneAgent-Linux.sh     "https://${ENV_ID}.live.dynatrace.com/api/v1/deployment/installer/agent/unix/latest?Api-Token=${PAAS_TOKEN}&arch=x86&flavor=default"

  sudo /bin/sh Dynatrace-OneAgent-Linux.sh     APP_LOG_CONTENT_ACCESS=1 INFRA_ONLY=0 --set-network-zone=onprem-db
  ```
  **Purpose:** Host/process metrics; optional Postgres log ingestion.

- [ ] **🏷️ Post‑install Tags**  
  ```bash
  /opt/dynatrace/oneagent/agent/tools/oneagentctl     --set-host-tag=role=db --set-host-tag=env=prod --set-network-zone=onprem-db
  ```
  **Purpose:** Standardized filtering & dashboards.

- [ ] **🔍 Verify**  
  `systemctl status oneagent` and check Dynatrace **Hosts**.  
  **Purpose:** Confirm agent is running and reporting.

---

## 6️⃣ Dynatrace Hub — PostgreSQL Extension 2.0

- [ ] **📦 Install the Extension**  
  **What:** Dynatrace Hub → *PostgreSQL* → **Install** (Extension 2.0; ID commonly `custom:tech:postgres` — verify in Hub).  
  **Purpose:** Server‑side DB metric collection.

- [ ] **👥 Assign to ActiveGate Group**  
  **What:** Select AG group that has reachability to DBs.  
  **Purpose:** Runs the extension where the DB is reachable.

- [ ] **🔐 Credential Vault**  
  **What:** Create a Vault entry for `dynatrace` DB credentials.  
  **Purpose:** No plaintext credentials; enables rotation without config edits.

- [ ] **➕ Add Endpoint(s)**  
  **What:** For each DB — host, port, database, **select Vault credential**, enable SSL. Optionally choose feature sets.  
  **Purpose:** Define monitored targets.

- [ ] **🧪 Test Connection**  
  **What:** Use the extension test (if present) or watch AG logs for success.  
  **Purpose:** Early detection of cert/firewall/permission issues.

- [ ] **📉 DDU & Feature Sets (Awareness)**  
  **What:** High‑freq or broad feature sets increase data volume (DDU).  
  **Purpose:** Cost/perf planning.

---

## 7️⃣ Execution Plans (Optional Deep Diagnostics)

If you want Dynatrace to display **EXPLAIN plans** for top/slow queries:

- [ ] **📁 Create Schema & Helper Function** *(DBA‑owned; SECURITY DEFINER)*  
  ```sql
  CREATE SCHEMA IF NOT EXISTS dynatrace AUTHORIZATION <dba_owner_role>;
  REVOKE ALL ON SCHEMA dynatrace FROM PUBLIC;
  GRANT USAGE ON SCHEMA dynatrace TO dynatrace;

  CREATE OR REPLACE FUNCTION dynatrace.dynatrace_execution_plan(query TEXT)
  RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
  DECLARE r JSON;
  BEGIN
    EXECUTE 'EXPLAIN (FORMAT JSON) ' || query INTO r;
    RETURN r;
  END $$;

  REVOKE ALL ON FUNCTION dynatrace.dynatrace_execution_plan(TEXT) FROM PUBLIC;
  GRANT EXECUTE ON FUNCTION dynatrace.dynatrace_execution_plan(TEXT) TO dynatrace;
  ```
  **Purpose:** Let `dynatrace` fetch plans securely without broad privileges.

- [ ] **⚠️ Security Notes**  
  - Own the function with a privileged DBA role.  
  - Restrict EXECUTE to only `dynatrace`.  
  - Optionally validate/normalize input to reduce risk of misuse.

---

## 8️⃣ Validation, Dashboards, Alerts

- [ ] **👀 Metrics Visible**  
  **Where:** Dynatrace → **Databases → PostgreSQL** entity shows connections, locks, cache hit, replication lag, etc.  
  **Purpose:** Confirms ingestion.

- [ ] **🔥 Top Queries Visible** (Level B)  
  **What:** Top/slow queries populated from `pg_stat_statements`.  
  **Purpose:** Identify hotspots.

- [ ] **🧠 Execution Plans Visible** (Level C)  
  **What:** EXPLAIN JSON available in query drill‑down.  
  **Purpose:** Root‑cause analysis (indexing, joins).

- [ ] **📊 Dashboards**  
  **What:** Build DB overview dashboard (connections, locks, deadlocks, replication lag, cache hit, temp files).  
  **Purpose:** Operations at a glance.

- [ ] **🚨 Alerting**  
  **Examples:**  
  - Connections > N for ≥5 min  
  - Deadlocks > 0  
  - Replication lag > X seconds  
  - Cache hit ratio < threshold  
  **Purpose:** Proactive incident response.

---

## 9️⃣ Runbook, Ownership, Troubleshooting

### 👥 Ownership
- **Postgres Team:** DB user, `pg_hba.conf`, TLS on DB, extensions, execution‑plan helper, DB restarts/reloads, connection logging.  
- **Dynatrace Team:** ActiveGate install/hardening, proxy & cert trust, extension install/config, Credential Vault, dashboards/alerts.

### 🧰 Common Troubleshooting

| Symptom | Likely Cause | What to Check |
|---|---|---|
| `AG cannot reach SaaS` | Proxy/firewall | Proxy config in `custom.properties`, firewall egress to `*.live.dynatrace.com` |
| `Connection refused 5432` | Firewall/route | Security group/NACL, on‑prem firewall, `nc -vz <db> 5432` |
| `SSL error / cert unknown` | Missing CA trust | Import CA to AG trust store; hostname matches; `openssl s_client` |
| `Auth failed` | Wrong creds/pg_hba | Vault entry updated? `pg_hba.conf` hostssl rule includes AG subnet |
| `No Top Queries` | `pg_stat_statements` not active | Confirm extension installed & in `shared_preload_libraries` |
| `No Execution Plans` | Helper missing or privileges | Schema/function present? EXECUTE granted to `dynatrace` |

---

## 🔁 Security & Compliance Lifecycle

- [ ] **🔐 Password Rotation** — Update DB password per policy; refresh Credential Vault; verify reconnection.  
- [ ] **🧾 Audit & Review** — Quarterly review of `dynatrace` user privileges and AG firewall rules.  
- [ ] **⬆️ Patch & Upgrade** — Keep AG and Extension versions current.  
- [ ] **📜 Change Management** — Document endpoint adds/removals, parameter changes, and schema/function deployments.

---

## ✅ Acceptance Criteria

- ActiveGate shows **Connected/Healthy**; egress via proxy verified.  
- `dynatrace` DB user created with **`pg_monitor`**, access restricted via **`pg_hba.conf`**, TLS enforced.  
- Extension 2.0 installed, endpoints configured, **connection test passes**.  
- **Metrics** visible; **Top queries** (if Level B) present; **Execution plans** (if Level C) retrievable.  
- Dashboards and alerts configured; runbook published; secrets in Credential Vault.

---

## 📎 Appendix — Scripts & Snippets

### A. Create Monitoring User (Least Privilege)
```sql
CREATE USER dynatrace WITH PASSWORD '<STRONG_PASSWORD>' INHERIT;
GRANT pg_monitor TO dynatrace;
-- Optional: limit to specific DB(s)
-- GRANT CONNECT ON DATABASE <db> TO dynatrace;
```

### B. Enable Top Queries (`pg_stat_statements`)
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
GRANT SELECT ON pg_stat_statements TO dynatrace;
/* If needed, ensure shared_preload_libraries includes pg_stat_statements
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
SELECT pg_reload_conf();  -- restart may be required
*/
```

### C. Execution Plan Helper (SECURITY DEFINER)
```sql
CREATE SCHEMA IF NOT EXISTS dynatrace AUTHORIZATION <dba_owner_role>;
REVOKE ALL ON SCHEMA dynatrace FROM PUBLIC;
GRANT USAGE ON SCHEMA dynatrace TO dynatrace;

CREATE OR REPLACE FUNCTION dynatrace.dynatrace_execution_plan(query TEXT)
RETURNS JSON LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE r JSON;
BEGIN
  EXECUTE 'EXPLAIN (FORMAT JSON) ' || query INTO r;
  RETURN r;
END $$;

REVOKE ALL ON FUNCTION dynatrace.dynatrace_execution_plan(TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION dynatrace.dynatrace_execution_plan(TEXT) TO dynatrace;
```

### D. `pg_hba.conf` Example (Restrict to AG Subnet)
```
hostssl all dynatrace 10.50.0.0/24 md5
```

### E. ActiveGate Proxy Config
`/var/lib/dynatrace/gateway/config/custom.properties`
```ini
[http.client]
proxy-server=<proxy-host>:<proxy-port>
proxy-user=<svc_proxy_user>
proxy-password=<svc_proxy_password>
```

### F. OneAgent Install (On‑prem)
```bash
ENV_ID="<your-env-id>"
PAAS_TOKEN="dt0c01.xxxxx"
curl -o Dynatrace-OneAgent-Linux.sh   "https://${ENV_ID}.live.dynatrace.com/api/v1/deployment/installer/agent/unix/latest?Api-Token=${PAAS_TOKEN}&arch=x86&flavor=default"
sudo /bin/sh Dynatrace-OneAgent-Linux.sh   APP_LOG_CONTENT_ACCESS=1 INFRA_ONLY=0 --set-network-zone=onprem-db
/opt/dynatrace/oneagent/agent/tools/oneagentctl   --set-host-tag=role=db --set-host-tag=env=prod --set-network-zone=onprem-db
```

### G. Quick Test Commands
```bash
# SaaS egress
curl -I https://<your-env>.live.dynatrace.com

# DB reachability
nc -vz <db-host> 5432

# TLS check to Postgres
openssl s_client -connect <db-host>:5432 -starttls postgres

# DB auth check
psql -h <db-host> -p 5432 -U dynatrace -d <db> "sslmode=require" -c "select 1;"
```

---

### 🧩 (Optional) Architecture at a Glance
```
[ Clients ]                [ Dynatrace SaaS ]
      |                           ▲
      | HTTPS 443 (via proxy)     | Control plane / data ingest
      v                           |
[ ActiveGate ] ── TCP 5432 ──> [ PostgreSQL Servers ]
      ▲
      | (optional)
      | OneAgent on DB hosts (on‑prem only, logs + host/process metrics)
```

I can’t directly edit the file you uploaded — but I’ve prepared the **exact Markdown section** with sources and attribute names. You can simply append it to the end of your `Postgres_Dynatrace_Enterprise_Checklist_ULTIMATE.md` file (right after the Appendix section).

Here’s the final section:

```markdown
## 📊 PostgreSQL Metrics & Insights by Level (with Source & Dynatrace Attribute)

### 🔹 **Level A — Basic DB Metrics (via `pg_stat_*` views)**

| Category | Metric | Source View / Function | Dynatrace Attribute | Purpose |
|---------|--------|----------------------|--------------------|---------|
| **Connections & Sessions** | Active Connections | `pg_stat_activity` | `db.connections.active` | Monitor session count; alert near `max_connections`. |
| | Idle Connections | `pg_stat_activity` | `db.connections.idle` | Identify wasted connection slots; tune poolers. |
| | Idle in Transaction | `pg_stat_activity` | `db.connections.idle_in_transaction` | Detect transactions blocking vacuum, causing bloat. |
| | Longest Running Query | `pg_stat_activity` | `db.query.longest_duration` | Catch runaway queries/transactions. |
| **Locks & Waits** | Blocked Queries | `pg_locks` | `db.locks.waiting` | Identify queries stuck on locks. |
| | Deadlocks | `pg_stat_database.deadlocks` | `db.locks.deadlocks` | Each deadlock rolls back a transaction. |
| **Transactions & Throughput** | Commits / Rollbacks | `pg_stat_database` | `db.transactions.commits`, `db.transactions.rollbacks` | Monitor TPS; rollbacks may indicate app errors. |
| **Cache & Buffers** | Cache Hit Ratio | Derived: `heap_blks_hit / (heap_blks_hit + heap_blks_read)` | `db.cache.hit_ratio` | Low ratio → tune queries, memory. |
| | Buffers Allocated/Written | `pg_stat_bgwriter` | `db.buffers.allocated`, `db.buffers.written` | Indicates memory churn. |
| **WAL & Checkpoints** | WAL Written | `pg_stat_wal` / `pg_stat_archiver` | `db.wal.bytes_written` | Track write workload, replication pressure. |
| | Checkpoints | `pg_stat_bgwriter` | `db.checkpoints.timed`, `db.checkpoints.requested` | Detect I/O storms from frequent checkpoints. |
| **Temp Usage** | Temp Files/Bytes | `pg_stat_database` | `db.temp.bytes`, `db.temp.files` | Detect sorts/spills to disk. |
| **Replication & HA** | Replication Lag | `pg_stat_replication` | `db.replication.lag.bytes` / `db.replication.lag.ms` | Alert when lag exceeds RTO. |
| | Replication Slots | `pg_replication_slots` | `db.replication.slots.active` | Prevent WAL buildup. |
| **Autovacuum Health** | Vacuum/Analyze Count | `pg_stat_user_tables` | `db.autovacuum.count`, `db.analyze.count` | Confirm vacuum keeps up. |
| | Dead Tuples | `pg_stat_user_tables.n_dead_tup` | `db.tuples.dead` | Large counts → table bloat. |
| **Table/Index Scans** | Seq / Index Scan Count | `pg_stat_user_tables` | `db.scans.seq`, `db.scans.index` | High seq scan ratio = possible missing indexes. |
| **Database Size** | Database Size | `pg_database_size()` | `db.size.bytes` | Capacity planning. |

---

### 🔹 **Level B — Top Queries (via `pg_stat_statements`)**

| Category | Metric / Insight | Source | Dynatrace Attribute | Purpose |
|---------|-----------------|--------|--------------------|---------|
| **Top Queries** | Top by Total Time | `pg_stat_statements.total_exec_time` | `db.query.top.total_time` | Tune queries consuming most DB time. |
| | Top by Calls | `pg_stat_statements.calls` | `db.query.top.calls` | Detect frequently executed queries (N+1 patterns). |
| | Top by Avg Duration | `mean_exec_time` | `db.query.top.avg_time` | Identify slowest queries even if rare. |
| | Top by I/O | `shared_blks_read` / `shared_blks_dirtied` | `db.query.top.io` | Detect queries causing highest I/O. |
| **Normalized SQL** | Query Text | `pg_stat_statements.query` | `db.query.normalized_text` | Group queries by normalized form for better insights. |

---

### 🔹 **Level C — Execution Plans (via Helper Function)**

| Category | Metric / Insight | Source | Dynatrace Attribute | Purpose |
|---------|-----------------|--------|--------------------|---------|
| **Plan Tree** | JSON Plan Output | `dynatrace.dynatrace_execution_plan()` | `db.query.plan.json` | Visualize join order, cost, index usage. |
| **Join Strategies** | Join Node Counts | EXPLAIN JSON nodes | `db.query.plan.join_counts` | Detect suboptimal joins (nested loops, hash joins). |
| **Scan Types** | Seq vs Index Scan Ratio | EXPLAIN JSON nodes | `db.query.plan.seq_scan_ratio` | Spot missing indexes. |
| **Row Estimates** | Planned vs Actual | EXPLAIN JSON nodes | `db.query.plan.estimate_vs_actual` | Reveal misestimated plans → ANALYZE or adjust stats targets. |

---

### 🎯 Practical Use
- **Level A** → Core health and capacity monitoring. Good for 24×7 ops dashboards.  
- **Level B** → Query workload analysis. Pinpoints hotspots and inefficiencies.  
- **Level C** → Root cause diagnostics. Used when deep tuning or RCA is needed.
```



