# 📘 Dynatrace S3 Lambda Forwarder — Docker Build Documentation

## 🧾 Overview

This document outlines the full execution flow, directory structure, and Dockerfile logic used in building the **State Farm–customized Docker image** for the Dynatrace S3 Lambda forwarder.

---

## ⚙️ Execution Flow — Step-by-Step

| Step | Description |
|------|-------------|
| 1️⃣ | Docker build is initiated via `build.sh` |
| 2️⃣ | Proxy, JFrog, and GitLab credentials are loaded from Docker secrets |
| 3️⃣ | Custom internal YUM repos and pip configs are setup using `/opt/sf_scripts` |
| 4️⃣ | Required system dependencies (`yajl-devel`, `gcc`, etc.) are installed |
| 5️⃣ | Internal certificates (`sftrust.crt`, `cacerts.crt`) are added for TLS communication |
| 6️⃣ | AWS Lambda AppConfig and Insights extensions are copied and unpacked |
| 7️⃣ | Python dependencies are installed into the Lambda runtime folder (`$LAMBDA_TASK_ROOT`, i.e. `/var/task`) |
| 8️⃣ | Function code and configs are copied into `/var/task` |
| 9️⃣ | `CMD ["app.lambda_handler"]` tells Lambda to use `app.py`’s `lambda_handler` function |

---

## 📁 Directory Structure & Purpose

| Path | Description |
|------|-------------|
| `src/` | Python code for Lambda function (e.g. `app.py`, helper modules, requirements.txt) |
| `src/requirements.txt` | Runtime dependencies |
| `src/requirements-dev.txt` | Optional development dependencies |
| `config/` | Config files consumed by `app.py` (e.g., `config/settings.yml`) |
| `.tmp/${ARCH}/` | Pre-downloaded Lambda layer zips like `aws_appconfig_extension.zip` |
| `scripts/` | Internal State Farm helper scripts (YUM/pip/JFrog setup) |
| `build.sh` | Local shell to build image with secrets, proxies, and build arguments |
| `.docker/secrets/` | GitLab & JFrog auth files + proxy config + `.netrc` |
| `ca-files/` | Internal CA bundles like `cacerts.crt` and `sftrust.crt` |

---

## 🐳 Dockerfile Code Behavior

```
COPY src ${LAMBDA_TASK_ROOT}
ADD config ${LAMBDA_TASK_ROOT}/config
```

### 🔍 What this does:

| Instruction | Description |
|-------------|-------------|
| `COPY src ${LAMBDA_TASK_ROOT}` | Copies the Lambda function code and dependencies into `/var/task`, where Lambda expects to find your handler |
| `ADD config ${LAMBDA_TASK_ROOT}/config` | Adds internal YAML or JSON configuration files for the Lambda to read at runtime |
| `CMD ["app.lambda_handler"]` | Instructs Lambda to start by calling `lambda_handler` in `app.py` at `/var/task/app.py` |

📌 `$LAMBDA_TASK_ROOT` is defined by AWS Lambda base image as `/var/task`.