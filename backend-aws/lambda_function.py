import os
import json
import uuid
import boto3
from botocore.exceptions import ClientError

# Initialize S3 client (will be updated if cross-account role is used)
s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
OWN_BUCKET = os.environ.get("OWN_BUCKET", "crashtruth-raw-saivineethpinnoju")
EXP = int(os.environ.get("URL_EXPIRY_SECONDS", "600"))

# Cross-account role ARN (optional)
TARGET_ROLE_ARN = os.environ.get("TARGET_ROLE_ARN")

def get_s3_client():
    """
    Get S3 client, optionally assuming a cross-account role
    """
    if TARGET_ROLE_ARN:
        try:
            # Assume cross-account role
            sts_client = boto3.client('sts')
            assumed_role = sts_client.assume_role(
                RoleArn=TARGET_ROLE_ARN,
                RoleSessionName='LambdaCrossAccountSession'
            )
            
            # Create S3 client with assumed role credentials
            s3_client = boto3.client(
                's3',
                aws_access_key_id=assumed_role['Credentials']['AccessKeyId'],
                aws_secret_access_key=assumed_role['Credentials']['SecretAccessKey'],
                aws_session_token=assumed_role['Credentials']['SessionToken']
            )
            
            return s3_client
            
        except ClientError as e:
            raise e
    else:
        # Use default S3 client
        return s3

def lambda_handler(event, context):
    """
    AWS Lambda function to generate presigned URLs for video uploads.
    
    Expected event structure from API Gateway:
    {
        "httpMethod": "POST",
        "body": "{\"userId\": \"user123\", \"fileName\": \"video.mp4\"}"
    }
    """
    
    # Parse the JSON body from API Gateway
    try:
        # Check if this is a direct test invoke (event is the body) or API Gateway invoke (event has body field)
        if 'body' in event:
            # API Gateway invoke - body is in event.body
            if isinstance(event.get('body'), str):
                body = json.loads(event.get('body', '{}'))
            else:
                body = event.get('body', {})
        else:
            # Direct test invoke - event is the body itself
            body = event
    except json.JSONDecodeError as e:
        body = {}
    
    # Extract parameters
    user_id = body.get("userId")
    fileName = body.get("fileName", "video.mp4")
    
    # Validate required parameters
    if not user_id:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "missing userId",
                "message": "userId is required"
            })
        }

    try:
        # Generate unique video ID and S3 key
        video_id = str(uuid.uuid4())
        key = f"user/{user_id}/{video_id}.mp4"
        key2 = f"uploads/{video_id}.mp4"
        
        # Get S3 client (with cross-account role if configured)
        s3_client = get_s3_client()
        
        # Generate first presigned URL for cross-account bucket (if configured)
        url1 = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET,
                "Key": key,
                "ContentType": "video/mp4",
                "ServerSideEncryption": "AES256"
            },
            ExpiresIn=EXP,
            HttpMethod="PUT"
        )

        # Generate second presigned URL for own bucket
        url2 = s3.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": OWN_BUCKET,
                "Key": key2,
                "ContentType": "video/mp4",
                "ServerSideEncryption": "AES256"
            },
            ExpiresIn=EXP,
            HttpMethod="PUT"
        )

        # Extract filename from the S3 key
        filename = key.split('/')[-1]  # Gets the last part after the last '/'
        filename2 = key2.split('/')[-1]  # Gets the last part after the last '/'
        
        # Return success response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "videoId": video_id,
                "fileName": filename,
                "key": key,
                "key2": key2,
                "presignedUrl1": url1,
                "presignedUrl2": url2,
                "fileName1": filename,
                "fileName2": filename2,
                "expiresIn": EXP,
                "contentType": "video/mp4"
            })
        }
        
    except Exception as e:
        # Return error response
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Failed to generate presigned URL",
                "message": str(e)
            })
        }
