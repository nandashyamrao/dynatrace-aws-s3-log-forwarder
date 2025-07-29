# 📦 CloudFront to Dynatrace Log Forwarding Pipeline

This table shows the data flow and responsibilities for each component involved in forwarding CloudFront logs to Dynatrace, using emojis that are reliable across most platforms.

---

## 🔁 Summary Table: Data Flow per Component

| 🔢 Step | 🔧 Component        | 📋 Role Description                             | 📤 Output Sent To                    | 🔁 Emoji Alternative |
|--------:|---------------------|--------------------------------------------------|--------------------------------------|-----------------------|
| 1️⃣     | **CloudFront**       | Generates access logs                          | 🪣 Amazon S3                         | 🌐 or 📘              |
| 2️⃣     | **Amazon S3**        | Stores logs and sends event                    | 📣 SNS Topic                         | 🪣 (bucket)           |
| 3️⃣     | **SNS Topic**        | Publishes event to subscribers                 | 📬 SQS Queue                         | 📣 (megaphone)        |
| 4️⃣     | **SQS Queue**        | Queues SNS notification                        | ⚙️ Lambda Trigger                    | 📥 (inbox tray)       |
| 5️⃣     | **Lambda Function**  | Parses, enriches, and forwards logs            | 🌐 Dynatrace API                     | 🧠 or 🔁              |
| 6️⃣     | **Dynatrace**        | Stores searchable, enriched log entries        | 🗃️ Dynatrace Logs Storage            | 📊 or 🧾              |

---

## 🆕 Recommended Emoji Substitutes

| Purpose                 | Recommended Emoji | Description              |
|------------------------|-------------------|--------------------------|
| Send Event             | 📣                | Megaphone (event sent)   |
| Triggered Input        | 📥                | Inbox Tray (received)    |
| Store/Search           | 🗃️ or 🧾           | Archive or receipt       |
| Enrich/Process         | ⚙️ or 🧠           | Gear or brain logic      |
| Logs / Data            | 📄 or 📊           | Log file / Graph         |

---

Feel free to copy-paste this into your internal documentation or a Dynatrace dashboard annotation.
