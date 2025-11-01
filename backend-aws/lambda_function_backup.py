import os
import json
import uuid
import boto3

s3 = boto3.client("s3")
BUCKET = os.environ["BUCKET"]
EXP = int(os.environ.get("URL_EXPIRY_SECONDS", "600"))

def lambda_handler(event, context):
    """
    AWS Lambda function to generate presigned URLs for video uploads.
    
    Expected event structure from API Gateway:
    {
        "httpMethod": "POST",
        "body": "{\"userId\": \"user123\", \"fileName\": \"video.mp4\"}"
    }
    """
    
    # Debug: Print the entire event to understand the structure
    print(f"DEBUG: Full event: {json.dumps(event, indent=2)}")
    
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
        print(f"DEBUG: Parsed body: {json.dumps(body, indent=2)}")
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON decode error: {e}")
        body = {}
    
    # Extract parameters
    user_id = body.get("userId")
    fileName = body.get("fileName", "video.mp4")
    
    print(f"DEBUG: user_id = {user_id}, fileName = {fileName}")
    
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

    # Generate unique video ID and S3 key
    video_id = str(uuid.uuid4())
    key = f"user/{user_id}/{video_id}.mp4"

    try:
        # Generate presigned URL for PUT operation
        url = s3.generate_presigned_url(
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

        # Return success response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "videoId": video_id,
                "key": key,
                "presignedUrl": url,
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
