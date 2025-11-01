# Add IAM Permissions to Deploy Lambda

Your user `ecr-deploy-user` needs additional IAM permissions to deploy the Lambda function.

## Quick Steps for AWS Admin

Have an AWS admin with IAM permissions run these commands:

### Step 1: Create the Policy

```bash
cd /Users/saivineethpinnoju/hackathons/incident_intelligence/lambda_getCloudWatch

aws iam create-policy \
  --policy-name LambdaDeploymentPolicy \
  --policy-document file://lambda-deployment-policy.json \
  --description "Allows deployment of CloudWatch cross-account Lambda function"
```

### Step 2: Attach Policy to Your User

```bash
aws iam attach-user-policy \
  --user-name ecr-deploy-user \
  --policy-arn arn:aws:iam::190460190639:policy/LambdaDeploymentPolicy
```

### Step 3: Verify

```bash
aws iam list-attached-user-policies --user-name ecr-deploy-user
```

You should see `LambdaDeploymentPolicy` in the list.

---

## What This Policy Allows

The policy grants permissions to:

1. **IAM Role Management** - Create and manage the Lambda execution role
2. **IAM Policy Management** - Create cross-account access policy
3. **Lambda Management** - Create and update Lambda functions
4. **CloudFormation Management** - Deploy via CloudFormation

**Scope**: Limited to specific resources for this project only (least privilege)

---

## After Permissions Are Added

Once the policy is attached to `ecr-deploy-user`, run:

```bash
./deploy_source_admin.sh
```

The deployment should now succeed!

---

## Alternative: Using AWS Console

If you prefer using the AWS Console:

### Step 1: Create Policy
1. Go to **IAM Console** → **Policies** → **Create Policy**
2. Click **JSON** tab
3. Paste contents of `lambda-deployment-policy.json`
4. Click **Next**
5. Name: `LambdaDeploymentPolicy`
6. Description: `Allows deployment of CloudWatch cross-account Lambda function`
7. Click **Create Policy**

### Step 2: Attach to User
1. Go to **IAM Console** → **Users** → **ecr-deploy-user**
2. Click **Add permissions** → **Attach policies directly**
3. Search for `LambdaDeploymentPolicy`
4. Check the box and click **Add permissions**

---

## Permissions Breakdown

### IAM Role Management
```
- iam:CreateRole
- iam:GetRole
- iam:AttachRolePolicy
- iam:PassRole
- iam:TagRole
```

Only for: `CloudWatchLambdaExecutionRole`

### IAM Policy Management
```
- iam:CreatePolicy
- iam:GetPolicy
```

Only for: `CrossAccountCloudWatchPolicy`

### Lambda Management
```
- lambda:CreateFunction
- lambda:UpdateFunctionCode
- lambda:UpdateFunctionConfiguration
- lambda:InvokeFunction
```

Only for: `CloudWatchCrossAccountFetcher`

### CloudFormation Management
```
- cloudformation:CreateStack
- cloudformation:DescribeStacks
- cloudformation:DescribeStackEvents
```

Only for: `cloudwatch-cross-account-source` stack

---

## Security Notes

✅ **Least Privilege**: Only grants permissions for specific resources  
✅ **Scoped**: Limited to this project only  
✅ **No Wildcards**: Specific role and function names  
✅ **Removable**: Can detach policy after deployment  

---

## Temporary Alternative

If you can't get IAM permissions added, you have two options:

### Option 1: Ask Admin to Deploy
Give these files to an admin:
- `deploy_source_admin.sh`
- `cloudformation_source_account.yaml`

They can run the script from their account.

### Option 2: AWS Console Manual Deployment
See `DEPLOY_WITH_ADMIN.md` for step-by-step AWS Console instructions.

---

## After Successful Deployment

You can optionally remove the policy:

```bash
aws iam detach-user-policy \
  --user-name ecr-deploy-user \
  --policy-arn arn:aws:iam::190460190639:policy/LambdaDeploymentPolicy
```

The Lambda function will continue working; you only need these permissions for deployment.


