#!/usr/bin/env bash
set -euo pipefail

AUTH_FILE="${HOME}/.dtoauth"
if [[ ! -f "$AUTH_FILE" ]]; then
  echo "ERROR: $AUTH_FILE not found"; exit 1
fi

# ~/.dtoauth format:
# 1: client_id
# 2: client_secret
# 3: resource (urn:dtaccount:..., or empty)
# 4: scope (space-separated; optional, e.g. "account-id:read openid profile")
client_id=$(sed -n '1p' "$AUTH_FILE" | tr -d '\r')
client_secret=$(sed -n '2p' "$AUTH_FILE" | tr -d '\r')
resource=$(sed -n '3p' "$AUTH_FILE" | tr -d '\r')
scope=$(sed -n '4p' "$AUTH_FILE" | tr -d '\r' || true)

TOKEN_URL="https://sso.dynatrace.com/sso/oauth2/token"

call_oauth () {
  echo "---- TRY: $1 ----"
  shift
  # -sS: silent but show errors, --fail: non-2xx => exit nonzero, -L follow redirects
  resp=$(curl -sS --fail -L --request POST "$TOKEN_URL" \
    --header "content-type: application/x-www-form-urlencoded" \
    "$@") || { echo "HTTP error. Response:"; echo "${resp:-<none>}"; return 1; }

  # Parse access_token (prefer jq if available)
  if command -v jq >/dev/null; then
    token=$(echo "$resp" | jq -r '.access_token // empty')
    exp=$(echo "$resp" | jq -r '.expires_in // empty')
  else
    token=$(echo "$resp" | sed -n 's/.*"access_token":"\([^"]*\)".*/\1/p')
    exp=$(echo "$resp" | sed -n 's/.*"expires_in":\([0-9]*\).*/\1/p')
  fi

  if [[ -n "$token" ]]; then
    echo "token: $token"
    [[ -n "$exp" ]] && echo "expires_in: ${exp}s"
    echo "export DT_ACCESS_TOKEN='$token'"
    return 0
  else
    echo "No access_token in response:"
    echo "$resp"
    return 1
  fi
}

# Build URL-encoded form pieces
base_fields=(
  --data-urlencode "grant_type=client_credentials"
  --data-urlencode "client_id=${client_id}"
  --data-urlencode "client_secret=${client_secret}"
)

with_resource=("${base_fields[@]}" --data-urlencode "resource=${resource}")
with_scope=("${base_fields[@]}" --data-urlencode "scope=${scope}")
with_both=("${base_fields[@]}" --data-urlencode "resource=${resource}" --data-urlencode "scope=${scope}")

# Try order:
# 1) both resource + scope (if both provided)
# 2) scope only (common requirement)
# 3) resource only (some older flows)
# 4) base only (last resort)
tried=0
if [[ -n "${resource}" && -n "${scope}" ]]; then call_oauth "resource+scope" "${with_both[@]}" && exit 0; tried=1; fi
if [[ -n "${scope}" ]];   then call_oauth "scope-only"    "${with_scope[@]}" && exit 0; tried=1; fi
if [[ -n "${resource}" ]]; then call_oauth "resource-only" "${with_resource[@]}" && exit 0; tried=1; fi
call_oauth "no-resource-no-scope" "${base_fields[@]}" && exit 0

echo "All attempts failed. Please check that:
- The OAuth client exists in Dynatrace SSO and has the scopes you are requesting.
- If your tenant requires a resource (urn:dtaccount:…), use the correct Account UUID.
- Your client_secret is correct (watch for line breaks or hidden characters)."
exit 2
