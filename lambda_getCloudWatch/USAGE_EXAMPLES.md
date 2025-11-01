# CloudWatch Cross-Account Lambda - Usage Examples

Your Lambda function can now fetch **both CloudWatch Metrics AND CloudWatch Logs** from the target account!

## 📊 What It Can Fetch

### 1. CloudWatch Metrics (Numerical Data)
- CPU utilization, memory usage
- Request counts, error counts
- Database connections
- Custom metrics from your applications

### 2. CloudWatch Logs (Text/Log Data)
- Application logs from Lambda functions
- Server logs from EC2 instances
- API Gateway logs
- Any custom logs sent to CloudWatch

---

## 🔍 Available Log Groups in Target Account

The target account (993260645905) has these log groups:

**Lambda Function Logs:**
- `/aws/lambda/CrashTruth-AnalyzeFrames`
- `/aws/lambda/CrashTruth-FaultAnalyzer`
- `/aws/lambda/CrashTruth-ReportGenerator`
- `/aws/lambda/CrashTruth-Tracker`
- `/aws/lambda/CreateUpload`
- `/aws/lambda/ExtractFramesTrigger`
- `/aws/lambda/taxbuddy-daily-ingest`
- `/aws/lambda/taxbuddy-embed`
- `/aws/lambda/taxbuddy-process-html`
- `/aws/lambda/uploadurlsintos3`

**SageMaker Logs:**
- `/aws/sagemaker/Endpoints/*` (multiple endpoints)
- `/aws/sagemaker/studio`

---

## 📋 Usage Examples

### Example 1: List All Log Groups

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "query_type": "logs",
    "list_log_groups": true
  }' \
  response.json && cat response.json | python3 -m json.tool
```

**Returns:**
- List of all CloudWatch Log Groups
- Storage size for each
- Retention policy

---

### Example 2: Query Logs from a Specific Lambda Function

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "query_type": "logs",
    "log_group_name": "/aws/lambda/CrashTruth-AnalyzeFrames",
    "hours_back": 24,
    "limit": 100
  }' \
  response.json && cat response.json | python3 -m json.tool
```

**Parameters:**
- `query_type`: "logs" (required for log queries)
- `log_group_name`: Name of the log group (required)
- `hours_back`: How far back to search (default: 1 hour)
- `limit`: Max number of log events (default: 100, max: 10000)

**Returns:**
- Log events with timestamps
- Log stream names
- Event messages
- Total count

---

### Example 3: Search Logs with a Filter Pattern

Find ERROR messages in logs:

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "query_type": "logs",
    "log_group_name": "/aws/lambda/CrashTruth-AnalyzeFrames",
    "filter_pattern": "ERROR",
    "hours_back": 48,
    "limit": 50
  }' \
  response.json && cat response.json | python3 -m json.tool
```

**Filter Pattern Examples:**
- `"ERROR"` - Find lines containing "ERROR"
- `"[level=ERROR]"` - CloudWatch Logs Insights pattern
- `"Exception"` - Find exceptions
- `"timeout"` - Find timeout errors
- `"?ERROR ?WARN"` - Find ERROR OR WARN

---

### Example 4: Query Specific Log Streams

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "query_type": "logs",
    "log_group_name": "/aws/lambda/CreateUpload",
    "log_stream_names": ["2025/10/26/[$LATEST]abc123"],
    "hours_back": 6,
    "limit": 200
  }' \
  response.json && cat response.json | python3 -m json.tool
```

---

### Example 5: Get Lambda Invocation Metrics

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "query_type": "metrics",
    "namespace": "AWS/Lambda",
    "metric_name": "Invocations",
    "statistics": ["Sum"],
    "period": 300,
    "hours_back": 24
  }' \
  response.json && cat response.json | python3 -m json.tool
