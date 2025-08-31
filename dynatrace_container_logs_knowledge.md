# 📘 Knowledge Document: Dynatrace Container Logs, Enrichment & Monitoring

This document consolidates the full conversation between the user and ChatGPT into a **structured reference guide** on how Dynatrace handles **container logs** across different contexts (Standalone, Kubernetes, Enterprise SaaS).

---

## 1. Overview
Dynatrace collects container logs and enriches them with metadata (`dt.host.*`, `dt.container.*`, `kubernetes.*`) so they can be correlated with metrics and traces in **Dynatrace SaaS (Grail)**.  
Enrichment requires correct installation of **OneAgent**, runtime socket access, RBAC in Kubernetes, and ActiveGate log monitoring capability.

---

## 2. OneAgent Setup

- **Full-stack mode**: OneAgent runs on the host (VM/bare metal) or as a **DaemonSet** in Kubernetes.  
- **App-only mode** (injected into container) → only sees app logs, no host/container context.  
- For **container logs with host enrichment**:  
  - Ensure OneAgent is full-stack.  
  - Enable Container Monitoring and Log Enrichment in the Dynatrace UI.  
  - Verify ActiveGate has Log Monitoring capability.

Example DQL to check:
```dql
fetch logs
| summarize by log.source, dt.host.name, dt.container.id
```

---

## 3. Log Enrichment Fields

**Enriched log entry example:**
```json
{
  "timestamp": "2025-08-29T14:15:10.123Z",
  "level": "ERROR",
  "content": "Database connection timeout after 30s",
  "log.source": "/var/log/app/server.log",
  "dt.host.name": "onprem-app-node01",
  "dt.host.id": "HOST-1A2B3C4D5E6789F0",
  "dt.container.id": "b6a1d2f38f4e73c9...",
  "dt.process.name": "java",
  "kubernetes.cluster.name": "prod-k8s-cluster",
  "kubernetes.namespace": "payments",
  "kubernetes.pod.name": "payments-api-7f9cdb45d8-xyz12",
  "kubernetes.node.name": "worker-node-01"
}
```

---

## 4. Container Runtime Socket

The **container runtime socket** is how OneAgent queries the runtime to map processes → containers.  

- **Docker** → `/var/run/docker.sock`  
- **containerd** → `/run/containerd/containerd.sock`  
- **CRI-O** → `/var/run/crio/crio.sock`  

Without access: logs ingested but no `dt.container.*`.  

**Analogy**: Like the **guest book at a hotel** 🏨. OneAgent (guest) sees someone but needs the guest book (socket) to know which room (container/pod).  

---

## 5. DaemonSet vs Deployment

| Feature | **DaemonSet (OneAgent)** | **Deployment (ActiveGate)** |
|---------|--------------------------|-----------------------------|
| Purpose | Ensures **one pod per node** for local visibility. | Runs a fixed number of replicas for load-balancing traffic. |
| Use Case | OneAgent → needs to see all node containers. | ActiveGate → central log/metric forwarding. |
| Analogy | Guard on each floor of a hotel 🏨. | Receptionists in the lobby 🛎️. |

---

## 6. Container Log Sources

1. **stdout/stderr** → Default logs, stored by runtime.  
   - Docker → `/var/lib/docker/containers/...-json.log`  
   - K8s → `/var/log/pods/.../0.log`  
2. **App log files** → e.g., `/var/log/app/error.log`.  
   - Requires `APP_LOG_CONTENT_ACCESS=1`.  

**Analogy**:  
- stdout/stderr = dashboard lights 🚗.  
- App files = mechanic’s notebook 📓.  

---

## 7. Types of Logs in Containers

- **Application logs** → framework messages, exceptions.  
- **Web server logs** → access logs (Nginx, Apache).  
- **Database/middleware logs** → errors from DBs, Kafka, Redis.  
- **Runtime/system logs** → container engine events.  
- **K8s control plane logs** → scheduler, API server.  

