#!/bin/bash
# One-command deployment for admin user in TARGET account (993260645905)
# Source account: 190460190639

set -e

echo "================================================"
echo "CloudWatch Cross-Account Lambda - Target Setup"
echo "================================================"
echo ""
echo "Target Account: 993260645905"
echo "Source Account: 190460190639"
echo ""

# Check AWS credentials
echo "Verifying AWS credentials..."
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

if [ "$CURRENT_ACCOUNT" != "993260645905" ]; then
    echo "❌ ERROR: Wrong AWS account!"
    echo "   Current: $CURRENT_ACCOUNT"
    echo "   Expected: 993260645905"
    echo ""
    echo "Please configure AWS CLI for account 993260645905"
    exit 1
fi

echo "✓ AWS account verified: $CURRENT_ACCOUNT"
echo ""

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-target \
  --template-body file://cloudformation_target_account.yaml \
  --parameters \
    ParameterKey=SourceAccountId,ParameterValue=190460190639 \
    ParameterKey=SourceLambdaRoleName,ParameterValue=CloudWatchLambdaExecutionRole \
  --capabilities CAPABILITY_NAMED_IAM

echo "✓ Stack creation initiated"
echo ""
echo "Waiting for stack to complete..."

aws cloudformation wait stack-create-complete \
  --stack-name cloudwatch-cross-account-target

echo "✓ Stack created successfully!"
echo ""

# Get outputs
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""

ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name cloudwatch-cross-account-target \
  --query 'Stacks[0].Outputs[?OutputKey==`CrossAccountRoleArn`].OutputValue' \
  --output text)

echo "Cross-Account Role ARN:"
echo "  $ROLE_ARN"
echo ""

echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""
echo "The source account (190460190639) Lambda function can now"
echo "access CloudWatch data in this account (993260645905)."
echo ""
echo "To test from source account:"
echo "  aws lambda invoke \\"
echo "    --function-name CloudWatchCrossAccountFetcher \\"
echo "    --payload file://test_event.json \\"
echo "    response.json"
echo ""


