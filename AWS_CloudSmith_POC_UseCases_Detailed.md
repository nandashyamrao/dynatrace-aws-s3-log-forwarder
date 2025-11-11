# 📘 AWS CloudSmith + Dynatrace + AIDevOps — Detailed Use Cases

This document describes the **core four use cases** validated during the Proof of Concept (POC) phase for AWS CloudSmith and Dynatrace integration with AIDevOps.

Each use case includes its objective, flow, AI involvement, and enterprise value.

---

## 🟣 Use Case 1 — IAM Permission Drift Detection

### 🎯 Objective
Automatically detect and explain AWS Lambda or service failures caused by **missing or modified IAM permissions**.

### 🧱 Architecture Involved
- **AWS Lambda** using **S3 SDK**
- **IAM Role** with restricted permissions
- **CloudTrail** + **Config** for historical change tracking
- **Dynatrace Davis AI** detecting the runtime failure
- **AWS CloudSmith AI Engine** performing configuration-drift analysis

### 🧩 Flow of Events
1. Lambda writes objects to S3 bucket.
2. IAM policy update removes `s3:PutObject` from Lambda role.
3. Next invocation returns HTTP 403 AccessDenied.
4. Dynatrace detects Lambda error rate → opens a **Problem**.
5. Problem payload sent to **AWS CloudSmith**.
6. CloudSmith:
   - Reads IAM role JSON
   - Queries **CloudTrail** for IAM policy change
   - Correlates timestamp with error
7. AI outputs:
   > “Execution role `lambda-ingest-r1` lost `s3:PutObject` at 14:02 UTC. Lambda failures started 14:03 UTC.”
8. **AIDevOps App** summarizes in Slack/Console.

### ⚙️ AI Actions
| Step | Engine | Description |
|------|---------|--------------|
| 1 | Dynatrace Davis | Detects anomaly |
| 2 | CloudSmith | Cross-checks IAM policy & CloudTrail |
| 3 | AIDevOps | Generates natural-language root cause |

### 🧠 Business Value
- Eliminates manual IAM debugging.  
- Reduces MTTR from hours to minutes.  
- Provides auditable configuration drift detection.

### 🛡️ Governance
Read-only; IAM policy access logged in CloudTrail.

---

## 🟣 Use Case 2 — Deployment Impact Correlation

### 🎯 Objective
Identify if a new deployment or CloudFormation change caused a spike in latency or service failure.

### 🧱 Architecture Involved
- **CodePipeline / CloudFormation / GitHub Actions**
- **ECS / Lambda / API Gateway** monitored by Dynatrace
- **CloudWatch** metrics + **CloudTrail** stack events
- **CloudSmith** temporal correlation model

### 🧩 Flow of Events
1. DevOps deploys new version via CodePipeline.
2. Post-deployment, latency spikes on `/orders` API.
3. Dynatrace creates **Problem**.
4. CloudSmith retrieves:
   - CloudFormation events
   - CodePipeline execution logs
   - CloudWatch anomalies
5. Finds deployment 6 minutes before spike.
6. AI summarizes:
   > “Performance degradation correlates with deployment `orders-api-stack` execution #243 at 14:55 UTC.”

### ⚙️ AI Actions
- Temporal correlation between deployment and metric anomaly.
- Assigns confidence score (e.g., 0.92) for change impact.
- Posts to Slack or AIDevOps console.

### 🧠 Business Value
- Links code changes to production impact.  
- Shortens war-room investigation time.  
- Creates automated audit trail.

### 🛡️ Governance
CloudSmith reads from deployment metadata only. No write access.

---

## 🟣 Use Case 3 — Infrastructure Misconfiguration / Policy Mismatch

### 🎯 Objective
Detect and explain network or policy misconfigurations (e.g., VPC endpoint and S3 bucket policy mismatch).

### 🧱 Architecture Involved
- **API Gateway → Lambda → S3**
- **VPC Endpoint Policy**
- **S3 Bucket Policy**
- **CloudTrail**, **Config**, **VPC Flow Logs**
- **CloudSmith Topology Graph**

### 🧩 Flow of Events
1. Lambda in VPC calls S3 PutObject → fails.
2. Dynatrace flags error in downstream dependency.
3. CloudSmith builds topology graph:
   - API → Lambda → VPC → Endpoint → S3.
4. Finds bucket policy denies endpoint access.
5. Output:
   > “S3 Bucket `orders-data` policy denies access from VPC Endpoint `vpce-0abc123`. Update policy to allow.”

### ⚙️ AI Actions
- Cross-service topology reasoning.
- Detects broken dependency chain.
- Suggests least-privilege correction.

### 🧠 Business Value
- Prevents multi-layer AWS misconfigurations.
- Delivers topology-aware RCA.
- Improves network visibility.

### 🛡️ Governance
Read-only; no policy modification allowed.

---

## 🟣 Use Case 4 — Persistent vs New Incident Differentiation

### 🎯 Objective
Differentiate between chronic incidents and new regressions using CloudWatch + Config timelines.

### 🧱 Architecture Involved
- **Dynatrace Problem Feed**
- **CloudWatch metrics**
- **AWS Config snapshots**
- **CloudSmith Temporal Reasoning Model**

### 🧩 Flow of Events
1. Dynatrace flags repeated “timeout” errors.
2. CloudSmith loads 30-day metrics and config diffs.
3. Detects identical pattern since previous month.
4. Concludes:
   > “Incident persisted since July 21. No new change correlates — likely existing issue.”

### ⚙️ AI Actions
- Baseline vs current comparison.  
- Historical signature correlation.  
- Problem de-duplication.

### 🧠 Business Value
- Reduces alert fatigue.  
- Focuses SREs on new incidents.  
- Improves operational efficiency.

### 🛡️ Governance
Uses stored CloudWatch data; no sensitive export.

---

## 🧭 Use Case Summary Table

| # | Category | Description | AI Focus | Business Value |
|---|-----------|--------------|-----------|----------------|
| 1 | **IAM Drift** | Detects missing permissions causing failures | Config Correlation | Rapid RCA |
| 2 | **Deployment Impact** | Links code changes to performance | Temporal Causality | Faster MTTR |
| 3 | **Infra Misconfig** | Finds cross-service policy mismatch | Topology Reasoning | Outage Prevention |
| 4 | **Persistent vs New** | Distinguishes old vs new issues | Temporal Learning | Alert Reduction |

---

© 2025 AWS & Dynatrace | *Internal Beta – CloudSmith x AIDevOps Detailed Use Cases*
