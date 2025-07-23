
# ✅ SNS ➝ SQS Message Flow Debugging Guide

Ensure SNS can send messages to SQS and that KMS encryption is not blocking delivery or processing.

---

## 🧭 Step 1: Confirm SNS Subscription Is Active

```bash
aws sns list-subscriptions-by-topic \
  --topic-arn arn:aws:sns:us-east-1:<account-id>:<topic-name>
```

### 🔍 Expected Output:
- `"Protocol": "sqs"`
- `"Endpoint": "arn:aws:sqs:us-east-1:<account-id>:<queue-name>"`
- `"SubscriptionArn"` must **not** be `"PendingConfirmation"`

✅ If confirmed: the SQS subscription is active.

---

## 📦 Step 2: Check SQS for Incoming Messages

```bash
aws sqs receive-message \
  --queue-url https://sqs.us-east-1.amazonaws.com/<account-id>/<queue-name> \
  --max-number-of-messages 5 \
  --visibility-timeout 10 \
  --wait-time-seconds 2
```

### 🔍 Expected Output:
```json
{
  "Messages": [
    {
      "MessageId": "string",
      "ReceiptHandle": "string",
      "MD5OfBody": "string",
      "Body": "string"
    }
  ]
}
```

- ✅ Messages should include `"Body"` with SNS payload.
- ❌ If empty: queue may be idle, or another consumer is deleting messages.

---

## 🔐 Step 3: Validate Lambda Logs for KMS Decryption Errors

```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/<lambda-function-name> \
  --limit 5
```

### 🔍 Look for:
- ✅ Successful logs → Message processed
- ❌ Errors like:
  - `AccessDeniedException`
  - `kms:Decrypt` failure
  - `Unable to decrypt message using KMS key`

---

## 🛡️ Extra Tip: Test SNS Publish Manually

```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:<account-id>:<topic-name> \
  --message "Test message from CLI"
```

Then re-run Step 2 to confirm it arrived in SQS.

---

## ✅ Quick Substitution Table

| Placeholder              | Replace With                            |
|--------------------------|------------------------------------------|
| `<account-id>`           | Your AWS Account ID (e.g. `190731337505`) |
| `<topic-name>`           | Your SNS Topic Name                      |
| `<queue-name>`           | Your SQS Queue Name                      |
| `<lambda-function-name>` | Your Lambda function that reads from SQS |
