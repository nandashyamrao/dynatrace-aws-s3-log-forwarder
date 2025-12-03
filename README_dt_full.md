# 🧾 dt-csvlookup-datapipeline
### Automated S3 → Clean CSV → Dynatrace Lookup Table Data Pipeline

![Status](https://img.shields.io/badge/status-active-brightgreen)  
![GitLab CI](https://img.shields.io/badge/GitLab-CI%2FCD-blue?logo=gitlab)  
![Dynatrace](https://img.shields.io/badge/Dynatrace-Lookup_Table-purple?logo=dynatrace)  
![AWS](https://img.shields.io/badge/AWS-S3-orange?logo=amazonaws)

---

## ⭐ Executive Summary

The **dt-csvlookup-datapipeline** project provides a fully automated, secure, and high-quality data pipeline that:

1. **Pulls CSV metadata daily** from an AWS S3 bucket  
2. **Cleans and transforms** the dataset using a custom AWK normalization script  
3. **Authenticates using Dynatrace OAuth (client credentials)**  
4. **Uploads the final CSV** into a Dynatrace **Lookup Table** used for enrichment, tagging, ownership mapping, automation, and FinOps analytics  

This ensures that Dynatrace always has an accurate, enterprise-wide, continuously refreshed metadata table—without manual intervention.

---

## 📘 Project Overview

This repository implements an automated GitLab CI/CD pipeline to maintain an **authoritative mapping table** for Dynatrace.

The pipeline guarantees:

- **Data freshness** (daily pulls)  
- **Data quality** (normalized, validated, safe)  
- **Security** (OAuth + internal CA trust bundle)  
- **Reliability** (GitLab CI automation)  
- **Traceability** (artifacts + logs)

---

## 🏗️ Architecture (High-Level)

> GitLab’s Mermaid renderer is strict, so this repo uses a simple ASCII diagram that works in all views.

```text
+------------+       +------------------------+       +------------------+
|  S3 Bucket | ----> | GitLab Job 1           | ----> | processed.csv     |
|  Raw CSV   |       | Download & Process     |       | (artifact)        |
+------------+       +------------------------+       +------------------+
                                                           |
                                                           v
                                                     +------------------+
                                                     | GitLab Job 2     |
                                                     | OAuth & Upload   |
                                                     +------------------+
                                                           |
                                                           v
                                                 +------------------------+
                                                 | Dynatrace OAuth Server |
                                                 |  (token)               |
                                                 +------------------------+
                                                           |
                                                           v
                                                 +------------------------+
                                                 | Dynatrace Tenant       |
                                                 | Lookup Table API       |
                                                 +------------------------+
```

---

## 📂 Source CSV Schema (S3)

Each record contains enterprise metadata vital for Dynatrace enrichment:

| Column              | Example                                      | Description                |
|---------------------|----------------------------------------------|----------------------------|
| `solma_id`          | `421914`                                     | Unique application ID      |
| `ci_name`           | `1099 CUSTOMER SUMMARY - APP01886`           | CI or application name     |
| `area_name`         | `Life Health IPS`                            | Business area              |
| `director_alias`    | `QGME`                                       | Director alias             |
| `manager_alias`     | `LT42`                                       | Manager alias              |
| `product_name`      | `Life Health IPS Centralized Ops Software Eng` | Product name            |
| `product_suite_name`| `—`                                          | Product suite name         |
| `tier`              | `5`                                          | Tier classification        |
| `wg_name`           | `WG10239`                                    | Workgroup name             |
| `costing_id`        | `C06742`                                     | Cost center ID             |
| `exec_alias`        | `GJWZ`                                       | Executive alias            |
| `manager_name`      | `Ben Wallace`                                | Manager full name          |
| `director_name`     | `Nikki Cross`                                | Director full name         |
| `exec_name`         | `Shanese G Lawson-Smith`                     | Executive full name        |
| `last_updated`      | `11/25/2025 0:06`                            | Timestamp                  |
| `platforms`         | `EUC – Enterprise Technology`                | Platform(s)                |
| `tech_owner_alias`  | `QRZC`                                       | Tech owner alias           |
| `tech_owner_name`   | `Mike Dunn`                                  | Tech owner full name       |

---

## 🧼 Processing Script (`scripts/process_csv.sh`)

The included AWK script performs **enterprise-grade data sanitization**, ensuring Dynatrace receives only clean and safe values.

### 🔧 Key Features

- Trims leading and trailing whitespace  
- Removes illegal or noisy characters  
- Strips unnecessary outer quotes  
- Converts empty/`NULL`/whitespace-only fields → `NA`  
- Handles embedded commas and quotes safely  
- Rebuilds each line character-by-character to avoid CSV corruption  
- Field-specific behavior:
  - **`solma_id`** → kept numeric-looking, quotes removed  
  - **`product_name`** → blanks normalized, avoids double-quotes  
  - **All other columns** → if effectively empty, normalized to `NA`  

This guarantees lookup-table integrity required across many Dynatrace tagging, enrichment, and automation rules.

---

## ⚙️ How the Pipeline Works (Step by Step)

### 1. Trigger

The GitLab pipeline can be:

- Scheduled (e.g., daily), or  
- Triggered manually when a new CSV is available in S3.

### 2. Job 1 – `download_and_process_csv`

1. **Download from S3**

   ```bash
   aws s3 cp "s3://<bucket>/<prefix>/file.csv" input.csv
   ```

2. **Process via AWK Script**

   ```bash
   ./scripts/process_csv.sh input.csv processed.csv
   ```

3. **Store Artifact**

   - `processed.csv` is stored as a **GitLab artifact** so the next job can use it.
   - If processing fails, the pipeline stops here.

### 3. Job 2 – `upload_csv_to_dynatrace`

1. **Request OAuth Access Token**

   The job calls the Dynatrace OAuth server using the **client credentials flow**:

   ```bash
   curl -X POST "$DYNATRACE_OAUTH_TOKEN_URL"      -H "Content-Type: application/x-www-form-urlencoded"      --data-urlencode "grant_type=client_credentials"      --data-urlencode "client_id=$DYNATRACE_OAUTH_CLIENT_ID"      --data-urlencode "client_secret=$DYNATRACE_OAUTH_CLIENT_SECRET"      --data-urlencode "scope=$DYNATRACE_OAUTH_SCOPE"      --data-urlencode "resource=$DYNATRACE_ACCOUNT_URN"
   ```

   The JSON response contains an `access_token` which is used as a Bearer token.

2. **Upload to Dynatrace Lookup Table**

   The cleaned CSV is uploaded using the Dynatrace **Lookup Tables API**:

   ```bash
   curl -X POST      "$DYNATRACE_TENANT_URL/platform/lookup-tables/v1/tables/$DYNATRACE_LOOKUP_NAME/records:import"      -H "Authorization: Bearer $ACCESS_TOKEN"      -H "Content-Type: text/csv"      --data-binary "@processed.csv"
   ```

3. **Validate Result**

   - The HTTP status code is checked.  
   - For non‑2xx responses, the job prints the response body and **fails** the pipeline so the issue is visible.

### 4. Result in Dynatrace

- The lookup table now contains the latest, cleaned metadata.  
- Dynatrace can use this data for:
  - Automated tagging and enrichment  
  - Dynamic routing of alerts  
  - Ownership mapping and dashboards  
  - FinOps and cost reporting  
  - Automation workflows and rules

---

## 🛠️ Repository Layout

```text
dt-csvlookup-datapipeline/
│
├── .gitlab-ci.yml                  # CI pipeline definition
├── README.md                       # Project documentation
└── scripts/
    └── process_csv.sh              # AWK data cleaner/normalizer
```

---

## 🧪 GitLab CI/CD Jobs

### 1️⃣ `download_and_process_csv`

- Downloads raw CSV from S3  
- Runs the AWK normalization script  
- Produces `processed.csv` as an artifact  

### 2️⃣ `upload_csv_to_dynatrace`

- Retrieves OAuth token via `sso.dynatrace.com`  
- Uploads the processed CSV to the Dynatrace lookup table  
- Uses enterprise CA bundle for SSL validation (`DT_CERT_PATH`)  
- Validates response and fails on non‑2xx  

---

## 🔐 Required GitLab CI Variables

All secrets must be **masked**, **protected**, and never checked into source control.

| Variable                         | Purpose                             |
|----------------------------------|-------------------------------------|
| `AWS_ACCESS_KEY_ID`             | AWS IAM access                      |
| `AWS_SECRET_ACCESS_KEY`         | AWS IAM secret                      |
| `AWS_SESSION_TOKEN`             | Optional, for STS sessions          |
| `DYNATRACE_OAUTH_CLIENT_ID`     | Dynatrace OAuth client ID           |
| `DYNATRACE_OAUTH_CLIENT_SECRET` | Dynatrace OAuth client secret       |
| `DYNATRACE_ACCOUNT_URN`         | Dynatrace account URN               |
| `DYNATRACE_OAUTH_SCOPE`         | e.g. `platform:lookup-tables:write` |
| `DYNATRACE_OAUTH_TOKEN_URL`     | OAuth token URL                     |
| `DYNATRACE_TENANT_URL`          | Dynatrace environment URL           |
| `DYNATRACE_LOOKUP_NAME`         | Lookup table name                   |
| `DT_CERT_PATH`                  | CA certificate bundle path          |

---

## 🏢 Security, Compliance & Certificates

### ✔ Enterprise CA bundle

All outbound connections to Dynatrace APIs use the internal CA bundle:

```bash
curl --cacert "$DT_CERT_PATH" ...
```

### ✔ Zero plain‑text credentials

- No secrets are stored in the repository.  
- All credentials are managed via GitLab CI Variables.

### ✔ OAuth 2.0 Client Credentials Flow

- Uses a non‑interactive, machine‑to‑machine authentication pattern.  
- Follows Dynatrace best practices for automation.

### ✔ Data quality governance

The AWK script ensures:

- No blank fields (everything normalized to valid values like `NA`)  
- No malformed quotes or broken CSV rows  
- No invalid characters or unescaped commas  
- Column‑consistent behavior across all rows  

---

## 🧭 Benefits at a Glance

✔ Fully hands‑free data refresh  
✔ Eliminates manual CSV uploads  
✔ Improves observability accuracy  
✔ Enables stable tagging and automation in Dynatrace  
✔ Supports FinOps, service ownership, and compliance reporting  
✔ Provides full audit trail via GitLab pipeline history  

---

## 📌 Changelog

### v1.0.0 – Initial Release

- Added GitLab CI/CD pipeline  
- Added AWK‑based CSV cleaning engine  
- Integrated S3 → Dynatrace Lookup import automation  
- Added OAuth client credential authentication  
- Added enterprise CA bundle support  

---

## 👥 Contact

**Event Management / Observability / Dynatrace Platform Engineering**  
For enhancements, incidents, or onboarding assistance.
