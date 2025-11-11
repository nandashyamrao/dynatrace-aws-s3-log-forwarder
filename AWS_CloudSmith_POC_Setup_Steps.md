# 🧭 AWS CloudSmith + Dynatrace + AIDevOps – Step-by-Step POC Setup Guide

---

## 🧩 1. Understand the Architecture

| Layer | Description |
|-------|--------------|
| 🟣 **Dynatrace** | Detects anomalies using Davis AI and sends problem context. |
| 🟡 **AWS CloudSmith (AIOps backend)** | AI engine hosted by AWS that analyzes AWS-level data. |
| 🟢 **AIDevOps Operator App** | The AWS console interface and Slack-integrated chat assistant. |
| 🔐 **IAM Role (AgentSpace Role)** | Provides CloudSmith read-only access to your AWS account. |

📊 **Flow Summary**
```
Dynatrace → CloudSmith (AI investigation) → AIDevOps Operator App → Remediation / Report
```

---

## 🧱 2. Account Onboarding

1. 📨 **Request Beta Access**
   - Get your AWS account allow-listed by AWS AIDevOps Beta Team.
2. 🧾 **Confirm Opt-In**
   - Accept AWS CloudSmith Beta Terms.
   - AWS enables your account for CloudSmith backend access (`preprod.cloudsmith.amazonaws.com`).
3. 🌎 **Region:** `us-east-1`
   - Console: [AWS AIDevOps](https://us-east-1.console.aws.amazon.com/aidevops/home?region=us-east-1)

---

## 🧰 3. Create an AgentSpace

1. Navigate to **AWS AIDevOps Console → AgentSpaces**.  
2. Click **Create AgentSpace**.  
3. Enter:
   - 📛 *Name*: e.g., `Enterprise-Observability-POC`
   - 🗒️ *Description*: “Dynatrace + CloudSmith Integration”  
4. Click **Submit**.  

✅ Defines a workspace linking CloudSmith AI to your AWS environment.

---

## 🧩 4. Create IAM Roles

### Option 1 — Automated Role Creation (Recommended)
1. In the AIDevOps console → **Associations tab**  
2. Choose **Auto-create AIDevOps Role**  
3. Approve the CloudFormation stack.

This creates:
- `AIOpsAssistantPolicy` (read-only multi-service policy)
- `AIDevOpsOperatorRole` (for Operator App)
- Trust for `preprod.cloudsmith.amazonaws.com`

### Option 2 — Manual Creation
- Create IAM role with **trust** for the CloudSmith service account (`622494126653`).  
- Attach **AIOpsAssistantPolicy** manually.

---

## ⚙️ 5. Integrate with Dynatrace

1. In Dynatrace → **Settings → Integrations → AWS**, confirm AWS connection.  
2. Ensure Dynatrace API access is enabled.  
3. CloudSmith consumes “Problem payloads” via API tokens.  
4. Each new Dynatrace Problem triggers a CloudSmith AI investigation.

---

## 🔗 6. Enable Data Sources

| Source | Requirement |
|---------|--------------|
| 🧾 CloudTrail | Must be enabled across all accounts. |
| ⚙️ AWS Config | Needed for configuration diffs and topology graph. |
| 📈 CloudWatch Metrics | Required for correlation and anomaly tracking. |
| 🧠 IAM | Tracks roles, permissions, and identity changes. |

---

## 🧭 7. Build AWS Topology

CloudSmith auto-discovers via:
- CloudFormation stacks  
- Resource tags (`application`, `team`, `environment`)  
- VPCs and relationships  

View topology under **AIDevOps → AgentSpace → Topology View**.

---

## 🧠 8. Run Your First Investigation

1. Trigger a controlled error (e.g., remove `s3:PutObject` permission).  
2. Dynatrace detects failure → Problem created.  
3. CloudSmith analyzes telemetry and returns explanation:  
   > “Lambda `ingestion-demo` failed because IAM Role `r1` lost `s3:PutObject`.”  

✅ Confirms full AI loop: **Detect → Analyze → Explain → Action.**

---

## 🔒 9. Apply Governance and Security Controls

| Control | Purpose |
|----------|----------|
| 🛡️ SCPs | Block CloudSmith from reading PII or restricted workloads. |
| 🧾 CloudTrail Monitoring | Track CloudSmith service principal activity. |
| 🧠 IAM Analyzer | Validate role trust relationships. |
| 🔐 Risk Register | Document CloudSmith’s read-only access scope. |

---

## ⚙️ 10. Automate Remediation (Optional)

Integrate with **ServiceNow** or **AWS Systems Manager (SSM)**:  
Example:
```bash
aws ssm start-automation-execution --document-name "Remediate-Lambda-IAM-Role"
```
Slack notifications summarize findings + remediation status.

---

## 📊 11. Reporting and Review

After testing:
- Export reports from AIDevOps:
  - Problem types
  - Root causes
  - MTTR trends
- Present alongside merged POC document for leadership review.

---

## 🎯 POC Success Criteria

| Goal | Metric | Target |
|------|---------|--------|
| 🚨 Detection | Dynatrace detects AWS incidents | 100% of test events |
| 🧠 AI Analysis | CloudSmith root cause accuracy | ≥90% |
| 📊 MTTR | Reduction in diagnosis time | ≥60% faster |
| 🔒 Security | Zero unauthorized actions | ✅ |

---

## 🏁 Summary

✅ You’ve configured:
- AgentSpace + IAM roles  
- Dynatrace integration  
- AI-driven detection & analysis loop  
- Enterprise-grade security guardrails  

**Outcome:** CloudSmith + Dynatrace + AIDevOps working together for AI-powered observability and automation.  

---

© 2025 AWS & Dynatrace | *Internal Beta – CloudSmith x AIDevOps POC Setup Guide*
