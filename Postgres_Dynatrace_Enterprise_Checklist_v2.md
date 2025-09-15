# 🛡️ Enterprise Checklist — PostgreSQL Observability in Dynatrace SaaS

This checklist is for **two teams** — **Postgres Team** (DBA) and **Dynatrace Team** (Monitoring/Infra) — to enable full PostgreSQL monitoring in Dynatrace SaaS via ActiveGate.

---

## 0️⃣ Scope & Planning (Shared)

- [ ] **Inventory & Scope**  
  *List DBs (hostname, port, TLS setup, on-prem vs RDS), AG host(s), network zones, and success criteria.*  
  **Purpose:** Avoid missing DBs and prevent rework in firewall and credential requests.

- [ ] **Decide Visibility Level**  
  Dynatrace PostgreSQL Extension 2.0 supports multiple levels of visibility.  
  Pick which ones you want to enable **up front**, as they define required privileges and change approvals:

  ### 🔹 Level A — Basic DB Metrics (Always Recommended)
  - **What You Get:**  
    - Active connections  
    - Waiting / blocked queries  
    - Deadlocks  
    - Transactions committed/rolled back  
    - Cache hit ratio  
    - Replication status & lag  
    - WAL activity & disk usage  
    - Checkpoint stats, buffer stats  
  - **Dynatrace Views:**  
    - "PostgreSQL" tile in **Databases** view  
    - Metrics available in DQL and dashboards  
    - Alerting on connections, replication lag, deadlocks
  - **Privileges Needed:**  
    - User with `pg_monitor`  
    - `CONNECT` privilege on the monitored DB  
  - **Change Scope:**  
    - Safe for production, read-only monitoring, no schema changes.

  ### 🔹 Level B — + Top Queries (Performance Hotspots)
  - **What You Get:**  
    - Top 100 queries by total execution time (from `pg_stat_statements`)  
    - Query count, avg duration, total runtime  
    - Query text (normalized)  
    - Correlation with DB load spikes in Dynatrace Problems  
  - **Dynatrace Views:**  
    - "Top queries" section in the Database screen  
    - Queries listed with execution stats  
    - Ability to drill down into slow query patterns over time
  - **Privileges Needed:**  
    - Everything from Level A  
    - `pg_stat_statements` extension enabled  
    - `GRANT SELECT ON pg_stat_statements TO dynatrace;`
  - **Change Scope:**  
    - Requires DB restart or reload if `pg_stat_statements` not previously enabled  
    - Involves config change (`shared_preload_libraries`) on some Postgres versions

  ### 🔹 Level C — + Execution Plans (Deep Diagnostics)
  - **What You Get:**  
    - Execution plan for top queries (EXPLAIN output in JSON)  
    - Ability to see which indexes were used or missing  
    - Estimated cost vs. rows vs. actual execution time  
    - Root-cause hints for slow queries (Seq Scan, Nested Loop, etc.)
  - **Dynatrace Views:**  
    - "Execution plan" tab for each slow query  
    - Plan tree visualization inside Dynatrace Problems
  - **Privileges Needed:**  
    - Everything from Level B  
    - Helper schema + SECURITY DEFINER function (created by DBA)
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
  - **Change Scope:**  
    - Schema creation + function deployment (change management needed)  
    - Security review (ensures no arbitrary SQL execution)

**Purpose:**  
This choice determines **what data you will see** in Dynatrace, **what privileges are granted**, and the **security/change management steps** required.

---

## 1️⃣ Network & Firewall (Dynatrace Team + Security)
... (rest of the file unchanged from v1)
