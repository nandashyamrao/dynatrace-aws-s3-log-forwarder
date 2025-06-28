#!/bin/bash
set -e

# 👇 Configuration
CERT_FILE=~/sfcacerts/cacerts.crt
SECRETS=(/run/secrets/JFROG_USER /run/secrets/JFROG_TOKEN /run/secrets/JFROG_TEMP_IDENTITY_TOKEN)
JFROG_REPO_URL="https://packages.icl.statefarm"
YUM_MIRROR_URL="https://mirror.centos.org"  # Fallback repo

echo "🔍 Validating build prerequisites..."

# 1️⃣ Check CA Certificate
if [ ! -f "$CERT_FILE" ]; then
  echo "❌ CA cert not found at $CERT_FILE"
  exit 1
else
  echo "✅ CA certificate found at $CERT_FILE"
fi

# 2️⃣ Check for mounted secrets
for secret in "${SECRETS[@]}"; do
  if [ ! -f "$secret" ]; then
    echo "❌ Secret not found: $secret"
    exit 1
  fi
done
echo "✅ All required secrets are present."

# 3️⃣ Check JFrog repo reachability
echo -n "🌐 Checking access to JFrog repo: $JFROG_REPO_URL ... "
if curl -s --cacert "$CERT_FILE" --connect-timeout 5 "$JFROG_REPO_URL" >/dev/null; then
  echo "✅ reachable."
else
  echo "❌ Unreachable. Check network or certs."
  exit 1
fi

# 4️⃣ Optional: Validate fallback yum mirror
echo -n "🛰️  Checking fallback yum mirror: $YUM_MIRROR_URL ... "
if curl -s --connect-timeout 5 "$YUM_MIRROR_URL" >/dev/null; then
  echo "✅ mirror available."
else
  echo "⚠️  Mirror not available. This might affect fallback behavior."
fi

echo "🎯 All checks passed. Proceeding to build..."
exec ./build.sh "$@"
