# AWS AppConfig Manual Setup for Lambda Integration

This guide explains **manual setup of AWS AppConfig** for use with AWS Lambda, including naming conventions, required resources, Lambda environment variables, and permission essentials. It also provides a **Terraform code example** for automating the creation of these resources, and explains the end-to-end flow of how the build and deployment works.

---

## 1. **AppConfig Resource Naming Conventions**

To ensure your Lambda can reliably fetch configuration, use a consistent naming pattern for your AppConfig resources:

| Resource Type               | Example Name                                   | Purpose                                             |
|-----------------------------|------------------------------------------------|-----------------------------------------------------|
| AppConfig Application       | `sf-ems-dynatrace-s3-logfwd-app-config`        | Top-level grouping for all related configs          |
| AppConfig Environment       | `sf-ems-dynatrace-s3-logfwd`                   | Typically matches your deployment environment name  |
| Configuration Profile 1     | `log-forwarding-rules`                         | Stores rules for log forwarding                     |
| Configuration Profile 2     | `log-processing-rules`                         | Stores rules for log processing                     |
| Deployment Strategy         | `sf-ems-dynatrace-s3-logfwd-AllAtOnce`         | Controls config rollout behavior                    |

**You can customize these names,** but they must be referenced consistently in your Lambda’s environment variables and permissions.

---

## 2. **Manual AppConfig Setup Steps (AWS Console or CLI)**

### a. **Create the Application**
- Go to AWS Systems Manager > AppConfig > Applications > Create application
- Name: `sf-ems-dynatrace-s3-logfwd-app-config`
- Description: (optional)

### b. **Create the Environment**
- Within your application, choose "Environments" > "Create environment"
- Name: `sf-ems-dynatrace-s3-logfwd`
- Description: (optional)

### c. **Create Configuration Profiles**
- For each profile:
    - Name: `log-forwarding-rules` (and repeat for `log-processing-rules`)
    - Location URI: `Hosted` (unless using S3/SSM Parameter Store)
    - Type: `AWS.Freeform`
    - Description: (optional)

### d. **Add Hosted Configuration Versions**
- For each profile, create at least one configuration version.
- Use JSON or other content matching your application needs.

### e. **Create Deployment Strategy**
- Name: `sf-ems-dynatrace-s3-logfwd-AllAtOnce`
- Deployment method: All at once (or as preferred)
- Duration: 0 min (for immediate rollout)
- Replicate to: None

### f. **Deploy Configurations**
- Deploy each configuration profile to the environment using your deployment strategy.

---

## 3. **Lambda Environment Variables (Essentials)**

Your Lambda must know **where to find the config**. The two most common approaches:

### **A. If Using the AppConfig Lambda Extension (Recommended)**
Add this environment variable to your Lambda:

```
AWS_APPCONFIG_EXTENSION_PREFETCH_LIST=/applications/sf-ems-dynatrace-s3-logfwd-app-config/environments/sf-ems-dynatrace-s3-logfwd/configurations/log-forwarding-rules,/applications/sf-ems-dynatrace-s3-logfwd-app-config/environments/sf-ems-dynatrace-s3-logfwd/configurations/log-processing-rules
```
- This tells the extension which configs to prefetch and keep up-to-date at `/opt/appconfig/`.

### **B. If Fetching via boto3 (SDK) in Code**
Set custom environment variables for use in your code, e.g.:

- `APPCONFIG_APPLICATION=sf-ems-dynatrace-s3-logfwd-app-config`
- `APPCONFIG_ENVIRONMENT=sf-ems-dynatrace-s3-logfwd`
- `APPCONFIG_PROFILE=log-forwarding-rules`

And in your code, reference these when calling the AppConfigData APIs.

---

## 4. **Lambda IAM Role Essentials**

> **Important:**  
> AWS AppConfig ARNs use resource IDs, **not names**. When resources are created by Terraform or CloudFormation, the ARNs must be constructed using the generated AppConfig resource IDs (not the display names). This ensures correct permissions.

Attach a policy allowing your Lambda to fetch config from AppConfig.  
Below is a dynamic Terraform-based approach that always uses the correct IDs.

---

## 5. **Terraform Code Example**

Below is a Terraform configuration to automate the AppConfig setup and IAM permissions.  
**This version outputs a policy that can be directly attached to the Lambda execution role, using AppConfig resource IDs.**

