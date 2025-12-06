# Multi-Account Terraform Module Setup  
## sf-ems-prod · sf-ems-test · sf-logpoc-test  
### GitLab OIDC → AWS S3 → Secrets Manager → Dynatrace Lookup

This document defines a **module-based Terraform layout** to manage the same GitLab → AWS → Dynatrace pipeline across **three AWS accounts**:

- `sf-ems-prod`
- `sf-ems-test`
- `sf-logpoc-test`

It uses a single reusable **module** and three small **per-account stacks**.

---

## 1. Repository / Terraform Folder Layout

Suggested layout:

```text
infra/
└── dt-csvlookup/
    ├── modules/
    │   └── dt-csvlookup-env/
    │       ├── main.tf
    │       ├── variables.tf
    │       └── outputs.tf
    └── envs/
        ├── sf-ems-test/
        │   └── main.tf
        ├── sf-ems-prod/
        │   └── main.tf
        └── sf-logpoc-test/
            └── main.tf
```

You will run `terraform init/plan/apply` **from within each env folder** (e.g. `envs/sf-ems-test`), using the correct AWS credentials/profile for that account.

---

## 2. Module: `modules/dt-csvlookup-env`

This module creates, **per account**:

- An S3 bucket:  
  `sf-<account>-<env>-dtcsvlookupdata` via a generic `account_prefix` + `bucket_suffix`
- An IAM role that GitLab CI assumes via **OIDC**
- An IAM policy granting:
  - Read-only access to that S3 bucket
  - Read access to a Secrets Manager secret (Dynatrace OAuth config)
- A Secrets Manager secret `dtcsvlookup` (with placeholder JSON)

> You can reuse this module in **any account** by changing `account_prefix` and provider configuration.

---

### 2.1 `modules/dt-csvlookup-env/variables.tf`

```hcl
variable "aws_region" {
  description = "AWS region to deploy resources in"
  type        = string
  default     = "us-east-1"
}

variable "gitlab_domain" {
  description = "GitLab OIDC domain (State Farm GitLab)"
  type        = string
  default     = "sfgitlab.opr.statefarm.org"
}

variable "gitlab_sub" {
  description = "GitLab OIDC 'sub' claim (project_path + ref)"
  type        = string
  # Matches dt-csvlookup-datapipeline main branch
  default     = "project_path:event-management/observability/dynatrace/dt-csvlookup-datapipeline:ref_type:branch:ref:main"
}

variable "account_prefix" {
  description = <<EOT
Enterprise prefix indicating the AWS account and environment.
Examples:
  - "sf-ems-test"
  - "sf-ems-prod"
  - "sf-logpoc-test"
This is used in naming of S3 buckets, IAM roles, and policies.
EOT
  type = string
}

variable "bucket_suffix" {
  description = "Suffix to append to account_prefix for the S3 bucket name."
  type        = string
  default     = "dtcsvlookupdata"  # gives sf-ems-test-dtcsvlookupdata, etc.
}

variable "role_name_override" {
  description = <<EOT
Optional custom IAM role name. If empty, a name will be derived from account_prefix.
EOT
  type    = string
  default = ""
}

variable "policy_name_override" {
  description = <<EOT
Optional custom IAM policy name. If empty, a name will be derived from account_prefix.
EOT
  type    = string
  default = ""
}

variable "dt_secret_name" {
  description = "Name of the AWS Secrets Manager secret for Dynatrace OAuth."
  type        = string
  default     = "dtcsvlookup"
}
```

---

### 2.2 `modules/dt-csvlookup-env/main.tf`

