#!/usr/bin/env zsh
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <environment_name>"
  exit 1
fi

ENV_NAME=$1
echo "Deploying environment: $ENV_NAME"

cd deploy/aws
npm install -g aws-cdk
pip install -r requirements.txt
cdk deploy TtbLabelComplianceStack-${ENV_NAME} -c env_name=${ENV_NAME} --require-approval never
echo "Deployment of $ENV_NAME complete."
