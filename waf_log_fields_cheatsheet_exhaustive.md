# ✅ AWS WAF Log Fields – Categorized with Real-World Sample Values

### 📅 Request Timing

| Field | Description | Sample Value |
|-------|-------------|---------------|
| timestamp | The time when AWS WAF received the request | 2025-07-13T14:23:00Z |

### 🌐 Request Context

| Field | Description | Sample Value |
|-------|-------------|---------------|
| httpRequest.clientIp | The IP address that sent the request | 198.51.100.23 |
| httpRequest.country | The country of origin for the request | US |
| httpRequest.method | The HTTP method of the request | POST |
| httpRequest.uri | The URI of the request | /api/login |
| httpRequest.args | The query arguments of the request | user=admin |
| httpRequest.headers | The headers included in the request | [{"name":"User-Agent","value":"curl/7.79.1"}] |
| httpRequest.httpVersion | The HTTP version of the request | HTTP/1.1 |

### 🛡️ Rule Evaluation

| Field | Description | Sample Value |
|-------|-------------|---------------|
| ruleGroupList | List of rule groups that matched | [{"ruleGroupId":"AWS#DefaultRuleSet","terminatingRuleId":"SQLi_BODY"}] |
| terminatingRuleId | The ID of the rule that terminated evaluation | SQLi_BODY |
| terminatingRuleType | Type of rule that terminated the evaluation | REGULAR |
| action | Final action taken on the request | BLOCK |

### 📊 Labels and Tags

| Field | Description | Sample Value |
|-------|-------------|---------------|
| labels | Labels added to the request during evaluation | ["awswaf:managed:aws:sql-database"] |
| rateBasedRuleList | List of rate-based rules that evaluated the request | [] |

### 🧾 Metadata

| Field | Description | Sample Value |
|-------|-------------|---------------|
| formatVersion | The version of the log format | 1.0 |
| webaclId | The ID of the WebACL associated with the request | arn:aws:wafv2:us-east-1:123456789012:regional/webacl/my-waf |
| terminatingRuleMatchDetails | Details on the rule that matched | [{"conditionType":"SQL_INJECTION","location":"BODY"}] |
