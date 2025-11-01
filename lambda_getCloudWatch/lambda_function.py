import json
import os
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError


def lambda_handler(event, context):
    """
    Lambda function to fetch CloudWatch logs from a different AWS account.
    
    Can be called directly or via API Gateway.
    
    Environment Variables:
        TARGET_ACCOUNT_ROLE_ARN: The ARN of the role to assume in the target account
        TARGET_REGION: AWS region where CloudWatch data resides (default: us-east-1)
    
    Event Parameters (direct invocation):
        log_group_name: Name of the log group (REQUIRED)
        timestamp: Optional timestamp
        limit: Optional limit (default: 1000)
        filter_pattern: Optional filter (default: "Processed")
    
    Query Parameters (API Gateway):
        log_group_name: Name of the log group (optional, defaults to CrashTruth-AnalyzeFrames)
    """
    
    # Check if called from API Gateway
    is_api_gateway = 'requestContext' in event
    
    if is_api_gateway:
        # Extract parameters from API Gateway event
        query_params = event.get('queryStringParameters') or {}
        log_group_name = query_params.get('log_group_name', '/aws/lambda/CrashTruth-AnalyzeFrames')
        
        # Create a normalized event for processing
        normalized_event = {
            'log_group_name': log_group_name
        }
    else:
        # Direct invocation
        normalized_event = event
        log_group_name = event.get('log_group_name')
    
    # Get configuration from environment variables
    target_role_arn = os.environ.get('TARGET_ACCOUNT_ROLE_ARN')
    target_region = os.environ.get('TARGET_REGION', 'us-east-1')
    
    if not target_role_arn:
        error_response = {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'TARGET_ACCOUNT_ROLE_ARN environment variable is required'
            })
        }
        if is_api_gateway:
            error_response['headers'] = {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        return error_response
    
    # Validate required parameters
    if not log_group_name:
        error_response = {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'log_group_name is required'
            })
        }
        if is_api_gateway:
            error_response['headers'] = {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        return error_response
    
    try:
        # Assume the role in the target account
        credentials = assume_cross_account_role(target_role_arn)
        
        # Create CloudWatch Logs client
        logs_client = boto3.client(
            'logs',
            region_name=target_region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        
        # Create S3 client for report fetching
        s3_client = boto3.client(
            's3',
            region_name=target_region,
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken']
        )
        
        # Fetch logs after the given timestamp
        result = fetch_logs_after_timestamp(logs_client, normalized_event)
        
        # If progress level is 4, check if report is generated
        if result.get('found') and result.get('progress_level') == 4:
            # Check CrashTruth-ReportGenerator for "Report generated"
            report_event = {
                'log_group_name': '/aws/lambda/CrashTruth-ReportGenerator'
            }
            report_result = check_report_generated(logs_client, report_event)
            
            if not report_result.get('found'):
                # Report not generated yet, downgrade to level 3
                result['progress_level'] = 3
                result['progress_percentage'] = 75.0
                result['report_status'] = 'Processing complete, waiting for report generation'
            else:
                # Report generated, fetch the actual report content from S3
                report_message = report_result.get('message', '')
                s3_report_result = fetch_report_from_s3(s3_client, report_message)
                
                result['report_status'] = 'Report generated'
                result['report_message'] = report_message
                
                if s3_report_result.get('found'):
                    result['report_content'] = s3_report_result.get('report_content', '')
                    result['report_folder'] = s3_report_result.get('report_folder', '')
                    result['report_timestamp'] = s3_report_result.get('report_timestamp', '')
                else:
                    result['report_content'] = 'Report generated but content could not be fetched from S3'
        
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully fetched CloudWatch logs',
                'data': result
            }, default=str)
        }
        
        if is_api_gateway:
            response['headers'] = {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        
        return response
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        error_response = {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'{error_code}: {error_message}'
            })
        }
        
        if is_api_gateway:
            error_response['headers'] = {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        
        return error_response
        
    except Exception as e:
        error_response = {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
        
        if is_api_gateway:
            error_response['headers'] = {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        
        return error_response


def assume_cross_account_role(role_arn, session_name='CrossAccountCloudWatchSession'):
    """
    Assume a role in another AWS account.
    
    Args:
        role_arn: The ARN of the role to assume
        session_name: Name for the assumed role session
        
    Returns:
        dict: Temporary credentials
    """
    sts_client = boto3.client('sts')
    
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=session_name,
        DurationSeconds=3600  # 1 hour
    )
    
    return response['Credentials']




def fetch_logs_after_timestamp(logs_client, event):
    """
    Fetch the FIRST/LATEST line that starts with "Processed" or "detections_all.jsonl already exists".
    
    If "detections_all.jsonl already exists" is found, skip to report checking (level 4).
    
    Searches the last 1000 lines and returns ONLY the first match found.
    
    Args:
        logs_client: Boto3 CloudWatch Logs client
        event: Lambda event containing:
            - log_group_name: Name of the log group (REQUIRED)
            - timestamp: Optional - defaults to last 24 hours
            - limit: Optional - defaults to 1000
            - filter_pattern: Optional - defaults to "Processed"
        
    Returns:
        dict: Single event if found, or not found message
    """
    log_group_name = event.get('log_group_name')
    timestamp = event.get('timestamp')
    limit = event.get('limit', 1000)
    
    # Check for both "Processed" and "detections_all.jsonl already exists"
    filter_pattern = event.get('filter_pattern', 'Processed')
    
    # If no timestamp provided, default to last 24 hours
    if not timestamp:
        timestamp = int((datetime.utcnow() - timedelta(hours=24)).timestamp())
    
    # Parse the timestamp
    start_time_ms = parse_timestamp(timestamp)
    
    # End time is now
    end_time_ms = int(datetime.utcnow().timestamp() * 1000)
    
    # Build filter parameters - fetch more than limit to ensure we get the latest
    # We'll fetch up to 10x the limit or 10000 events (CloudWatch max per request)
    fetch_limit = min(limit * 10, 10000)
    
    filter_params = {
        'logGroupName': log_group_name,
        'startTime': start_time_ms,
        'endTime': end_time_ms,
        'limit': fetch_limit
    }
    
    # Add filter pattern if provided
    if filter_pattern:
        filter_params['filterPattern'] = filter_pattern
    
    # First, check for "detections_all.jsonl already exists" - this takes priority
    already_exists_params = filter_params.copy()
    already_exists_params['filterPattern'] = 'detections_all.jsonl already exists'
    already_exists_params['limit'] = 10
    
    try:
        already_exists_response = logs_client.filter_log_events(**already_exists_params)
        already_exists_events = already_exists_response.get('events', [])
        
        if already_exists_events:
            # Found "detections_all.jsonl already exists" - processing was already done
            latest_event = max(already_exists_events, key=lambda x: x['timestamp'])
            return {
                'log_group': log_group_name,
                'found': True,
                'message': latest_event['message'],
                'progress_level': 4,  # Skip directly to checking report
                'progress_percentage': 100.0,
                'processed': 0,
                'total': 0,
                'timestamp': latest_event['timestamp'],
                'timestamp_iso': datetime.fromtimestamp(latest_event['timestamp'] / 1000).isoformat(),
                'logStreamName': latest_event.get('logStreamName', ''),
                'already_processed': True,
                'total_matches': len(already_exists_events)
            }
    except Exception:
        pass  # Continue to normal "Processed" check
    
    # Query logs for "Processed" pattern - fetch ALL events in the time range
    all_events = []
    next_token = None
    
    while True:
        if next_token:
            filter_params['nextToken'] = next_token
        
        response = logs_client.filter_log_events(**filter_params)
        
        # Format and add events
        for event_data in response.get('events', []):
            all_events.append({
                'timestamp': event_data['timestamp'],  # Unix milliseconds
                'timestamp_iso': datetime.fromtimestamp(event_data['timestamp'] / 1000).isoformat(),
                'message': event_data['message'],
                'logStreamName': event_data.get('logStreamName', ''),
                'eventId': event_data.get('eventId', '')
            })
        
        # Stop if no more results
        if 'nextToken' not in response:
            break
        
        next_token = response.get('nextToken')
        
        # Stop if we've fetched enough for limit (optimization)
        if len(all_events) >= fetch_limit:
            break
    
    # Sort by timestamp (descending - NEWEST FIRST)
    all_events.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Find the most recent "Processed" line that is actually recent (within 2 minutes)
    for event in all_events:
        message = event['message']
        
        # Parse the "Processed [HH:MM:SS] X/Y frames..." pattern
        progress_level = parse_progress_level(message)
        
        # If this message is recent, return it
        if progress_level['is_recent']:
            return {
                'log_group': log_group_name,
                'found': True,
                'message': message,
                'progress_level': progress_level['level'],
                'progress_percentage': progress_level['percentage'],
                'processed': progress_level['processed'],
                'total': progress_level['total'],
                'timestamp': event['timestamp'],
                'timestamp_iso': event['timestamp_iso'],
                'logStreamName': event['logStreamName'],
                'total_matches': len(all_events),
                'message_timestamp': progress_level['message_timestamp'],
                'is_recent': True
            }
    
    # If no recent messages found, return not found
    return {
        'log_group': log_group_name,
        'found': False,
        'message': 'No recent "Processed" messages found (all messages are older than 2 minutes)',
        'searched_from': datetime.fromtimestamp(start_time_ms / 1000).isoformat(),
        'searched_to': datetime.fromtimestamp(end_time_ms / 1000).isoformat(),
        'total_matches': len(all_events)
    }


def fetch_report_from_s3(s3_client, report_message):
    """
    Extract S3 path from report message and fetch the report content.
    
    Args:
        s3_client: Boto3 S3 client
        report_message: Log message like "Report generated → s3://crashtruth-reports/uuid/report.txt"
        
    Returns:
        dict: {found: bool, report_content: str, report_folder: str, report_timestamp: str}
    """
    import re
    
    try:
        # Extract S3 path from message
        # Pattern: "Report generated → s3://crashtruth-reports/uuid/report.txt"
        s3_match = re.search(r's3://crashtruth-reports/([^/]+)/report\.txt', report_message)
        
        if not s3_match:
            return {
                'found': False,
                'message': 'Could not extract S3 path from report message'
            }
        
        report_folder = s3_match.group(1)
        report_key = f"{report_folder}/report.txt"
        
        # Fetch the report from S3
        report_response = s3_client.get_object(Bucket='crashtruth-reports', Key=report_key)
        report_content = report_response['Body'].read().decode('utf-8')
        
        return {
            'found': True,
            'report_content': report_content,
            'report_folder': report_folder,
            'report_timestamp': report_response['LastModified'].isoformat(),
            'message': f'Report fetched from S3: {report_folder}'
        }
        
    except Exception as e:
        return {
            'found': False,
            'message': f'Error fetching report from S3: {str(e)}'
        }


def check_report_generated(logs_client, event):
    """
    Check if "Report generated" line exists in CrashTruth-ReportGenerator logs.
    
    Only checks the last 5 minutes of logs.
    
    Args:
        logs_client: Boto3 CloudWatch Logs client
        event: Lambda event containing log_group_name
        
    Returns:
        dict: {found: bool, message: str}
    """
    log_group_name = event.get('log_group_name')
    
    # Check only the last 5 minutes
    timestamp = int((datetime.utcnow() - timedelta(minutes=5)).timestamp())
    start_time_ms = parse_timestamp(timestamp)
    end_time_ms = int(datetime.utcnow().timestamp() * 1000)
    
    # Search for "Report generated"
    filter_params = {
        'logGroupName': log_group_name,
        'startTime': start_time_ms,
        'endTime': end_time_ms,
        'filterPattern': 'Report generated',
        'limit': 10
    }
    
    try:
        response = logs_client.filter_log_events(**filter_params)
        events = response.get('events', [])
        
        if events:
            # Found "Report generated"
            latest_event = max(events, key=lambda x: x['timestamp'])
            return {
                'found': True,
                'message': latest_event['message'],
                'timestamp': latest_event['timestamp'],
                'timestamp_iso': datetime.fromtimestamp(latest_event['timestamp'] / 1000).isoformat()
            }
        else:
            return {
                'found': False,
                'message': 'Report not generated yet'
            }
    except Exception as e:
        return {
            'found': False,
            'message': f'Error checking report: {str(e)}'
        }


def parse_progress_level(message):
    """
    Parse "Processed [HH:MM:SS] X/Y frames..." and return progress level 1-4.
    Also checks if the timestamp in the message is recent (within last 2 minutes).
    
    Progress levels:
        1 = 0-25%
        2 = 25-50%
        3 = 50-75%
        4 = 75-100%
    
    Args:
        message: Log message containing "Processed [HH:MM:SS] X/Y frames..."
        
    Returns:
        dict: {
            'level': int (1-4),
            'percentage': float,
            'processed': int,
            'total': int,
            'is_recent': bool,
            'message_timestamp': str
        }
    """
    import re
    from datetime import datetime, timedelta
    
    # Try to extract timestamp and X/Y pattern from the message
    # Pattern: "Processed [HH:MM:SS] X/Y frames" (new format) or "Processed X/Y frames" (old format)
    match = re.search(r'Processed\s+\[(\d{2}:\d{2}:\d{2})\]\s+(\d+)/(\d+)', message)
    
    # If new format not found, try old format
    if not match:
        match = re.search(r'Processed\s+(\d+)/(\d+)', message)
        if match:
            # Old format - assume it's recent (no timestamp to check)
            processed = int(match.group(1))
            total = int(match.group(2))
            
            # Calculate percentage
            if total > 0:
                percentage = (processed / total) * 100
            else:
                percentage = 0
            
            # Determine level (1-4)
            if percentage <= 25:
                level = 1
            elif percentage <= 50:
                level = 2
            elif percentage <= 75:
                level = 3
            else:
                level = 4
            
            return {
                'level': level,
                'percentage': round(percentage, 2),
                'processed': processed,
                'total': total,
                'is_recent': True,  # Assume old format messages are recent
                'message_timestamp': None
            }
    
    if match:
        message_time_str = match.group(1)  # HH:MM:SS
        processed = int(match.group(2))
        total = int(match.group(3))
        
        # Calculate percentage
        if total > 0:
            percentage = (processed / total) * 100
        else:
            percentage = 0
        
        # Check if the timestamp is recent (within last 2 minutes)
        try:
            # Parse the timestamp from the message
            message_time = datetime.strptime(message_time_str, '%H:%M:%S').time()
            current_time = datetime.now().time()
            
            # Convert to datetime objects for comparison (using today's date)
            today = datetime.now().date()
            message_datetime = datetime.combine(today, message_time)
            current_datetime = datetime.now()
            
            # If message time is from yesterday (crossed midnight), add a day
            if message_datetime > current_datetime:
                message_datetime = message_datetime - timedelta(days=1)
            
            # Check if message is within last 2 minutes
            time_diff = current_datetime - message_datetime
            is_recent = time_diff <= timedelta(minutes=2)
            
        except Exception:
            # If timestamp parsing fails, assume it's recent
            is_recent = True
        
        # Determine level (1-4)
        if percentage <= 25:
            level = 1
        elif percentage <= 50:
            level = 2
        elif percentage <= 75:
            level = 3
        else:
            level = 4
        
        return {
            'level': level,
            'percentage': round(percentage, 2),
            'processed': processed,
            'total': total,
            'is_recent': is_recent,
            'message_timestamp': message_time_str
        }
    else:
        # If pattern not found, return level 0
        return {
            'level': 0,
            'percentage': 0,
            'processed': 0,
            'total': 0,
            'is_recent': False,
            'message_timestamp': None
        }


def parse_timestamp(timestamp):
    """
    Parse various timestamp formats and return Unix milliseconds.
    
    Supported formats:
        - Unix milliseconds: 1698307200000
        - Unix seconds: 1698307200
        - ISO 8601: "2025-10-26T08:00:00"
        - ISO 8601 with Z: "2025-10-26T08:00:00Z"
        - ISO 8601 with timezone: "2025-10-26T08:00:00+00:00"
    
    Args:
        timestamp: Timestamp in various formats
        
    Returns:
        int: Unix timestamp in milliseconds
    """
    # If already an integer, check if it's seconds or milliseconds
    if isinstance(timestamp, int):
        # If it's a reasonable Unix timestamp in seconds (10 digits)
        if timestamp < 10000000000:
            return timestamp * 1000
        # Already in milliseconds
        return timestamp
    
    # If it's a string, try to parse it
    if isinstance(timestamp, str):
        # Try parsing as ISO 8601
        try:
            # Handle 'Z' timezone indicator
            if timestamp.endswith('Z'):
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                dt = datetime.fromisoformat(timestamp)
            
            return int(dt.timestamp() * 1000)
        except ValueError:
            # Try parsing as integer string
            try:
                ts_int = int(timestamp)
                if ts_int < 10000000000:
                    return ts_int * 1000
                return ts_int
            except ValueError:
                raise ValueError(f"Invalid timestamp format: {timestamp}")
    
    # If it's a float, treat as seconds
    if isinstance(timestamp, float):
        return int(timestamp * 1000)
    
    raise ValueError(f"Unsupported timestamp type: {type(timestamp)}")

