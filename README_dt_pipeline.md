# dt-csvlookup-datapipeline
## Automated S3 → Clean CSV → Dynatrace Lookup Table Data Pipeline

![Status](https://img.shields.io/badge/status-active-brightgreen)
![GitLab CI](https://img.shields.io/badge/GitLab-CI%2FCD-blue?logo=gitlab)
![Dynatrace](https://img.shields.io/badge/Dynatrace-Lookup_Table-purple?logo=dynatrace)
![AWS](https://img.shields.io/badge/AWS-S3-orange?logo=amazonaws)

## Executive Summary
This project automates:
1. Pulling CSV metadata from S3
2. Cleaning via AWK script
3. Dynatrace OAuth authentication
4. Upload to Dynatrace lookup table

## CSV Schema
| Column | Example | Description |
|--------|---------|-------------|
| solma_id | 421914 | Unique application ID |
| ci_name | 1099 CUSTOMER SUMMARY - APP01886 | Application name |
| area_name | Life Health IPS | Business area |
| director_alias | QGME | Director alias |
| manager_alias | LT42 | Manager alias |
| product_name | Life Health IPS Centralized Ops Software Eng | Product name |
| product_suite_name | — | Product suite |
| tier | 5 | Tier classification |
| wg_name | WG10239 | Workgroup |
| costing_id | C06742 | Cost center |
| exec_alias | GJWZ | Exec alias |
| manager_name | Ben Wallace | Manager name |
| director_name | Nikki Cross | Director |
| exec_name | Shanese G Lawson-Smith | Executive |
| last_updated | 11/25/2025 0:06 | Timestamp |
| platforms | EUC – Enterprise Technology | Platforms |
| tech_owner_alias | QRZC | Tech Owner alias |
| tech_owner_name | Mike Dunn | Tech Owner |

## Architecture Diagram (ASCII)
```
S3 Bucket --> GitLab Job 1 --> process_csv.sh --> Artifact
Artifact --> GitLab Job 2 --> Dynatrace OAuth --> Dynatrace Lookup
```

## Pipeline Structure
- download_and_process_csv
- upload_csv_to_dynatrace

## Contact
Event Management / Observability / Dynatrace Platform Engineering
