#!/bin/bash
# One-command deployment for admin user in SOURCE account (190460190639)
# Target account: 993260645905

set -e

echo "================================================"
echo "CloudWatch Cross-Account Lambda - Source Setup"
echo "================================================"
echo ""
echo "Source Account: 190460190639"
echo "Target Account: 993260645905"
echo "Target Region: us-east-1"
echo ""

# Check AWS credentials
echo "Verifying AWS credentials..."
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

if [ "$CURRENT_ACCOUNT" != "190460190639" ]; then
    echo "❌ ERROR: Wrong AWS account!"
    echo "   Current: $CURRENT_ACCOUNT"
    echo "   Expected: 190460190639"
    echo ""
    echo "Please configure AWS CLI for account 190460190639"
    exit 1
fi

echo "✓ AWS account verified: $CURRENT_ACCOUNT"
echo ""

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-source \
  --template-body file://cloudformation_source_account.yaml \
  --parameters \
    ParameterKey=TargetAccountId,ParameterValue=993260645905 \
    ParameterKey=TargetRegion,ParameterValue=us-east-1 \
  --capabilities CAPABILITY_NAMED_IAM

echo "✓ Stack creation initiated"
echo ""
echo "Waiting for stack to complete (2-3 minutes)..."

aws cloudformation wait stack-create-complete \
  --stack-name cloudwatch-cross-account-source

echo "✓ Stack created successfully!"
echo ""

# Get outputs
echo "================================================"
echo "Deployment Complete!"
echo "================================================"
echo ""

LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name cloudwatch-cross-account-source \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionArn`].OutputValue' \
  --output text)

ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name cloudwatch-cross-account-source \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaExecutionRoleArn`].OutputValue' \
  --output text)

echo "Lambda Function ARN:"
echo "  $LAMBDA_ARN"
echo ""
echo "Lambda Execution Role ARN:"
echo "  $ROLE_ARN"
echo ""

echo "================================================"
echo "NEXT STEP: Configure Target Account"
echo "================================================"
echo ""
echo "An admin in target account 993260645905 needs to run:"
echo ""
echo "  aws cloudformation create-stack \\"
echo "    --stack-name cloudwatch-cross-account-target \\"
echo "    --template-body file://cloudformation_target_account.yaml \\"
echo "    --parameters \\"
echo "      ParameterKey=SourceAccountId,ParameterValue=190460190639 \\"
echo "      ParameterKey=SourceLambdaRoleName,ParameterValue=CloudWatchLambdaExecutionRole \\"
echo "    --capabilities CAPABILITY_NAMED_IAM"
echo ""
echo "See target_account_instructions.txt for details"
echo ""


