# Cross-Account CloudWatch Access - Complete Setup Guide

## Overview

This setup allows a Lambda function in **Source Account** to fetch CloudWatch metrics from **Target Account**.

## Prerequisites

- Admin/IAM permissions in both AWS accounts
- AWS CLI configured
- Target Account ID

## Deployment Options

### Option 1: CloudFormation (Recommended)

This is the easiest method as it creates all resources automatically.

#### Step 1: Deploy to SOURCE Account (where Lambda runs)

```bash
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-source \
  --template-body file://cloudformation_source_account.yaml \
  --parameters \
    ParameterKey=TargetAccountId,ParameterValue=<TARGET_ACCOUNT_ID> \
    ParameterKey=TargetRegion,ParameterValue=us-east-1 \
  --capabilities CAPABILITY_NAMED_IAM
```

Wait for stack to complete:
```bash
aws cloudformation wait stack-create-complete \
  --stack-name cloudwatch-cross-account-source
```

Get the Lambda execution role ARN (needed for target account):
```bash
aws cloudformation describe-stacks \
  --stack-name cloudwatch-cross-account-source \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaExecutionRoleArn`].OutputValue' \
  --output text
```

#### Step 2: Deploy to TARGET Account (where CloudWatch data lives)

**Switch to target account credentials**, then run:

```bash
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-target \
  --template-body file://cloudformation_target_account.yaml \
  --parameters \
    ParameterKey=SourceAccountId,ParameterValue=<SOURCE_ACCOUNT_ID> \
    ParameterKey=SourceLambdaRoleName,ParameterValue=CloudWatchLambdaExecutionRole \
  --capabilities CAPABILITY_NAMED_IAM
```

Wait for completion:
```bash
aws cloudformation wait stack-create-complete \
  --stack-name cloudwatch-cross-account-target
```

#### Step 3: Test the Setup

Switch back to source account, then:

```bash
aws lambda invoke \
  --function-name CloudWatchCrossAccountFetcher \
  --payload file://test_event.json \
  response.json

cat response.json
```

---

### Option 2: Manual AWS CLI Setup

If you prefer manual setup or can't use CloudFormation:

#### SOURCE Account Setup

**1. Create IAM Role**
```bash
aws iam create-role \
  --role-name CloudWatchLambdaExecutionRole \
  --assume-role-policy-document file://trust_policy.json

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name CloudWatchLambdaExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create and attach cross-account assume role policy
aws iam create-policy \
  --policy-name CrossAccountCloudWatchPolicy \
  --policy-document file://source_account_iam_policy.json

# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Attach the policy
aws iam attach-role-policy \
  --role-name CloudWatchLambdaExecutionRole \
  --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/CrossAccountCloudWatchPolicy
```

**2. Package and Deploy Lambda**
```bash
# Install dependencies
pip install -r requirements.txt -t package/
cp lambda_function.py package/

# Create deployment package
cd package
zip -r ../lambda_function.zip .
cd ..

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name CloudWatchLambdaExecutionRole --query Role.Arn --output text)

# Create Lambda function
aws lambda create-function \
  --function-name CloudWatchCrossAccountFetcher \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_function.zip \
  --timeout 60 \
  --memory-size 256 \
  --environment Variables="{TARGET_ACCOUNT_ROLE_ARN=arn:aws:iam::<TARGET_ACCOUNT_ID>:role/CrossAccountCloudWatchRole,TARGET_REGION=us-east-1}"
```

#### TARGET Account Setup

**Switch to target account credentials**, then:

```bash
# Create the role
aws iam create-role \
  --role-name CrossAccountCloudWatchRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::<SOURCE_ACCOUNT_ID>:role/CloudWatchLambdaExecutionRole"
      },
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach CloudWatch read permissions
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

### Option 3: Using Deployment Script

If you have IAM permissions, you can use the deployment script:

