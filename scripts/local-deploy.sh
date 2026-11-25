#!/usr/bin/env bash
# Build the image, start a 3-node kind cluster and deploy the chart locally.
set -euo pipefail

CLUSTER=lab
TAG=local-$(git rev-parse --short HEAD 2>/dev/null || echo dev)

kind get clusters | grep -qx "$CLUSTER" || kind create cluster --name "$CLUSTER" --config cluster/kind-config.yaml

docker build --build-arg APP_VERSION="$TAG" -t status-api:"$TAG" .
kind load docker-image status-api:"$TAG" --name "$CLUSTER"

helm upgrade --install status-api helm/status-api \
  --namespace status-api --create-namespace \
  --set image.repository=status-api --set image.tag="$TAG" \
  --atomic --wait --timeout 3m

kubectl -n status-api get deploy,pods,svc
echo "Try: kubectl -n status-api port-forward svc/status-api-status-api 8081:80 && curl localhost:8081"