```hcl
provider "aws" {
  region = "us-west-2" # Change as needed
}

variable "account_id" {
  description = "AWS Account ID"
  type        = string
}

variable "region" {
  description = "AWS Region"
  type        = string
  default     = "us-west-2"
}

# AppConfig Application
resource "aws_appconfig_application" "log_forwarder" {
  name        = "sf-ems-dynatrace-s3-logfwd-app-config"
  description = "AppConfig application for Dynatrace S3 Log Forwarder"
}

# AppConfig Environment
resource "aws_appconfig_environment" "log_forwarder_env" {
  application_id = aws_appconfig_application.log_forwarder.id
  name           = "sf-ems-dynatrace-s3-logfwd"
  description    = "Environment for Dynatrace S3 Log Forwarder"
}

# Configuration Profiles
resource "aws_appconfig_configuration_profile" "log_forwarding_rules" {
  application_id = aws_appconfig_application.log_forwarder.id
  name           = "log-forwarding-rules"
  location_uri   = "hosted"
  type           = "AWS.Freeform"
  description    = "Log forwarding rules"
}

resource "aws_appconfig_configuration_profile" "log_processing_rules" {
  application_id = aws_appconfig_application.log_forwarder.id
  name           = "log-processing-rules"
  location_uri   = "hosted"
  type           = "AWS.Freeform"
  description    = "Log processing rules"
}

# Hosted Configuration Versions
resource "aws_appconfig_hosted_configuration_version" "log_forwarding_rules_ver" {
  application_id            = aws_appconfig_application.log_forwarder.id
  configuration_profile_id  = aws_appconfig_configuration_profile.log_forwarding_rules.id
  content_type              = "application/json"
  description               = "Initial log-forwarding-rules"
  content                   = jsonencode({ "example": "value" }) # Replace with real config
}

resource "aws_appconfig_hosted_configuration_version" "log_processing_rules_ver" {
  application_id            = aws_appconfig_application.log_forwarder.id
  configuration_profile_id  = aws_appconfig_configuration_profile.log_processing_rules.id
  content_type              = "application/json"
  description               = "Initial log-processing-rules"
  content                   = jsonencode({ "example": "value" }) # Replace with real config
}

# Deployment Strategy
resource "aws_appconfig_deployment_strategy" "all_at_once" {
  name                       = "sf-ems-dynatrace-s3-logfwd-AllAtOnce"
  deployment_duration_in_minutes = 0
  final_bake_time_in_minutes     = 0
  growth_factor                 = 100
  replicate_to                  = "NONE"
  description                   = "AllAtOnce strategy for log forwarder"
}

# Deploy Configurations
resource "aws_appconfig_deployment" "log_forwarding_rules" {
  application_id           = aws_appconfig_application.log_forwarder.id
  environment_id           = aws_appconfig_environment.log_forwarder_env.id
  configuration_profile_id = aws_appconfig_configuration_profile.log_forwarding_rules.id
  configuration_version    = aws_appconfig_hosted_configuration_version.log_forwarding_rules_ver.version_number
  deployment_strategy_id   = aws_appconfig_deployment_strategy.all_at_once.id
  description              = "Deploy log-forwarding-rules"
}

resource "aws_appconfig_deployment" "log_processing_rules" {
  application_id           = aws_appconfig_application.log_forwarder.id
  environment_id           = aws_appconfig_environment.log_forwarder_env.id
  configuration_profile_id = aws_appconfig_configuration_profile.log_processing_rules.id
  configuration_version    = aws_appconfig_hosted_configuration_version.log_processing_rules_ver.version_number
  deployment_strategy_id   = aws_appconfig_deployment_strategy.all_at_once.id
  description              = "Deploy log-processing-rules"
}

# Lambda IAM Policy for AppConfig Access (using IDs, not names)
data "aws_iam_policy_document" "lambda_appconfig" {
  statement {
    actions = [
      "appconfig:StartConfigurationSession",
      "appconfig:GetLatestConfiguration"
    ]
    resources = [
      "arn:aws:appconfig:${var.region}:${var.account_id}:application/${aws_appconfig_application.log_forwarder.id}",
      "arn:aws:appconfig:${var.region}:${var.account_id}:application/${aws_appconfig_application.log_forwarder.id}/environment/${aws_appconfig_environment.log_forwarder_env.id}/*"
    ]
  }
}

resource "aws_iam_policy" "lambda_appconfig_access" {
  name   = "LambdaAppConfigAccess"
  policy = data.aws_iam_policy_document.lambda_appconfig.json
}

output "lambda_appconfig_access_policy_arn" {
  value       = aws_iam_policy.lambda_appconfig_access.arn
  description = "IAM Policy ARN to grant Lambda access to AppConfig (uses application/environment IDs)"
}
```

---

## 6. **Build & Deployment Flow Explanation**

The following summarizes the typical flow from infrastructure build to Lambda configuration retrieval:

1. **Terraform Build**  
   - Terraform provisions all AppConfig resources: Application, Environment, Configuration Profiles, Hosted Versions, Deployment Strategy, and Deployments.  
   - Terraform also creates an IAM policy (using resource IDs in ARNs) granting Lambda permission to retrieve configuration.

2. **IAM Policy Attachment**  
   - The output policy ARN (`lambda_appconfig_access_policy_arn`) is attached to the Lambda execution role.  
   - This policy allows Lambda to call `appconfig:StartConfigurationSession` and `appconfig:GetLatestConfiguration` on the correct AppConfig resources.

3. **Lambda Deployment**  
   - Lambda is deployed with environment variables indicating which AppConfig application/environment/profile to use.
   - Optionally, the AppConfig Lambda Extension is included as a layer or in the container image.

4. **Config Fetch at Runtime**  
   - When Lambda executes, it either:
     - Uses the Lambda Extension to prefetch and cache configuration from AppConfig, **or**
     - Uses SDK calls (e.g., boto3) to fetch configuration directly via the AppConfigData APIs, using the environment variables for lookup.
   - The Lambda function thus receives the latest configuration as defined in AppConfig.

5. **Ongoing Updates**  
   - To update configuration, modify the hosted configuration version or create a new deployment in AppConfig.
   - Lambda will pick up the new config on next execution (immediate if using the extension, or on next fetch if using SDK).

---

## 7. **Summary Checklist**

- [ ] AppConfig Application, Environment, Profiles, Versions, Deployment Strategy created (manually or with Terraform).
- [ ] Naming conventions used consistently in Lambda environment variables and IAM policy.
- [ ] Lambda execution role has required AppConfig permissions (using resource IDs).
- [ ] Lambda environment variable(s) point to correct AppConfig resources.
- [ ] If using Lambda Extension, it is added as a Lambda Layer or in the container image.

---

## 8. **References**

- [AWS AppConfig Documentation](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-configuration-and-deployment.html)
- [AppConfig Lambda Extension Guide](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-lambda-extensions.html)
- [AppConfig Permissions Reference](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-access-control-iam.html)
