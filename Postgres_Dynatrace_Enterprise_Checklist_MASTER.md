# 🛡️ Enterprise Checklist — PostgreSQL Observability in Dynatrace SaaS

This comprehensive guide is for **two teams** — **Postgres Team** (DBA) and **Dynatrace Team** (Monitoring/Infra) — to enable **full PostgreSQL monitoring** in Dynatrace SaaS via ActiveGate.

It combines:
- ✅ Planning & network/firewall requirements
- ✅ Proxy & certificate setup for enterprise environments
- ✅ Database user creation, privileges, and optional execution plan helper
- ✅ ActiveGate configuration & health checks
- ✅ OneAgent installation (optional)
- ✅ Dynatrace PostgreSQL Extension 2.0 setup
- ✅ Validation, dashboards, and alerting guidance
- ✅ Security & compliance lifecycle tasks
- ✅ Detailed PostgreSQL metric catalog (grouped by Level A/B/C)
- ✅ Ready-to-run SQL and shell snippets for deployment

---

## 🧭 Table of Contents

1. [Scope & Planning (Shared)](#0️⃣-scope--planning-shared)  
2. [Dynatrace Documentation Verification Checklist](#-dynatrace-documentation-verification-checklist)  
3. [Network & Firewall](#1️⃣-network--firewall-dynatrace--security)  
4. [Certificates & TLS](#2️⃣-certificates--tls-shared)  
5. [Database User & Permissions](#3️⃣-database-user--permissions-postgres-team)  
6. [ActiveGate Readiness](#4️⃣-activegate-readiness-dynatrace-team)  
7. [OneAgent (Optional)](#5️⃣-oneagent-on-db-host-optional--onprem-only)  
8. [PostgreSQL Extension 2.0 Setup](#6️⃣-dynatrace-hub--postgresql-extension-20)  
9. [Execution Plans (Optional)](#7️⃣-execution-plans-optional-deep-diagnostics)  
10. [Validation, Dashboards & Alerts](#8️⃣-validation-dashboards-alerts)  
11. [Runbook, Ownership, Troubleshooting](#9️⃣-runbook-ownership-troubleshooting)  
12. [Security & Compliance Lifecycle](#-security--compliance-lifecycle)  
13. [Metrics & Insights by Level](#-postgresql-metrics--insights-by-level-with-source--dynatrace-attribute)  
14. [Appendix: Scripts & Snippets](#-appendix--scripts--snippets)

---

## 0️⃣ Scope & Planning (Shared)

- [ ] **Inventory & Scope**  
  *List DBs (hostname, port, TLS setup, on‑prem vs RDS), ActiveGate host(s), network zones, and success criteria.*  
  **Purpose:** Avoid missed systems; inform firewall, proxy, and credential design.

- [ ] **Decide Visibility Level**  
  Dynatrace PostgreSQL Extension 2.0 supports multiple levels of visibility. Choose what you want to enable **up front** — this drives required privileges and change approvals.

### 🔹 Level A — Basic DB Metrics (Always Recommended)
- **What You Get:** Connections, waits, deadlocks, transactions, cache hit ratio, WAL activity, replication lag, buffer stats.
- **Privileges Needed:** User with `pg_monitor` + `CONNECT` privilege.
- **Change Scope:** Safe, read‑only, no schema changes.

### 🔹 Level B — + Top Queries
- **What You Get:** Top 100 queries by total execution time (`pg_stat_statements`), normalized query text, execution counts, I/O usage.
- **Privileges Needed:** Level A + `pg_stat_statements` extension enabled + `GRANT SELECT` to `dynatrace`.
- **Change Scope:** Requires `shared_preload_libraries` change if not already enabled (reload or restart).

### 🔹 Level C — + Execution Plans
- **What You Get:** JSON execution plans for top queries, index usage, row estimates.
- **Privileges Needed:** Level B + helper schema and SECURITY DEFINER function.
- **Change Scope:** Requires DBA-owned schema/function deployment and security review.

---

## 📋 Dynatrace Documentation Verification Checklist

| Area | What to Verify | Why |
|------|----------------|-----|
| **ActiveGate** | Version ≥ 1.269, outbound HTTPS to `*.live.dynatrace.com`, proxy configured | Required for Extension 2.0 + TLS |
| **Certificates** | DB TLS enabled, CA trusted by AG | Secure connection & avoid SSL errors |
| **Postgres Version** | PostgreSQL ≥ 11 | Compatibility |
| **pg_stat_statements** | Installed & loaded via `shared_preload_libraries` | Needed for Top Queries |
| **Credential Vault** | Used for storing DB user credentials | No plaintext passwords |
| **Feature Sets** | Decide which metrics feature sets to enable | Control DDU consumption |
| **Execution Plan Function** | Created & EXECUTE granted only to `dynatrace` | Required for Level C |
| **Audit Logging** | Log DB connections for `dynatrace` user | Compliance & troubleshooting |
| **Scaling** | Endpoints per config < 20k | Avoid hitting Dynatrace limits |

---

## 1️⃣ Network & Firewall (Dynatrace + Security)

- Outbound HTTPS 443 from ActiveGate to Dynatrace SaaS
- Outbound TCP 5432 from ActiveGate to Postgres servers
- Configure proxy settings in `custom.properties` if needed
- Restrict inbound access to ActiveGate (jump hosts + MFA)
- Validate connectivity using `curl`, `nc`, `openssl`

---

## 2️⃣ Certificates & TLS (Shared)

- Enforce TLS on Postgres (`ssl = on`, TLSv1.2+)
- Import CA certs into ActiveGate truststore (`update-ca-trust` or `update-ca-certificates`)
- Ensure NTP/time sync for AG and DB hosts

---

## 3️⃣ Database User & Permissions (Postgres Team)

- Create `dynatrace` user with `pg_monitor`
- Enable `pg_stat_statements` for Level B
- Configure `pg_hba.conf` to allow AG subnet with SSL (`hostssl`)
- Smoke test credentials using `psql` before Dynatrace configuration

---

## 4️⃣ ActiveGate Readiness (Dynatrace Team)

- Harden OS, patch, minimal packages
- Confirm AG shows **Connected/Healthy** in Dynatrace
- Assign AG to proper network zone (`gatewayctl --set-network-zone`)
- Locate logs: `/var/log/dynatrace/gateway/`

---

## 5️⃣ OneAgent on DB Host (Optional / On‑prem only)

- Install silently with network zone and tags for host grouping
- Verify `systemctl status oneagent` and that host shows in Dynatrace

---

## 6️⃣ Dynatrace Hub — PostgreSQL Extension 2.0

- Install from Hub (Extension 2.0)
- Assign to AG group with DB reachability
- Store DB credentials in Credential Vault
- Configure endpoints, enable SSL, test connection
- Select feature sets carefully (affects DDU consumption)

---

## 7️⃣ Execution Plans (Optional Deep Diagnostics)

- Create `dynatrace` schema and `dynatrace_execution_plan()` SECURITY DEFINER function
- Restrict EXECUTE privilege to `dynatrace`
- Review by security team

---

## 8️⃣ Validation, Dashboards & Alerts

- Confirm metrics visible under Databases → PostgreSQL
- Confirm Top Queries and Execution Plans (if enabled)
- Build dashboards for connections, cache hit ratio, replication lag, deadlocks
- Configure alerts for connections > 80%, deadlocks > 0, cache hit ratio < 90%, replication lag > threshold

---

## 9️⃣ Runbook, Ownership, Troubleshooting

- **Postgres Team:** DB user, TLS setup, schema deployment, connection logging
- **Dynatrace Team:** AG setup, proxy/certs, extension configuration, dashboards, alerts

Common issues & checks:
- Proxy/firewall: check `custom.properties`
- SSL failures: import CA certs, validate hostname
- No Top Queries: check `pg_stat_statements` is enabled
- No Plans: check function exists and EXECUTE granted

---

## 🔁 Security & Compliance Lifecycle

- Rotate DB password periodically; update Credential Vault
- Quarterly review of privileges & AG firewall rules
- Keep ActiveGate and Extension updated

---

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
- **Level A:** Core health/capacity monitoring (24×7 dashboards)
- **Level B:** Query workload analysis (performance tuning)
- **Level C:** Root-cause diagnostics (deep performance investigations)

---

## 📎 Appendix — Scripts & Snippets

### A. Create Monitoring User
```sql
CREATE USER dynatrace WITH PASSWORD '<STRONG_PASSWORD>' INHERIT;
GRANT pg_monitor TO dynatrace;
```

### B. Enable Top Queries
```sql
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
GRANT SELECT ON pg_stat_statements TO dynatrace;
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
SELECT pg_reload_conf();
```

### C. Execution Plan Helper Function
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

### D. ActiveGate Proxy Config
```ini
[http.client]
proxy-server=<proxy-host>:<proxy-port>
proxy-user=<svc_proxy_user>
proxy-password=<svc_proxy_password>
```

### E. OneAgent Installation
```bash
ENV_ID="<your-env-id>"
PAAS_TOKEN="dt0c01.xxxxx"
curl -o Dynatrace-OneAgent-Linux.sh "https://${ENV_ID}.live.dynatrace.com/api/v1/deployment/installer/agent/unix/latest?Api-Token=${PAAS_TOKEN}&arch=x86&flavor=default"
sudo /bin/sh Dynatrace-OneAgent-Linux.sh APP_LOG_CONTENT_ACCESS=1 INFRA_ONLY=0 --set-network-zone=onprem-db
```

### F. Quick Connectivity Tests
```bash
curl -I https://<your-env>.live.dynatrace.com
nc -vz <db-host> 5432
openssl s_client -connect <db-host>:5432 -starttls postgres
psql -h <db-host> -p 5432 -U dynatrace -d <db> "sslmode=require" -c "select 1;"
```
