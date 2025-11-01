# Simple Usage Guide - Fetch Logs After Timestamp

Your Lambda function now does ONE thing simply: **Fetch logs from a specific log group after a given timestamp**.

## 📝 What You Need

You need the **log group NAME** (not ARN):

**Available Log Groups in Target Account:**
```
/aws/lambda/CrashTruth-AnalyzeFrames
/aws/lambda/CrashTruth-FaultAnalyzer
/aws/lambda/CrashTruth-ReportGenerator
/aws/lambda/CrashTruth-Tracker
/aws/lambda/CreateUpload
/aws/lambda/ExtractFramesTrigger
/aws/lambda/taxbuddy-daily-ingest
/aws/lambda/taxbuddy-embed
/aws/lambda/taxbuddy-process-html
/aws/lambda/uploadurlsintos3
/aws/sagemaker/studio
```

---

## 🚀 Usage

### Required Parameters:
1. **`log_group_name`** - Name of the log group (string)
2. **`timestamp`** - Fetch logs AFTER this time (multiple formats supported)

### Optional Parameters:
3. **`limit`** - Max number of events to return (default: 1000)
4. **`filter_pattern`** - Filter log messages (e.g., "ERROR", "Exception")

---

## 📅 Timestamp Formats (All Work!)

### 1. ISO 8601 String with Timezone (Recommended)
```json
{
  "log_group_name": "/aws/lambda/CrashTruth-AnalyzeFrames",
  "timestamp": "2025-10-26T08:00:00Z"
}
```

### 2. ISO 8601 String (Local Time)
```json
{
  "log_group_name": "/aws/lambda/CreateUpload",
  "timestamp": "2025-10-26T08:00:00"
}
```

### 3. Unix Timestamp in Seconds
```json
{
  "log_group_name": "/aws/lambda/uploadurlsintos3",
  "timestamp": 1729900000
}
```

### 4. Unix Timestamp in Milliseconds
```json
{
  "log_group_name": "/aws/sagemaker/studio",
  "timestamp": 1729900000000
}
```

---

## 💻 Command Line Examples

### Example 1: Get All Logs Since Yesterday
```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "log_group_name": "/aws/lambda/CrashTruth-AnalyzeFrames",
    "timestamp": "2025-10-25T00:00:00Z"
  }' \
  response.json && cat response.json | python3 -m json.tool
```

### Example 2: Get Recent Logs with Limit
```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "log_group_name": "/aws/lambda/CreateUpload",
    "timestamp": "2025-10-26T06:00:00Z",
    "limit": 100
  }' \
  response.json && cat response.json | python3 -m json.tool
```

### Example 3: Filter for ERROR Messages Only
```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "log_group_name": "/aws/lambda/CrashTruth-FaultAnalyzer",
    "timestamp": "2025-10-26T00:00:00Z",
    "filter_pattern": "ERROR"
  }' \
  response.json && cat response.json | python3 -m json.tool
```

### Example 4: Using Unix Timestamp
```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "log_group_name": "/aws/lambda/uploadurlsintos3",
    "timestamp": 1729900000,
    "limit": 50
  }' \
  response.json && cat response.json | python3 -m json.tool
```

---

## 📊 Response Format

```json
{
  "statusCode": 200,
  "body": {
    "message": "Successfully fetched CloudWatch logs",
    "data": {
      "log_group": "/aws/lambda/CrashTruth-AnalyzeFrames",
      "events_count": 10,
      "events": [
        {
          "timestamp": 1761460091936,
          "timestamp_iso": "2025-10-26T06:28:11.936000",
          "message": "INIT_START Runtime Version: python:3.13.v64...",
          "logStreamName": "2025/10/26/[$LATEST]143fb6ba9c584812a910c55a1991a50c",
          "eventId": "39281872687645062013130350035297378392126175520581943296"
        }
      ],
      "start_timestamp": 1729900000000,
      "start_timestamp_iso": "2024-10-25T23:46:40",
      "end_timestamp": 1761466895568,
      "end_timestamp_iso": "2025-10-26T08:21:35.568000",
      "filter_pattern": "None",
      "limit_applied": 10
    }
  }
}
```

### Fields Explained:
- **`events_count`** - Number of log events returned
- **`events`** - Array of log events
  - **`timestamp`** - Unix timestamp in milliseconds
  - **`timestamp_iso`** - Human-readable timestamp
  - **`message`** - The actual log message
  - **`logStreamName`** - Which log stream it came from
- **`start_timestamp`** - Your requested timestamp
- **`end_timestamp`** - Current time (when query ran)

---

## 🐍 Python Example