```hcl
terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_caller_identity" "current" {}

locals {
  # Example: sf-ems-test-dtcsvlookupdata
  s3_bucket_name = "${var.account_prefix}-${var.bucket_suffix}"

  # Derived IAM names if not explicitly overridden
  role_name = (
    var.role_name_override != "" ?
    var.role_name_override :
    "${var.account_prefix}-role-dtcsvlookup-gitlab"
  )

  policy_name = (
    var.policy_name_override != "" ?
    var.policy_name_override :
    "${var.account_prefix}-policy-dtcsvlookup-gitlab-s3-sm-readonly"
  )

  # ARN of pre-existing GitLab OIDC provider in this account
  gitlab_oidc_provider_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${var.gitlab_domain}"

  gitlab_audience = "https://${var.gitlab_domain}"
}

# -------------------------------------------------------------------
# S3 bucket for GitLab CI CSV source
# -------------------------------------------------------------------
resource "aws_s3_bucket" "gitlab_ci_source" {
  bucket = local.s3_bucket_name

  tags = {
    application            = "dynatrace"
    bca                    = "dynatrace"
    contact                = "DL-Dynatrace-Support.DLRFHX@internal.statefarm.com"
    cost-center            = "255184"
    off-hours-shutdown     = "disabled"
    sf-data-classification = "Internal-Use-Only"
    tenant                 = "dynatrace"
    vault_hostname         = "https://vault.infra.ic1.statefarm.com"
    workgroup              = "WG9900"
  }
}

resource "aws_s3_bucket_public_access_block" "gitlab_ci_source" {
  bucket = aws_s3_bucket.gitlab_ci_source.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Optional: enable versioning to keep history of uploaded CSVs
resource "aws_s3_bucket_versioning" "gitlab_ci_source" {
  bucket = aws_s3_bucket.gitlab_ci_source.id

  versioning_configuration {
    status = "Enabled"
  }
}

# -------------------------------------------------------------------
# Secrets Manager secret for Dynatrace OAuth (placeholder values)
# -------------------------------------------------------------------
resource "aws_secretsmanager_secret" "dt_oauth" {
  name        = var.dt_secret_name
  description = "Dynatrace OAuth credentials and endpoints for dt-csvlookup pipeline in ${var.account_prefix}"

  tags = {
    application            = "dynatrace"
    bca                    = "dynatrace"
    contact                = "DL-Dynatrace-Support.DLRFHX@internal.statefarm.com"
    cost-center            = "255184"
    off-hours-shutdown     = "disabled"
    sf-data-classification = "Internal-Use-Only"
    tenant                 = "dynatrace"
    vault_hostname         = "https://vault.infra.ic1.statefarm.com"
    workgroup              = "WG9900"
  }
}

resource "aws_secretsmanager_secret_version" "dt_oauth_version" {
  secret_id = aws_secretsmanager_secret.dt_oauth.id

  secret_string = jsonencode({
    client_id          = "<REPLACE_WITH_DT_CLIENT_ID>"
    client_secret      = "<REPLACE_WITH_DT_CLIENT_SECRET>"
    grant_type         = "client_credentials"
    resource           = "<REPLACE_WITH_DT_RESOURCE>"
    dt_token_url       = "https://sso2.dynatrace.com/sso/oauth2/token"
    dt_upload_url_test = "<REPLACE_WITH_DT_TEST_LOOKUP_UPLOAD_URL>"
    dt_upload_url_prod = "<REPLACE_WITH_DT_PROD_LOOKUP_UPLOAD_URL>"
  })
}

# -------------------------------------------------------------------
# IAM role assumed by GitLab CI via OIDC
# -------------------------------------------------------------------
resource "aws_iam_role" "gitlab_ci_s3_reader" {
  name        = local.role_name
  description = "Role assumed by GitLab CI via OIDC to read CSV from S3 and Dynatrace secret from Secrets Manager in ${var.account_prefix}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = local.gitlab_oidc_provider_arn
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "${var.gitlab_domain}:sub" = var.gitlab_sub
            "${var.gitlab_domain}:aud" = local.gitlab_audience
          }
        }
      }
    ]
  })

  tags = {
    application            = "dynatrace"
    bca                    = "dynatrace"
    contact                = "DL-Dynatrace-Support.DLRFHX@internal.statefarm.com"
    cost-center            = "255184"
    off-hours-shutdown     = "disabled"
    sf-data-classification = "Internal-Use-Only"
    tenant                 = "dynatrace"
    vault_hostname         = "https://vault.infra.ic1.statefarm.com"
    workgroup              = "WG9900"
  }
}

# -------------------------------------------------------------------
# IAM policy: S3 read-only + Secrets Manager read access
# -------------------------------------------------------------------
resource "aws_iam_policy" "gitlab_ci_s3_sm_readonly" {
  name        = local.policy_name
  description = "Read-only access to S3 bucket ${local.s3_bucket_name} and Dynatrace secret ${var.dt_secret_name} for GitLab CI in ${var.account_prefix}"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ListBucket"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = "arn:aws:s3:::${local.s3_bucket_name}"
      },
      {
        Sid    = "ReadObjects"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "arn:aws:s3:::${local.s3_bucket_name}/*"
      },
      {
        Sid    = "ReadDynatraceSecret"
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Resource = aws_secretsmanager_secret.dt_oauth.arn
      }
    ]
  })

  tags = {
    application            = "dynatrace"
    bca                    = "dynatrace"
    contact                = "DL-Dynatrace-Support.DLRFHX@internal.statefarm.com"
    cost-center            = "255184"
    off-hours-shutdown     = "disabled"
    sf-data-classification = "Internal-Use-Only"
    tenant                 = "dynatrace"
    vault_hostname         = "https://vault.infra.ic1.statefarm.com"
    workgroup              = "WG9900"
  }
}

resource "aws_iam_role_policy_attachment" "gitlab_ci_s3_sm_readonly_attach" {
  role       = aws_iam_role.gitlab_ci_s3_reader.name
  policy_arn = aws_iam_policy.gitlab_ci_s3_sm_readonly.arn
}
```

