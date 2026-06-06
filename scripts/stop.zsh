#!/usr/bin/env zsh
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <environment_name>"
  exit 1
fi

ENV_NAME=$1
echo "Stopping environment: $ENV_NAME"

CLUSTER_NAME=$(aws ecs list-clusters --query "clusterArns[?contains(@, 'Cluster${ENV_NAME}')]" --output text)
if [ -z "$CLUSTER_NAME" ] || [ "$CLUSTER_NAME" = "None" ]; then
  echo "Cluster for $ENV_NAME not found."
  exit 1
fi

API_SERVICE=$(aws ecs list-services --cluster $CLUSTER_NAME --query "serviceArns[?contains(@, 'ApiService')]" --output text)
WORKER_SERVICE=$(aws ecs list-services --cluster $CLUSTER_NAME --query "serviceArns[?contains(@, 'WorkerService')]" --output text)

if [ -n "$API_SERVICE" ]; then
  aws ecs update-service --cluster $CLUSTER_NAME --service $API_SERVICE --desired-count 0 > /dev/null
  echo "Stopped API service"
fi

if [ -n "$WORKER_SERVICE" ]; then
  aws ecs update-service --cluster $CLUSTER_NAME --service $WORKER_SERVICE --desired-count 0 > /dev/null
  echo "Stopped Worker service"
fi

echo "Environment $ENV_NAME stopped."
