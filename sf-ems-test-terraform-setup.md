
# sf-ems-test Terraform Setup — dt-csvlookup Role & Secret

This document describes how to use the Terraform files for the **sf-ems-test** AWS account to:

1. Create the **`dtcsvlookup`** Secrets Manager secret (Dynatrace OAuth client).
2. Create the **`gitlab-ci-s3-reader-role`** IAM role.
3. Attach an IAM policy that lets the role read:
   - The `sf-ems-dynatrace-test-scripts` S3 bucket (prefix `dtlookup/`).
   - The `dtcsvlookup` secret.
4. Configure the GitLab OIDC trust so your CI job can assume the role.

---

## 1. Folder Structure

Place the files in your GitLab repo at the following paths:

```text
terraform/
  modules/
    dtcsvlookup_secret/
      main.tf
      variables.tf
      outputs.tf

    gitlab_ci_s3_reader_role/
      main.tf
      variables.tf
      outputs.tf

  envs/
    sf-ems-test/
      main.tf
      variables.tf
      trust.json
      README.md  (optional helper; this file is similar)
      sf-ems-test.auto.tfvars  (local only, NOT committed)
```

> **Note:** `sf-ems-test.auto.tfvars` is **not** generated for you; it is created locally with real secrets and must **never** be committed to Git.

---

## 2. Modules Overview

### 2.1 `dtcsvlookup_secret` module

- Creates an AWS Secrets Manager secret.
- Stores the Dynatrace OAuth client configuration as a JSON string.
- Outputs the secret ARN.

Key file: `terraform/modules/dtcsvlookup_secret/main.tf`

```hcl
resource "aws_secretsmanager_secret" "this" {
  name        = var.secret_name
  description = var.secret_description
}

resource "aws_secretsmanager_secret_version" "this" {
  secret_id     = aws_secretsmanager_secret.this.id
  secret_string = jsonencode({
    client_id          = var.client_id
    client_secret      = var.client_secret
    grant_type         = var.grant_type
    resource           = var.resource
    dt_token_url       = var.dt_token_url
    dt_upload_url_prod = var.dt_upload_url_prod
    dt_upload_url_test = var.dt_upload_url_test
  })
}
```

---

### 2.2 `gitlab_ci_s3_reader_role` module

- Creates the IAM role used by GitLab CI.
- Attaches a policy that:
  - Lists the S3 bucket.
  - Reads objects under `dtlookup/`.
  - Reads the `dtcsvlookup` secret.

Key file: `terraform/modules/gitlab_ci_s3_reader_role/main.tf`

```hcl
resource "aws_iam_role" "this" {
  name                 = var.role_name
  description          = var.role_description
  max_session_duration = 3600

  assume_role_policy = var.assume_role_policy_json

  tags = merge(
    {
      Project     = "dt-csvlookup-datapipeline"
      ManagedBy   = "terraform"
      Environment = var.environment
    },
    var.tags
  )
}

locals {
  bucket_arn  = "arn:aws:s3:::${var.s3_bucket_name}"
  objects_arn = "${local.bucket_arn}/dtlookup/*"
  secret_arn  = var.dtcsvlookup_secret_arn
}

resource "aws_iam_policy" "this" {
  name        = var.policy_name
  description = var.policy_description

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid    = "ListBucket",
        Effect = "Allow",
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ],
        Resource = local.bucket_arn
      },
      {
        Sid    = "ReadObjects",
        Effect = "Allow",
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ],
        Resource = local.objects_arn
      },
      {
        Sid    = "AllowReadDtCsvLookupSecret",
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ],
        Resource = local.secret_arn
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach" {
  role       = aws_iam_role.this.name
  policy_arn = aws_iam_policy.this.arn
}
```

---

## 3. Environment: `sf-ems-test`

The environment folder **wires the modules together** for the EMS test account.

Key file: `terraform/envs/sf-ems-test/main.tf`