```

**Parameters:**
- `query_type`: "metrics" (or omit - metrics is default)
- `namespace`: AWS service namespace (AWS/Lambda, AWS/EC2, etc.)
- `metric_name`: Specific metric name
- `statistics`: ["Average", "Sum", "Maximum", "Minimum", "SampleCount"]
- `period`: Data point interval in seconds (60, 300, 3600, etc.)
- `hours_back`: Time range

---

### Example 6: Get Metrics for Specific Lambda Function

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "namespace": "AWS/Lambda",
    "metric_name": "Duration",
    "dimensions": [
      {
        "Name": "FunctionName",
        "Value": "CrashTruth-AnalyzeFrames"
      }
    ],
    "statistics": ["Average", "Maximum"],
    "period": 300,
    "hours_back": 12
  }' \
  response.json && cat response.json | python3 -m json.tool
```

---

### Example 7: Get Lambda Error Metrics

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "namespace": "AWS/Lambda",
    "metric_name": "Errors",
    "dimensions": [
      {
        "Name": "FunctionName",
        "Value": "CrashTruth-AnalyzeFrames"
      }
    ],
    "statistics": ["Sum"],
    "period": 300,
    "hours_back": 24
  }' \
  response.json && cat response.json | python3 -m json.tool
```

---

### Example 8: Get SageMaker Endpoint Logs

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "query_type": "logs",
    "log_group_name": "/aws/sagemaker/studio",
    "hours_back": 24,
    "limit": 100
  }' \
  response.json && cat response.json | python3 -m json.tool
```

---

### Example 9: Search for Specific Log Groups

```bash
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "query_type": "logs",
    "list_log_groups": true,
    "log_group_prefix": "/aws/lambda/CrashTruth"
  }' \
  response.json && cat response.json | python3 -m json.tool
```

**Returns:** Only log groups starting with "/aws/lambda/CrashTruth"

---

## 📊 Common CloudWatch Metrics

### Lambda Metrics (`AWS/Lambda`)
- **Invocations** - Number of times function was invoked
- **Errors** - Number of errors
- **Duration** - Execution time in milliseconds
- **Throttles** - Number of throttled invocations
- **ConcurrentExecutions** - Concurrent executions
- **DeadLetterErrors** - Failed async invocations

### EC2 Metrics (`AWS/EC2`)
- **CPUUtilization** - CPU percentage
- **NetworkIn** - Network bytes in
- **NetworkOut** - Network bytes out
- **DiskReadBytes** - Disk read bytes
- **DiskWriteBytes** - Disk write bytes

### RDS Metrics (`AWS/RDS`)
- **CPUUtilization** - CPU percentage
- **DatabaseConnections** - Number of connections
- **FreeStorageSpace** - Available storage
- **ReadLatency** - Read operation latency
- **WriteLatency** - Write operation latency

### API Gateway Metrics (`AWS/ApiGateway`)
- **Count** - Total API requests
- **4XXError** - Client-side errors
- **5XXError** - Server-side errors
- **Latency** - Request latency

---

## 🔎 CloudWatch Logs Filter Pattern Examples

### Simple Text Matching
```json
{
  "filter_pattern": "ERROR"
}
```

### JSON Log Filtering
```json
{
  "filter_pattern": "{ $.level = \"ERROR\" }"
}
```

### Multiple Conditions
```json
{
  "filter_pattern": "?ERROR ?WARN ?CRITICAL"
}
```

### Exclude Pattern
```json
{
  "filter_pattern": "-\"INFO\""
}
```

### Field Extraction
```json
{
  "filter_pattern": "[timestamp, request_id, level, message]"
}
```

---

## 💡 Python Script Example

Save this as `query_cloudwatch.py`:

