Here is your download-ready Markdown file, clean, structured, and formatted with a table + IAM actions list.

⸻

✅ Cross-Account S3 Access Setup for GitLab OIDC Pipeline

How to allow your GitLab CI job to read an S3 bucket in another AWS account

⸻

📌 Overview

Your GitLab CI pipeline currently:
	•	Uses OIDC to assume an IAM role (Account A)
	•	Reads CSV files from an S3 bucket
	•	Processes the CSV and uploads to Dynatrace

If the S3 bucket is moved to another AWS account (Account B), your pipeline will still work — as long as IAM and the bucket policy are configured correctly.

The GitLab YAML does not need changes, except updating the bucket name.
All changes happen in IAM role policy, bucket policy, and optional KMS key policy.

⸻

🏗️ Architecture Summary

GitLab Pipeline
     |
     | assumes
     v
IAM Role (Account A)
     |
     | requests access to S3 bucket in Account B
     v
S3 Bucket (Account B)

To make this work:
	1.	Role in Account A must ALLOW reading the bucket
	2.	Bucket policy in Account B must TRUST the role
	3.	(Optional) KMS key in Account B must ALLOW the role to decrypt objects

⸻

📄 Access Matrix

Component	Account	Needs Change?	Description
IAM Role Policy	Account A	✅ Yes	Allows s3:ListBucket + s3:GetObject on Account B bucket
S3 Bucket Policy	Account B	✅ Yes	Grants trust to the GitLab role
KMS Key Policy (optional)	Account B	Maybe	Required only if bucket uses SSE-KMS
GitLab CI YAML	Pipeline	❌ No	Stays the same; only bucket name changes


⸻

🛠️ 1. IAM Role Policy in Account A

Attach to:
arn:aws:iam::<ACCOUNT_A_ID>:role/gitlab-ci-s3-reader-role

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowReadCrossAccountBucket",
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::sf-otheraccount-dtcsvlookupdata"
    },
    {
      "Sid": "AllowGetObjectsCrossAccountBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::sf-otheraccount-dtcsvlookupdata/*"
    }
  ]
}


⸻

🛠️ 2. Bucket Policy in Account B

Apply this on the bucket itself:

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowGitLabReaderRoleAccess",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<ACCOUNT_A_ID>:role/gitlab-ci-s3-reader-role"
      },
      "Action": [
        "s3:ListBucket",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::sf-otheraccount-dtcsvlookupdata",
        "arn:aws:s3:::sf-otheraccount-dtcsvlookupdata/*"
      ]
    }
  ]
}


⸻

🔐 3. If the Bucket Uses SSE-KMS Encryption (Optional)

If S3 objects use a customer-managed KMS key, extend the KMS key policy:

{
  "Sid": "AllowGitLabRoleKMSUse",
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::<ACCOUNT_A_ID>:role/gitlab-ci-s3-reader-role"
  },
  "Action": [
    "kms:Decrypt",
    "kms:GenerateDataKey"
  ],
  "Resource": "*"
}


⸻

🧪 4. GitLab CI YAML (No Change Required)

You continue using:

aws s3 ls "s3://${PROJECT_BUCKET_NAME}/"
aws s3 cp "s3://${PROJECT_BUCKET_NAME}/${CSV_KEY}" "./${CSV_KEY}"

Only change:

PROJECT_BUCKET_NAME: "sf-otheraccount-dtcsvlookupdata"

Everything else remains identical.

⸻

📌 Summary Table of Required AWS IAM Actions

AWS Resource	Required IAM Actions	Where Defined
S3 Bucket (Account B)	s3:ListBucket	Role policy + bucket policy
S3 Objects (Account B)	s3:GetObject	Role policy + bucket policy
KMS Key (if used)	kms:Decrypt, kms:GenerateDataKey	KMS key policy in Account B


⸻

🎉 Final Summary

Your GitLab pipeline can seamlessly read from another AWS account with:
	1.	Role policy update in Account A
	2.	Bucket policy update in Account B
	3.	Optional KMS permission updates

Once done — your CSV ingestion, transformation, and Dynatrace upload will continue working with zero YAML modifications.

⸻

If you want, I can also generate:

✅ Terraform for the cross-account setup
✅ CloudFormation policies
✅ A full diagram ASCII + PNG version
Just tell me!