```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  trust_policy = file("${path.module}/trust.json")
}

module "dtcsvlookup_secret" {
  source = "../../modules/dtcsvlookup_secret"

  secret_name        = "dtcsvlookup"
  secret_description = "Dynatrace API creds to send CSV files to lookup tables"

  client_id          = var.dtcsvlookup_client_id
  client_secret      = var.dtcsvlookup_client_secret
  grant_type         = "client_credentials"
  resource           = var.dtcsvlookup_resource
  dt_token_url       = var.dt_token_url
  dt_upload_url_prod = var.dt_upload_url_prod
  dt_upload_url_test = var.dt_upload_url_test
}

module "gitlab_ci_s3_reader_role" {
  source = "../../modules/gitlab_ci_s3_reader_role"

  role_name               = "gitlab-ci-s3-reader-role"
  policy_name             = "gitlab-ci-s3-readonly-dt-sf-ems-test"
  environment             = "sf-ems-test"
  assume_role_policy_json = local.trust_policy

  s3_bucket_name         = "sf-ems-dynatrace-test-scripts"
  dtcsvlookup_secret_arn = module.dtcsvlookup_secret.secret_arn

  tags = {
    Owner       = "Observability-Dynatrace"
    Application = "dt-csvlookup-datapipeline"
  }
}
```

---

## 4. GitLab OIDC Trust (`trust.json`)

File: `terraform/envs/sf-ems-test/trust.json`

This configures the trust relationship for the **sf-ems-test** account (ID `351454108853`) so your GitLab project can assume the role via OIDC:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::351454108853:oidc-provider/sfgitlab.opr.statefarm.org"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "sfgitlab.opr.statefarm.org:aud": "https://sfgitlab.opr.statefarm.org",
          "sfgitlab.opr.statefarm.org:sub": "project_path:event-management/observability/dynatrace/dt-csvlookup-datapipeline:ref_type:branch:ref:main"
        }
      }
    }
  ]
}
```

> If your GitLab project path or branch changes, update the `sub` condition.

---

## 5. `sf-ems-test.auto.tfvars` Template

Create this file **locally only** (do not commit) at:

```text
terraform/envs/sf-ems-test/sf-ems-test.auto.tfvars
```

Suggested template:

```hcl
# === Dynatrace OAuth client (from your existing secret in logpoc) ===
dtcsvlookup_client_id     = "<your_client_id>"       # e.g. dt0s02.J2SW1YNL
dtcsvlookup_client_secret = "<your_client_secret>"   # full secret value
dtcsvlookup_resource      = "<your_dt_account_urn>"  # e.g. urn:dtaccount:59b4bf64-f6dd-45d8-bda7-03c78d4478ac5

# === Dynatrace OAuth token endpoint ===
dt_token_url = "https://sso.dynatrace.com/sso/oauth2/token"

