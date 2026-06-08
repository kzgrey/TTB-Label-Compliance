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
python3 -m pip install -r requirements.txt

# Deploy the infrastructure and save the outputs to a JSON file
cdk deploy TtbLabelComplianceStack-${ENV_NAME} -c env_name=${ENV_NAME} --require-approval never --outputs-file cdk-outputs.json

echo "Extracting outputs for Frontend Deployment..."
# Parse the JSON outputs using Python
ALB_DNS=$(python3 -c "import json; d=json.load(open('cdk-outputs.json')); print(list(d.values())[0]['AlbDnsName'])")
FRONTEND_BUCKET=$(python3 -c "import json; d=json.load(open('cdk-outputs.json')); print(list(d.values())[0]['FrontendBucketName'])")
FRONTEND_URL=$(python3 -c "import json; d=json.load(open('cdk-outputs.json')); print(list(d.values())[0]['FrontendWebsiteUrl'])")

echo "Backend API URL: http://$ALB_DNS"
echo "Frontend S3 Bucket: $FRONTEND_BUCKET"

echo "Building Frontend..."
cd ../../src/frontend
npm install
# Build the frontend with the deployed backend URL injected
VITE_API_URL=http://$ALB_DNS npm run build

echo "Deploying Frontend to S3..."
aws s3 sync dist s3://$FRONTEND_BUCKET --delete

echo "======================================================"
echo "Deployment of $ENV_NAME complete."
echo "Frontend is live at: $FRONTEND_URL"
echo "======================================================"
