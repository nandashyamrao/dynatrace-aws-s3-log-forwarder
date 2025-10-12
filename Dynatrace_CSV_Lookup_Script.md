# 🧾 Combined Dynatrace CSV Upload Script (Secure)

This script performs three key tasks:

1. Cleans and transforms your input AWS account CSV file
2. Retrieves a secure OAuth2 access token from Dynatrace
3. Uploads the cleaned file as a lookup table via the Dynatrace Resource Store API

---

## 🧩 Overview

This script assumes your Dynatrace environment ID is **`cqf94088`** and securely stores your OAuth client credentials in `~/dtscript/secret/`.

---

## 🧾 **`~/dtscript/run.sh`**

```bash
#!/usr/bin/env bash
set -Eeuo pipefail

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
DIR="${HOME}/dtscript"
INPUT="${DIR}/input.csv"
OUTPUT="${DIR}/account.csv"

# Secure secret storage (each file contains only the value)
ID_FILE="${DIR}/secret/client_id"
SECRET_FILE="${DIR}/secret/client_secret"
RESOURCE_FILE="${DIR}/secret/resource"

# Dynatrace endpoints (for cqf94088 environment)
TOKEN_URL="https://sso.dynatrace.com/sso/oauth2/token"
UPLOAD_URL="https://cqf94088.apps.dynatrace.com/platform/storage/resource-store/v1/files/tabular/lookup:upload"

DISPLAY_NAME="SF AWS Account Map"
DESCRIPTION="Map AWS account ID to account name, area, cost center, and environment"
LOOKUP_FIELD="account_id"
OVERWRITE=true

# ─────────────────────────────────────────────
# DEPENDENCY CHECKS
# ─────────────────────────────────────────────
for cmd in awk sort curl sed mktemp; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "❌ Missing dependency: $cmd"; exit 1;
  }
done

[[ -f "$INPUT" ]] || { echo "❌ Input file not found: $INPUT"; exit 1; }

# ─────────────────────────────────────────────
# PROMPT FOR SECRETS IF MISSING
# ─────────────────────────────────────────────
if [[ ! -f "$ID_FILE" || ! -f "$SECRET_FILE" || ! -f "$RESOURCE_FILE" ]]; then
  echo "🔐 Creating secret files under $DIR/secret/"
  mkdir -p "${DIR}/secret"
  chmod 700 "${DIR}/secret"

  read -rp "Dynatrace client_id: " cid
  read -rsp "Dynatrace client_secret: " csec; echo
  read -rp "Dynatrace resource (urn:dtaccount:...): " res

  printf '%s' "$cid"  > "$ID_FILE"
  printf '%s' "$csec" > "$SECRET_FILE"
  printf '%s' "$res"  > "$RESOURCE_FILE"
  chmod 600 "${DIR}/secret/"*
  unset cid csec res
  echo "✅ Secrets saved securely."
fi

# ─────────────────────────────────────────────
# 1️⃣ CLEAN INPUT CSV
# ─────────────────────────────────────────────
temp_clean="$(mktemp)"
trap 'rm -f "$temp_clean" "$temp_token" "$temp_body"' EXIT

echo "🧹 Cleaning CSV..."

awk -F',' '
NR > 1 {                                 # Skip header
  if ($0 ~ /\(not set\)/) next           # Skip lines with (not set)
  gsub(/-/, "", $1)                      # Remove hyphens from account ID

  # Trim whitespace
  for (i = 1; i <= NF; i++) {
    gsub(/^[ \t]+|[ \t]+$/, "", $i)
  }

  # Determine environment (prod/test)
  env = "test"
  for (i = 1; i <= NF; i++) {
    if (tolower($i) ~ /prod/) { env = "prod"; break }
  }

  # Rebuild line excluding last column (unblended_cost)
  line = $1
  for (i = 2; i < NF; i++) line = line "," $i

  # Add environment column
  print line "," env
}' "$INPUT" > "$temp_clean"

# Sort numerically by first column
sort -t',' -k1,1n "$temp_clean" > "$OUTPUT"

echo "✅ Cleaned, environment-tagged CSV saved: $OUTPUT"

# ─────────────────────────────────────────────
# 2️⃣ GET ACCESS TOKEN SECURELY
# ─────────────────────────────────────────────
echo "🔑 Requesting Dynatrace access token..."

client_id="$(<"$ID_FILE")"
client_secret="$(<"$SECRET_FILE")"
resource="$(<"$RESOURCE_FILE")"

temp_body="$(mktemp)"
printf 'grant_type=client_credentials&client_id=%s&client_secret=%s&resource=%s'   "$(printf %s "$client_id" | sed 's/%/%25/g; s/&/%26/g; s/=/%3D/g; s/+/%2B/g; s/ /%20/g')"   "$(printf %s "$client_secret" | sed 's/%/%25/g; s/&/%26/g; s/=/%3D/g; s/+/%2B/g; s/ /%20/g')"   "$(printf %s "$resource" | sed 's/%/%25/g; s/&/%26/g; s/=/%3D/g; s/+/%2B/g; s/ /%20/g')"   > "$temp_body"

temp_token="$(mktemp)"
curl -sS --fail-with-body -X POST "$TOKEN_URL"   -H "Content-Type: application/x-www-form-urlencoded"   --data-binary @"$temp_body" > "$temp_token" || {
    echo "❌ Failed to retrieve token."; cat "$temp_token"; exit 1;
  }

access_token="$(sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p' "$temp_token")"
[[ -n "$access_token" ]] || { echo "❌ No token found in response."; cat "$temp_token"; exit 1; }

echo "✅ Token acquired."

# ─────────────────────────────────────────────
# 3️⃣ UPLOAD LOOKUP FILE TO DYNATRACE
# ─────────────────────────────────────────────
echo "📤 Uploading lookup table to Dynatrace..."

read -r -d '' request_json <<JSON
{
  "displayName": "${DISPLAY_NAME}",
  "description": "${DESCRIPTION}",
  "lookupField": "${LOOKUP_FIELD}",
  "parsePattern": "LD:account_id \,\" LD:account_name \,\" LD:owning_area \,\" LD:owning_cost_id \,\" LD:env",
  "overwrite": ${OVERWRITE}
}
JSON

curl -sS --fail-with-body -X POST "$UPLOAD_URL"   -H "Authorization: Bearer ${access_token}"   -H "User-Agent: dtscript/1.0"   -F "request=${request_json};type=application/json"   -F "content=@${OUTPUT};type=text/csv;filename=account.csv" || {
    echo "❌ Upload failed."; exit 1;
  }

echo "✅ Upload successful! File: $OUTPUT"
```