```bash
chmod +x deploy_simple.sh
./deploy_simple.sh <TARGET_ACCOUNT_ID> <TARGET_REGION>
```

Then follow the instructions in `target_account_setup.txt` for target account setup.

---

## Testing

### Test Event Examples

**Test 1: EC2 CPU Metrics**
```json
{
  "namespace": "AWS/EC2",
  "metric_name": "CPUUtilization",
  "statistics": ["Average", "Maximum"],
  "period": 300,
  "hours_back": 1
}
```

**Test 2: Lambda Errors**
```json
{
  "namespace": "AWS/Lambda",
  "metric_name": "Errors",
  "statistics": ["Sum"],
  "period": 60,
  "hours_back": 24
}
```

**Test 3: RDS Database Connections**
```json
{
  "namespace": "AWS/RDS",
  "metric_name": "DatabaseConnections",
  "dimensions": [
    {
      "Name": "DBInstanceIdentifier",
      "Value": "my-database-instance"
    }
  ],
  "statistics": ["Average", "Maximum"],
  "period": 300,
  "hours_back": 6
}
```

### Invoke Lambda

```bash
aws lambda invoke \
  --function-name CloudWatchCrossAccountFetcher \
  --payload file://test_event.json \
  response.json

cat response.json | jq .
```

---

## Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRole"

**Solution:** Verify that:
1. Target account role exists with correct name: `CrossAccountCloudWatchRole`
2. Trust policy in target account allows source account Lambda role
3. Source account Lambda role has permission to assume target role

### Error: "Access Denied" when fetching metrics

**Solution:** Ensure target account role has CloudWatch read permissions attached

### Error: "Role not found"

**Solution:** 
1. Check that target account role ARN is correct in Lambda environment variables
2. Verify role name matches exactly (case-sensitive)
3. Ensure role is created in the correct target account

### Error: "Invalid parameter: period"

**Solution:** Period must be a multiple of 60 seconds and match the metric's resolution

---

## Security Best Practices

1. **Least Privilege**: Only grant necessary CloudWatch permissions
2. **External ID**: Add external ID to trust policy for additional security
3. **Resource Tags**: Tag all resources for better governance
4. **CloudTrail**: Enable CloudTrail to monitor cross-account access
5. **Regular Audits**: Review AssumeRole activity regularly
6. **Limit Regions**: Restrict access to specific regions if possible

---

## Updating the Lambda Function

To update the Lambda code:

```bash
# Package new code
pip install -r requirements.txt -t package/
cp lambda_function.py package/
cd package && zip -r ../lambda_function.zip . && cd ..

# Update function
aws lambda update-function-code \
  --function-name CloudWatchCrossAccountFetcher \
  --zip-file fileb://lambda_function.zip
```

---

## Clean Up

### SOURCE Account
```bash
aws cloudformation delete-stack --stack-name cloudwatch-cross-account-source
```

Or manually:
```bash
aws lambda delete-function --function-name CloudWatchCrossAccountFetcher
aws iam detach-role-policy --role-name CloudWatchLambdaExecutionRole --policy-arn <POLICY_ARN>
aws iam delete-role --role-name CloudWatchLambdaExecutionRole
```

### TARGET Account
```bash
aws cloudformation delete-stack --stack-name cloudwatch-cross-account-target
```

Or manually:
```bash
aws iam delete-role-policy --role-name CrossAccountCloudWatchRole --policy-name CloudWatchReadAccess
aws iam delete-role --role-name CrossAccountCloudWatchRole
```

---

## Cost Considerations

- **Lambda**: First 1M requests/month free, then $0.20 per 1M requests
- **CloudWatch API**: ~$0.01 per 1,000 GetMetricStatistics requests
- **Data Transfer**: Cross-region transfer may incur charges
- **CloudWatch Logs**: Lambda execution logs stored in CloudWatch

Estimated cost for 10,000 invocations/day: ~$1-2/month


