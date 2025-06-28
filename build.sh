#!/bin/bash
set -e

# ================================
# CONFIGURATION
# ================================
export IMAGE_NAME="sf-dt-s3-lambda-fwd"
export GITLAB_REGISTRY="registry.sfgitlab.opr.statefarm.org"
export GITLAB_USER="yrht"  # Update if needed
export GITLAB_TOKEN_FILE="$HOME/.gitlab-token"
export JFROG_REGISTRY="packages.ic1.statefarm"
export JFROG_USER="yrht"  # Update if needed
export JFROG_TOKEN_FILE="$HOME/.jfrog-token"
export DOCKER_SECRET_PATH="$HOME/docker/secrets"
export DATACENTER="aws"

# ================================
# GitLab Docker Registry Login
# ================================
if [[ -f "$GITLAB_TOKEN_FILE" ]]; then
  echo "[INFO] Logging in to GitLab registry..."
  LOGIN_OUTPUT=$(cat "$GITLAB_TOKEN_FILE" | docker login "$GITLAB_REGISTRY" -u "$GITLAB_USER" --password-stdin 2>&1)
  if [[ $? -eq 0 ]]; then
    echo "[SUCCESS] GitLab Docker login succeeded."
  else
    echo "[ERROR] GitLab Docker login failed: $LOGIN_OUTPUT"
  fi
else
  echo "[ERROR] GitLab token file not found at $GITLAB_TOKEN_FILE"
fi

# ================================
# JFrog Docker Registry Login
# ================================
if [[ -f "$JFROG_TOKEN_FILE" ]]; then
  echo "[INFO] Logging in to JFrog registry..."
  LOGIN_OUTPUT=$(cat "$JFROG_TOKEN_FILE" | docker login "$JFROG_REGISTRY" -u "$JFROG_USER" --password-stdin 2>&1)
  if [[ $? -eq 0 ]]; then
    echo "[SUCCESS] JFrog Docker login succeeded."
  else
    echo "[ERROR] JFrog Docker login failed: $LOGIN_OUTPUT"
  fi
else
  echo "[ERROR] JFrog token file not found at $JFROG_TOKEN_FILE"
fi

# ================================
# Handle Proxy Detection (Optional)
# ================================
if [[ "${HTTP_PROXY}" =~ "127.0.0" ]] || [[ "${HTTP_PROXY}" =~ "localhost" ]]; then
  echo "[INFO] Proxy set to localhost; skipping."
  unset HTTP_PROXY
else
  echo "${HTTP_PROXY}" > proxy.txt
fi

# ================================
# Build Docker Image with Secrets
# ================================
echo "[INFO] Building Docker image '${IMAGE_NAME}' using BuildKit..."
DOCKER_BUILDKIT=1 docker build \
  --secret id=pip_conf,env=PIP_CONF \
  --secret id=apt_auth_conf,env=APT_AUTH_CONF \
  --secret id=http_proxy,src=proxy.txt \
  --secret id=JFROG_USER,src=${DOCKER_SECRET_PATH}/JFROG_USER \
  --secret id=JFROG_TOKEN,src=${DOCKER_SECRET_PATH}/JFROG_TOKEN \
  --build-arg DATACENTER=${DATACENTER} \
  --progress plain \
  -t ${IMAGE_NAME} \
  -f Dockerfile .

rm -f proxy.txt
