#!/usr/bin/env bash

# ================================
# build.sh - Docker image builder with proxy + secret support
# ================================

# Detect local proxy/zscaler and prevent it from interfering with pip
if [[ "${HTTP_PROXY}" =~ "127.0.0.1" ]] || [[ "${HTTP_PROXY}" =~ "localhost" ]]; then
  echo "Unsetting proxy, localhost detected"
  unset HTTP_PROXY
  unset http_proxy
  touch proxy.txt
else
  echo "${HTTP_PROXY}" > proxy.txt
fi

DOCKER_BUILDKIT=1 docker build \
  --secret id=pip_conf,env=PIP_CONF \
  --secret id=apt_auth_conf,env=APT_AUTH_CONF \
  --secret id=http_proxy,src=proxy.txt \
  --secret id=jfrog_token,env=JFROG_TOKEN \
  --secret id=jfrog_user,env=JFROG_USER \
  --build-arg DATACENTER=${DATACENTER} \
  --progress plain \
  -f Dockerfile.lambda.s3.forwarder \
  "$@"

rm -f proxy.txt
