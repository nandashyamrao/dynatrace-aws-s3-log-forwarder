#!/usr/bin/env bash
set -euo pipefail

# Read ~/.dtoauth (3 lines) and strip any Windows CRLFs
AUTH_FILE="${HOME}/.dtoauth"
if [[ ! -f "$AUTH_FILE" ]]; then
  echo "ERROR: $AUTH_FILE not found." >&2
  exit 1
fi

client_id=$(sed -n '1p' "$AUTH_FILE" | tr -d '\r')
client_secret=$(sed -n '2p' "$AUTH_FILE" | tr -d '\r')
resource=$(sed -n '3p' "$AUTH_FILE" | tr -d '\r')

# Dynatrace OAuth token endpoint
TOKEN_URL="https://sso.dynatrace.com/sso/oauth2/token"

# Call OAuth (use urlencoding to avoid issues with special chars)
resp=$(
  curl -sS --fail --request POST "$TOKEN_URL" \
    --header "content-type: application/x-www-form-urlencoded" \
    --data "grant_type=client_credentials" \
    --data-urlencode "client_id=${client_id}" \
    --data-urlencode "client_secret=${client_secret}" \
    --data-urlencode "resource=${resource}"
)

# Prefer jq if available; fall back to a simple parser
if command -v jq >/dev/null 2>&1; then
  access_token=$(echo "$resp" | jq -r '.access_token')
  expires_in=$(echo "$resp" | jq -r '.expires_in')
else
  access_token=$(echo "$resp" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
  expires_in=$(echo "$resp" | sed -n 's/.*"expires_in":\([0-9]*\).*/\1/p')
fi

if [[ -z "${access_token:-}" ]]; then
  echo "ERROR: Could not extract access_token. Raw response:" >&2
  echo "$resp" >&2
  exit 1
fi

# Print helpful outputs
echo "token: ${access_token}"
[[ -n "${expires_in:-}" ]] && echo "expires_in: ${expires_in}s"

# If you run:  ./dt_token.sh --export
if [[ "${1:-}" == "--export" ]]; then
  echo ""
  echo "export DT_ACCESS_TOKEN='${access_token}'"
fi