```python
import boto3
import json
from datetime import datetime, timedelta

def get_logs_after_timestamp(log_group, timestamp, limit=100):
    """
    Fetch CloudWatch logs from target account after a specific timestamp.
    
    Args:
        log_group: Name of the log group (e.g., "/aws/lambda/MyFunction")
        timestamp: ISO 8601 string or Unix timestamp
        limit: Max number of events to return
    
    Returns:
        List of log events
    """
    lambda_client = boto3.client('lambda')
    
    payload = {
        "log_group_name": log_group,
        "timestamp": timestamp,
        "limit": limit
    }
    
    response = lambda_client.invoke(
        FunctionName='CloudWatchCrossAccountFetcher',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    data = json.loads(result['body'])
    
    if data.get('data'):
        return data['data']['events']
    return []

# Example 1: Get logs from the last hour
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
logs = get_logs_after_timestamp(
    "/aws/lambda/CrashTruth-AnalyzeFrames",
    one_hour_ago.isoformat() + "Z",
    limit=100
)

print(f"Found {len(logs)} log events")
for log in logs:
    print(f"[{log['timestamp_iso']}] {log['message']}")

# Example 2: Get ERROR logs from specific time
logs = get_logs_after_timestamp(
    "/aws/lambda/CreateUpload",
    "2025-10-26T06:00:00Z",
    limit=50
)

# Example 3: Using Unix timestamp
import time
yesterday = int(time.time()) - 86400
logs = get_logs_after_timestamp(
    "/aws/lambda/uploadurlsintos3",
    yesterday,
    limit=200
)
```

---

## 🔍 Filter Patterns

### Simple Text Matching
```json
{
  "filter_pattern": "ERROR"
}
```
Finds all log lines containing "ERROR"

### Multiple Terms (OR)
```json
{
  "filter_pattern": "?ERROR ?WARN ?CRITICAL"
}
```
Finds lines with ERROR OR WARN OR CRITICAL

### Multiple Terms (AND)
```json
{
  "filter_pattern": "ERROR timeout"
}
```
Finds lines with both "ERROR" AND "timeout"

### Exclude Pattern
```json
{
  "filter_pattern": "-\"INFO\""
}
```
Excludes lines containing "INFO"

### JSON Field Matching
```json
{
  "filter_pattern": "{ $.level = \"ERROR\" }"
}
```
For JSON-formatted logs, match specific fields

---

## 🎯 Common Use Cases

### 1. Get All Logs Since Last Check
```bash
# Save last timestamp somewhere, then query from that point
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "log_group_name": "/aws/lambda/MyFunction",
    "timestamp": 1729900000
  }' response.json
```

### 2. Monitor for Errors Since Deployment
```bash
# After deploying at 08:00, check for errors
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "log_group_name": "/aws/lambda/MyFunction",
    "timestamp": "2025-10-26T08:00:00Z",
    "filter_pattern": "ERROR"
  }' response.json
```

### 3. Continuous Log Streaming
```python
import time
import json
import boto3

lambda_client = boto3.client('lambda')
log_group = "/aws/lambda/CrashTruth-AnalyzeFrames"
last_timestamp = int(time.time()) * 1000  # Current time in ms

while True:
    # Fetch new logs
    response = lambda_client.invoke(
        FunctionName='CloudWatchCrossAccountFetcher',
        Payload=json.dumps({
            "log_group_name": log_group,
            "timestamp": last_timestamp,
            "limit": 100
        })
    )
    
    result = json.loads(response['Payload'].read())
    data = json.loads(result['body'])
    
    if data.get('data') and data['data']['events']:
        for event in data['data']['events']:
            print(f"[{event['timestamp_iso']}] {event['message']}")
            last_timestamp = max(last_timestamp, event['timestamp'] + 1)
    
    # Wait before next poll
    time.sleep(5)
```

---

## ⚠️ Important Notes

1. **Log Group Name** - Use the name, not ARN
   - ✅ Correct: `/aws/lambda/MyFunction`
   - ❌ Wrong: `arn:aws:logs:us-east-1:123456789:log-group:/aws/lambda/MyFunction`

2. **Timestamp** - Logs are fetched from your timestamp until NOW

3. **Limit** - Default is 1000 events, can be increased up to 10,000

4. **Pagination** - The function automatically handles pagination up to your limit

5. **Sorting** - Results are sorted by timestamp (oldest first)

6. **Both Timestamps** - Response includes both Unix milliseconds and ISO format

---

## 🔐 Security

- ✅ Uses temporary credentials (1-hour expiry)
- ✅ Cross-account role with read-only permissions
- ✅ All access logged in CloudTrail
- ✅ No permanent credentials stored

---

## 💰 Cost

- CloudWatch Logs queries: ~$0.005 per GB scanned
- Lambda invocations: First 1M requests/month free
- For typical usage: ~$0.50-$1.00/month

---

**That's it! Just provide log group name and timestamp, get logs!** 🎉


