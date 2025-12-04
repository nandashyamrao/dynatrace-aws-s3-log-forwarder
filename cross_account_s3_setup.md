# Cross-Account S3 Access Setup for GitLab OIDC Pipeline

## Overview
Your GitLab CI pipeline currently:
- Uses OIDC to assume an IAM role (Account A)
- Reads CSV files from S3
- Processes and uploads into Dynatrace

If the S3 bucket exists in another AWS account (**Account B**), the pipeline will continue to work **as long as IAM role permissions and S3 bucket policies allow cross-account access**.

---

## 🔁 Architecture Flow
GitLab Pipeline → IAM Role (Account A) → **Cross‑Account S3 Bucket** (Account B)

---

## 🔎 Access Matrix

| Component | Account | Change Required? | Purpose |
|----------|---------|------------------|---------|
| **IAM Role Policy** | Account A | ✅ Yes | Allow read access to Account B’s bucket |
| **S3 Bucket Policy** | Account B | ✅ Yes | Trust Account A’s IAM role |
| **KMS Key Policy** | Account B | ⚠️ Maybe | Only if bucket uses SSE‑KMS |
| **GitLab CI YAML** | Pipeline | ❌ No | Only bucket name updates |

---

## 1️⃣ IAM Role Policy (Account A)
This allows the GitLab OIDC‑assumed role to read from Account B’s S3 bucket.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowReadCrossAccountBucket",
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::sf-otheraccount-dtcsvlookupdata"
    },
    {
      "Sid": "AllowGetObjectsCrossAccountBucket",
      "Effect": "Allow",
      "Action": ["s3:GetObject"],
      "Resource": "arn:aws:s3:::sf-otheraccount-dtcsvlookupdata/*"
    }
  ]
}
```

---

## 2️⃣ S3 Bucket Policy (Account B)
This trusts the role from Account A.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowGitLabReaderRoleAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<ACCOUNT_A_ID>:role/gitlab-ci-s3-reader-role"
      },
      "Action": ["s3:ListBucket", "s3:GetObject"],
      "Resource": [
        "arn:aws:s3:::sf-otheraccount-dtcsvlookupdata",
        "arn:aws:s3:::sf-otheraccount-dtcsvlookupdata/*"
      ]
    }
  ]
}
```

---

## 3️⃣ (Optional) KMS Key Policy (Account B)
Required if bucket encryption uses **SSE‑KMS** with a customer-managed CMK.

```json
{
  "Sid": "AllowGitLabRoleKMSUse",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::<ACCOUNT_A_ID>:role/gitlab-ci-s3-reader-role"
  },
  "Action": ["kms:Decrypt", "kms:GenerateDataKey"],
  "Resource": "*"
}
```

---

## 4️⃣ GitLab CI YAML Changes
Only the bucket name needs to change:

```
PROJECT_BUCKET_NAME: "sf-otheraccount-dtcsvlookupdata"
```

No other YAML updates are required because the credentials are already coming from OIDC.

---

## 📝 Required IAM Permissions Summary

| Resource | Actions Needed | Reason |
|----------|----------------|--------|
| **S3 Bucket** | s3:ListBucket | Allow listing of objects |
| **S3 Objects** | s3:GetObject | Download CSV |
| **KMS Key (optional)** | kms:Decrypt, kms:GenerateDataKey | Read encrypted data |

---

## ✅ Summary
Once the IAM role in Account A and bucket policy in Account B are configured for cross-account access:

- Your GitLab pipeline continues working **without code changes**
- You only change the bucket name in the YAML
- Dynatrace upload logic stays exactly the same

---