# === Dynatrace Lookup upload URLs ===
dt_upload_url_prod = "https://cqf94808.apps.dynatrace.com/platform/storage/resource-store/v1/files/tabular/lookup:upload"
dt_upload_url_test = "https://rfk59887.apps.dynatrace.com/platform/storage/resource-store/v1/files/tabular/lookup:upload"
```

You can copy the real values from your **existing `dtcsvlookup` secret in the LogPOC account** and reuse them here, or create a separate Dynatrace OAuth client for EMS test if required by your security team.

---

## 6. Running Terraform in sf-ems-test

1. Log into AWS console or CLI as an **admin in sf-ems-test**.
2. In your Git repo, after copying files into `terraform/`, run:

```bash
cd terraform/envs/sf-ems-test
terraform init
terraform plan
terraform apply
```

3. Terraform will:

   - Create/update the **`dtcsvlookup`** secret.
   - Create the **`gitlab-ci-s3-reader-role`** IAM role.
   - Attach the S3 + Secrets policy.
   - Configure the trust relationship per `trust.json`.

---

## 7. Optional: Git ignore for tfvars

Add this to your repo’s `.gitignore` to ensure secrets are never committed:

```gitignore
# Terraform environment secrets
terraform/envs/sf-ems-test/*.auto.tfvars
```

---

## 8. Quick Checklist for the Admin

- [ ] Files are in `terraform/` with the specified structure.  
- [ ] `trust.json` has account ID `351454108853` and correct GitLab project path.  
- [ ] `sf-ems-test.auto.tfvars` exists **locally** with valid Dynatrace credentials.  
- [ ] AWS CLI or console session is using the **sf-ems-test** account.  
- [ ] `terraform init`, `plan`, and `apply` succeed with no errors.  
- [ ] GitLab CI job is configured to assume `gitlab-ci-s3-reader-role` in sf-ems-test.

Once all the above are done, your GitLab pipeline should be able to:

- Assume the role via OIDC.
- Read CSVs from `sf-ems-dynatrace-test-scripts/dtlookup/`.
- Call Dynatrace APIs using the secret from Secrets Manager.
Here’s a clear, concrete breakdown of how many AWS resources you are building with this Terraform setup, and why each exists.

⸻

✅ High-level answer

👉 You are building 5 AWS resources in total
(plus 1 logical attachment resource that Terraform tracks)

⸻

🧱 Resource-by-resource breakdown

1️⃣ AWS Secrets Manager Secret

Resource type

aws_secretsmanager_secret

Name

dtcsvlookup

Purpose
	•	Stores Dynatrace OAuth credentials and endpoints:
	•	client_id
	•	client_secret
	•	token URL
	•	lookup upload URLs
	•	Used by GitLab CI (via IAM role) to authenticate to Dynatrace

Why this is needed
	•	Secrets are not hardcoded in GitLab
	•	Central, auditable secret storage
	•	Rotation-ready

✅ Counts as 1 AWS resource

⸻

2️⃣ Secrets Manager Secret Version

Resource type

aws_secretsmanager_secret_version

Purpose
	•	Stores the actual JSON payload (key/value pairs) inside the secret
	•	Every update creates a new version

Important clarification
	•	AWS Console shows this as part of the same secret
	•	Terraform treats it as a separate resource

✅ Counts as 1 AWS resource

⸻

3️⃣ IAM Role

Resource type

aws_iam_role

Name

gitlab-ci-s3-reader-role

Purpose
	•	Assumed by GitLab CI via OIDC
	•	Provides short-lived credentials (STS)
	•	No static IAM users or access keys

Trust relationship
	•	Trusted identity:

arn:aws:iam::351454108853:oidc-provider/sfgitlab.opr.statefarm.org


	•	Restricted to:
	•	One GitLab project
	•	One branch (main)

✅ Counts as 1 AWS resource

⸻

4️⃣ IAM Policy (Customer-managed)

Resource type

aws_iam_policy

Name

gitlab-ci-s3-readonly-dt-sf-ems-test

What it allows
	•	s3:ListBucket on:

sf-ems-dynatrace-test-scripts


	•	s3:GetObject* on:

sf-ems-dynatrace-test-scripts/dtlookup/*


	•	secretsmanager:GetSecretValue on:

dtcsvlookup



Why separate from role
	•	Clean separation of:
	•	Who can assume the role (trust)
	•	What the role can do (policy)

✅ Counts as 1 AWS resource

⸻

5️⃣ IAM Role Policy Attachment

Resource type

aws_iam_role_policy_attachment

Purpose
	•	Attaches the policy to the role
	•	Terraform tracks this relationship explicitly

Important note
	•	AWS does not show this as a “resource”
	•	Terraform must track it to manage lifecycle cleanly

✅ Counts as 1 Terraform-managed resource

⸻

📊 Final Count Summary

#	Resource	Type
1	Secrets Manager Secret	aws_secretsmanager_secret
2	Secret Version	aws_secretsmanager_secret_version
3	IAM Role	aws_iam_role
4	IAM Policy	aws_iam_policy
5	Role ↔ Policy Attachment	aws_iam_role_policy_attachment


⸻

🎯 Total

👉 5 AWS resources created

👉 2 logical groupings
	•	Secrets group (1 secret + versions)
	•	IAM group (role + policy + attachment)

⸻

🧠 What you are not creating (important)

You are NOT creating:
	•	❌ IAM users
	•	❌ Access keys
	•	❌ Cross-account policies
	•	❌ S3 buckets
	•	❌ GitLab resources
	•	❌ Dynatrace resources

This is purely identity + secret enablement, which is exactly correct.

⸻

If you want, next I can:
	•	Diagram the trust → role → policy → secret flow
	•	Explain which resources are mutable vs immutable
	•	Explain what happens during terraform apply vs re-apply

Just say the word.
