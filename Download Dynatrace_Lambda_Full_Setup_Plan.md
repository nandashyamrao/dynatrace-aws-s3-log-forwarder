
# ✅ Dynatrace Lambda Forwarder – Full Setup Plan

This setup includes:
- 🔨 Terraform-managed resources
- 🛠️ Manual configuration
- 📜 Required policies
- 📦 Explanation of each component

---

## 🔢 Template / Manual Setup

| #  | Resource Setup Source | Resource Type                              | Account     | Purpose / Notes                                                                 |
|----|------------------------|--------------------------------------------|-------------|----------------------------------------------------------------------------------|
| 1  | `template.yaml`        | 🐍 Lambda (Image-based)                    | Account A   | Main log forwarder Lambda that processes logs and sends to Dynatrace            |
| 2  | `template.yaml`        | 🔐 IAM Role + Policy                      | Account A   | Permissions to access S3, SQS, SSM, and KMS                                     |
| 3  | `template.yaml`        | 📩 SQS Queue                               | Account A   | Receives EventBridge events from Account B                                      |
| 4  | `template.yaml`        | 📦 ECR Repository                          | Account A   | Hosts Docker image for Lambda                                                   |
| 5  | `template.yaml`        | 🧠 AppConfig (Environment + Config)        | Account A   | Stores log processing & forwarding rules                                        |
| 6  | `eventbridge-cross-region-or-account-forward-rules.yaml` | 🌉 EventBridge Rule          | Account B   | Forwards S3 PUT events to Account A Event Bus or SQS                            |
| 7  | `eventbridge-cross-region-or-account-forward-rules.yaml` | 🛂 IAM Role (EventBridge)    | Account B   | Grants EventBridge permission to invoke target in Account A                     |
| 8  | Manual or Terraform    | 🔐 SSM Parameters (DT_API_TOKEN, URL)     | Account A   | Stores secrets securely                                                         |
| 9  | Manual or Terraform    | 🔐 KMS Key (for SSM)                       | Account A   | Encrypts sensitive values stored in SSM                                         |
| 10 | Manual or TF inline    | 📜 S3 Bucket Policy                        | Account B   | Allows Lambda in Account A to read log files                                    |
| 11 | Manual or TF inline    | 📜 SQS Queue Policy                        | Account A   | Allows EventBridge from Account B to send messages                              |
| 12 | Manual or TF inline    | 📜 IAM Trust Policy                        | Account A   | Allows Lambda + access to SSM and S3                                            |
| 13 | Manual or Terraform    | 🧭 Event Bus Permissions                   | Account A   | Allow Account B to publish events (if using EventBus directly)                  |
| 14 | Manual                 | 📁 S3 Bucket (cf-logs-bucket-b)            | Account B   | Stores CloudFront access logs                                                   |
| 15 | Manual                 | 🧪 Enable EventBridge Notification         | Account B   | Configure EventBridge on S3 PUT events                                          |

---

## 🧱 Suggested Terraform Modules

| Module Name             | Description                                           |
|------------------------|-------------------------------------------------------|
| `lambda_forwarder`     | Creates Lambda, IAM role, and associated permissions  |
| `sqs_forwarding_queue` | Creates SQS queue and attaches access policies        |
| `appconfig_ruleset`    | Creates AppConfig Environment and Configuration       |
| `ssm_kms`              | Provisions SSM secrets with encryption via KMS        |
| `eventbridge_rule_b`   | EventBridge rule in Account B with IAM targeting A    |
| `ecr_repo`             | Deploys ECR repository for Lambda image               |
| `bucket_policy_b`      | Grants read access on logs bucket to Lambda in A      |

---

Would you like this full setup in modular Terraform layout (with `variables.tf`, `main.tf`, `outputs.tf`)?

Or as a **monolithic Terraform plan** with inline code examples?

Let me know and I’ll generate it for download 📥
