#!/bin/bash

# Simple deployment script - uses placeholder for target account
# Update TARGET_ACCOUNT_ID before running or pass as argument

set -e

# Configuration
FUNCTION_NAME="CloudWatchCrossAccountFetcher"
ROLE_NAME="CloudWatchLambdaExecutionRole"
POLICY_NAME="CrossAccountCloudWatchPolicy"
RUNTIME="python3.11"
HANDLER="lambda_function.lambda_handler"
TIMEOUT=60
MEMORY=256

# Accept target account as argument or use placeholder
TARGET_ACCOUNT_ID=${1:-"REPLACE_WITH_TARGET_ACCOUNT_ID"}
TARGET_REGION=${2:-"us-east-1"}

echo "========================================="
echo "CloudWatch Cross-Account Lambda Deployer"
echo "========================================="
echo ""

# Get current AWS account ID
echo "Getting AWS account information..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
REGION=${REGION:-us-east-1}

echo "✓ Source Account ID: ${ACCOUNT_ID}"
echo "✓ Region: ${REGION}"
echo "✓ Target Account ID: ${TARGET_ACCOUNT_ID}"
echo "✓ Target Region: ${TARGET_REGION}"
echo ""

if [ "$TARGET_ACCOUNT_ID" == "REPLACE_WITH_TARGET_ACCOUNT_ID" ]; then
    echo "⚠️  Please provide target account ID as first argument:"
    echo "   ./deploy_simple.sh <TARGET_ACCOUNT_ID> [TARGET_REGION]"
    echo ""
    echo "Example:"
    echo "   ./deploy_simple.sh 123456789012 us-east-1"
    exit 1
fi

TARGET_ROLE_ARN="arn:aws:iam::${TARGET_ACCOUNT_ID}:role/CrossAccountCloudWatchRole"

# Step 1: Create IAM Role for Lambda
echo "Creating IAM role for Lambda..."

if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "✓ IAM role already exists"
else
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://trust_policy.json \
        --description "Execution role for CloudWatch cross-account Lambda"
    
    echo "✓ Created IAM role: ${ROLE_NAME}"
    echo "Waiting for role to propagate..."
    sleep 10
fi

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# Step 2: Create and attach policy
echo "Creating and attaching IAM policy..."

# Check if policy exists
POLICY_EXISTS=$(aws iam list-policies --query "Policies[?PolicyName=='${POLICY_NAME}'].Arn" --output text)

if [ -n "$POLICY_EXISTS" ]; then
    POLICY_ARN=$POLICY_EXISTS
    echo "✓ Policy already exists: ${POLICY_NAME}"
else
    POLICY_ARN=$(aws iam create-policy \
        --policy-name $POLICY_NAME \
        --policy-document file://source_account_iam_policy.json \
        --description "Allows Lambda to assume role in target account" \
        --query Policy.Arn \
        --output text)
    echo "✓ Created policy: ${POLICY_NAME}"
fi

# Attach policy to role
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN 2>/dev/null || echo "✓ Policy already attached"

echo "Waiting for policy to propagate..."
sleep 5

# Step 3: Package Lambda function
echo "Packaging Lambda function..."

rm -rf package lambda_function.zip 2>/dev/null || true

mkdir -p package
pip install -r requirements.txt -t package/ --quiet
cp lambda_function.py package/

cd package
zip -r ../lambda_function.zip . -q
cd ..

echo "✓ Created deployment package"

# Step 4: Deploy Lambda function
echo "Deploying Lambda function..."

if aws lambda get-function --function-name $FUNCTION_NAME 2>/dev/null; then
    echo "Updating existing Lambda function..."
    
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_function.zip
    
    sleep 2
    
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --handler $HANDLER \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --environment Variables="{TARGET_ACCOUNT_ROLE_ARN=${TARGET_ROLE_ARN},TARGET_REGION=${TARGET_REGION}}"
    
    echo "✓ Updated Lambda function"
else
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler $HANDLER \
        --zip-file fileb://lambda_function.zip \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --environment Variables="{TARGET_ACCOUNT_ROLE_ARN=${TARGET_ROLE_ARN},TARGET_REGION=${TARGET_REGION}}" \
        --description "Fetches CloudWatch metrics from cross-account"
    
    echo "✓ Created Lambda function"
fi

# Clean up
rm -rf package

echo ""
echo "========================================="
echo "✓ Deployment Complete!"
echo "========================================="
echo ""
echo "Lambda Function: ${FUNCTION_NAME}"
echo "Region: ${REGION}"
echo "Role ARN: ${ROLE_ARN}"
echo ""
echo "Next: Configure target account (${TARGET_ACCOUNT_ID})"
echo "See target_account_setup.txt for instructions"
echo ""

# Generate target account setup file
cat > target_account_setup.txt << EOF
TARGET ACCOUNT SETUP INSTRUCTIONS
==================================

Target Account ID: ${TARGET_ACCOUNT_ID}
Source Account ID: ${ACCOUNT_ID}
Region: ${TARGET_REGION}

STEP 1: Create IAM Role
------------------------
Role Name: CrossAccountCloudWatchRole

STEP 2: Set Trust Policy
-------------------------
This allows the Lambda function in account ${ACCOUNT_ID} to assume this role.

aws iam create-role \\
  --role-name CrossAccountCloudWatchRole \\
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
      },
      "Action": "sts:AssumeRole"
    }]
  }'

STEP 3: Attach CloudWatch Permissions
--------------------------------------
This grants read access to CloudWatch metrics and logs.

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

STEP 4: Verify Setup
--------------------
aws iam get-role --role-name CrossAccountCloudWatchRole

Expected Role ARN: arn:aws:iam::${TARGET_ACCOUNT_ID}:role/CrossAccountCloudWatchRole

TESTING
-------
After target account is configured, test the Lambda:

aws lambda invoke \\
  --function-name ${FUNCTION_NAME} \\
  --payload file://test_event.json \\
  response.json

cat response.json
EOF

echo "Target account instructions saved to: target_account_setup.txt"


