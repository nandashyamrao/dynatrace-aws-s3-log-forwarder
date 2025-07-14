# 🧾 CloudFront Log Fields — Grouped for Easy Reference

This guide groups the [AWS CloudFront standard log fields](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/AccessLogs.html#LogFileFormat) into categories for easier understanding and recall.

---

## ✅ 1. Timestamp & Location
| Field | Description | Sample Value |
|-------|-------------|---------------|
| `date` | Date of the request (YYYY-MM-DD) | — |
| `time` | Time of the request (HH:MM:SS) | — |
| `x-edge-location` | AWS Edge location (e.g., LAX3) | — |
| Field | Meaning | — |
| ------------------- | ---------------------------------- | — |
| `cs-method` | HTTP method (GET, POST, etc.) | — |
| `cs-uri-stem` | URI path requested | — |
| `cs-uri-query` | Query string parameters | — |
| `sc-status` | HTTP status code returned | — |
| `sc-bytes` | Bytes sent to the client | — |
| `cs-bytes` | Bytes received from the client | — |
| `cs-protocol` | Protocol used (http or https) | — |
| `cs-protocol-version` | HTTP version (e.g., HTTP/1.1) | — |
| `cs(Referer)` | Referrer header | — |
| `cs(User-Agent)` | User agent string | — |
| `cs(Cookie)` | Cookie sent by client | — |
| `cs-host` | Host header | — |
| Field | Meaning | — |
| ------------------ | --------------------------------- | — |
| `c-ip` | Client IP address | — |
| `x-forwarded-for` | Original client IP via proxy | — |
| `time-to-first-byte` | Time to first byte in seconds | — |
| Field | Meaning | — |
| ------------------------ | ---------------------------------- | — |
| `x-edge-result-type` | CloudFront result (Hit, Miss, etc.) | — |
| `x-edge-request-id` | Unique ID for the request | — |
| `x-edge-response-result-type` | Final result (e.g., Error) | — |
| `cs-signer` | Signed URL signer | — |
| `cs-auth-type` | Authentication type | — |
| `cs-username` | Username | — |
| `cs-referer` | Alternative referer field | — |
| Field | Meaning | — |
| --------------------- | ---------------------------------- | — |
| `x-edge-cache-status` | Cache status (Hit, Miss, Error) | — |
| `x-origin-status` | Origin server HTTP status | — |
| `x-origin-host` | Origin server host | — |
| `x-origin-shield` | Origin shield region | — |
| Field | Meaning | — |
| ------------------------ | --------------------------------- | — |
| `rsc-bytes` | Response size from origin | — |
| `rs-bytes` | Final response size to client | — |
| `cs-headers` | Request headers | — |
| `sc-headers` | Response headers | — |
| `ssl-protocol` | SSL protocol used | — |
| `ssl-cipher` | SSL cipher used | — |
| `fle-status` | Field-level encryption status | — |
| `fle-encrypted-fields` | Count of encrypted fields | — |
| `protocol` | Protocol (redundant to cs-protocol) | — |