# Lambda Function Deployment Guide

## Lambda Function: Check Processed Video

This Lambda function searches for processed videos in S3 after a specific upload timestamp.

### Function Details

- **File**: `lambda-check-processed-video.py`
- **Runtime**: Python 3.9+
- **Handler**: `lambda_function.lambda_handler`
- **API Gateway Endpoint**: `/check-processed` (POST)

---

## Deployment Steps

### 1. Create the Lambda Function

#### Using AWS Console:

1. Go to AWS Lambda Console
2. Click **Create function**
3. Choose **Author from scratch**
4. Configure:
   - **Function name**: `CrashTruth-CheckProcessedVideo`
   - **Runtime**: Python 3.12 (or 3.9+)
   - **Architecture**: x86_64
5. Click **Create function**

#### Using AWS CLI:

```bash
# Create deployment package
zip lambda-check-processed-video.zip lambda-check-processed-video.py

# Create Lambda function
aws lambda create-function \
  --function-name CrashTruth-CheckProcessedVideo \
  --runtime python3.12 \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/YOUR_LAMBDA_ROLE \
  --handler lambda-check-processed-video.lambda_handler \
  --zip-file fileb://lambda-check-processed-video.zip \
  --region us-west-1
```

---

### 2. Configure IAM Permissions

The Lambda function needs permission to list objects in S3.

#### IAM Policy (attach to Lambda execution role):

```json
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
        "arn:aws:s3:::crashtruth-raw-saivineethpinnoju",
        "arn:aws:s3:::crashtruth-raw-saivineethpinnoju/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

---

### 3. Configure Lambda Settings

- **Memory**: 256 MB (adjust based on bucket size)
- **Timeout**: 30 seconds
- **Environment Variables**: None required (uses boto3 default credentials)

---

### 4. Add API Gateway Trigger

#### Option A: Using Existing API Gateway

If you already have the API Gateway: `c7fyq6f6v5.execute-api.us-west-1.amazonaws.com`

1. Go to API Gateway Console
2. Select your API
3. Create new resource: `/check-processed`
4. Create POST method
5. Integration type: Lambda Function
6. Select region: `us-west-1`
7. Lambda function: `CrashTruth-CheckProcessedVideo`
8. Enable **Lambda Proxy Integration**
9. Deploy API to `prod` stage

#### Option B: Create New API Gateway

```bash
aws apigatewayv2 create-integration \
  --api-id c7fyq6f6v5 \
  --integration-type AWS_PROXY \
  --integration-uri arn:aws:lambda:us-west-1:YOUR_ACCOUNT_ID:function:CrashTruth-CheckProcessedVideo \
  --payload-format-version 2.0
```

---

### 5. Enable CORS

The Lambda function already includes CORS headers, but ensure API Gateway also allows CORS:

#### In API Gateway Console:

1. Select the `/check-processed` resource
2. Click **Enable CORS**
3. Configure:
   - **Access-Control-Allow-Origin**: `*` (or your specific domain)
   - **Access-Control-Allow-Headers**: `Content-Type`
   - **Access-Control-Allow-Methods**: `POST, OPTIONS`
4. Deploy changes

---

## Testing

### Test Input (Lambda Console):

```json
{
  "body": "{\"uploadTimestamp\": \"2024-10-26T10:30:00.000Z\", \"videoId\": \"test-123\"}"
}
```

### Test via API Gateway (curl):

```bash
curl -X POST https://c7fyq6f6v5.execute-api.us-west-1.amazonaws.com/prod/check-processed \
  -H "Content-Type: application/json" \
  -d '{
    "uploadTimestamp": "2024-10-26T10:30:00.000Z",
    "videoId": "test-video-id"
  }'
```

### Expected Response (Video Found):

```json
{
  "found": true,
  "video": {
    "key": "processed/20241026_103500/video.mp4",
    "url": "https://crashtruth-raw-saivineethpinnoju.s3.us-west-1.amazonaws.com/processed/20241026_103500/video.mp4",
    "lastModified": "2024-10-26T10:35:00.000Z",
    "folder": "processed/20241026_103500",
    "size": 1048576
  }
}
```

### Expected Response (No Video Yet):

```json
{
  "found": false,
  "message": "No processed video found yet"
}
```

---

## Monitoring

### CloudWatch Logs

View logs in CloudWatch:
- Log Group: `/aws/lambda/CrashTruth-CheckProcessedVideo`

### Common Issues

1. **403 Forbidden**: Check IAM permissions for S3 access
2. **CORS Error**: Enable CORS in API Gateway
3. **Timeout**: Increase Lambda timeout if bucket has many objects
4. **No videos found**: Check bucket name and prefix are correct

---

## Integration with Frontend

The frontend automatically polls this endpoint every 10 seconds (after 20 second delay):

**Endpoint**: `https://c7fyq6f6v5.execute-api.us-west-1.amazonaws.com/prod/check-processed`

**Request**:
```json
{
  "uploadTimestamp": "2024-10-26T10:30:00.000Z",
  "videoId": "video-id-from-upload"
}
```

When a processed video is found, it displays in a video player on the progress page.

---

## Cost Estimation

- **Lambda**: ~$0.0000002 per invocation + compute time
- **S3 LIST operations**: $0.005 per 1,000 requests
- **API Gateway**: $1.00 per million requests

**Estimated cost per user**: < $0.001 (assuming video found within 10 polls)

---

## Security Considerations

1. ✅ Lambda function uses IAM role for S3 access (no hardcoded credentials)
2. ✅ CORS configured to prevent unauthorized access
3. ⚠️ Consider adding API Gateway authentication/API keys for production
4. ⚠️ Consider encrypting S3 bucket with KMS

---

## Updates and Maintenance

To update the Lambda function:

```bash
# Update code
zip lambda-check-processed-video.zip lambda-check-processed-video.py

# Update Lambda
aws lambda update-function-code \
  --function-name CrashTruth-CheckProcessedVideo \
  --zip-file fileb://lambda-check-processed-video.zip \
  --region us-west-1
```

---

## Architecture Diagram

```
User uploads video
     ↓
Record timestamp
     ↓
Progress page loads
     ↓
Wait 20 seconds
     ↓
Poll every 10s → API Gateway → Lambda → S3 List Objects
                                  ↓
                         Filter by timestamp
                                  ↓
                         Return video URL
                                  ↓
                    Display in video player
```

