# AWS AppConfig Manual Setup for Lambda Integration

This guide explains **manual setup of AWS AppConfig** for use with AWS Lambda, including naming conventions, required resources, Lambda environment variables, and permission essentials. It also provides a **Terraform code example** for automating the creation of these resources.

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

Attach a policy allowing your Lambda to fetch config from AppConfig:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "appconfig:StartConfigurationSession",
        "appconfig:GetLatestConfiguration"
      ],
      "Resource": [
        "arn:aws:appconfig:<region>:<account-id>:application/sf-ems-dynatrace-s3-logfwd-app-config",
        "arn:aws:appconfig:<region>:<account-id>:application/sf-ems-dynatrace-s3-logfwd-app-config/environment/sf-ems-dynatrace-s3-logfwd/*"
      ]
    }
  ]
}
```
- Replace `<region>` and `<account-id>` with your values.
- Add more ARNs if you use multiple applications/environments.

---

## 5. **Terraform Code Example**

Below is a Terraform configuration to automate the AppConfig setup and IAM permissions.

```hcl
provider "aws" {
  region = "us-west-2" # Change as needed
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

# Lambda IAM Policy for AppConfig Access
data "aws_iam_policy_document" "lambda_appconfig" {
  statement {
    actions = [
      "appconfig:StartConfigurationSession",
      "appconfig:GetLatestConfiguration"
    ]
    resources = [
      "arn:aws:appconfig:${var.region}:${var.account_id}:application/sf-ems-dynatrace-s3-logfwd-app-config",
      "arn:aws:appconfig:${var.region}:${var.account_id}:application/sf-ems-dynatrace-s3-logfwd-app-config/environment/sf-ems-dynatrace-s3-logfwd/*"
    ]
  }
}

resource "aws_iam_policy" "lambda_appconfig_access" {
  name   = "LambdaAppConfigAccess"
  policy = data.aws_iam_policy_document.lambda_appconfig.json
}
```

---

## 6. **Summary Checklist**

- [ ] AppConfig Application, Environment, Profiles, Versions, Deployment Strategy created (manually or with Terraform).
- [ ] Naming conventions used consistently in Lambda environment variables and IAM policy.
- [ ] Lambda execution role has required AppConfig permissions.
- [ ] Lambda environment variable(s) point to correct AppConfig resources.
- [ ] If using Lambda Extension, it is added as a Lambda Layer or in the container image.

---

## 7. **References**

- [AWS AppConfig Documentation](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-creating-configuration-and-deployment.html)
- [AppConfig Lambda Extension Guide](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-integration-lambda-extensions.html)
- [AppConfig Permissions Reference](https://docs.aws.amazon.com/appconfig/latest/userguide/appconfig-access-control-iam.html)
