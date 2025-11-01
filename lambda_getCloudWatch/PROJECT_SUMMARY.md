# Cross-Account CloudWatch Lambda - Project Summary

## ✅ Yes, You CAN Access CloudWatch from a Different AWS Account!

This project is **ready to deploy**. All code, configurations, and deployment scripts have been created.

---

## 📋 What We've Built

### Core Files
- **`lambda_function.py`** (4.9 KB) - Main Lambda function that:
  - Uses STS AssumeRole to access target account
  - Fetches CloudWatch metrics with temporary credentials
  - Supports all CloudWatch namespaces and custom queries

### Deployment Options

#### Option 1: CloudFormation (Recommended) ⭐
- **`cloudformation_source_account.yaml`** - Complete source account setup
- **`cloudformation_target_account.yaml`** - Complete target account setup  
- **`deploy_cloudformation.sh`** - Automated deployment script

#### Option 2: Manual CLI
- **`deploy_simple.sh`** - Step-by-step CLI deployment
- **`source_account_iam_policy.json`** - IAM policy for Lambda role
- **`trust_policy.json`** - Lambda execution role trust policy

### Documentation
- **`QUICKSTART.md`** - 5-minute getting started guide
- **`SETUP_INSTRUCTIONS.md`** - Comprehensive setup guide (all 3 methods)
- **`README.md`** - Architecture and usage examples

### Testing
- **`test_event.json`** - Sample CloudWatch query
- **`requirements.txt`** - Python dependencies (boto3)

---

## 🚀 Quick Deployment (5 Minutes)

### Step 1: Deploy to Source Account (This Account)

```bash
./deploy_cloudformation.sh
```

**What it does:**
- Creates Lambda function: `CloudWatchCrossAccountFetcher`
- Creates IAM role: `CloudWatchLambdaExecutionRole`
- Sets up all permissions automatically
- Prompts you for target account ID

**Your current AWS configuration:**
- Account ID: `190460190639`
- Region: `us-west-1`
- User: `ecr-deploy-user`

### Step 2: Configure Target Account

After Step 1, a file `target_account_setup_cf.txt` will contain exact commands.

**In the target AWS account:**
```bash
aws cloudformation create-stack \
  --stack-name cloudwatch-cross-account-target \
  --template-body file://cloudformation_target_account.yaml \
  --parameters \
    ParameterKey=SourceAccountId,ParameterValue=190460190639 \
    ParameterKey=SourceLambdaRoleName,ParameterValue=CloudWatchLambdaExecutionRole \
  --capabilities CAPABILITY_NAMED_IAM
```

### Step 3: Test

```bash
aws lambda invoke \
  --function-name CloudWatchCrossAccountFetcher \
  --payload file://test_event.json \
  response.json

cat response.json
```

---

## 🏗️ Architecture

```
┌─────────────────────────┐          ┌─────────────────────────┐
│   SOURCE ACCOUNT        │          │   TARGET ACCOUNT        │
│   (190460190639)        │          │   (Your Target)         │
│                         │          │                         │
│  ┌──────────────────┐   │          │  ┌──────────────────┐   │
│  │ Lambda Function  │   │          │  │ IAM Role         │   │
│  │ CloudWatchCross  │───┼──────────┼─>│ CrossAccount     │   │
│  │ AccountFetcher   │   │ AssumeRole  │ CloudWatchRole   │   │
│  └──────────────────┘   │          │  └──────────────────┘   │
│           │             │          │           │             │
│           │             │          │           ▼             │
│  ┌──────────────────┐   │          │  ┌──────────────────┐   │
│  │ IAM Role         │   │          │  │ CloudWatch       │   │
│  │ Lambda           │   │          │  │ Metrics & Logs   │   │
│  │ ExecutionRole    │   │          │  └──────────────────┘   │
│  └──────────────────┘   │          │                         │
└─────────────────────────┘          └─────────────────────────┘
```

---

## 📝 How It Works

1. **Lambda Execution**: Your Lambda runs in source account
2. **STS AssumeRole**: Lambda assumes role in target account using STS
3. **Temporary Credentials**: Receives temporary AWS credentials (1-hour validity)
4. **CloudWatch Access**: Uses credentials to fetch CloudWatch data
5. **Return Data**: Returns metrics to caller

### Security Features
✅ No permanent credentials stored  
✅ Temporary credentials auto-expire  
✅ Least privilege IAM permissions  
✅ CloudTrail audit trail  
✅ Cross-account trust policy required

---

## 🎯 Use Cases

### Fetch EC2 Metrics
```json
{
  "namespace": "AWS/EC2",
  "metric_name": "CPUUtilization",
  "statistics": ["Average", "Maximum"],
  "hours_back": 1
}
```

### Fetch RDS Metrics
```json
{
  "namespace": "AWS/RDS",
  "metric_name": "DatabaseConnections",
  "dimensions": [
    {"Name": "DBInstanceIdentifier", "Value": "prod-db"}
  ],
  "hours_back": 24
}
```

### Fetch Lambda Errors
```json
{
  "namespace": "AWS/Lambda",
  "metric_name": "Errors",
  "statistics": ["Sum"],
  "hours_back": 6
}
```

### Supported Namespaces
All AWS CloudWatch namespaces:
- AWS/EC2, AWS/RDS, AWS/Lambda
- AWS/ECS, AWS/ELB, AWS/ApplicationELB
- AWS/S3, AWS/DynamoDB, AWS/CloudFront
- AWS/ApiGateway, AWS/SQS, AWS/SNS
- Custom namespaces

---

## 🔧 Environment Variables

Set in Lambda (automatically configured by deployment):

| Variable | Description | Example |
|----------|-------------|---------|
| `TARGET_ACCOUNT_ROLE_ARN` | ARN of role in target account | `arn:aws:iam::123456789012:role/CrossAccountCloudWatchRole` |
| `TARGET_REGION` | Region where CloudWatch data lives | `us-east-1` |

---

## 📊 Cost Estimate

For moderate usage (10,000 invocations/day):

| Service | Cost |
|---------|------|
| Lambda invocations | ~$0.40/month |
| Lambda compute (256MB) | ~$0.50/month |
| CloudWatch API calls | ~$0.30/month |
| CloudWatch Logs | ~$0.10/month |
| **Total** | **~$1.30/month** |

First 1M Lambda requests are free tier!

---

## 🐛 Troubleshooting

### "Access Denied" when assuming role
→ Verify target account role exists and trust policy is correct

### "Metrics not found"
→ Check namespace, metric name, and dimensions are exact (case-sensitive)

### "Lambda timeout"
→ Increase timeout in Lambda configuration (currently 60s)

### "Invalid credentials"
→ Ensure Lambda execution role has `sts:AssumeRole` permission

---

## 📚 Documentation Files

1. **`QUICKSTART.md`** - Start here! 5-minute guide
2. **`SETUP_INSTRUCTIONS.md`** - Detailed setup (3 deployment methods)
3. **`README.md`** - Architecture and examples
4. **This file** - Project overview

---

## 🎉 Ready to Deploy!

Run this command to get started:

```bash
./deploy_cloudformation.sh
```

Or for step-by-step guidance, see `QUICKSTART.md`.

---

## 📞 Next Actions

1. ✅ Source account code - **COMPLETE**
2. ✅ Deployment scripts - **COMPLETE**
3. ⏳ Deploy to source account - **RUN: `./deploy_cloudformation.sh`**
4. ⏳ Configure target account - **Follow generated instructions**
5. ⏳ Test Lambda function - **Use `test_event.json`**

---

**Everything is ready! Just run the deployment script when you have the target account ID.**


