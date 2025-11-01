#!/usr/bin/env node

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Load configuration
const config = JSON.parse(fs.readFileSync('./deploy-config.json', 'utf8'));

function runCommand(command, description) {
  console.log(`🔄 ${description}...`);
  try {
    execSync(command, { stdio: 'inherit' });
    console.log(`✅ ${description} completed`);
  } catch (error) {
    console.error(`❌ ${description} failed:`, error.message);
    process.exit(1);
  }
}

function checkAwsCli() {
  try {
    execSync('aws --version', { stdio: 'pipe' });
    console.log('✅ AWS CLI is installed');
  } catch (error) {
    console.error('❌ AWS CLI is not installed. Please install it first.');
    process.exit(1);
  }
}

function checkAwsCredentials() {
  try {
    execSync('aws sts get-caller-identity', { stdio: 'pipe' });
    console.log('✅ AWS credentials are configured');
  } catch (error) {
    console.error('❌ AWS credentials not configured. Please run "aws configure" first.');
    process.exit(1);
  }
}

function buildApp() {
  console.log('📦 Building the application...');
  runCommand('npm run build', 'Building Next.js app');
  
  if (!fs.existsSync('./out')) {
    console.error('❌ Build failed. "out" directory not found.');
    process.exit(1);
  }
  console.log('✅ Build completed successfully');
}

function deployToS3() {
  const bucketName = config.aws.bucketName;
  const region = config.aws.region;
  
  // Check if bucket exists
  try {
    execSync(`aws s3 ls s3://${bucketName}`, { stdio: 'pipe' });
    console.log(`✅ Bucket ${bucketName} already exists`);
  } catch (error) {
    console.log(`📦 Creating S3 bucket ${bucketName}...`);
    runCommand(`aws s3 mb s3://${bucketName} --region ${region}`, 'Creating S3 bucket');
    
    // Configure bucket for static website hosting
    runCommand(`aws s3 website s3://${bucketName} --index-document index.html --error-document 404.html`, 'Configuring S3 website hosting');
  }
  
  // Upload files
  console.log('⬆️ Uploading files to S3...');
  runCommand(`aws s3 sync ./out/ s3://${bucketName} --delete --cache-control "${config.build.cacheControl}"`, 'Uploading files to S3');
  
  // Set proper content types for HTML files
  console.log('🔧 Setting proper content types...');
  runCommand(`aws s3 cp s3://${bucketName}/index.html s3://${bucketName}/index.html --content-type "text/html" --metadata-directive REPLACE`, 'Setting HTML content type');
  runCommand(`aws s3 cp s3://${bucketName}/404.html s3://${bucketName}/404.html --content-type "text/html" --metadata-directive REPLACE`, 'Setting 404 HTML content type');
  runCommand(`aws s3 cp s3://${bucketName}/404/index.html s3://${bucketName}/404/index.html --content-type "text/html" --metadata-directive REPLACE`, 'Setting 404 index HTML content type');
}

function invalidateCloudFront() {
  const distributionId = config.aws.distributionId;
  
  if (distributionId === 'YOUR_DISTRIBUTION_ID') {
    console.log('⚠️ Please update DISTRIBUTION_ID in deploy-config.json before running CloudFront invalidation');
    return;
  }
  
  console.log('🔄 Invalidating CloudFront cache...');
  runCommand(`aws cloudfront create-invalidation --distribution-id ${distributionId} --paths "/*"`, 'Invalidating CloudFront cache');
}

function main() {
  console.log('🚀 Starting deployment process for Collision Analysis App...\n');
  
  // Pre-flight checks
  checkAwsCli();
  checkAwsCredentials();
  
  // Build and deploy
  buildApp();
  deployToS3();
  invalidateCloudFront();
  
  console.log('\n✅ Deployment completed successfully!');
  console.log(`🌐 Your app should be available at: https://${config.aws.distributionId}.cloudfront.net`);
  console.log(`📊 S3 Bucket: s3://${config.aws.bucketName}`);
}

main();
