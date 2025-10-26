import boto3, json, os

# ===== CONFIG =====
MC_ENDPOINT = "https://mediaconvert.us-east-1.amazonaws.com"
ROLE_ARN    = "arn:aws:iam::993260645905:role/media"
BUCKET_OUT  = "crashtruth-frames"
# ===================

mc = boto3.client("mediaconvert", endpoint_url=MC_ENDPOINT)

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))
    
    # extract the video path from the S3 event
    record = event["Records"][0]
    bucket = record["s3"]["bucket"]["name"]
    key    = record["s3"]["object"]["key"]

    if not key.endswith(".mp4"):
        print("Not an mp4 file. Skipping.")
        return {"status": "skipped"}

    # derive base filename
    filename = key.split("/")[-1]
    base = filename.rsplit(".", 1)[0]
    dest = f"s3://{BUCKET_OUT}/{base}/"

    print(f"Starting MediaConvert job for {filename}")

    # job settings
    job = {
      "Role": ROLE_ARN,
      "Settings": {
        "Inputs": [{"FileInput": f"s3://{bucket}/{key}"}],
        "OutputGroups": [
          {  # (A) small MP4 (MediaConvert requires one video output)
            "Name": "MP4 Group",
            "OutputGroupSettings": {
              "Type": "FILE_GROUP_SETTINGS",
              "FileGroupSettings": {"Destination": dest}
            },
            "Outputs": [{
              "NameModifier": "_preview",
              "ContainerSettings": {"Container": "MP4", "Mp4Settings": {}},
              "VideoDescription": {
                "CodecSettings": {
                  "Codec": "H_264",
                  "H264Settings": {
                    "RateControlMode": "CBR",
                    "Bitrate": 500000,
                    "GopSize": 60,
                    "GopSizeUnits": "FRAMES"
                  }
                }
              }
            }]
          },
          {  # (B) frame capture @ 5 fps
            "Name": "FrameCapture Group",
            "OutputGroupSettings": {
              "Type": "FILE_GROUP_SETTINGS",
              "FileGroupSettings": {"Destination": dest}
            },
            "Outputs": [{
              "ContainerSettings": {"Container": "RAW"},
              "VideoDescription": {
                "CodecSettings": {
                  "Codec": "FRAME_CAPTURE",
                  "FrameCaptureSettings": {
                    "FramerateNumerator": 5,
                    "FramerateDenominator": 1,
                    "Quality": 80
                  }
                }
              }
            }]
          }
        ]
      }
    }

    # submit the job
    resp = mc.create_job(**job)
    job_id = resp["Job"]["Id"]
    print(f"✅ Frame extraction started for {filename} → JobID: {job_id}")

    return {"status": "started", "jobId": job_id, "video": filename}
