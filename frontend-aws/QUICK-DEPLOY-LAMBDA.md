# Quick Lambda Deployment - Check Processed Video

## 🚀 Fast Deployment Steps

### 1. Create Lambda Function (AWS Console)

1. Go to: https://console.aws.amazon.com/lambda
2. Click **Create function**
3. Settings:
   - Name: `CrashTruth-CheckProcessedVideo`
   - Runtime: `Python 3.12`
   - Role: Use existing role or create new with S3 read permissions
4. Click **Create**
5. Copy-paste code from `lambda-check-processed-video.py`
6. Click **Deploy**

### 2. Set Lambda Configuration

- **Memory**: 256 MB
- **Timeout**: 30 seconds

### 3. Add S3 Permissions to Lambda Role

Go to IAM → Roles → Your Lambda Role → Add inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetObject"],
      "Resource": [
        "arn:aws:s3:::crashtruth-raw-saivineethpinnoju",
        "arn:aws:s3:::crashtruth-raw-saivineethpinnoju/*"
      ]
    }
  ]
}
```

### 4. Add to API Gateway

1. Go to: https://console.aws.amazon.com/apigateway
2. Select your API: `c7fyq6f6v5`
3. Create Resource: `/check-processed`
4. Create Method: `POST`
5. Integration: Lambda Function
6. Lambda: `CrashTruth-CheckProcessedVideo`
7. ✅ Enable **Lambda Proxy Integration**
8. Enable CORS
9. **Deploy to Stage**: `prod`

### 5. Test It!

```bash
curl -X POST https://c7fyq6f6v5.execute-api.us-west-1.amazonaws.com/prod/check-processed \
  -H "Content-Type: application/json" \
  -d '{"uploadTimestamp": "2024-10-26T10:00:00.000Z"}'
```

Expected: `{"found": false, "message": "No processed video found yet"}`

---

## ✅ Done!

Your frontend will now:
- ⏱️ Wait 20 seconds after upload
- 🔄 Poll every 10 seconds
- 📹 Display processed video when found

---

## 🐛 Troubleshooting

| Error | Solution |
|-------|----------|
| `403 Forbidden` | Check S3 permissions in IAM role |
| `CORS error` | Enable CORS in API Gateway |
| `Timeout` | Increase Lambda timeout to 30s |
| `Not found` | Verify API Gateway endpoint URL |

---

## 📊 How It Works

```
Upload → Record Time → Progress Page
                            ↓
                   [Wait 20 seconds]
                            ↓
                   [Poll every 10s]
                            ↓
              Lambda checks S3 for new video.mp4
                            ↓
              Returns URL → Display in player
```

---

## 🎯 Expected Behavior

- User uploads video at `10:30:00`
- Processing creates `processed/folder/video.mp4` at `10:32:15`
- Lambda finds it (because `10:32:15 > 10:30:00`)
- Video displays on progress page
- Polling stops automatically

That's it! 🎉