```python
import boto3
import json

def query_logs(log_group, hours=24, filter_pattern=None):
    """Query CloudWatch logs from target account"""
    
    lambda_client = boto3.client('lambda')
    
    payload = {
        "query_type": "logs",
        "log_group_name": log_group,
        "hours_back": hours,
        "limit": 100
    }
    
    if filter_pattern:
        payload["filter_pattern"] = filter_pattern
    
    response = lambda_client.invoke(
        FunctionName='CloudWatchCrossAccountFetcher',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    data = json.loads(result['body'])
    
    print(f"Log Group: {log_group}")
    print(f"Events Found: {data['data']['events_count']}")
    print("\nLog Events:")
    
    for event in data['data']['events']:
        print(f"\n[{event['timestamp']}] {event['logStreamName']}")
        print(event['message'])

# Usage
query_logs("/aws/lambda/CrashTruth-AnalyzeFrames", hours=24, filter_pattern="ERROR")
```

Run it:
```bash
python3 query_cloudwatch.py
```

---

## 🎯 Real-World Use Cases

### 1. Monitor Application Errors
```bash
# Get error logs from all Lambda functions
for func in CrashTruth-AnalyzeFrames CreateUpload ExtractFramesTrigger; do
  aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
    --cli-binary-format raw-in-base64-out \
    --payload "{\"query_type\":\"logs\",\"log_group_name\":\"/aws/lambda/$func\",\"filter_pattern\":\"ERROR\",\"hours_back\":24,\"limit\":50}" \
    response.json
  cat response.json | python3 -m json.tool
done
```

### 2. Track Lambda Performance
```bash
# Get duration metrics for all Lambda functions
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "namespace": "AWS/Lambda",
    "metric_name": "Duration",
    "statistics": ["Average", "Maximum", "Minimum"],
    "period": 300,
    "hours_back": 24
  }' \
  response.json && cat response.json | python3 -m json.tool
```

### 3. Incident Investigation
```bash
# Search for exceptions in specific time window
aws lambda invoke --function-name CloudWatchCrossAccountFetcher \
  --cli-binary-format raw-in-base64-out \
  --payload '{
    "query_type": "logs",
    "log_group_name": "/aws/lambda/CrashTruth-FaultAnalyzer",
    "filter_pattern": "?Exception ?Error ?Traceback",
    "hours_back": 6,
    "limit": 200
  }' \
  response.json && cat response.json | python3 -m json.tool
```

---

## 📈 Response Format

### Metrics Response
```json
{
  "statusCode": 200,
  "body": {
    "message": "Successfully fetched CloudWatch metrics",
    "data": {
      "metric_statistics": [
        {
          "Timestamp": "2025-10-26 03:19:00+00:00",
          "Sum": 446.0,
          "Unit": "Count"
        }
      ],
      "metric_label": "Invocations",
      "available_metrics": [...]
    }
  }
}
```

### Logs Response
```json
{
  "statusCode": 200,
  "body": {
    "message": "Successfully fetched CloudWatch logs",
    "data": {
      "log_group": "/aws/lambda/MyFunction",
      "events_count": 25,
      "events": [
        {
          "timestamp": "2025-10-26T08:15:30",
          "message": "START RequestId: abc-123",
          "logStreamName": "2025/10/26/[$LATEST]xyz",
          "eventId": "12345"
        }
      ],
      "searched_from": "2025-10-25T08:15:30",
      "searched_to": "2025-10-26T08:15:30",
      "filter_pattern": "ERROR"
    }
  }
}
```

---

## 🚨 Important Notes

1. **Log Retention**: Logs are only available based on retention settings
2. **Limits**: Default limit is 100 events, max is 10,000 per query
3. **Time Range**: Logs can be queried up to the retention period
4. **Permissions**: The target account role already has CloudWatch Logs permissions
5. **Cost**: CloudWatch Logs queries are billed at ~$0.005 per GB scanned

---

## 🔐 Security

All queries use:
- ✅ Temporary credentials (1-hour expiry)
- ✅ Cross-account IAM role assumption
- ✅ Read-only permissions
- ✅ CloudTrail audit logging
- ✅ No permanent credentials stored

---

**You can now query both metrics AND logs from the target account!** 🎉


