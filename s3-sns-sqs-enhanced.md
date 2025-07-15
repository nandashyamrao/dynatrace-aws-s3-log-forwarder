# 📬 Handling S3 → SNS → SQS Messaging with Enhanced Attributes

This document explains the architecture and message structure for handling **S3 events** via **SNS** with enriched attributes, delivering them to **SQS**, where downstream consumers (like Lambda or processors) can **filter and process messages efficiently** using subscription filters.

---

## 🚫 Why the Default Dynatrace `app.py` Fails with SNS → SQS Messages

### 🧾 What the SQS Message Looks Like (from SNS)

When an S3 event is published to **SNS**, and SNS delivers it to **SQS**, the **message body** inside the SQS record looks like this:

```json
{
  "Type": "Notification",
  "MessageId": "abcd-1234",
  "Message": "{ \"Records\": [ ... ] }",
  "MessageAttributes": {
    "bucket": {
      "Type": "String",
      "Value": "log-bucket"
    },
    "eventName": {
      "Type": "String",
      "Value": "ObjectCreated:Put"
    }
  },
  ...
}
```

> 🔸 Notice: The **actual S3 event is wrapped as a string** inside the `Message` field.

---

### 🧾 What the Lambda Sees

When a Lambda is triggered by this SQS message, the incoming payload to the handler looks like:

```json
{
  "Records": [
    {
      "body": "{ \"Type\": \"Notification\", \"Message\": \"{\\\"Records\\\": [...] }\" }"
    }
  ]
}
```

This means your Lambda must:
1. Parse `record['body']` once → gives the SNS envelope.
2. Parse `sns_message['Message']` again → gives the real S3 event.

---

### ❌ Why the Original `app.py` Drops or Crashes

The original `app.py` assumes that `json.loads(record['body'])` immediately returns either:
- An EventBridge format with `detail`, or
- An S3 format with `Records` directly.

It does **not** expect an extra SNS envelope.

As a result:
- It **crashes** with `KeyError` on `payload['detail']` or `payload['Records']`
- Or it **logs a warning** and silently **drops the message** as "unsupported event structure"

---

### ✅ How Our Modified Code Fixes It

In your updated code (as shown in the image), the fix is:

```python
try:
    sns_message = json.loads(message['body'])
    if 'Message' in sns_message:
        payload = json.loads(sns_message['Message'])  # 🔥 Double parse for SNS format
    else:
        payload = sns_message
except json.decoder.JSONDecodeError as exception:
    logger.warning('Dropping message %s, body is not valid JSON', exception.doc)
    continue
```

Then you support both formats:

```python
if 'detail' in payload:
    # EventBridge → SQS case
elif 'Records' in payload and 's3' in payload['Records'][0]:
    # SNS → SQS case
else:
    logger.warning("unsupported event structure. Skipping message.")
    continue
```

✅ This ensures that **SNS-wrapped S3 events are properly parsed**, and **no messages are dropped**.

---