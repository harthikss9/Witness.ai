# Deployment Instructions for Admin User

Your current AWS user (`ecr-deploy-user`) doesn't have IAM permissions to create roles. This guide is for someone with admin access to deploy the Lambda function.

## Target Configuration

- **Source Account ID**: `190460190639` (where Lambda will run)
- **Target Account ID**: `993260645905` (where CloudWatch data lives)
- **Target Region**: `us-east-1`

---

## Option 1: CloudFormation Deployment (Easiest) ⭐

An admin user should run these commands in the **source account (190460190639)**:

```bash
cd /Users/saivineethpinnoju/hackathons/incident_intelligence/lambda_getCloudWatch

# Deploy the stack
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-source \
  --template-body file://cloudformation_source_account.yaml \
  --parameters \
    ParameterKey=TargetAccountId,ParameterValue=993260645905 \
    ParameterKey=TargetRegion,ParameterValue=us-east-1 \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name cloudwatch-cross-account-source

# Get outputs
aws cloudformation describe-stacks \
  --stack-name cloudwatch-cross-account-source \
  --query 'Stacks[0].Outputs'
```

---

## Option 2: Manual AWS CLI Deployment

If CloudFormation is not preferred, use these manual commands:

### Step 1: Create IAM Role for Lambda

```bash
# Create the role
aws iam create-role \
  --role-name CloudWatchLambdaExecutionRole \
  --assume-role-policy-document file://trust_policy.json \
  --description "Execution role for CloudWatch cross-account Lambda"

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name CloudWatchLambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create custom policy for cross-account access
aws iam create-policy \
  --policy-name CrossAccountCloudWatchPolicy \
  --policy-document file://source_account_iam_policy.json \
  --description "Allows Lambda to assume role in target account"

# Attach custom policy
aws iam attach-role-policy \
  --role-name CloudWatchLambdaExecutionRole \
  --policy-arn arn:aws:iam::190460190639:policy/CrossAccountCloudWatchPolicy
```

### Step 2: Package Lambda Function

```bash
# Install dependencies
pip install -r requirements.txt -t package/
cp lambda_function.py package/

# Create deployment package
cd package
zip -r ../lambda_function.zip .
cd ..
```

### Step 3: Create Lambda Function

```bash
# Create the function
aws lambda create-function \
  --function-name CloudWatchCrossAccountFetcher \
  --runtime python3.11 \
  --role arn:aws:iam::190460190639:role/CloudWatchLambdaExecutionRole \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 60 \
  --memory-size 256 \
  --environment Variables="{TARGET_ACCOUNT_ROLE_ARN=arn:aws:iam::993260645905:role/CrossAccountCloudWatchRole,TARGET_REGION=us-east-1}" \
  --description "Fetches CloudWatch metrics from cross-account"
```

---

## After Source Account Deployment

Once the Lambda is deployed in source account, configure the **target account (993260645905)**.

### Target Account Setup

An admin in target account `993260645905` should run:

```bash
# Option A: Using CloudFormation
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-target \
  --template-body file://cloudformation_target_account.yaml \
  --parameters \
    ParameterKey=SourceAccountId,ParameterValue=190460190639 \
    ParameterKey=SourceLambdaRoleName,ParameterValue=CloudWatchLambdaExecutionRole \
  --capabilities CAPABILITY_NAMED_IAM

# Option B: Using IAM CLI
aws iam create-role \
  --role-name CrossAccountCloudWatchRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::190460190639:role/CloudWatchLambdaExecutionRole"
      },
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name CrossAccountCloudWatchRole \
  --policy-name CloudWatchReadAccess \
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
```

---

## Testing

After both accounts are configured:

```bash
# Test the Lambda function
aws lambda invoke \
  --function-name CloudWatchCrossAccountFetcher \
  --payload file://test_event.json \
  response.json

# View results
cat response.json | jq .
```

---

## Quick Copy-Paste Commands

### For Admin in Source Account (190460190639):

```bash
cd /Users/saivineethpinnoju/hackathons/incident_intelligence/lambda_getCloudWatch

aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-source \
  --template-body file://cloudformation_source_account.yaml \
  --parameters \
    ParameterKey=TargetAccountId,ParameterValue=993260645905 \
    ParameterKey=TargetRegion,ParameterValue=us-east-1 \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation wait stack-create-complete --stack-name cloudwatch-cross-account-source
```

### For Admin in Target Account (993260645905):

```bash
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-target \
  --template-body file://cloudformation_target_account.yaml \
  --parameters \
    ParameterKey=SourceAccountId,ParameterValue=190460190639 \
    ParameterKey=SourceLambdaRoleName,ParameterValue=CloudWatchLambdaExecutionRole \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation wait stack-create-complete --stack-name cloudwatch-cross-account-target
```

---

## What Gets Created

### Source Account (190460190639):
- Lambda Function: `CloudWatchCrossAccountFetcher`
- IAM Role: `CloudWatchLambdaExecutionRole`
- IAM Policy: `CrossAccountCloudWatchPolicy`

### Target Account (993260645905):
- IAM Role: `CrossAccountCloudWatchRole` (with trust to source account)
- IAM Policy: `CloudWatchReadAccess` (attached to role)

---

## Verification

### Check Source Account:
```bash
aws lambda get-function --function-name CloudWatchCrossAccountFetcher
aws iam get-role --role-name CloudWatchLambdaExecutionRole
```

### Check Target Account:
```bash
aws iam get-role --role-name CrossAccountCloudWatchRole
```


