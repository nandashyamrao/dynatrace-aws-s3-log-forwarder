# 🆚 EventBridge vs SNS for S3 Event Processing

This document highlights the differences between using **Amazon EventBridge** and **Amazon SNS** for processing S3 events, especially when targeting Lambda or SQS consumers.

---

## ✅ Advantages of Using EventBridge

- **Native Integration with S3**  
  Enabling EventBridge for S3 delivers rich, structured events directly without extra wrapping.

- **No Double Parsing Needed**  
  EventBridge delivers events in clean JSON format — directly usable in Lambda without decoding an extra `Message` field.

- **Supports Fine-Grained Event Filtering**  
  EventBridge rules support content-based pattern matching on nested fields like:
  ```json
  {
    "detail": {
      "bucket": {
        "name": ["log-bucket"]
      },
      "object": {
        "key": [{
          "prefix": "AWSLogs/", "suffix": ".gz"
        }]
      }
    }
  }
  ```

- **Multiple Targets per Rule**  
  One EventBridge rule can fan out to multiple targets (e.g., Lambda, SQS, Step Functions) without SNS fan-out complexity.

- **Supports Input Transformation**  
  You can transform the message payload before it reaches the target (e.g., reduce size, extract only key fields).

- **Observability with CloudWatch**  
  EventBridge integrates with CloudWatch for metrics and monitoring of matched and failed rule invocations.

- **Cross-Account Event Routing**  
  Events from one AWS account can be forwarded to EventBridge in another account natively.

---

## ⚠️ Limitations of SNS for S3 Events

- **Message Wrapping Adds Complexity**  
  SNS wraps the actual S3 event inside a `Message` field — requires double JSON parsing in Lambda.

- **MessageAttributes Are Flat**  
  Filtering is limited to top-level string attributes (e.g., `bucket`, `eventName`). No nested filtering like EventBridge supports.

- **No Input Transformation**  
  You cannot transform the event before it reaches the target (SQS or Lambda).

- **No Native Observability**  
  SNS lacks native event metrics, logs, or dead-letter queue support without additional setup.

- **Limited Routing Logic**  
  SNS filtering is basic compared to EventBridge's JSON pattern matching and logical operators.

---

## 🧠 Recommendation

If you're building **structured, multi-destination event workflows** that benefit from filtering, routing, and observability — **EventBridge is the preferred choice**.

SNS remains useful for **simple pub/sub** and fan-out patterns, especially when used with raw delivery and stateless consumers.
---

## 🔍 Why EventBridge Does Not Use Subscriptions Like SNS

### 🧭 Key Conceptual Difference

In **SNS**, you define **subscriptions** — consumers (like Lambda, SQS, or HTTP endpoints) **subscribe** to a topic and receive every message that gets published.

In contrast, **EventBridge does not use a subscription-based model**. Instead, it uses:

- **Rules**, which **match patterns** on events flowing through the Event Bus
- **Targets**, which are **explicitly defined** per rule

This means:

| Feature | SNS | EventBridge |
|--------|-----|-------------|
| Uses subscriptions | ✅ Yes | ❌ No |
| Uses filtering rules | ❌ Basic attribute filters | ✅ Powerful JSON-based pattern matching |
| Auto-fanout to all subscribers | ✅ Yes | ❌ No — you must define each rule and target manually |
| Delivery mechanism | Push to all subscribers | Selective routing based on rules |

---

### 🧠 Why EventBridge Has No Subscription Layer

EventBridge operates more like a **routing engine** than a pub/sub service:

- Each rule **independently inspects** incoming events and chooses whether to route them.
- There’s **no global list of subscribers** waiting for all events on the bus.
- Every target (e.g., Lambda, SQS) must be **explicitly assigned to a rule**.

This provides more **control and precision**, especially when:

- You want different services to react to different patterns.
- You want to send different payload shapes using input transformations.
- You want rich, schema-based filtering, not just attribute matching.

---

### ✅ Summary

- EventBridge does not support **subscriptions** like SNS.
- It uses **rules and targets** to explicitly define what happens to each event.
- This gives you **granular routing**, but also means **no automatic fan-out** like SNS.