**Analogy**: Restaurant 🍳  
- Chef shouting = app logs.  
- Waiters’ notes = access logs.  
- Pantry logs = DB.  
- Building maintenance = runtime logs.  
- Manager clipboard = K8s control plane.  

---

## 8. Running Containers in Contexts

| Context | Runtime | Logging | Dynatrace role |
|---------|---------|---------|----------------|
| **Standalone VM** | Docker/Podman | `/var/lib/docker/...json.log` | OneAgent on host |
| **Kubernetes** | containerd/CRI-O | `/var/log/pods/.../0.log` | OneAgent DaemonSet |
| **Enterprise** | Same as above | Same as above | OneAgent + ActiveGate → SaaS |

**Analogies**:  
- Standalone = food truck 🚚.  
- Kubernetes = restaurant chain 🍽️.  
- Enterprise Dynatrace = auditors 👀 at every branch.  

---

## 9. End-to-End Log Line Journey

Example log line:  
```text
2025-08-29 14:15:10 ERROR Database connection timeout after 30s
```

### Standalone Docker
- Stored in: `/var/lib/docker/...-json.log`  
- Enriched: `dt.host.*`, `dt.container.*`  

### Kubernetes
- Stored in: `/var/log/pods/.../0.log`  
- Enriched: `dt.host.*`, `dt.container.*`, `kubernetes.*`  

### Enterprise Dynatrace
- Same storage.  
- Enriched: above + Dynatrace entity IDs (`HOST-*`, `PROC-*`).  

---

## 10. Permissions Checklist

| Component | Permission | Why Needed | If Missing |
|-----------|------------|------------|------------|
| Host OS | OneAgent root/full-stack | Read logs, map processes | No host-level data |
| Runtime | Access to socket | Map process→container | No container metadata |
| Kubernetes | RBAC get/list/watch (pods, nodes, ns) | Enrich with `kubernetes.*` | No pod/namespace mapping |
| ActiveGate | Log Monitoring capability | Forward logs | Logs never leave host |
| Network | Outbound HTTPS 443 | Upload to SaaS | Logs stuck locally |

---

## 11. Install Checklists

### Kubernetes / OpenShift
- Install **ActiveGate** with Log Monitoring.  
- Deploy **Dynatrace Operator** via Helm.  
- Namespace annotation:  
  ```bash
  kubectl annotate namespace payments oneagent.dynatrace.com/logs=true --overwrite
  ```

### VM / Docker
- Install ActiveGate.  
- Install OneAgent:  
  ```bash
  sudo sh Dynatrace-OneAgent-Linux.sh APP_LOG_CONTENT_ACCESS=1 INFRA_ONLY=0
  ```

---

## 12. Validation (DQL)

### Verify enrichment
```dql
fetch logs
| fields content, dt.host.name, dt.container.id, kubernetes.namespace, kubernetes.pod.name
| limit 10
```

### Errors by pod
```dql
fetch logs
| filter level in ("ERROR","FATAL")
| summarize errors=count(), by:[dt.host.name, kubernetes.namespace, kubernetes.pod.name]
```

### Noisy containers
```dql
fetch logs
| summarize logs=count(), by:[dt.container.id, dt.host.name, kubernetes.namespace]
| sort logs desc
| limit 20
```

---

## 13. Flow Diagrams

**Standalone**  
```
App → stdout/stderr → Docker JSON log → OneAgent → ActiveGate → Dynatrace SaaS
```

**Kubernetes**  
```
App in Pod → stdout/stderr → Pod log (0.log) → OneAgent DaemonSet → ActiveGate → SaaS
```

**Enterprise Dynatrace**  
```
App → runtime log → OneAgent (enrich) → ActiveGate → SaaS (Grail)
```

---

# ✅ Summary

- Install OneAgent in **full-stack** mode.  
- Ensure runtime socket + RBAC + log enrichment are enabled.  
- Logs gain `dt.host.*`, `dt.container.*`, and `kubernetes.*` automatically.  
- ActiveGate forwards securely to SaaS.  
- Dynatrace Grail + DQL = full correlation across **logs, metrics, and traces**.

---
