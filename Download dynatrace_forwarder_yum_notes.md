# 🧾 Why Dynatrace AWS S3 Log Forwarder Uses `yum` and `yajl-devel`

## 📌 Summary

The Dynatrace AWS S3 Log Forwarder uses the `yum` package manager to install `yajl-devel` and other OS dependencies. This is due to the choice of Amazon Linux / RHEL-based base image that is compatible with AWS Lambda runtimes.

---

## ✅ Availability of `yajl` Across Popular Package Managers

| OS / Distro             | Package Manager | Package Name        | Notes                                                                 |
|-------------------------|------------------|---------------------|-----------------------------------------------------------------------|
| **Amazon Linux / RHEL / CentOS** | `yum` / `dnf`       | `yajl-devel`        | Required for compiling/linking C extensions using YAJL                |
| **Debian / Ubuntu**     | `apt`            | `libyajl-dev`       | Equivalent to `yajl-devel`                                            |
| **Alpine Linux**        | `apk`            | ❌ *Not available*   | Must be compiled from source — **not suitable** for lightweight builds |
| **Homebrew (macOS)**    | `brew`           | `yajl`              | Only useful for local dev builds                                      |

---

## 🔍 Why This Design Choice?

- The forwarder uses **Amazon Linux-compatible images** to ensure runtime parity with AWS Lambda.
- `yajl-devel` is used for **efficient JSON parsing**, crucial for processing large volumes of AWS logs.
- `yum` is the default package manager on Amazon Linux 2 and RHEL-based systems.

---

## ⚙️ Could This Be Changed?

Technically yes, with tradeoffs:

- **Use `apt`** on Ubuntu-based images — possible if runtime isn't constrained by Lambda compatibility.
- **Alpine-based builds** — very lightweight, but require compiling YAJL from source.
- **Use Python-native alternatives** — such as `orjson` or `ujson`, which may offer sufficient performance without C bindings.

---

## 🧠 Recommendation

For production-grade processing of structured AWS logs, sticking with `yajl-devel` on Amazon Linux ensures:

- Compatibility
- Performance
- Ease of maintenance with AWS Lambda layers

However, lightweight alternatives may be explored if minimizing image size or startup latency is a priority.

---

