# ✅ CloudFront Log Fields – Categorized with Real-World Sample Values

### 📅 Request Timing

| Field | Description | Sample Value |
|-------|-------------|---------------|
| date | The date when the request was received | 2025-07-13 |
| time | The time when the request was received | 14:23:00 |

### 📍 Edge Location Info

| Field | Description | Sample Value |
|-------|-------------|---------------|
| x-edge-location | The CloudFront edge location that served the request | SFO20-C1 |

### 📦 Response Details

| Field | Description | Sample Value |
|-------|-------------|---------------|
| sc-bytes | The number of bytes returned to the client | 2150 |
| sc-status | The HTTP status code returned to the viewer | 200 |

### 🌐 Viewer Identity

| Field | Description | Sample Value |
|-------|-------------|---------------|
| c-ip | The IP address of the viewer that made the request | 203.0.113.24 |
| cs(User-Agent) | The user agent of the browser/device that made the request | Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) |
| cs(Referer) | The referrer URL that led the viewer to the request | https://www.google.com/search?q=example |

### 🧾 Request Details

| Field | Description | Sample Value |
|-------|-------------|---------------|
| cs-method | The HTTP method used for the request | GET |
| cs(Host) | The host header of the request | cdn.example.com |
| cs-uri-stem | The URI stem (path) portion of the request | /images/logo.png |
| cs-uri-query | The query string portion of the request URI | version=1.2.3&format=webp |

### 🔐 Security

| Field | Description | Sample Value |
|-------|-------------|---------------|
| ssl-protocol | The SSL/TLS protocol negotiated during the request | TLSv1.3 |
| ssl-cipher | The SSL/TLS cipher negotiated during the request | ECDHE-RSA-AES128-GCM-SHA256 |

### 📥 Request Origin & Headers

| Field | Description | Sample Value |
|-------|-------------|---------------|
| x-forwarded-for | The X-Forwarded-For header identifying originating IP | 198.51.100.5 |
| cs(Cookie) | The Cookie header sent by the client | sessionid=abc123 |
| cs(Accept-Encoding) | The Accept-Encoding header from the client | gzip, deflate, br |
| cs(Referer) | Referrer that led to the request | https://www.example.com/page |

### 📤 Response Headers

| Field | Description | Sample Value |
|-------|-------------|---------------|
| cs-protocol | The protocol used by the client (http or https) | https |
| cs-bytes | The number of bytes received from the client | 512 |
| time-taken | The total time taken to serve the request | 0.123 |
