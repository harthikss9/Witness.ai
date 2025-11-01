# Video Upload Presigned URL Lambda Function

This Lambda function generates presigned URLs for uploading video files to S3.

## Files Created

- `lambda_function.py` - Main Lambda function code
- `requirements.txt` - Python dependencies
- `README.md` - This documentation

## Setup Instructions

### 1. Environment Variables
Set these environment variables in your Lambda function:
- `BUCKET` - Your S3 bucket name (required)
- `URL_EXPIRY_SECONDS` - URL expiration time in seconds (optional, defaults to 600)

### 2. IAM Permissions
Your Lambda execution role needs these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:PutObjectAcl"
            ],
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        }
    ]
}
```

### 3. API Gateway Integration
- Create a REST API
- Create a POST method (e.g., `/upload`)
- Set integration type to "Lambda Function"
- Select this Lambda function
- Enable CORS if needed

## Request Format

Send a POST request to your API Gateway endpoint:

```json
{
    "userId": "user123",
    "fileName": "my-video.mp4"
}
```

## Response Format

Success response:
```json
{
    "videoId": "550e8400-e29b-41d4-a716-446655440000",
    "key": "user/user123/550e8400-e29b-41d4-a716-446655440000.mp4",
    "presignedUrl": "https://your-bucket.s3.amazonaws.com/...",
    "expiresIn": 600,
    "contentType": "video/mp4"
}
```

Error response:
```json
{
    "error": "missing userId",
    "message": "userId is required"
}
```

## Usage

1. Call the API to get a presigned URL
2. Use the presigned URL to upload your video file directly to S3
3. The file will be stored at the path specified in the `key` field

## Testing

Test with curl:
```bash
curl -X POST https://your-api-gateway-url/upload \
  -H "Content-Type: application/json" \
  -d '{"userId": "user123", "fileName": "my-video.mp4"}'
```
