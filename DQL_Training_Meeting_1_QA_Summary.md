# Dynatrace DQL Training Meeting 1 — Q&A Summary

**Week 1: Introduction to Grail & DQL Basics**  
**Date:** October 9  
**Trainer:** Nathan Fosdick  
**Assistants:** Lawrence Cuneaz, Vinma Arige, Soumya Tadepalli  
**Topic Focus:** Grail Data Model, Buckets, DQL basics, and Notebooks

---

## Q1. What topics were covered in this first DQL training session?
**A:**  
- Introduction to Dynatrace Grail (Architecture & Use Cases)  
- Understanding Data Objects, Buckets, and Schema  
- Basic DQL Commands: `fetch`, `filter`, `summarize`, `parse`, `timeframe`  
- Comparing DQL vs SQL  
- Exploring Notebooks in Dynatrace for querying  
- Best Practices for writing your first queries  

---

## Q2. How can I access the DQL training materials or notebook?
**A:**  
- Shared Dynatrace Playground:  
  [https://wdf10606.apps.dynatrace.com/apps/dynatrace.notebooks/notebooks](https://wdf10606.apps.dynatrace.com/apps/dynatrace.notebooks/notebooks)  
- If access is denied, create your own notebook in the playground environment.  
- For StateFarm users, access is managed through:  
  [https://enterpriseprodamer.gftlab.gov.statefarm.org/dynatrace/dynatrace-access-on-saas](https://enterpriseprodamer.gftlab.gov.statefarm.org/dynatrace/dynatrace-access-on-saas)

---

## Q3. What are “buckets” in Dynatrace Grail?
**A:**  
- Buckets are data storage containers in Grail.  
- Created and managed by the Dynatrace support team, not end-users.  
- Each environment (e.g., AWS, ROSA, app area) may have its own bucket.  
- Common examples:  
  - `default_logs`  
  - `shipping_log_bucket`  
  - `dt.system.bucket`

---

## Q4. Can teams create their own buckets?
**A:**  
No — buckets are provisioned by the Dynatrace platform team.  
Teams can, however, query their designated bucket or the shared ones.

---

## Q5. How do I query logs from a specific bucket?
**A:**  
Use the `fetch` command with the bucket name:
```dql
fetch logs, bucket=("default_logs", "shipping_log_bucket")
```
Or with a timeframe:
```dql
fetch logs, bucket=("default_logs")
| timeframe between "2025-09-20T12:00:02Z" and "2025-09-20T13:00:02Z"
```

---

## Q6. What’s the difference between using “bucket” and using a “filter”?
**A:**  
- `bucket` defines where data is fetched from.  
- `filter` defines which subset of data you want after it’s fetched.  

Example:
```dql
fetch logs, bucket=("default_logs")
| filter aws.accountId == "123456789012"
```

---

## Q7. Can you sample or limit the number of log entries?
**A:**  
Yes — using the `sample` function.
```dql
fetch logs, bucket=("default_logs")
| sample(limit:10)
```

---

## Q8. Are bucket names case-sensitive?
**A:**  
Yes, bucket names are case-sensitive.  
Ensure they match the exact name when writing queries.

---

## Q9. Do Dynatrace logs have an expiration period?
**A:**  
Yes, logs are retained for 35 days by default.

---

## Q10. What happens if I get the error “result size exceeded”?
**A:**  
This means the dataset is too large for Dynatrace’s internal query limit.  
Try narrowing the timeframe or using filters to reduce the result size.

---

## Q11. How can I upload a CSV file or custom data into a notebook?
**A:**  
Currently, you can create and edit your own notebooks,  
but uploading custom files is not supported yet in the shared playground.

---

## Q12. What’s the relationship between “dataObjects” and “buckets”?
**A:**  
- Buckets store logs or metric streams.  
- Data objects describe what’s inside the bucket (tables, views, etc.).  
- You can view them using:
```dql
fetch dt.system.data_objects
```

---

## Q13. How to check available tables or objects?
**A:**  
Run:
```dql
fetch dt.system.data_objects
| filter type == "table"
```

---

## Q14. Are there standard bucket patterns used by Dynatrace?
**A:**  
Yes. Example patterns include:  
- `dt.system.bucket` → platform-wide logs  
- `app_pipeline.pipeline` → application-specific logs  
- `rosaa_bucket` → ROSA environment logs

---

## Q15. What was said about future sessions?
**A:**  
- The next session continues where this one left off.  
- Future Thursday meetings will replace the usual weekly coaching sessions.  
- Recordings and transcripts are available under the meeting recap.

---

## Q16. Where can I find the meeting recordings?
**A:**  
They are attached under the Meeting Chat → Recordings section.  
Two recordings by Nathan Fosdick and Dwight Wood were uploaded.  
Note: OneDrive retention = 20 days.

---

## Q17. How long did the meeting last?
**A:**  
Approximately 1 hour 20 minutes, ending at 11:20 AM.

---

## Q18. Any next steps suggested by the trainers?
**A:**  
- Practice DQL commands in your own notebook.  
- Join the DQL User Group (Teams).  
- Explore Dynatrace docs:  
  - [Glossary](https://docs.dynatrace.com/docs/discover-dynatrace/get-started/glossary)  
  - [DQL Comparison](https://docs.dynatrace.com/docs/dynatrace-query-language/dql-compare)  
  - [Notebooks Guide](https://docs.dynatrace.com/docs/dynatrace-notebooks/notebooks)
