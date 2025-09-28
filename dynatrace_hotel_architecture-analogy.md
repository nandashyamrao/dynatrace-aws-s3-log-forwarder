# 🏨 Dynatrace SaaS Hotel – Setup Analogy (with Environment Boundary)

This version shows a **clear boundary** between **your AWS environment** and **Dynatrace SaaS**. Both live in AWS, but they are **separate responsibility domains**.

---

## 🗺️ Text‑Box Architecture with Boundary

```text
====================  YOUR AWS ENVIRONMENT (Customer VPC/Accounts)  ====================

+-------------------------------------------------------------+
|  🚌 Lambda Buses (Your Code)                                |
|  - Each invocation = busload of guests (log batches)        |
|  - Dynatrace layer = tour guide (tags/collects telemetry)   |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  🛂 ActiveGate (Shuttle Terminal & Staging)                 |
|  - Validates tickets (API token) on port 9999               |
|  - Waiting area (disk queue) if hotel is busy               |
|  - Sends shuttles (HTTPS) to SaaS                           |
+-------------------------------------------------------------+

------------------------------------  TRUST BOUNDARY  ------------------------------------
                  (Outbound HTTPS 443 from ActiveGate to Dynatrace SaaS)

===========================  DYNATRACE SAAS (Dynatrace-managed)  ==========================

+-------------------------------------------------------------+
|  🏢 HAProxy (Hotel Lobby & Front Desk)                      |
|  - Controls lobby capacity, routes guests to desks          |
|  - Queues when desks are busy, rejects when full (503)      |
|  - Metrics: active connections, queue depth, 5xx count      |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  👩‍🍳 Ingestion Service (Check-in Desks / Kitchen)           |
|  - Each pod = check-in desk                                 |
|  - Connection Pool = stoves (limited)                       |
|  - If all stoves busy, orders wait on counter               |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|  📦 Grail (Pantry / Record Room)                            |
|  - Stores logs, ready for dashboards, queries, alerts       |
+-------------------------------------------------------------+
```

**Notes**
- **Your Side (Customer AWS):** You deploy and manage **Lambda** and **ActiveGate** (capacity, disk queue, networking).  
- **Trust Boundary:** Only **outbound HTTPS:443** from ActiveGate to SaaS. No inbound openings required into your VPC.  
- **Dynatrace SaaS Side:** Dynatrace operates **HAProxy**, **ingestion pods**, **connection pools**, and **Grail**.

---

## 🧭 Mermaid Diagram with Subgraphs (Boundary)

```mermaid
flowchart TB
  subgraph C[Customer AWS Environment]
    L[🚌 Lambda Buses<br/>Dynatrace layer = Tour Guide]
    AG[🛂 ActiveGate<br/>Shuttle Terminal & Staging<br/>:9999 + Disk Queue]
    L --> AG
  end

  %% Trust boundary / egress over HTTPS
  AG -- Outbound HTTPS 443 --> H

  subgraph S[Dynatrace SaaS (Dynatrace-managed)]
    H[🏢 HAProxy<br/>Lobby & Front Desk<br/>Queue & 503s when full]
    I[👩‍🍳 Ingestion Pods<br/>Check-in Desks + Stoves (Connection Pool)]
    G[📦 Grail<br/>Pantry & Record Room]
    H --> I --> G
  end

  classDef good fill:#e8f5e9,stroke:#2e7d32,stroke-width:1px,color:#1b5e20;
  classDef edge fill:#e3f2fd,stroke:#1565c0,stroke-width:1px,color:#0d47a1;
  class L good; class AG edge; class H edge; class I good; class G good;
```

---

## 🔑 Ownership at a Glance
- **Customer AWS (You):** Lambda concurrency & batch size, ActiveGate scaling/queue, security groups/NACLs.  
- **Dynatrace SaaS:** HAProxy capacity & policy, ingestion scaling, **connection pool size**, Grail durability.

**One‑liner:** *Your environment sends telemetry out through a single egress (HTTPS 443) to Dynatrace’s SaaS edge. Everything past that boundary — HAProxy, ingestion pods, and connection pools — is Dynatrace‑managed.*
