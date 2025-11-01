#!/bin/bash

# Lambda Deployment Script for Check Processed Video
# This script deploys the Lambda function and sets up API Gateway integration

set -e

# Configuration
FUNCTION_NAME="CrashTruth-CheckProcessedVideo"
RUNTIME="python3.12"
HANDLER="lambda-check-processed-video.lambda_handler"
REGION="us-west-1"
API_ID="c7fyq6f6v5"
STAGE_NAME="prod"
BUCKET_NAME="crashtruth-raw-saivineethpinnoju"
ROLE_NAME="CrashTruth-Lambda-S3-Role"

echo "🚀 Deploying Lambda function: $FUNCTION_NAME"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "📋 AWS Account ID: $ACCOUNT_ID"

# Create IAM Role for Lambda (if it doesn't exist)
echo ""
echo "🔐 Checking IAM Role..."
if aws iam get-role --role-name $ROLE_NAME 2>/dev/null; then
    echo "✅ IAM Role already exists: $ROLE_NAME"
else
    echo "📝 Creating IAM Role: $ROLE_NAME"
    
    # Create trust policy
    cat > /tmp/trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

    # Create the role
    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document file:///tmp/trust-policy.json \
        --description "Role for CrashTruth Lambda to access S3"
    
    # Attach basic Lambda execution policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    
    # Create and attach S3 access policy
    cat > /tmp/s3-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject"
      ],
      "Resource": [
        "arn:aws:s3:::$BUCKET_NAME",
        "arn:aws:s3:::$BUCKET_NAME/*"
      ]
    }
  ]
}
EOF

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name S3ReadAccess \
        --policy-document file:///tmp/s3-policy.json
    
    echo "✅ IAM Role created successfully"
    echo "⏳ Waiting 10 seconds for IAM role to propagate..."
    sleep 10
fi

ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

# Create deployment package
echo ""
echo "📦 Creating deployment package..."
cd "$(dirname "$0")"
zip -q lambda-check-processed-video.zip lambda-check-processed-video.py
echo "✅ Deployment package created: lambda-check-processed-video.zip"

# Check if Lambda function exists
echo ""
echo "🔍 Checking if Lambda function exists..."
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "♻️  Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://lambda-check-processed-video.zip \
        --region $REGION
    
    echo "⚙️  Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --handler $HANDLER \
        --timeout 30 \
        --memory-size 256 \
        --region $REGION
    
    echo "✅ Lambda function updated successfully"
else
    echo "🆕 Creating new Lambda function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime $RUNTIME \
        --role $ROLE_ARN \
        --handler $HANDLER \
        --zip-file fileb://lambda-check-processed-video.zip \
        --timeout 30 \
        --memory-size 256 \
        --region $REGION \
        --description "Checks for processed videos in S3 bucket after upload timestamp"
    
    echo "✅ Lambda function created successfully"
fi

# Clean up deployment package
rm lambda-check-processed-video.zip
echo "🧹 Cleaned up deployment package"

# Get Lambda function ARN
FUNCTION_ARN=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION --query 'Configuration.FunctionArn' --output text)
echo "📍 Lambda ARN: $FUNCTION_ARN"

# Configure API Gateway integration
echo ""
echo "🌐 Configuring API Gateway integration..."
echo "API Gateway ID: $API_ID"

# Get the API Gateway ARN for Lambda permission
API_ARN="arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID"

# Add permission for API Gateway to invoke Lambda
echo "🔑 Adding API Gateway invoke permission..."
aws lambda add-permission \
    --function-name $FUNCTION_NAME \
    --statement-id apigateway-invoke-check-processed \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "$API_ARN/*/*/*" \
    --region $REGION \
    2>/dev/null || echo "⚠️  Permission already exists (this is okay)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Lambda function deployed successfully!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo "1. Go to API Gateway Console: https://console.aws.amazon.com/apigateway"
echo "2. Select API: $API_ID"
echo "3. Create resource: /check-processed"
echo "4. Create method: POST"
echo "5. Integration type: Lambda Function"
echo "6. Lambda: $FUNCTION_NAME"
echo "7. ✅ Enable Lambda Proxy Integration"
echo "8. Enable CORS"
echo "9. Deploy to stage: $STAGE_NAME"
echo ""
echo "🔗 Expected endpoint: https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE_NAME/check-processed"
echo ""
echo "🧪 Test with:"
echo "curl -X POST https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE_NAME/check-processed \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"uploadTimestamp\": \"2024-10-26T10:00:00.000Z\"}'"
echo ""

