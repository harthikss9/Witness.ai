# Quick Start Guide

## What This Does

Allows your Lambda function (in this account) to fetch CloudWatch metrics from a different AWS account.

## Current Status

✅ Source account AWS configured  
✅ Lambda function code ready  
✅ CloudFormation templates created  
⏳ **Ready to deploy**

## Deploy Now (5 minutes)

### Step 1: Deploy to Source Account (This Account)

Run the deployment script:

```bash
./deploy_cloudformation.sh
```

You'll be prompted for:
- **Target Account ID**: The AWS account ID where CloudWatch data lives
- **Target Region**: The region where the CloudWatch data is (default: us-east-1)

This will create:
- Lambda function: `CloudWatchCrossAccountFetcher`
- IAM role: `CloudWatchLambdaExecutionRole`
- All necessary permissions

### Step 2: Configure Target Account

After Step 1 completes, you'll get a file `target_account_setup_cf.txt` with exact commands.

**Switch to the target AWS account** and run:

```bash
# Using CloudFormation (easiest)
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-target \
  --template-body file://cloudformation_target_account.yaml \
  --parameters \
    ParameterKey=SourceAccountId,ParameterValue=<YOUR_SOURCE_ACCOUNT_ID> \
    ParameterKey=SourceLambdaRoleName,ParameterValue=CloudWatchLambdaExecutionRole \
  --capabilities CAPABILITY_NAMED_IAM
```

### Step 3: Test

Back in the source account:

```bash
aws lambda invoke \
  --function-name CloudWatchCrossAccountFetcher \
  --payload file://test_event.json \
  response.json

cat response.json
```

## Example Usage

The Lambda function accepts JSON with these parameters:

```json
{
  "namespace": "AWS/EC2",
  "metric_name": "CPUUtilization",
  "statistics": ["Average", "Maximum"],
  "period": 300,
  "hours_back": 1
}
```

### Common CloudWatch Namespaces

- `AWS/EC2` - EC2 instances
- `AWS/RDS` - RDS databases  
- `AWS/Lambda` - Lambda functions
- `AWS/ECS` - ECS containers
- `AWS/ELB` - Load balancers
- `AWS/S3` - S3 buckets
- `AWS/DynamoDB` - DynamoDB tables

### Example: Get RDS Metrics

```json
{
  "namespace": "AWS/RDS",
  "metric_name": "DatabaseConnections",
  "dimensions": [
    {"Name": "DBInstanceIdentifier", "Value": "my-db"}
  ],
  "statistics": ["Average"],
  "period": 300,
  "hours_back": 24
}
```

## Files Overview

- **`lambda_function.py`** - Main Lambda code
- **`cloudformation_source_account.yaml`** - CloudFormation for source account
- **`cloudformation_target_account.yaml`** - CloudFormation for target account
- **`deploy_cloudformation.sh`** - Automated deployment script
- **`test_event.json`** - Sample test event
- **`SETUP_INSTRUCTIONS.md`** - Detailed setup guide

## Troubleshooting

**Error: Stack already exists**
```bash
# Delete and recreate
aws cloudformation delete-stack --stack-name cloudwatch-cross-account-source
aws cloudformation wait stack-delete-complete --stack-name cloudwatch-cross-account-source
./deploy_cloudformation.sh
```

**Error: Access Denied when invoking Lambda**
```bash
# Verify target account role exists
aws iam get-role --role-name CrossAccountCloudWatchRole
```

**Error: Metrics not found**
- Verify the namespace and metric name are correct
- Check that metrics exist in the target account/region
- Ensure dimensions match exactly (case-sensitive)

## Next Steps

1. Deploy using `./deploy_cloudformation.sh`
2. Configure target account (follow instructions in generated file)
3. Test with sample events
4. Integrate into your application

## Need Help?

- See `SETUP_INSTRUCTIONS.md` for detailed documentation
- Check `README.md` for architecture details
- Review AWS CloudWatch metrics documentation


