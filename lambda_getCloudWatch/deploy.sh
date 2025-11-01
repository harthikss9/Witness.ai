#!/bin/bash

# Deployment script for CloudWatch Cross-Account Lambda Function
# This script creates the Lambda function and IAM role in the SOURCE account

set -e

# Configuration
FUNCTION_NAME="CloudWatchCrossAccountFetcher"
ROLE_NAME="CloudWatchLambdaExecutionRole"
POLICY_NAME="CrossAccountCloudWatchPolicy"
RUNTIME="python3.11"
HANDLER="lambda_function.lambda_handler"
TIMEOUT=60
MEMORY=256

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CloudWatch Cross-Account Lambda Deployer${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Get current AWS account ID
echo -e "${YELLOW}→ Getting AWS account information...${NC}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region)
REGION=${REGION:-us-east-1}

echo -e "${GREEN}✓ Source Account ID: ${ACCOUNT_ID}${NC}"
echo -e "${GREEN}✓ Region: ${REGION}${NC}\n"

# Prompt for target account configuration
echo -e "${YELLOW}→ Target account configuration:${NC}"
read -p "Enter TARGET AWS Account ID (where CloudWatch data lives): " TARGET_ACCOUNT_ID
read -p "Enter TARGET AWS Region [us-east-1]: " TARGET_REGION
TARGET_REGION=${TARGET_REGION:-us-east-1}

if [ -z "$TARGET_ACCOUNT_ID" ]; then
    echo -e "${YELLOW}⚠ Target Account ID is required!${NC}"
    exit 1
fi

TARGET_ROLE_ARN="arn:aws:iam::${TARGET_ACCOUNT_ID}:role/CrossAccountCloudWatchRole"

echo -e "${GREEN}✓ Target Role ARN: ${TARGET_ROLE_ARN}${NC}\n"

# Step 1: Create IAM Role for Lambda
echo -e "${YELLOW}→ Creating IAM role for Lambda...${NC}"

if aws iam get-role --role-name $ROLE_NAME &>/dev/null; then
    echo -e "${GREEN}✓ IAM role already exists${NC}"
else
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file://trust_policy.json \
        --description "Execution role for CloudWatch cross-account Lambda" \
        --output text &>/dev/null
    
    echo -e "${GREEN}✓ Created IAM role: ${ROLE_NAME}${NC}"
    
    # Wait for role to be created
    echo -e "${YELLOW}→ Waiting for role to be available...${NC}"
    sleep 10
fi

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# Step 2: Attach custom policy to role
echo -e "${YELLOW}→ Attaching cross-account policy...${NC}"

# Delete existing policy if it exists
if aws iam get-policy --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" &>/dev/null; then
    echo -e "${YELLOW}→ Detaching existing policy...${NC}"
    aws iam detach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" &>/dev/null || true
    
    # Delete all policy versions except default
    VERSIONS=$(aws iam list-policy-versions \
        --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" \
        --query 'Versions[?!IsDefaultVersion].VersionId' \
        --output text)
    
    for VERSION in $VERSIONS; do
        aws iam delete-policy-version \
            --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" \
            --version-id $VERSION &>/dev/null || true
    done
    
    aws iam delete-policy \
        --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}" &>/dev/null || true
    
    sleep 2
fi

POLICY_ARN=$(aws iam create-policy \
    --policy-name $POLICY_NAME \
    --policy-document file://source_account_iam_policy.json \
    --description "Allows Lambda to assume role in target account for CloudWatch access" \
    --query Policy.Arn \
    --output text)

aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn $POLICY_ARN

echo -e "${GREEN}✓ Attached policy: ${POLICY_NAME}${NC}"

# Wait for policy to propagate
sleep 5

# Step 3: Package Lambda function
echo -e "${YELLOW}→ Packaging Lambda function...${NC}"

# Clean up old package
rm -rf package lambda_function.zip

# Install dependencies
pip install -r requirements.txt -t package/ --quiet

# Copy lambda function
cp lambda_function.py package/

# Create zip file
cd package
zip -r ../lambda_function.zip . -q
cd ..

echo -e "${GREEN}✓ Created deployment package${NC}"

# Step 4: Create or Update Lambda function
echo -e "${YELLOW}→ Deploying Lambda function...${NC}"

if aws lambda get-function --function-name $FUNCTION_NAME &>/dev/null; then
    echo -e "${YELLOW}→ Updating existing Lambda function...${NC}"
    
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda_function.zip \
        --output text &>/dev/null
    
    sleep 2
    
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --handler $HANDLER \
        --timeout $TIMEOUT \
        --memory-size $MEMORY \
        --environment Variables="{TARGET_ACCOUNT_ROLE_ARN=${TARGET_ROLE_ARN},TARGET_REGION=${TARGET_REGION}}" \
        --output text &>/dev/null
    
    echo -e "${GREEN}✓ Updated Lambda function${NC}"
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
        --description "Fetches CloudWatch metrics from cross-account" \
        --output text &>/dev/null
    
    echo -e "${GREEN}✓ Created Lambda function${NC}"
fi

# Clean up
rm -rf package

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "${BLUE}Lambda Function Details:${NC}"
echo -e "  Name: ${FUNCTION_NAME}"
echo -e "  ARN: arn:aws:lambda:${REGION}:${ACCOUNT_ID}:function:${FUNCTION_NAME}"
echo -e "  Role: ${ROLE_ARN}"
echo -e "  Region: ${REGION}\n"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}NEXT STEPS - TARGET ACCOUNT SETUP${NC}"
echo -e "${YELLOW}========================================${NC}\n"