---

### 2.3 `modules/dt-csvlookup-env/outputs.tf`

```hcl
output "s3_bucket_name" {
  description = "Name of the S3 bucket for GitLab CI CSV source"
  value       = aws_s3_bucket.gitlab_ci_source.bucket
}

output "gitlab_ci_role_arn" {
  description = "IAM role ARN to use in GitLab CI for OIDC → AWS STS"
  value       = aws_iam_role.gitlab_ci_s3_reader.arn
}

output "gitlab_ci_policy_arn" {
  description = "ARN of the IAM policy granting read-only S3 + Secrets Manager access"
  value       = aws_iam_policy.gitlab_ci_s3_sm_readonly.arn
}

output "dt_secret_name" {
  description = "Name of the Dynatrace OAuth secret in Secrets Manager"
  value       = aws_secretsmanager_secret.dt_oauth.name
}

output "dt_secret_arn" {
  description = "ARN of the Dynatrace OAuth secret in Secrets Manager"
  value       = aws_secretsmanager_secret.dt_oauth.arn
}
```

---

## 3. Environment: `envs/sf-ems-test/main.tf`

This stack deploys the module into the **sf-ems-test** account.

```hcl
terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# Configure this provider with credentials for sf-ems-test
provider "aws" {
  region = "us-east-1"
  # profile = "sf-ems-test"  # or use env vars / SSO
}

module "dt_csvlookup_env" {
  source = "../../modules/dt-csvlookup-env"

  aws_region     = "us-east-1"
  account_prefix = "sf-ems-test"

  # GitLab details (same across envs if using same project/branch)
  gitlab_domain = "sfgitlab.opr.statefarm.org"
  gitlab_sub    = "project_path:event-management/observability/dynatrace/dt-csvlookup-datapipeline:ref_type:branch:ref:main"

  bucket_suffix = "dtcsvlookupdata"  # => sf-ems-test-dtcsvlookupdata

  # Optional overrides (otherwise derived)
  # role_name_override   = "sf-ems-test-role-dtcsvlookup-gitlab"
  # policy_name_override = "sf-ems-test-policy-dtcsvlookup-gitlab-s3-sm-readonly"

  dt_secret_name = "dtcsvlookup"  # name inside sf-ems-test
}

output "s3_bucket_name" {
  value = module.dt_csvlookup_env.s3_bucket_name
}

output "gitlab_ci_role_arn" {
  value = module.dt_csvlookup_env.gitlab_ci_role_arn
}

output "dt_secret_name" {
  value = module.dt_csvlookup_env.dt_secret_name
}
```

---

## 4. Environment: `envs/sf-ems-prod/main.tf`

Same module, different `account_prefix` and (optionally) different secret.

```hcl
terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# Configure this provider with credentials for sf-ems-prod
provider "aws" {
  region = "us-east-1"
  # profile = "sf-ems-prod"
}

module "dt_csvlookup_env" {
  source = "../../modules/dt-csvlookup-env"

  aws_region     = "us-east-1"
  account_prefix = "sf-ems-prod"

  gitlab_domain = "sfgitlab.opr.statefarm.org"
  gitlab_sub    = "project_path:event-management/observability/dynatrace/dt-csvlookup-datapipeline:ref_type:branch:ref:main"

  bucket_suffix = "dtcsvlookupdata"  # => sf-ems-prod-dtcsvlookupdata

  dt_secret_name = "dtcsvlookup"     # name inside sf-ems-prod
}

output "s3_bucket_name" {
  value = module.dt_csvlookup_env.s3_bucket_name
}

output "gitlab_ci_role_arn" {
  value = module.dt_csvlookup_env.gitlab_ci_role_arn
}

output "dt_secret_name" {
  value = module.dt_csvlookup_env.dt_secret_name
}
```

