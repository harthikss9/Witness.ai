#!/bin/bash

# CloudFormation deployment script for SOURCE account

set -e

echo "=========================================="
echo "CloudWatch Cross-Account Lambda Deployer"
echo "Using CloudFormation"
echo "=========================================="
echo ""

# Get current account info
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
CURRENT_REGION=$(aws configure get region)
CURRENT_REGION=${CURRENT_REGION:-us-west-1}

echo "Current Account: ${CURRENT_ACCOUNT}"
echo "Current Region: ${CURRENT_REGION}"
echo ""

# Prompt for target account info
echo "Target Account Configuration:"
read -p "Enter Target Account ID (where CloudWatch data lives): " TARGET_ACCOUNT_ID
read -p "Enter Target Region [us-east-1]: " TARGET_REGION
TARGET_REGION=${TARGET_REGION:-us-east-1}

if [ -z "$TARGET_ACCOUNT_ID" ]; then
    echo "❌ Target Account ID is required!"
    exit 1
fi

echo ""
echo "Configuration Summary:"
echo "  Source Account: ${CURRENT_ACCOUNT} (${CURRENT_REGION})"
echo "  Target Account: ${TARGET_ACCOUNT_ID} (${TARGET_REGION})"
echo ""
read -p "Proceed with deployment? (y/n): " CONFIRM

if [ "$CONFIRM" != "y" ]; then
    echo "Deployment cancelled"
    exit 0
fi

STACK_NAME="cloudwatch-cross-account-source"

echo ""
echo "→ Creating CloudFormation stack..."

aws cloudformation create-stack \
  --stack-name $STACK_NAME \
  --template-body file://cloudformation_source_account.yaml \
  --parameters \
    ParameterKey=TargetAccountId,ParameterValue=$TARGET_ACCOUNT_ID \
    ParameterKey=TargetRegion,ParameterValue=$TARGET_REGION \
  --capabilities CAPABILITY_NAMED_IAM

echo "✓ Stack creation initiated"
echo ""
echo "→ Waiting for stack to complete (this may take 2-3 minutes)..."

aws cloudformation wait stack-create-complete --stack-name $STACK_NAME

echo "✓ Stack created successfully!"
echo ""

# Get outputs
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""

LAMBDA_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionArn`].OutputValue' \
  --output text)

ROLE_ARN=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaExecutionRoleArn`].OutputValue' \
  --output text)

TARGET_ROLE=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --query 'Stacks[0].Outputs[?OutputKey==`TargetAccountRoleArn`].OutputValue' \
  --output text)

echo "Lambda Function ARN:"
echo "  $LAMBDA_ARN"
echo ""
echo "Lambda Execution Role ARN:"
echo "  $ROLE_ARN"
echo ""
echo "Expected Target Role ARN:"
echo "  $TARGET_ROLE"
echo ""

# Save target account instructions
cat > target_account_setup_cf.txt << EOF
========================================
TARGET ACCOUNT SETUP INSTRUCTIONS
========================================

Target Account ID: ${TARGET_ACCOUNT_ID}
Source Account ID: ${CURRENT_ACCOUNT}

OPTION 1: Using CloudFormation (Recommended)
---------------------------------------------

1. Log into AWS account ${TARGET_ACCOUNT_ID}

2. Deploy the CloudFormation stack:

aws cloudformation create-stack \\
  --stack-name cloudwatch-cross-account-target \\
  --template-body file://cloudformation_target_account.yaml \\
  --parameters \\
    ParameterKey=SourceAccountId,ParameterValue=${CURRENT_ACCOUNT} \\
    ParameterKey=SourceLambdaRoleName,ParameterValue=CloudWatchLambdaExecutionRole \\
  --capabilities CAPABILITY_NAMED_IAM

3. Wait for completion:

aws cloudformation wait stack-create-complete \\
  --stack-name cloudwatch-cross-account-target


OPTION 2: Manual IAM Setup
---------------------------

1. Create IAM role:

aws iam create-role \\
  --role-name CrossAccountCloudWatchRole \\
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "AWS": "${ROLE_ARN}"
      },
      "Action": "sts:AssumeRole"
    }]
  }'

2. Attach CloudWatch permissions:

aws iam put-role-policy \\
  --role-name CrossAccountCloudWatchRole \\
  --policy-name CloudWatchReadAccess \\
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:ListMetrics",
          "cloudwatch:GetMetricData",
          "cloudwatch:DescribeAlarms"
        ],
        "Resource": "*"
      },
      {
        "Effect": "Allow",
        "Action": [
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:GetLogEvents",
          "logs:FilterLogEvents"
        ],
        "Resource": "*"
      }
    ]
  }'


TESTING
-------

After target account is configured, test from source account (${CURRENT_ACCOUNT}):

aws lambda invoke \\
  --function-name CloudWatchCrossAccountFetcher \\
  --payload file://test_event.json \\
  response.json

cat response.json
EOF

echo "=========================================="
echo "NEXT STEPS"
echo "=========================================="
echo ""
echo "1. Configure the TARGET account (${TARGET_ACCOUNT_ID})"
echo "   See: target_account_setup_cf.txt"
echo ""
echo "2. Test the Lambda function:"
echo "   aws lambda invoke \\"
echo "     --function-name CloudWatchCrossAccountFetcher \\"
echo "     --payload file://test_event.json \\"
echo "     response.json"
echo ""
echo "Target account setup instructions saved to:"
echo "  target_account_setup_cf.txt"
echo ""


