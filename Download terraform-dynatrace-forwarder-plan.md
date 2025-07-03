
# 🧱 Dynatrace S3 Log Forwarder – Terraform Resource Plan

This setup is for forwarding CloudFront logs stored in an S3 bucket in **Account B** to a **Dynatrace Lambda forwarder in Account A**, using EventBridge and SQS for cross-account communication.

---

## ✅ Inputs Required

| Variable | Description |
|----------|-------------|
| `dt_api_url` | Dynatrace log ingest URL |
| `dt_api_token` | Dynatrace API token (stored in SSM) |
| `lambda_image_uri` | ECR image URI for the Lambda |
| `account_a_id` | AWS Account ID for the central Lambda (forwarder) |
| `account_b_id` | AWS Account ID for the S3 CloudFront bucket |
| `region` | Region (e.g. `us-east-1`) |
| `cloudfront_bucket_name` | Name of S3 bucket holding CloudFront logs |
| `eventbridge_rule_name` | Name of the EventBridge rule in Account B |

---

## 🔢 Terraform Resources by Purpose

### 1. S3 Bucket (in Account B)

- `aws_s3_bucket.cloudfront_logs`
- `aws_s3_bucket_policy.cloudfront_logs_policy`

✅ Enables EventBridge notification:
```hcl
resource "aws_s3_bucket_notification" "eventbridge" {
  bucket = aws_s3_bucket.cloudfront_logs.id
  eventbridge_configuration {}
}
```

---

### 2. EventBridge Rule and Permissions (in Account B)

- `aws_cloudwatch_event_rule.forward_to_account_a`
- `aws_cloudwatch_event_target.cross_account_sqs`
- `aws_iam_role.eventbridge_invoke_role` (if needed)
- `aws_cloudwatch_event_permission.allow_account_a`

✅ Forwards `.gz` PUT events from S3 to Account A:
```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": { "name": ["cloudfront-logs-bucket"] },
    "object": { "key": [{ "prefix": "cloudfront/" }] }
  }
}
```

---

### 3. Event Bus (optional, Account A if used)

- `aws_cloudwatch_event_bus.default` (used implicitly unless custom bus needed)

---

### 4. SQS Queue in Account A

- `aws_sqs_queue.cloudfront_event_queue`
- `aws_sqs_queue_policy.allow_eventbridge_send`

✅ Receives cross-account EventBridge messages:
```json
{
  "Principal": { "Service": "events.amazonaws.com" },
  "Condition": {
    "ArnEquals": {
      "aws:SourceArn": "arn:aws:events:<region>:<account_b_id>:rule/<eventbridge_rule_name>"
    }
  }
}
```

---

### 5. IAM Roles and Policies for Lambda (in Account A)

- `aws_iam_role.lambda_execution`
- `aws_iam_policy.lambda_cross_account_access`

✅ Permissions:
- `s3:GetObject`, `s3:ListBucket` on Account B’s bucket
- `sqs:ReceiveMessage`, `sqs:DeleteMessage`
- `ssm:GetParameter` for Dynatrace secrets

---

### 6. Lambda Function (in Account A)

- `aws_lambda_function.dynatrace_forwarder`
- `aws_lambda_event_source_mapping.sqs_trigger`

✅ Uses container image:
```hcl
image_uri = var.lambda_image_uri
```

✅ Triggers:
- SQS → Lambda

✅ Environment Variables:
- `DT_API_URL`, `DT_API_TOKEN` (fetched from SSM)

---

### 7. AWS SSM Parameter Store (in Account A)

- `aws_ssm_parameter.dt_api_url`
- `aws_ssm_parameter.dt_api_token`

✅ Secrets stored encrypted (with KMS if needed)

---

### 8. ECR Repository for Lambda Image (optional in Account A)

- `aws_ecr_repository.lambda_forwarder_repo`
- `aws_ecr_lifecycle_policy.cleanup`

✅ Push Docker image for Lambda:
```bash
docker build -t dynatrace-forwarder .
docker tag dynatrace-forwarder:latest <account_id>.dkr.ecr.<region>.amazonaws.com/lambda-forwarder:latest
docker push ...
```

---

## 📤 Outputs (Optional)

```hcl
output "sqs_queue_arn" {
  value = aws_sqs_queue.cloudfront_event_queue.arn
}

output "lambda_function_name" {
  value = aws_lambda_function.dynatrace_forwarder.function_name
}

output "s3_bucket_name" {
  value = aws_s3_bucket.cloudfront_logs.bucket
}
```
