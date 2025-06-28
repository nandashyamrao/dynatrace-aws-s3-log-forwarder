# 🐳 StateFarm Dynatrace S3 Lambda Forwarder — Build Setup Overview

This document provides a complete reference of the file and directory structure for the **StateFarm Docker build** process to build the Dynatrace AWS S3 Lambda Forwarder, including secrets, scripts, certs, and build layers.

---

## 📁 Project Directory Structure

```
.
├── build.sh
├── Dockerfile
├── .docker/
│   └── secrets/
│       ├── proxy.txt
│       ├── JFROG_USER
│       ├── JFROG_TOKEN
│       └── GITLAB_TOKEN (optional)
├── .netrc
├── .tmp/
│   └── x86_64/
│       ├── aws_appconfig_extension.zip
│       └── aws_lambda_insights_extension.zip
├── src/
│   ├── app.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── ...
├── config/
│   └── ...
├── ca-files/
│   ├── sftrust.crt
│   └── cacerts.crt
└── common-files/
    └── scripts/
        ├── setup_dnf_repos.sh
        ├── jfrog_dnf_conf.sh
        └── jfrog_pip_conf.sh
```

---

## 📄 Key Files & Their Purpose

| File/Folder | Purpose |
|-------------|---------|
| `build.sh` | Automates Docker build with proxy, secrets, and StateFarm-specific setup. |
| `Dockerfile` | Docker image definition for building the Lambda function with certs and internal mirrors. |
| `.docker/secrets/proxy.txt` | Contains `http_proxy`, `https_proxy`, and `no_proxy`. |
| `.docker/secrets/JFROG_USER` | JFrog registry username. |
| `.docker/secrets/JFROG_TOKEN` | JFrog registry password/token. |
| `.docker/secrets/GITLAB_TOKEN` | Optional GitLab registry access token. |
| `.netrc` | Used by pip and tools to authenticate to JFrog or GitLab. |
| `.tmp/x86_64/*.zip` | Contains AWS Lambda AppConfig and Insights extensions. |
| `src/` | Python source code including Lambda handler. |
| `src/requirements.txt` | Required packages for Lambda runtime. |
| `src/requirements-dev.txt` | Dev/test/linting dependencies. |
| `config/` | Configuration files (JSON/YAML). |
| `ca-files/` | Internal certs to support secure HTTPS requests to internal systems. |
| `common-files/scripts/` | Scripts to setup YUM/DNF repos and configure pip to use JFrog mirrors. |

---

## 🧭 Build Flow Summary

1. **build.sh** authenticates to GitLab and JFrog, loads secrets.
2. Docker image is built using BuildKit with mounted secrets and arguments.
3. **Proxy settings** are applied from `proxy.txt` Docker secret.
4. **JFrog configuration** and internal certs are layered in.
5. **YUM** and **pip** are configured to use internal mirrors via scripts.
6. Python packages are installed with `pip`, using JFrog config.
7. Optional AWS Lambda extensions are extracted into `/opt`.

---

## ✅ Result

You will have a secure, reproducible Docker image for use in AWS Lambda with full support for:
- StateFarm CA certs
- Internal JFrog mirror
- BuildKit secrets
- Optional Lambda Insights and AppConfig extensions