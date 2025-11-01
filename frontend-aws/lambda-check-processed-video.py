import json
import boto3
from datetime import datetime, timedelta
from typing import List, Dict, Any
from botocore.client import Config

# Configure S3 client with signature version that supports encryption
s3_client = boto3.client('s3', config=Config(signature_version='s3v4'))

def lambda_handler(event, context):
    """
    Lambda function to check for processed videos in S3 after a specific timestamp.
    
    Expected input (POST body):
    {
        "uploadTimestamp": "2024-10-26T10:30:00.000Z",
        "videoId": "optional-video-id"
    }
    
    Returns:
    {
        "found": true/false,
        "video": {
            "key": "processed/folder/video.mp4",
            "url": "https://bucket.s3.region.amazonaws.com/key",
            "lastModified": "2024-10-26T10:35:00.000Z",
            "folder": "processed/folder"
        }
    }
    """
    
    try:
        # Parse the request body
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', {})
        
        upload_timestamp_str = body.get('uploadTimestamp')
        video_id = body.get('videoId', '')
        
        if not upload_timestamp_str:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'error': 'uploadTimestamp is required'
                })
            }
        
        # Parse the timestamp
        upload_timestamp = datetime.fromisoformat(upload_timestamp_str.replace('Z', '+00:00'))
        
        # S3 bucket and prefix configuration
        bucket_name = 'crashtruth-raw-saivineethpinnoju'
        prefix = 'processed/'
        region = 'us-west-1'
        
        # Search for processed videos
        processed_videos = search_processed_videos(
            bucket_name, 
            prefix, 
            upload_timestamp,
            region
        )
        
        if processed_videos:
            # Return the most recent video
            latest_video = processed_videos[0]
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'found': True,
                    'video': latest_video
                })
            }
        else:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type',
                    'Access-Control-Allow-Methods': 'POST, OPTIONS'
                },
                'body': json.dumps({
                    'found': False,
                    'message': 'No processed video found yet'
                })
            }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': json.dumps({
                'error': f'Failed to check for processed videos: {str(e)}'
            })
        }


def search_processed_videos(
    bucket_name: str, 
    prefix: str, 
    after_timestamp: datetime,
    region: str
) -> List[Dict[str, Any]]:
    """
    Search for video.mp4 files in S3 uploaded after the specified timestamp.
    
    Args:
        bucket_name: S3 bucket name
        prefix: Prefix to search under (e.g., 'processed/')
        after_timestamp: Only return files modified after this time
        region: AWS region
    
    Returns:
        List of video objects sorted by most recent first
    """
    processed_videos = []
    continuation_token = None
    
    try:
        while True:
            # List objects with pagination
            list_params = {
                'Bucket': bucket_name,
                'Prefix': prefix
            }
            
            if continuation_token:
                list_params['ContinuationToken'] = continuation_token
            
            response = s3_client.list_objects_v2(**list_params)
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    key = obj['Key']
                    last_modified = obj['LastModified']
                    
                    # Filter: only video.mp4 files
                    if not key.endswith('video.mp4'):
                        continue
                    
                    # Filter: only files modified after the timestamp
                    if last_modified <= after_timestamp:
                        continue
                    
                    # Extract folder path
                    folder = '/'.join(key.split('/')[:-1])
                    
                    # Generate simple presigned URL without response parameters
                    # The Content-Type is already set on the S3 object itself
                    url = s3_client.generate_presigned_url(
                        'get_object',
                        Params={
                            'Bucket': bucket_name,
                            'Key': key
                        },
                        ExpiresIn=3600  # 1 hour
                    )
                    
                    processed_videos.append({
                        'key': key,
                        'url': url,
                        'lastModified': last_modified.isoformat(),
                        'folder': folder,
                        'size': obj['Size']
                    })
            
            # Check if there are more results
            if response.get('IsTruncated'):
                continuation_token = response.get('NextContinuationToken')
            else:
                break
        
        # Sort by most recent first
        processed_videos.sort(key=lambda x: x['lastModified'], reverse=True)
        
        return processed_videos
    
    except Exception as e:
        print(f"Error searching S3: {str(e)}")
        raise

