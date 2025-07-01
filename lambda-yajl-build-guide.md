
# 🐳 Building AWS Lambda Python Images with YAJL — Without RHEL Dependency

## 📘 Introduction

With Red Hat Enterprise Linux (RHEL) becoming subscription-based and restricting unauthenticated access to its package repositories, enterprise teams that once relied on RHEL-based Docker images for building Python Lambda functions must now pivot to a strategy that is secure, flexible, and compliant with AWS Lambda's runtime.

This guide outlines a clean, reproducible, and secure approach to building AWS Lambda container images that include native C dependencies like **YAJL (Yet Another JSON Library)** and Python packages that require C compilation (e.g., `jsonslicer`, `regex`, `pygrok`). This approach **completely avoids RHEL** and instead leverages **Amazon Linux 2**, which aligns perfectly with the Lambda runtime.

---

## ❗ Why This Approach Is Needed

### 🔒 The Problem

- **RHEL no longer allows free access to package mirrors**.
- Docker builds based on RHEL images (`ubi8`, `rhel8`) now fail without a valid Red Hat subscription.
- Many Python packages that use C extensions require system libraries and a compiler (`gcc`, `yajl-devel`, etc.) during install.

### 🎯 The Goal

- **Avoid RHEL entirely**.
- **Build all native dependencies and Python packages in a controlled Stage 1 build**.
- **Deploy a final AWS Lambda-compatible image** that is clean, minimal, and doesn't carry unnecessary build tools or RHEL ties.

---

## 🧱 Multi-Stage Docker Build Strategy

This approach uses two Docker stages:

1. **Stage 1: Build Stage**
   - Use `amazonlinux:2` to build YAJL and all Python wheels.
   - Compile all native extensions ahead of time.
   - No RHEL involved.

2. **Stage 2: Runtime Stage**
   - Use `public.ecr.aws/lambda/python:<version>` as the final image.
   - Install prebuilt wheels from Stage 1.
   - Copy over YAJL headers/libs if needed.

---

### 🔨 Stage 1: Build YAJL and Python Wheels

```dockerfile
FROM amazonlinux:2 AS builder

RUN yum -y groupinstall "Development Tools" &&     yum install -y python3-pip yajl-devel

WORKDIR /build
COPY requirements.txt .

# Build all required Python packages as wheels
RUN pip3 install --upgrade pip &&     pip3 wheel --no-cache-dir --use-pep517 -r requirements.txt -w /tmp/wheels
```

---

### 🐍 Stage 2: Lambda Runtime (Clean Image)

```dockerfile
FROM public.ecr.aws/lambda/python:3.12

# Optional: include YAJL from builder
COPY --from=builder /usr/include/yajl /opt/yajl/include
COPY --from=builder /usr/lib64/libyajl* /opt/yajl/lib

ENV LD_LIBRARY_PATH="/opt/yajl/lib:${LD_LIBRARY_PATH}"
ENV C_INCLUDE_PATH="/opt/yajl/include:${C_INCLUDE_PATH}"

# Copy and install prebuilt wheels
COPY --from=builder /tmp/wheels /tmp/wheels
RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir --target "${LAMBDA_TASK_ROOT}" /tmp/wheels/*.whl

# Copy your application code
COPY src ${LAMBDA_TASK_ROOT}
CMD ["app.lambda_handler"]
```

---

## 📦 Why Not Install in Stage 2?

If you try to install `jsonslicer`, `regex`, or `pygrok` directly in Stage 2:

- You will need `gcc`, `yajl-devel`, and build backends.
- This adds unnecessary weight and complexity.
- It violates Lambda best practices of keeping runtime lean and secure.
- And worse, if you used to use RHEL for this — it will now **fail due to subscription lock**.

---

## ✅ Summary

| Goal                         | This Approach Enables                    |
|------------------------------|------------------------------------------|
| No RHEL or UBI dependencies  | ✅ Uses Amazon Linux 2 instead            |
| Minimal final image          | ✅ Keeps build tools out of runtime       |
| Native C libraries supported | ✅ Builds YAJL and C extensions in Stage 1|
| Secure, reproducible builds  | ✅ Supports air-gapped or CI environments |
| AWS Lambda compatibility     | ✅ Built on `public.ecr.aws/lambda/python`|

---

## 🛠️ Optional: Offline Build Script

You can also build the Python wheels offline:

```bash
pip install --upgrade pip
pip wheel --use-pep517 -r requirements.txt -w wheels/
```

Then just `COPY ./wheels` into the runtime image and install from there.

---

## 📌 Final Thoughts

This Docker build pattern is essential for modern enterprise development where:

- **Public access to RHEL packages is no longer guaranteed**
- **Security mandates minimal runtime images**
- **AWS Lambda runtime compatibility is critical**

By shifting all compilation to Stage 1 and relying on Amazon Linux 2 and Lambda base images, you gain maximum compatibility, portability, and control.

Let us know if you want this incorporated into GitLab CI/CD or Terraform-based image pipelines.


---

## 🖼️ Build Flow Diagram (Visual)

Below is a visual representation of the entire multi-stage Lambda Docker build process, including optional YAJL, AppConfig, and Lambda Insights support:

![Lambda YAJL Build Flow](/mnt/data/lambda-yajl-docker-build-flow.png)