---

## 5. Environment: `envs/sf-logpoc-test/main.tf`

For the `sf-logpoc-test` account:

```hcl
terraform {
  required_version = ">= 1.3.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

# Configure this provider with credentials for sf-logpoc-test
provider "aws" {
  region = "us-east-1"
  # profile = "sf-logpoc-test"
}

module "dt_csvlookup_env" {
  source = "../../modules/dt-csvlookup-env"

  aws_region     = "us-east-1"
  account_prefix = "sf-logpoc-test"

  gitlab_domain = "sfgitlab.opr.statefarm.org"
  gitlab_sub    = "project_path:event-management/observability/dynatrace/dt-csvlookup-datapipeline:ref_type:branch:ref:main"

  bucket_suffix = "dtcsvlookupdata"  # => sf-logpoc-test-dtcsvlookupdata

  dt_secret_name = "dtcsvlookup"     # name inside sf-logpoc-test
}

output "s3_bucket_name" {
  value = module.dt_csvlookup_env.s3_bucket_name
}

output "gitlab_ci_role_arn" {
  value = module.dt_csvlookup_env.gitlab_ci_role_arn
}

output "dt_secret_name" {
  value = module.dt_csvlookup_env.dt_secret_name
}
```

---

## 6. How GitLab CI Uses This (Per Account)

For each environment, you will:

1. Run `terraform apply` in the corresponding env folder
2. Capture the `gitlab_ci_role_arn` value
3. Use that ARN in your `.gitlab-ci.yml` include:

```yaml
include:
  - component: sfgitlab.opr.statefarm.org/sfcomponents/utilities/gitlab-oidc-aws-sts/template@1
    inputs:
      gitlab_oidc_role_arn: "<PASTE_ROLE_ARN_FROM_TERRAFORM_OUTPUT>"
      oidc_expires_in: "900"
      aws_region: "us-east-1"
```

4. Point the job to the correct bucket in that account:

```yaml
variables:
  PROJECT_BUCKET_NAME: "sf-ems-test-dtcsvlookupdata"  # or sf-ems-prod-..., sf-logpoc-test-...
  CSV_KEY: "orgdata.csv"
  AWS_REGION: "us-east-1"
  DT_SECRET_NAME: "dtcsvlookup"
```

The rest of the job (assume role, `aws s3 cp`, `process_csv.sh`, Secrets Manager fetch, Dynatrace OAuth & uploads) stays exactly as we already built.

---

## 7. Text Flow Diagram (Multi-Account View)

```text
GitLab Project: dt-csvlookup-datapipeline
Branch: main

For each environment (sf-ems-test, sf-ems-prod, sf-logpoc-test):

1) Terraform module creates:
   - S3 bucket: <account_prefix>-dtcsvlookupdata
   - IAM role:  <account_prefix>-role-dtcsvlookup-gitlab
   - IAM policy: <account_prefix>-policy-dtcsvlookup-gitlab-s3-sm-readonly
   - Secrets Manager secret: dtcsvlookup

2) GitLab pipeline for that environment:
   - Uses OIDC to assume the environment's IAM role
   - Reads orgdata.csv from the environment's S3 bucket
   - Runs process_csv.sh -> servicenow.csv
   - Reads Dynatrace OAuth config from dtcsvlookup (in that account)
   - Requests OAuth bearer token from Dynatrace
   - Uploads lookup to TEST and/or PROD tenant endpoints as configured

3) Each environment is isolated:
   - Different S3 buckets per account
   - Different IAM role ARN per account
   - Different secret values per account
```

---

## 8. How to Apply Per Environment

Example for `sf-ems-test`:

```bash
cd infra/dt-csvlookup/envs/sf-ems-test

terraform init
terraform plan
terraform apply
```

Repeat similarly for:

- `infra/dt-csvlookup/envs/sf-ems-prod`
- `infra/dt-csvlookup/envs/sf-logpoc-test`

Each env will:

- Create its own bucket (with that account prefix)
- Create its own IAM role & policy
- Create its own Dynatrace secret stub

---

This module structure gives you a **clean enterprise pattern**:

- One source of truth for the env wiring (the module)  
- Light per-account stacks driven by `account_prefix`  
- Perfect fit for `sf-ems-prod`, `sf-ems-test`, and `sf-logpoc-test`.

You can drop this file in your repo as:

```text
infra/dt-csvlookup/README-multi-account-modules.md
```

and use it as both implementation spec and documentation.
