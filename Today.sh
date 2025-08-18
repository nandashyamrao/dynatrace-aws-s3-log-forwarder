#!/usr/bin/env bash
set -euo pipefail

# ===== Config =====
# Dynatrace environment base URL (no trailing slash), e.g.:
#   export DT_ENV_URL="https://cf94088.apps.dynatrace.com"
: "${DT_ENV_URL:?Please export DT_ENV_URL (e.g., https://<tenant>.apps.dynatrace.com)}"

# API token file or env var:
TOKEN_FILE="${HOME}/.dynatracetoken"
API_TOKEN="${API_TOKEN:-$( [ -f "$TOKEN_FILE" ] && tr -d '\r\n' < "$TOKEN_FILE" || true )}"
: "${API_TOKEN:?Set API_TOKEN env var or put token in ${TOKEN_FILE}}"

CSV="dashboards.csv"            # CSV with headers: id,name,owner
OUT_DIR="dashboards_json"       # where JSON files will be written
mkdir -p "$OUT_DIR"

need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing: $1"; exit 1; }; }
need curl
need awk

echo "Reading IDs from: $CSV"
# Read CSV, skip header; first column must be 'id'
# Handles commas in name/owner by only extracting the first column via awk CSV mode
awk -v FS=',' '
  NR==1 { next }          # skip header
  {
    id=$1; gsub(/^[[:space:]]+|[[:space:]]+$/, "", id);
    if (id!="") print id;
  }
' "$CSV" | while IFS= read -r id; do
  echo "Downloading dashboard ${id}..."
  url="${DT_ENV_URL}/api/config/v1/dashboards/${id}"
  out="${OUT_DIR}/${id}.json"
  http_code=$(curl -sS -w "%{http_code}" -o "$out" \
    -H "accept: application/json; charset=utf-8" \
    -H "Authorization: Api-Token ${API_TOKEN}" \
    "$url")
  if [ "$http_code" != "200" ]; then
    echo "  ✗ HTTP $http_code → ${url}"
  else
    echo "  ✓ saved ${out}"
  fi
done

echo "Done. JSON files in: ${OUT_DIR}"