echo -e "${BLUE}You need to configure the TARGET account (${TARGET_ACCOUNT_ID}) with the following:${NC}\n"

echo -e "${YELLOW}1. Create IAM Role in Target Account:${NC}"
echo -e "   Role Name: CrossAccountCloudWatchRole\n"

echo -e "${YELLOW}2. Trust Policy (allow source account to assume role):${NC}"
cat << EOF

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}

EOF

echo -e "${YELLOW}3. Permissions Policy (CloudWatch read access):${NC}"
cat << 'EOF'

{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:GetMetricData",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:DescribeAlarmsForMetric"
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
}

EOF

echo -e "${YELLOW}4. AWS CLI Commands for Target Account:${NC}"
echo -e ""
echo -e "Save the trust policy to 'target_trust_policy.json' and run:"
echo -e "  ${BLUE}aws iam create-role --role-name CrossAccountCloudWatchRole --assume-role-policy-document file://target_trust_policy.json${NC}\n"
echo -e "Save the permissions policy to 'target_permissions.json' and run:"
echo -e "  ${BLUE}aws iam put-role-policy --role-name CrossAccountCloudWatchRole --policy-name CloudWatchReadAccess --policy-document file://target_permissions.json${NC}\n"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Testing${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo -e "Once target account is configured, test with:"
echo -e "  ${BLUE}aws lambda invoke --function-name ${FUNCTION_NAME} --payload file://test_event.json response.json${NC}\n"

echo -e "${YELLOW}Note: Target account setup file saved to: target_account_setup.txt${NC}\n"

# Save target account instructions to file
cat > target_account_setup.txt << EOF
TARGET ACCOUNT SETUP INSTRUCTIONS
==================================

Account ID: ${TARGET_ACCOUNT_ID}
Region: ${TARGET_REGION}

Step 1: Create IAM Role
------------------------
Role Name: CrossAccountCloudWatchRole

Step 2: Trust Policy
--------------------
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}

Step 3: Permissions Policy
---------------------------
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricStatistics",
        "cloudwatch:ListMetrics",
        "cloudwatch:GetMetricData",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:DescribeAlarmsForMetric"
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
}

AWS CLI Commands:
-----------------
# Create role
aws iam create-role \\
  --role-name CrossAccountCloudWatchRole \\
  --assume-role-policy-document file://target_trust_policy.json

# Attach permissions
aws iam put-role-policy \\
  --role-name CrossAccountCloudWatchRole \\
  --policy-name CloudWatchReadAccess \\
  --policy-document file://target_permissions.json
EOF


