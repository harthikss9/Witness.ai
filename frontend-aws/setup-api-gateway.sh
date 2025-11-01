#!/bin/bash

# API Gateway Setup Script for Check Processed Video endpoint

set -e

# Configuration
API_ID="c7fyq6f6v5"
REGION="us-west-1"
FUNCTION_NAME="CrashTruth-CheckProcessedVideo"
RESOURCE_PATH="check-processed"
STAGE_NAME="prod"

echo "🌐 Setting up API Gateway integration..."
echo "API ID: $API_ID"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
LAMBDA_ARN="arn:aws:lambda:$REGION:$ACCOUNT_ID:function:$FUNCTION_NAME"

# Get root resource ID
echo ""
echo "📋 Getting root resource..."
ROOT_RESOURCE_ID=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --region $REGION \
  --query 'items[?path==`/`].id' \
  --output text)

echo "Root Resource ID: $ROOT_RESOURCE_ID"

# Check if resource already exists
echo ""
echo "🔍 Checking if resource already exists..."
EXISTING_RESOURCE=$(aws apigateway get-resources \
  --rest-api-id $API_ID \
  --region $REGION \
  --query "items[?pathPart=='$RESOURCE_PATH'].id" \
  --output text)

if [ -n "$EXISTING_RESOURCE" ]; then
    echo "✅ Resource already exists: /$RESOURCE_PATH"
    RESOURCE_ID=$EXISTING_RESOURCE
else
    echo "📝 Creating resource: /$RESOURCE_PATH"
    RESOURCE_ID=$(aws apigateway create-resource \
      --rest-api-id $API_ID \
      --region $REGION \
      --parent-id $ROOT_RESOURCE_ID \
      --path-part $RESOURCE_PATH \
      --query 'id' \
      --output text)
    echo "✅ Resource created with ID: $RESOURCE_ID"
fi

# Create OPTIONS method for CORS preflight
echo ""
echo "🔧 Setting up CORS preflight (OPTIONS)..."
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method OPTIONS \
  --authorization-type NONE \
  --region $REGION \
  2>/dev/null || echo "⚠️  OPTIONS method already exists"

# Set up OPTIONS method response
aws apigateway put-method-response \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method OPTIONS \
  --status-code 200 \
  --response-parameters '{"method.response.header.Access-Control-Allow-Headers":true,"method.response.header.Access-Control-Allow-Methods":true,"method.response.header.Access-Control-Allow-Origin":true}' \
  --region $REGION \
  2>/dev/null || echo "⚠️  OPTIONS method response already exists"

# Set up OPTIONS integration
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method OPTIONS \
  --type MOCK \
  --request-templates '{"application/json":"{\"statusCode\": 200}"}' \
  --region $REGION \
  2>/dev/null || echo "⚠️  OPTIONS integration already exists"

# Set up OPTIONS integration response
aws apigateway put-integration-response \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method OPTIONS \
  --status-code 200 \
  --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'POST,OPTIONS'"'"'","method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' \
  --region $REGION \
  2>/dev/null || echo "⚠️  OPTIONS integration response already exists"

echo "✅ CORS preflight configured"

# Create POST method
echo ""
echo "📝 Creating POST method..."
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --authorization-type NONE \
  --region $REGION \
  2>/dev/null || echo "⚠️  POST method already exists"

# Set up Lambda integration with proxy
echo "🔗 Setting up Lambda integration..."
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $RESOURCE_ID \
  --http-method POST \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/$LAMBDA_ARN/invocations" \
  --region $REGION \
  2>/dev/null || echo "⚠️  POST integration already exists"

echo "✅ Lambda integration configured"

# Deploy API
echo ""
echo "🚀 Deploying API to stage: $STAGE_NAME"
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name $STAGE_NAME \
  --description "Added check-processed endpoint" \
  --region $REGION

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ API Gateway setup completed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Endpoint URL:"
echo "https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE_NAME/$RESOURCE_PATH"
echo ""
echo "🧪 Test with:"
echo "curl -X POST https://$API_ID.execute-api.$REGION.amazonaws.com/$STAGE_NAME/$RESOURCE_PATH \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"uploadTimestamp\": \"2024-10-26T10:00:00.000Z\"}'"
echo ""

