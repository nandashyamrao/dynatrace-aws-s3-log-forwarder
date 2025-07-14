# ✅ CloudTrail Log Fields – Categorized with Real-World Sample Values

### 🧾 Event Metadata

| Field | Description | Sample Value |
|-------|-------------|---------------|
| eventTime | The time the event occurred | 2025-07-13T14:23:45Z |
| eventName | The name of the API operation | RunInstances |
| eventSource | The AWS service that the request was made to | ec2.amazonaws.com |
| eventVersion | The CloudTrail event version | 1.08 |
| eventID | Unique ID for the event | abc12345-6789-0123-4567-abcdefabcdef |

### 👤 Identity Information

| Field | Description | Sample Value |
|-------|-------------|---------------|
| userIdentity.type | The type of user (IAMUser, Root, AssumedRole, etc.) | AssumedRole |
| userIdentity.arn | The Amazon Resource Name (ARN) of the principal | arn:aws:sts::123456789012:assumed-role/AdminRole/AWSCLI-Session |
| userIdentity.accountId | The AWS account ID of the user | 123456789012 |
| userIdentity.userName | The username of the IAM user | jdoe |

### 🌐 Request Context

| Field | Description | Sample Value |
|-------|-------------|---------------|
| sourceIPAddress | The IP address from which the request was made | 203.0.113.45 |
| userAgent | The agent used to make the request | aws-cli/2.0 |
| awsRegion | The AWS region where the request was made | us-east-1 |

### 🔧 Request Parameters

| Field | Description | Sample Value |
|-------|-------------|---------------|
| requestParameters | The parameters sent with the request | {"instanceType":"t2.micro"} |
| requestID | The AWS request ID | 12345678-abcd-1234-abcd-123456abcdef |

### 📤 Response Elements

| Field | Description | Sample Value |
|-------|-------------|---------------|
| responseElements | The elements returned in the response | {"instancesSet":{"items":[{"instanceId":"i-1234567890abcdef0"}]}} |

### 📁 Resources Accessed

| Field | Description | Sample Value |
|-------|-------------|---------------|
| resources | The AWS resources impacted by the request | [{"ARN":"arn:aws:ec2:us-east-1:123456789012:instance/i-1234567890abcdef0"}] |

### 🔒 Authorization

| Field | Description | Sample Value |
|-------|-------------|---------------|
| userIdentity.sessionContext.attributes.mfaAuthenticated | Whether MFA was used | true |
| userIdentity.sessionContext.attributes.creationDate | When the session was created | 2025-07-13T13:50:30Z |
