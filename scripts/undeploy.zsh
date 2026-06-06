#!/usr/bin/env zsh
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <environment_name>"
  exit 1
fi

ENV_NAME=$1
echo "Undeploying environment: $ENV_NAME"

# Empty the S3 bucket first to avoid CloudFormation failure
# We need to find the bucket name
BUCKET_NAME=$(aws cloudformation describe-stacks --stack-name TtbLabelComplianceStack-${ENV_NAME} --query 'Stacks[0].Outputs[?OutputKey==`JobsBucketName`].OutputValue' --output text 2>/dev/null || echo "")

if [ -n "$BUCKET_NAME" ] && [ "$BUCKET_NAME" != "None" ]; then
  echo "Emptying bucket $BUCKET_NAME..."
  aws s3 rm s3://${BUCKET_NAME} --recursive || true
fi

cd deploy/aws
cdk destroy TtbLabelComplianceStack-${ENV_NAME} -c env_name=${ENV_NAME} --force
echo "Undeployment of $ENV_NAME complete."
