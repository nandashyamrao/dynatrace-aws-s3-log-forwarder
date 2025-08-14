# CloudFront Dashboard Documentation

## Variables and Their DQL Queries

### 1. `aws_account_id`
```dql
fetch logs
| filter dt.system.bucket == "aws.cloudfront"
| summarize aws_account_id = collectDistinct(aws.account_id)
```

### 2. `distribution_name`
```dql
fetch logs
| filter dt.system.bucket == "aws.cloudfront"
| filter aws.account_id == ${aws_account_id}
| summarize distribution_name = collectDistinct(distribution_name)
```

---

## Dashboard Tiles

| #  | Tile Name & Link | Type | Queries | Preview | Visualization |
|----|------------------|------|---------|---------|---------------|
| 1  | [Average Latency](#) | Data | `fetch logs ...` | Screenshot/Description | Table |
| 2  | [Requests Over Time](#) | Data | `fetch logs ...` | Screenshot/Description | Time Series |
| 3  | [Top POPs by Traffic](#) | Data | `fetch logs ...` | Screenshot/Description | Table |
| 4  | [Error Rate](#) | Data | `fetch logs ...` | Screenshot/Description | Line Chart |

---

**Note:** All queries use one or both of the variables `aws_account_id` and `distribution_name` defined above.
