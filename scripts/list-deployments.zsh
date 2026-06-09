#!/usr/bin/env zsh
# Lists all active TtbLabelCompliance CDK deployments and their app URLs.

set -e

echo "Fetching active deployments from AWS CloudFormation..."
echo "--------------------------------------------------------"

# We query AWS CloudFormation for stacks matching our prefix that are not deleted.
# We extract the StackName, Status, FrontendWebsiteUrl, and ApiGatewayUrl.
aws cloudformation describe-stacks \
    --query 'Stacks[?starts_with(StackName, `TtbLabelComplianceStack-`) && StackStatus != `DELETE_COMPLETE`].{
        Environment: StackName,
        Status: StackStatus,
        FrontendURL: Outputs[?OutputKey==`FrontendWebsiteUrl`].OutputValue | [0],
        ApiGatewayURL: Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue | [0]
    }' \
    --output table

echo "--------------------------------------------------------"