---

## 🧰 Folder structure

```
~/dtscript/
├── input.csv             ← raw exported CSV from Excel
├── account.csv           ← cleaned + sorted CSV created by script
├── run.sh                ← this script
└── secret/
    ├── client_id
    ├── client_secret
    └── resource
```

Each secret file contains **only the value**, e.g.:

```
# ~/dtscript/secret/client_id
dts002.J25WNYL
```

```
# ~/dtscript/secret/client_secret
dts002.J25WNYL.KFY6WQ...
```

```
# ~/dtscript/secret/resource
urn:dtaccount:59b6e616-f6d4-45d8-bda7-08c70647b8e3
```

---

## 🧪 Run it

```bash
chmod +x ~/dtscript/run.sh
~/dtscript/run.sh
```

It will:
1. 🧹 Clean `input.csv` → `account.csv`  
2. 🔑 Securely fetch a Dynatrace token  
3. 📤 Upload the lookup to:  
   `https://cqf94088.apps.dynatrace.com/platform/storage/resource-store/v1/files/tabular/lookup:upload`

---

## ✅ Summary

| Step | Action | Result |
|------|--------|---------|
| 1️⃣ | Cleans input.csv | Removes header, `(not set)` rows, last column, dehyphenates IDs, adds `prod/test`, sorts numerically |
| 2️⃣ | Gets OAuth2 token | Uses secrets securely from files |
| 3️⃣ | Uploads lookup | Sends the CSV to Dynatrace Resource Store |
