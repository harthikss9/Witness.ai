# START HERE 🚀

## Quick Answer

**YES!** You can absolutely fetch CloudWatch data from a different AWS account. Everything is ready to deploy.

---

## Your Configuration

- **Source Account** (where Lambda runs): `190460190639`
- **Target Account** (CloudWatch data): `993260645905`
- **Target Region**: `us-east-1`

---

## ⚠️ Important Note

Your AWS user `ecr-deploy-user` doesn't have IAM permissions to create roles and Lambda functions.

**You need an admin user** to run the deployment.

---

## 🎯 Deployment (2 Simple Steps)

### Step 1: Source Account Deployment

**Have an admin in account `190460190639` run:**

```bash
./deploy_source_admin.sh
```

This creates the Lambda function and all necessary IAM roles.

**Takes:** ~2-3 minutes  
**Requires:** Admin/IAM permissions in source account

---

### Step 2: Target Account Deployment

**Have an admin in account `993260645905` run:**

```bash
./deploy_target_admin.sh
```

This creates the IAM role that allows cross-account access.

**Takes:** ~1 minute  
**Requires:** Admin/IAM permissions in target account  
**Note:** They'll need the `cloudformation_target_account.yaml` file

---

## 🧪 Testing

After both steps are complete, test from source account:

```bash
aws lambda invoke \
  --function-name CloudWatchCrossAccountFetcher \
  --payload file://test_event.json \
  response.json

cat response.json
```

---

## 📁 Key Files

### For Source Account Admin:
- `deploy_source_admin.sh` ⭐ **Run this script**
- `cloudformation_source_account.yaml` (used by script)

### For Target Account Admin:
- `deploy_target_admin.sh` ⭐ **Run this script**
- `cloudformation_target_account.yaml` (used by script)

### For Reference:
- `STATUS.md` - Current project status
- `DEPLOY_WITH_ADMIN.md` - Detailed deployment guide
- `target_account_instructions.txt` - Target account setup instructions

---

## 📚 Need More Details?

- **Quick Setup**: See `QUICKSTART.md`
- **Full Documentation**: See `SETUP_INSTRUCTIONS.md`
- **Current Status**: See `STATUS.md`
- **Architecture Info**: See `README.md`

---

## 💡 What Gets Created

### In Source Account (190460190639):
✅ Lambda function: `CloudWatchCrossAccountFetcher`  
✅ IAM role: `CloudWatchLambdaExecutionRole`  
✅ IAM policy: `CrossAccountCloudWatchPolicy`

### In Target Account (993260645905):
✅ IAM role: `CrossAccountCloudWatchRole`  
✅ Trust policy allowing source account  
✅ CloudWatch read permissions

---

## 🔒 Security

- ✅ Uses AWS STS AssumeRole (no permanent credentials)
- ✅ Temporary credentials (1-hour expiry)
- ✅ Least-privilege IAM permissions
- ✅ CloudTrail audit logging
- ✅ Follows AWS best practices

---

## 💰 Cost

For ~10,000 invocations/month: **~$0.70/month**

(First 1M Lambda requests are free!)

---

## 🎉 Example Usage

Once deployed, the Lambda accepts queries like:

### Get EC2 CPU Metrics:
```json
{
  "namespace": "AWS/EC2",
  "metric_name": "CPUUtilization",
  "statistics": ["Average", "Maximum"],
  "hours_back": 1
}
```

### Get RDS Metrics:
```json
{
  "namespace": "AWS/RDS",
  "metric_name": "DatabaseConnections",
  "dimensions": [
    {"Name": "DBInstanceIdentifier", "Value": "my-db"}
  ],
  "hours_back": 24
}
```

### Get Lambda Errors:
```json
{
  "namespace": "AWS/Lambda",
  "metric_name": "Errors",
  "statistics": ["Sum"],
  "hours_back": 6
}
```

---

## ✅ Next Action

**Share these files with your account admin:**

1. `deploy_source_admin.sh`
2. `cloudformation_source_account.yaml`
3. This file (`START_HERE.md`)

Then share with target account admin:

1. `deploy_target_admin.sh`
2. `cloudformation_target_account.yaml`
3. `target_account_instructions.txt`

---

## 🆘 Questions?

All documentation is in this folder:
- **`STATUS.md`** - Project status summary
- **`DEPLOY_WITH_ADMIN.md`** - Admin deployment guide
- **`SETUP_INSTRUCTIONS.md`** - Complete setup guide
- **`README.md`** - Architecture and examples

---

**Everything is configured and ready. Just need admin access to deploy! 🚀**


