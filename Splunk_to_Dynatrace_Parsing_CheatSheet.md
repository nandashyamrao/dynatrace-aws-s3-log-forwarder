
# 📘 Splunk → Dynatrace Cheat Sheet: Parsing & Matching

---

## 1. 🔑 **Basic Field Extraction**
**Log:**  
```
AddItemAsync called with userId=a332efea, productId=1ZYFJ3GM2N, quantity=1
```

| Tool     | Example | Extracted Fields |
|----------|---------|------------------|
| **Splunk** | `rex field=_raw "userId=(?<userId>\w+), productId=(?<productId>\w+), quantity=(?<quantity>\d+)"` | `userId=a332efea`<br>`productId=1ZYFJ3GM2N`<br>`quantity=1` |
| **Dynatrace (DPL)** | `parse content, "userId=" LD:userId ", productId=" LD:productId ", quantity=" INT:quantity` | Same fields extracted |

---

## 2. 🚨 **Error Log Filtering (Matching)**
**Log:**  
```
[ERROR] Payment failed for orderId=1021, reason=InsufficientFunds
```

| Tool     | Example | Purpose |
|----------|---------|---------|
| **Splunk** | `search _raw="Payment failed*"` | Match logs with payment failures |
| **Dynatrace** | `filter content matches "Payment failed for orderId=*"` | Same boolean match |

---

## 3. ☁️ **AWS CloudTrail Example**
**Log (JSON):**  
```json
{"eventTime":"2024-08-01T10:20:30Z","eventName":"CreateBucket","userIdentity":{"accountId":"123456789012"},"requestParameters":{"bucketName":"sf-prod-logs"}}
```

| Tool     | Example | Extracted Fields |
|----------|---------|------------------|
| **Splunk** | `spath input=_raw path=requestParameters.bucketName output=bucketName` | `bucketName = sf-prod-logs` |
| **Dynatrace (DPL)** | `parse content, "\"bucketName\":\"" LD:bucketName "\""` | `bucketName = sf-prod-logs` |

---

## 4. 🛡️ **AWS WAF Logs**
**Log (JSON):**  
```json
{"action":"BLOCK","ruleGroupList":[{"ruleGroupId":"AWS-AWSManagedRulesCommonRuleSet"}],"httpRequest":{"clientIp":"203.0.113.10","uri":"/login"}}
```

| Tool     | Example | Extracted Fields |
|----------|---------|------------------|
| **Splunk** | `spath input=_raw path=httpRequest.clientIp output=clientIp` | `clientIp = 203.0.113.10` |
| **Dynatrace (DPL)** | `parse content, "\"clientIp\":\"" LD:clientIp "\""` | `clientIp = 203.0.113.10` |

---

## 5. 🏦 **ServiceNow Incident Log**
**Log:**  
```
Application: Claims [App01]
Governing Service Name: PolicyService
Owning Workgroup: ClaimsTech
Incident Workgroup: ITSM-Incident
```

| Tool     | Example | Extracted Fields |
|----------|---------|------------------|
| **Splunk** | `rex field=_raw "Application:\s*(?<displayName>.*?)\s*\[(?<ApplicationName>[^\]]+)\]"` | `displayName=Claims`, `ApplicationName=App01` |
| **Dynatrace (DPL)** | `parse content, "Application: " LD:displayName " [" LD:ApplicationName "]"` | Same fields |

---

## 6. 📊 **Aggregation After Parse**
**Goal:** Count blocked WAF requests per rule group.

| Tool     | Example |
|----------|---------|
| **Splunk** | `spath path=ruleGroupList{}.ruleGroupId output=ruleGroupId | stats count by ruleGroupId` |
| **Dynatrace** | `parse content, "\"ruleGroupId\":\"" LD:ruleGroupId "\""  \| summarize count(), by:ruleGroupId` |

---

# ✅ **Key Takeaways**
- **Parsing** = extract fields → Splunk `rex/spath` ≈ Dynatrace `parse`.  
- **Matching** = filter logs → Splunk `search/like` ≈ Dynatrace `matches`.  
- **Enterprise Examples** = CloudTrail (buckets), WAF (rule groups, IPs), ServiceNow (workgroups), App logs (user/product/quantity).  
