import os, re, json, base64, boto3, traceback

# ✅ Configuration
SM_ENDPOINT    = "huggingface-pytorch-inference-2025-10-26-02-21-39-496"
FRAMES_BUCKET  = os.environ.get("FRAMES_BUCKET", "crashtruth-frames")
REPORTS_BUCKET = os.environ.get("REPORTS_BUCKET", "crashtruth-reports")
MIN_FRAMES     = int(os.environ.get("MIN_FRAMES", "8"))

# ✅ Clients
s3 = boto3.client("s3")
runtime = boto3.client("sagemaker-runtime")

def invoke_model(b64):
    """Invoke the SageMaker endpoint with base64 image input"""
    try:
        response = runtime.invoke_endpoint(
            EndpointName=SM_ENDPOINT,
            ContentType="application/json",
            Body=json.dumps({"inputs": b64})
        )
        result = response["Body"].read()
        return json.loads(result.decode("utf-8"))
    except Exception as e:
        print(f"❌ SageMaker call failed: {str(e)}")
        traceback.print_exc()
        return []

def list_frames(prefix: str):
    """List all frame keys in crashtruth-frames/<video_id>/"""
    keys, token = [], None
    while True:
        args = {"Bucket": FRAMES_BUCKET, "Prefix": prefix}
        if token:
            args["ContinuationToken"] = token
        r = s3.list_objects_v2(**args)
        contents = r.get("Contents", [])
        print(f"📂 Found {len(contents)} items in batch for prefix {prefix}")
        keys += [o["Key"] for o in contents if o["Key"].lower().endswith(".jpg")]
        token = r.get("NextContinuationToken")
        if not r.get("IsTruncated"):
            break
    print(f"✅ Total frames found: {len(keys)}")
    return sorted(keys)

def lambda_handler(event, _):
    print("🚀 Lambda triggered")
    print(json.dumps(event, indent=2))

    try:
        rec = event["Records"][0]["s3"]
        key = rec["object"]["key"]
        print(f"🖼️ Frame uploaded: {key}")
    except Exception as e:
        print("❌ Invalid S3 event:", str(e))
        traceback.print_exc()
        return {"statusCode": 400, "error": "invalid s3 event"}

    # derive video prefix "<videoId>/"
    m = re.match(r"([^/]+)/", key)
    if not m:
        print("❌ Could not extract video ID")
        return {"statusCode": 400, "error": "no video folder found"}
    video_id = m.group(1)
    prefix   = f"{video_id}/"
    print(f"🎞️ Detected video folder: {prefix}")

    report_key = f"{prefix}detections_all.jsonl"

    # skip if already processed
    try:
        s3.head_object(Bucket=REPORTS_BUCKET, Key=report_key)
        print("detections_all.jsonl already exists → skipping")
        return {"statusCode": 200}
    except s3.exceptions.ClientError:
        print("✅ No existing report, proceeding")

    # collect frames
    frames = list_frames(prefix)
    if len(frames) < MIN_FRAMES:
        print(f"⚠️ Only {len(frames)} frames (<{MIN_FRAMES}) → skipping")
        return {"statusCode": 200}

    print(f"🚗 Running inference for {len(frames)} frames on {SM_ENDPOINT}")

    lines = []
    for i, k in enumerate(frames, 1):
        try:
            img = s3.get_object(Bucket=FRAMES_BUCKET, Key=k)["Body"].read()
            b64 = base64.b64encode(img).decode("utf-8")
            detections = invoke_model(b64)
            lines.append(json.dumps({"frame": k, "detections": detections}))
            if i % 10 == 0:
                print(f"Processed {i}/{len(frames)} frames...")
        except Exception as e:
            print(f"❌ Error on frame {k}: {str(e)}")
            traceback.print_exc()

    try:
        s3.put_object(
            Bucket=REPORTS_BUCKET,
            Key=report_key,
            Body="\n".join(lines).encode("utf-8"),
            ContentType="application/json"
        )
        print(f"✅ Uploaded detections to s3://{REPORTS_BUCKET}/{report_key}")
    except Exception as e:
        print("❌ Failed to upload JSONL:", str(e))
        traceback.print_exc()

    print("🎯 Lambda completed successfully")
    return {"statusCode": 200, "report": f"s3://{REPORTS_BUCKET}/{report_key}"}