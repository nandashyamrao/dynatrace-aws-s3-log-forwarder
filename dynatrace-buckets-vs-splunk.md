# 📊 Dynatrace Buckets vs Splunk Context

This sheet explains how we are using **Dynatrace owning area buckets** in comparison to **Splunk indexes**.  
Each Dynatrace bucket serves the same role as a Splunk index — a logical container for logs/events/metrics with its own retention policy.

---

## 🔑 Bucket Mapping

| Dynatrace Bucket Name | Display Name | Data Type (`dt.system.table`) | Retention (days) | Splunk Equivalent / Context | Category |
|-----------------------|--------------|-------------------------------|------------------|-----------------------------|----------|
| administrative_services | administrative_services 35 days | logs | 35 | Equivalent to a Splunk **index** holding logs for the Administrative Services team. | Departmental |
| agency_marketing | agency_marketing 35 days | logs | 35 | Marketing index in Splunk. | Departmental |
| audit_logs_1yr | Dynatrace Audit Logs | logs | 1095 | Compliance/security audit index with longer retention. | Departmental |
| aws_cloudfront | AWS CloudFront | logs | 35 | Splunk index for **CloudFront logs**. | Departmental |
| aws_cloudtrail | AWS CloudTrail | logs | 35 | Splunk index for **CloudTrail logs**. | Departmental |
| corporate_business_development | corporate_business_development 35 days | logs | 35 | Departmental business development logs. | Departmental |
| default_bizevents | Business events | bizevents | 35 | Splunk **business transaction events**. | **System Default** |
| default_davis_custom_events | Custom Davis events (35 days) | events | 35 | Splunk notable/custom events index. | **System Default** |
| default_davis_events | Davis events and problems (15 months) | events | 462 | Long-retention problem/event index. | **System Default** |
| default_davis_k8s_ops_events | Kubernetes ops events (35 days) | events | 35 | Splunk index for Kubernetes operational events. | **System Default** |
| default_logs | Logs | logs | 35 | Equivalent to Splunk’s **main index** (catch-all). | **System Default** |
| default_metrics | Default metrics | metrics | 35 | Splunk metrics indexes (`metric_*`). | **System Default** |
| default_spans | Default spans | spans | 10 | Distributed tracing data (Splunk APM traces). | **System Default** |
| default_synthetic_detailed_events | Synthetic detailed events (35 days) | events | 35 | Splunk ITSI / synthetic monitoring results. | **System Default** |
| default_synthetic_events | Synthetic metrics (35 days) | events | 35 | Synthetic monitoring metrics. | **System Default** |
| default_user_events | Default user events | user.events | 35 | Splunk index for user events (clicks/actions). | **System Default** |
| default_user_sessions | Default user sessions | user.sessions | 35 | Equivalent to Splunk RUM sessions. | **System Default** |
| default_web_user_replays | Default user web replays | user.replays | 35 | Splunk synthetic playback/replay events. | **System Default** |
| dt_system_events | System events (1 year) | dt.system.events | 372 | Splunk’s `_internal` index (system activity). | **System Default** |
| dt_system_metrics | System metrics (180 days) | metrics | 180 | Splunk’s `_introspection` metrics index. | **System Default** |
| enterprise_compliance_ethics | enterprise_compliance_ethics 35 days | logs | 35 | Compliance/security logs. | Departmental |
| enterprise_operations | enterprise_operations 35 days | logs | 35 | Ops team logs. | Departmental |
| et_al_strat_execution | et_al_strat_execution 35 days | logs | 35 | Strategic execution logs. | Departmental |
| et_data_platform_eng | et_data_platform_eng 35 days | logs | 35 | Data platform engineering logs. | Departmental |
| et_ind_eng_oper_mgmt | et_ind_eng_oper_mgmt 35 days | logs | 35 | Operational management logs. | Departmental |
| et_pc_auto_fire | et_pc_auto_fire 35 days | logs | 35 | App/service-specific bucket. | Departmental |
| et_shared_services | et_shared_services 35 days | logs | 35 | Shared services logs. | Departmental |
| financial_operations | financial_operations 35 days | logs | 35 | Finance logs. | Departmental |
| health | health 35 days | logs | 35 | Health monitoring logs. | Departmental |
| human_resources_development | human_resources_development 35 days | logs | 35 | HR logs. | Departmental |
| information_security | information_security 35 days | logs | 35 | Splunk **security index**. | Departmental |
| internal_audit | internal_audit 35 days | logs | 35 | Splunk **audit index**. | Departmental |
| investment_planning_services | investment_planning_services 35 days | logs | 35 | Investment planning logs. | Departmental |
| law_department | law_department 35 days | logs | 35 | Legal logs. | Departmental |
| msccm-7days | null | logs | 7 | Short-term scratch index. | Departmental |
| pc_claims | pc_claims 35 days | logs | 35 | Claims logs. | Departmental |
| pc_claims_bizevents | pc_claims_bizevents 90 days | bizevents | 90 | Claims business events. | Departmental |
| pc_underwriting | pc_underwriting 35 days | logs | 35 | Underwriting logs. | Departmental |
| puso | puso 35 days | logs | 35 | Custom bucket. | Departmental |
| rosa | rosa 35 days | logs | 35 | Custom bucket. | Departmental |
| telematics | telematics 35 days | logs | 35 | Vehicle telematics logs. | Departmental |

---

## ✅ Key Points

- In Splunk, we organized data into **indexes** for search performance and retention.  
- In Dynatrace, we are using **owning area buckets** to achieve the same goal — separating logs/events/metrics by department, business function, or data type.  
- **System Default Buckets** (like `default_logs`, `default_metrics`, `dt_system_events`) are created/managed by Dynatrace and apply to all environments.  
- **Departmental Buckets** (like `administrative_services`, `financial_operations`, `pc_claims`) are specific to our business units and align with Splunk’s departmental indexes.  
- **Retention Days** in Dynatrace buckets = Splunk’s hot/warm/cold/frozen retention management.  

---
