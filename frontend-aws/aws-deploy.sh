#!/bin/bash

# AWS Deployment Script for Collision Analysis App
# This script deploys the Next.js app to S3 and CloudFront

set -e

# Configuration
BUCKET_NAME="collision-analysis-bucket"
DISTRIBUTION_ID="YOUR_DISTRIBUTION_ID"
REGION="us-west-1"

echo "🚀 Starting deployment process..."

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

# Build the application
echo "📦 Building the application..."
npm run build

# Check if out directory exists
if [ ! -d "out" ]; then
    echo "❌ Build failed. 'out' directory not found."
    exit 1
fi

# Create S3 bucket if it doesn't exist
echo "🪣 Checking S3 bucket..."
if ! aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "✅ Bucket $BUCKET_NAME already exists"
else
    echo "📦 Creating S3 bucket $BUCKET_NAME..."
    aws s3 mb "s3://$BUCKET_NAME" --region $REGION
    
    # Configure bucket for static website hosting
    aws s3 website "s3://$BUCKET_NAME" --index-document index.html --error-document 404.html
fi

# Upload files to S3
echo "⬆️ Uploading files to S3..."
aws s3 sync out/ "s3://$BUCKET_NAME" --delete --cache-control "public, max-age=31536000"

# Set proper content types
aws s3 cp "s3://$BUCKET_NAME" "s3://$BUCKET_NAME" --recursive --metadata-directive REPLACE --cache-control "public, max-age=31536000"

# Invalidate CloudFront cache
if [ "$DISTRIBUTION_ID" != "YOUR_DISTRIBUTION_ID" ]; then
    echo "🔄 Invalidating CloudFront cache..."
    aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*"
else
    echo "⚠️ Please update DISTRIBUTION_ID in this script before running CloudFront invalidation"
fi

echo "✅ Deployment completed successfully!"
echo "🌐 Your app should be available at: https://$DISTRIBUTION_ID.cloudfront.net"
