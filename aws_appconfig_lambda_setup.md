
# 📦 Terraform Setup for AWS AppConfig in Lambda

Use this when configuring your Lambda function to read AppConfig parameters like `log-forwarding-rules` and `log-processing-rules`.

---

## 📌 Required AppConfig Path Format

```
/applications/<application_name>/environments/<environment_name>/configurations/<configuration_profile_name>
```

---

## 🔧 Example AppConfig URIs

From the screenshot:

```txt
/applications/dts3fwdsns_cf_app_config/environments/dts3fwdsns_cf_app_config/configurations/log-forwarding-rules
/applications/dts3fwdsns_cf_app_config/environments/dts3fwdsns_cf_app_config/configurations/log-processing-rules
```

---

## 🛠️ Terraform Example: Lambda with Environment Variables

```hcl
resource "aws_lambda_function" "log_forwarder" {
  function_name = "dts3-log-forwarder"
  ...

  environment {
    variables = {
      LOG_FORWARDING_RULES_PARAM = "/applications/dts3fwdsns_cf_app_config/environments/dts3fwdsns_cf_app_config/configurations/log-forwarding-rules"
      LOG_PROCESSING_RULES_PARAM = "/applications/dts3fwdsns_cf_app_config/environments/dts3fwdsns_cf_app_config/configurations/log-processing-rules"
    }
  }
}
```

---

## 🔍 (Optional) Use Terraform Data Sources for Validation

Fetch AppConfig resources dynamically (optional but safer):

```hcl
data "aws_appconfig_application" "app" {
  name = "dts3fwdsns_cf_app_config"
}

data "aws_appconfig_environment" "env" {
  application_id = data.aws_appconfig_application.app.id
  name           = "dts3fwdsns_cf_app_config"
}

data "aws_appconfig_configuration_profile" "log_forwarding" {
  application_id = data.aws_appconfig_application.app.id
  name           = "log-forwarding-rules"
}

data "aws_appconfig_configuration_profile" "log_processing" {
  application_id = data.aws_appconfig_application.app.id
  name           = "log-processing-rules"
}
```

---

## ✅ Lambda with Dynamic AppConfig ARNs (Optional)

```hcl
resource "aws_lambda_function" "log_forwarder" {
  function_name = "dts3-log-forwarder"
  ...

  environment {
    variables = {
      LOG_FORWARDING_RULES_PARAM = data.aws_appconfig_configuration_profile.log_forwarding.arn
      LOG_PROCESSING_RULES_PARAM = data.aws_appconfig_configuration_profile.log_processing.arn
    }
  }
}
```

---

## 📎 Related CLI Commands

You can also list AppConfig values manually:

```bash
aws appconfig list-applications
aws appconfig list-environments --application-id <app_id>
aws appconfig list-configuration-profiles --application-id <app_id>
```
