#!/usr/bin/env bash
set -e

AUTH_FILE="${HOME}/.dtoauth"
client_id=$(sed -n '1p' "$AUTH_FILE" | tr -d '\r')
client_secret=$(sed -n '2p' "$AUTH_FILE" | tr -d '\r')
resource=$(sed -n '3p' "$AUTH_FILE" | tr -d '\r')

TOKEN_URL="https://sso.dynatrace.com/sso/oauth2/token"

echo "DEBUG: client_id=$client_id"
echo "DEBUG: resource=$resource"

curl -v --request POST "$TOKEN_URL" \
  --header "content-type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=client_credentials" \
  --data-urlencode "client_id=${client_id}" \
  --data-urlencode "client_secret=${client_secret}" \
  --data-urlencode "resource=${resource}"
