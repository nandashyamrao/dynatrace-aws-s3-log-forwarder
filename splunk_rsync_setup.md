# dt-csvlookup-datapipeline → Splunk rsync (SSH key via AWS Secrets Manager)

This document explains the **Splunk upload step** in your GitLab pipeline and provides a **YAML-safe** `.gitlab-ci.yml` example that:

- Uses **GitLab OIDC → AWS STS assume-role** (no GitLab CI secret variables needed for credentials).
- Pulls the **Splunk SSH private key** from **AWS Secrets Manager** (TEST vs PROD).
- Adds the key to **ssh-agent** at runtime (key never stored in the repo).
- Tries **multiple Splunk hosts** one-by-one until rsync succeeds.
- Supports a **dry-run mode** (SSH + rsync simulation, no remote writes).

---

## 🧱 What gets uploaded to Splunk?

Your job builds:

- `servicenow_final.csv` (cleaned)
- `splunk/servicenow.csv` (Splunk-formatted with `z_` prefixing and quoting rules)
- `summary.txt` (run summary)

The Splunk upload step rsyncs:

- `splunk/servicenow.csv` → `${SPLUNK_DEST_DIR}/` on a Splunk server

---

## 🔐 Where secrets live (enterprise-friendly)

Because your enterprise doesn’t allow storing these in GitLab CI env vars, keep them in **AWS Secrets Manager**.

### ✅ Recommended: single “pipeline secret” containing everything
Example secret name: `dtcsvlookup` (you already use this)

Add these fields:

- `splunk_id`: `splunk2` *(optional; you can hardcode splunk2 in YAML)*
- `splunk2_sshkey_test`: **private key PEM** for TEST uploads (multi-line)
- `splunk2_sshkey_prod`: **private key PEM** for PROD uploads (multi-line)

> **Important:** For multi-line PEM values, store them as normal JSON string values in Secrets Manager. AWS will preserve newlines.

---

## 🧑‍💼 Instructions for Splunk admin: create keys and install them

### Goal
Allow GitLab Runner jobs to SSH as user `splunk2` into Splunk servers using SSH keys.

### Steps (Splunk admin)
1. **Generate keypair** (recommended: one key per environment)
   ```bash
   ssh-keygen -t ed25519 -C "gitlab-dtcsvlookup-test" -f splunk2_gitlab_test -N ""
   ssh-keygen -t ed25519 -C "gitlab-dtcsvlookup-prod" -f splunk2_gitlab_prod -N ""
   ```

2. **Install the public key** on each Splunk server for user `splunk2`
   - Append the public key content into:
     - `/home/splunk2/.ssh/authorized_keys`
   - Ensure permissions:
     ```bash
     chmod 700 /home/splunk2/.ssh
     chmod 600 /home/splunk2/.ssh/authorized_keys
     chown -R splunk2:splunk2 /home/splunk2/.ssh
     ```

3. **Give the pipeline the private key**
   - Provide the **private** key files to your AWS Secrets Manager owner (NOT GitLab).
   - Store:
     - TEST private key → `splunk2_sshkey_test`
     - PROD private key → `splunk2_sshkey_prod`

✅ **Do you need 6 keys for 6 servers?**  
Not necessarily. **One keypair can be used across multiple servers** as long as the same public key is placed in `authorized_keys` on each server. Many enterprises still prefer **one key per environment** (TEST/PROD) for separation and auditability.

---

## 🧪 Dry-run mode (what it is)

“Dry run” means:

- ✅ Validate AWS can read the secret
- ✅ Validate ssh-agent can load the key
- ✅ Validate network/SSH connectivity to each Splunk host
- ✅ Show which files *would* be transferred via rsync
- ❌ Do **not** actually copy files to Splunk

In the YAML below, you control this with:

- `DRY_RUN: "true"` or `"false"`

---

## 🗺️ Text diagram of components

```
GitLab Pipeline Job (container image)
  |
  |--(OIDC JWT)--> AWS STS AssumeRole  -----> temporary AWS creds
  |
  |--(aws s3 cp)--> S3 bucket (orgdata.csv)
  |
  |--(process_csv.sh)--> servicenow_final.csv
  |--(awk transform)--> splunk/servicenow.csv
  |--(cat <<EOF)--> summary.txt
  |
  |--(aws secretsmanager get-secret-value)--> dtcsvlookup secret
  |        |--> splunk2_sshkey_test OR splunk2_sshkey_prod
  |
  |--(ssh-agent + ssh-add)--> in-memory private key
  |
  |--(for host in LIST; rsync ...)--> Splunk server(s)
           |--> /opt/splunk/var/servicenow.csv
```

---

## ✅ YAML-safe `.gitlab-ci.yml` example (fixed indentation + safe multi-line blocks)

- Uses a single `script: - |` block so you don’t get the classic error:
  - `/bin/bash: line XXX: -: command not found`
- Ensures `summary.txt` creation cannot break YAML parsing.

See the included `gitlab-ci-fixed.yml`.
