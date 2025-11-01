# Cross-Account CloudWatch Lambda Function

This Lambda function fetches CloudWatch metrics and logs from a different AWS account using cross-account IAM roles.

## Architecture

```
Source Account (Lambda)  --AssumeRole-->  Target Account (CloudWatch Data)
```

## Setup Instructions

### Step 1: Target Account Setup (Where CloudWatch Data Lives)

1. **Create an IAM Role** called `CrossAccountCloudWatchRole`

2. **Trust Policy** (allows source account to assume this role):
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "AWS": "arn:aws:iam::<SOURCE_ACCOUNT_ID>:root"
         },
         "Action": "sts:AssumeRole"
       }
     ]
   }
   ```
   Replace `<SOURCE_ACCOUNT_ID>` with your Lambda account ID.

3. **Attach CloudWatch Read Permissions** (see `iam_policies.json` for full policy)

4. **Note the Role ARN** - you'll need this (format: `arn:aws:iam::<TARGET_ACCOUNT_ID>:role/CrossAccountCloudWatchRole`)

### Step 2: Source Account Setup (Where Lambda Runs)

1. **Create/Update Lambda Execution Role** with these permissions:
   - Permission to assume the target account role
   - Basic Lambda execution permissions (CloudWatch Logs)

2. **Set Environment Variables** in Lambda:
   ```
   TARGET_ACCOUNT_ROLE_ARN = arn:aws:iam::<TARGET_ACCOUNT_ID>:role/CrossAccountCloudWatchRole
   TARGET_REGION = us-east-1  # or your target region
   ```

### Step 3: Deploy Lambda Function

1. **Package the function**:
   ```bash
   pip install -r requirements.txt -t .
   zip -r lambda_function.zip .
   ```

2. **Create Lambda function**:
   ```bash
   aws lambda create-function \
     --function-name CloudWatchCrossAccountFetcher \
     --runtime python3.11 \
     --role arn:aws:iam::<SOURCE_ACCOUNT_ID>:role/LambdaExecutionRole \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://lambda_function.zip \
     --timeout 60 \
     --environment Variables="{TARGET_ACCOUNT_ROLE_ARN=arn:aws:iam::<TARGET_ACCOUNT_ID>:role/CrossAccountCloudWatchRole,TARGET_REGION=us-east-1}"
   ```

## Usage Examples

### Example 1: Fetch EC2 CPU Utilization

```json
{
  "namespace": "AWS/EC2",
  "metric_name": "CPUUtilization",
  "statistics": ["Average", "Maximum"],
  "period": 300,
  "hours_back": 1
}
```

### Example 2: Fetch RDS Metrics

```json
{
  "namespace": "AWS/RDS",
  "metric_name": "DatabaseConnections",
  "dimensions": [
    {
      "Name": "DBInstanceIdentifier",
      "Value": "my-database"
    }
  ],
  "statistics": ["Sum"],
  "period": 300,
  "hours_back": 24
}
```

### Example 3: Fetch Lambda Errors

```json
{
  "namespace": "AWS/Lambda",
  "metric_name": "Errors",
  "dimensions": [
    {
      "Name": "FunctionName",
      "Value": "my-function"
    }
  ],
  "statistics": ["Sum"],
  "period": 60,
  "hours_back": 1
}
```

## Testing Locally

Create a test event file `test_event.json`:
```json
{
  "namespace": "AWS/EC2",
  "metric_name": "CPUUtilization",
  "hours_back": 1
}
```

Test with AWS SAM CLI:
```bash
sam local invoke -e test_event.json
```

## Security Best Practices

1. **Use External ID**: Add an external ID to the trust policy for additional security
2. **Least Privilege**: Only grant necessary CloudWatch permissions
3. **Resource Restrictions**: Limit access to specific CloudWatch namespaces if possible
4. **Enable CloudTrail**: Monitor AssumeRole calls between accounts
5. **Rotate Credentials**: The temporary credentials auto-expire after 1 hour

## Common Namespaces

- `AWS/EC2` - EC2 instances
- `AWS/RDS` - RDS databases
- `AWS/Lambda` - Lambda functions
- `AWS/ECS` - ECS containers
- `AWS/ELB` - Load balancers
- `AWS/S3` - S3 buckets
- `AWS/DynamoDB` - DynamoDB tables
- `AWS/CloudFront` - CloudFront distributions

## Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRole"
- Check that the Lambda execution role has permission to assume the target role
- Verify the target role ARN is correct

### Error: "Access Denied" when fetching metrics
- Ensure the target account role has CloudWatch read permissions
- Check that the trust policy allows the source account

### Error: "An error occurred (InvalidParameterValue)"
- Verify the metric namespace and name are correct
- Check that dimensions match existing metrics

## Cost Considerations

- CloudWatch API calls: ~$0.01 per 1,000 requests
- Lambda execution: Based on invocation count and duration
- Cross-account data transfer: May incur charges depending on region


