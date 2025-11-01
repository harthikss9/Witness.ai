#!/bin/bash

# Simplified Lambda Deployment Script
# Uses existing IAM role - update ROLE_ARN below

set -e

# Configuration - UPDATE THESE
FUNCTION_NAME="CrashTruth-CheckProcessedVideo"
RUNTIME="python3.12"
HANDLER="lambda-check-processed-video.lambda_handler"
REGION="us-west-1"
API_ID="c7fyq6f6v5"
STAGE_NAME="prod"

# Using existing Lambda execution role
ROLE_ARN="arn:aws:iam::190460190639:role/CloudWatchLambdaExecutionRole"

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

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Get the API Gateway ARN for Lambda permission
API_ARN="arn:aws:execute-api:$REGION:$ACCOUNT_ID:$API_ID"

# Add permission for API Gateway to invoke Lambda
echo ""
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
echo "⚠️  IMPORTANT: Add S3 permissions to the IAM role"
echo "Role: $ROLE_ARN"
echo ""
echo "Add this policy to the role:"
echo '{'
echo '  "Version": "2012-10-17",'
echo '  "Statement": [{'
echo '    "Effect": "Allow",'
echo '    "Action": ["s3:ListBucket", "s3:GetObject"],'
echo '    "Resource": ['
echo '      "arn:aws:s3:::crashtruth-raw-saivineethpinnoju",'
echo '      "arn:aws:s3:::crashtruth-raw-saivineethpinnoju/*"'
echo '    ]'
echo '  }]'
echo '}'
echo ""
echo "📋 Next Steps:"
echo "1. Add S3 permissions to IAM role (see above)"
echo "2. Go to API Gateway Console: https://console.aws.amazon.com/apigateway"
echo "3. Select API: $API_ID"
echo "4. Create resource: /check-processed"
echo "5. Create method: POST"
echo "6. Integration type: Lambda Function"
echo "7. Lambda: $FUNCTION_NAME"
echo "8. ✅ Enable Lambda Proxy Integration"
echo "9. Enable CORS"
echo "10. Deploy to stage: $STAGE_NAME"
echo ""
echo "🔗 Expected endpoint: https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE_NAME/check-processed"
echo ""

