# 📘 Container Log Flows — Standalone vs Kubernetes vs Enterprise Dynatrace

This document explains how **one log line** moves from a container to **Dynatrace SaaS** in three contexts:
1. Standalone VM (Docker/Podman)
2. Kubernetes / OpenShift (containerd / CRI-O)
3. Enterprise with Dynatrace (OneAgent + ActiveGate)

---

## 🗂️ Quick Comparison Table

| Context | Runtime | Log Storage Location | OneAgent Role | Enrichment | SaaS Result |
|---------|---------|----------------------|---------------|------------|-------------|
| **Standalone VM** | Docker/Podman | `/var/lib/docker/containers/<id>/<id>-json.log` | Host OneAgent tails JSON logs | `dt.host.*`, `dt.container.*` | Logs linked to host + container |
| **Kubernetes** | containerd / CRI-O | `/var/log/pods/<namespace>/<pod>/<id>/0.log` | OneAgent DaemonSet tails pod logs | `dt.host.*`, `dt.container.*`, `kubernetes.*` | Logs linked to host + pod/namespace |
| **Enterprise Dynatrace** | Same (Docker/K8s) | Same as above | OneAgent (host/DaemonSet) + ActiveGate | Adds Dynatrace IDs (`HOST-*`, `PROC-*`) | Logs fully correlated with metrics & traces |

---

## 1️⃣ Standalone VM / Bare-Metal (Docker)

**Raw Log (inside container stdout/stderr):**
```text
2025-08-29 14:15:10 ERROR Database connection timeout after 30s
```

**Runtime Storage (Docker JSON log):**
```json
{
  "log": "2025-08-29 14:15:10 ERROR Database connection timeout after 30s\n",
  "stream": "stderr",
  "time": "2025-08-29T14:15:10.123456789Z"
}
```
Stored at:
```
/var/lib/docker/containers/<container-id>/<container-id>-json.log
```

**In Dynatrace SaaS (after OneAgent enrichment):**
```json
{
  "timestamp": "2025-08-29T14:15:10Z",
  "content": "ERROR Database connection timeout after 30s",
  "dt.host.name": "vm-app-node01",
  "dt.container.id": "b6a1d2f38f4e..."
}
```

---

## 2️⃣ Kubernetes / OpenShift (containerd / CRI-O)

**Raw Log (pod stdout/stderr):**
```text
2025-08-29 14:15:10 ERROR Database connection timeout after 30s
```

**Runtime Storage (Pod log file):**
```
/var/log/pods/payments_ns/payments-api-7f9cdb45d8-xyz12/0.log
```

Example entry:
```text
2025-08-29T14:15:10.123456789Z stderr F 2025-08-29 14:15:10 ERROR Database connection timeout after 30s
```

**In Dynatrace SaaS (after DaemonSet enrichment):**
```json
{
  "timestamp": "2025-08-29T14:15:10Z",
  "content": "ERROR Database connection timeout after 30s",
  "dt.host.name": "worker-node-01",
  "dt.container.id": "b6a1d2f38f4e...",
  "kubernetes.namespace": "payments",
  "kubernetes.pod.name": "payments-api-7f9cdb45d8-xyz12",
  "kubernetes.node.name": "worker-node-01"
}
```

---

## 3️⃣ Enterprise Monitoring (Dynatrace OneAgent + ActiveGate)

**Raw Log (inside container):**
```text
2025-08-29 14:15:10 ERROR Database connection timeout after 30s
```

**Runtime Storage:**  
- Docker → JSON log file in `/var/lib/docker/containers/...`  
- containerd/CRI-O → Pod log file in `/var/log/pods/.../0.log`

**Enrichment Steps:**
1. OneAgent tails log file (on VM or via DaemonSet pod).  
2. Talks to runtime socket (`/var/run/docker.sock`, `/run/containerd/containerd.sock`, `/var/run/crio/crio.sock`) to map process → container.  
3. (In K8s) queries API (via Operator RBAC) for namespace/pod/node.  
4. Adds Dynatrace entity IDs (`HOST-*`, `PROC-*`).  

**Final Log in Dynatrace SaaS (Grail):**
```json
{
  "timestamp": "2025-08-29T14:15:10Z",
  "content": "ERROR Database connection timeout after 30s",
  "dt.host.name": "worker-node-01",
  "dt.host.id": "HOST-1A2B3C4D5E",
  "dt.container.id": "b6a1d2f38f4e...",
  "dt.process.name": "java",
  "kubernetes.cluster.name": "prod-k8s-cluster",
  "kubernetes.namespace": "payments",
  "kubernetes.pod.name": "payments-api-7f9cdb45d8-xyz12",
  "kubernetes.node.name": "worker-node-01"
}
```

---

## 🔄 End-to-End Flow Diagrams

### Standalone VM (Docker)
```
App → stdout/stderr → Docker JSON log → OneAgent on host → ActiveGate → Dynatrace SaaS
```

### Kubernetes (containerd/CRI-O)
```
App in Pod → stdout/stderr → Pod log file (0.log) → OneAgent DaemonSet → ActiveGate → Dynatrace SaaS
```

### Enterprise Dynatrace
```
App (VM/K8s) → runtime log file → OneAgent (host or DaemonSet) → metadata enrichment → ActiveGate → SaaS (Grail + DQL)
```

---

## 🌟 Why Context Matters

- **Standalone**: Logs are simple, one machine, local host enrichment.  
- **Kubernetes**: Logs distributed, OneAgent DaemonSet enriches with pod/namespace metadata.  
- **Enterprise Dynatrace**: Adds deep correlation (logs ↔ metrics ↔ traces) for full observability.

---
