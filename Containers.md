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
