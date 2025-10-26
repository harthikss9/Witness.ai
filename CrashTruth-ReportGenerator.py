import json, os, boto3, datetime, traceback

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime")

REPORTS_BUCKET = os.environ["REPORTS_BUCKET"]
MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
REPORT_FORMAT = os.environ.get("REPORT_FORMAT", "txt")
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "1800"))
TEMPERATURE = float(os.environ.get("TEMPERATURE", "0.3"))

def lambda_handler(event, _):
    try:
        # --- 1️⃣ Parse S3 Event ---
        rec = event["Records"][0]["s3"]
        bucket = rec["bucket"]["name"]
        key = rec["object"]["key"]
        prefix = key.rsplit("/", 1)[0]
        print(f"📥 Processing {bucket}/{key}")

        # --- 2️⃣ Load faults.json ---
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
        faults = json.loads(body)

        # ---------- Helpers ----------
        def pick_primary_and_struck(faults):
            tracks = faults.get("findings", [])
            if not tracks:
                return None, None

            def mttc(t):
                v = t.get("metrics", {}).get("min_ttc_s")
                return float(v) if v is not None else None

            def spd(t):
                return float(t.get("metrics", {}).get("mean_speed_pxps", 0.0))

            def has(t, flag):
                return flag in set(t.get("flags", []))

            ranked = sorted(
                tracks,
                key=lambda t: (
                    (mttc(t) if mttc(t) is not None else 1e9),
                    -int(has(t, "sudden_cutin")),
                    -int(has(t, "hard_approach")),
                    -spd(t),
                ),
            )
            primary = ranked[0]

            slowish = [t for t in tracks if has(t, "very_slow_track") or spd(t) <= 20.0]
            struck = None
            if slowish:
                struck = min(
                    slowish, key=lambda t: (mttc(t) if mttc(t) is not None else 1e9)
                )

            return primary, struck

        def compute_stats(faults):
            tracks = faults.get("findings", [])
            fps = faults.get("fps")
            prefix = faults.get("video_prefix", "")
            video_id = prefix.rsplit("/", 1)[-1] if prefix else prefix

            def risk_of(t): return t.get("risk", "low").lower()
            def mttc(t):
                v = t.get("metrics", {}).get("min_ttc_s")
                return float(v) if v is not None else None
            def spd(t):
                return float(t.get("metrics", {}).get("mean_speed_pxps", 0.0))

            high = [t for t in tracks if risk_of(t) == "high"]
            med = [t for t in tracks if risk_of(t) == "medium"]
            low = [t for t in tracks if risk_of(t) == "low"]

            ttcs = [(t["track_id"], mttc(t)) for t in tracks if mttc(t) is not None]
            worst_ttc = min(ttcs, key=lambda x: x[1]) if ttcs else (None, None)

            fastest = sorted(
                [(t["track_id"], spd(t)) for t in tracks],
                key=lambda x: x[1],
                reverse=True,
            )[:5]

            top_risky = sorted(
                tracks,
                key=lambda t: ((mttc(t) if mttc(t) is not None else 1e9), -spd(t)),
            )[:8]

            def count_flag(flag):
                return sum(1 for t in tracks if flag in set(t.get("flags", [])))

            cause_counts = {
                "sudden_cutin": count_flag("sudden_cutin"),
                "hard_approach": count_flag("hard_approach"),
                "weaving": count_flag("lateral_instability"),
                "very_slow_track": count_flag("very_slow_track"),
                "low_ttc_sustained": count_flag("low_ttc_sustained"),
            }

            primary, struck = pick_primary_and_struck(faults)

            return {
                "video_id": video_id,
                "fps": fps,
                "counts": {
                    "total": len(tracks),
                    "high": len(high),
                    "medium": len(med),
                    "low": len(low),
                },
                "worst_ttc": {"track_id": worst_ttc[0], "seconds": worst_ttc[1]},
                "fastest_tracks": fastest,
                "top_risky": [
                    {
                        "track_id": t["track_id"],
                        "risk": t.get("risk"),
                        "min_ttc_s": mttc(t),
                        "mean_speed_pxps": spd(t),
                        "flags": t.get("flags", []),
                    }
                    for t in top_risky
                ],
                "cause_counts": cause_counts,
                "causes_overall": faults.get("causes", []),
                "thresholds": faults.get("thresholds", {}),
                "summary": faults.get("summary", {}),
                "primary": primary,
                "struck": struck,
            }

        stats = compute_stats(faults)

        def fmt_track(t):
            if not t:
                return "Unknown"
            m = t.get("metrics", {}) if "metrics" in t else {}
            return f"Track {t.get('track_id','?')} (TTC={m.get('min_ttc_s')}, speed(px/s)={m.get('mean_speed_pxps')}, flags={t.get('flags', [])})"

        primary_str = fmt_track(stats["primary"])
        struck_str = fmt_track(stats["struck"])

        # ---------- Prompt ----------
        prompt = f"""
You are an accident reconstruction analyst. You will receive structured data from object tracking and fault analysis.

Here is the data:
{json.dumps(faults, indent=2)}

Write a short, human-readable crash report in simple language.
Explain:
1. What likely happened in the video (sequence of events).
2. Which vehicle(s) are probably at fault and why.
3. Key risky behaviors (tailgating, cutting in, weaving, etc.).
4. Any possible secondary causes (e.g., stationary obstacle, sudden braking).
5. End with safety recommendations in 2–3 bullet points.

Be specific but concise. Avoid technical jargon like 'TTC' or 'pxps' — use phrases like 'time gap' or 'speed difference' instead.
The report should sound like a real crash investigator writing for the public record.

### Ground Truth (Top 8 risky + all tracks)
{json.dumps(stats["top_risky"], indent=2)}
{json.dumps(faults, indent=2)}
"""

        # ---------- Invoke Bedrock ----------
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
        }

        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(payload),
            contentType="application/json",
            accept="application/json",
        )

        result = json.loads(response["body"].read())
        report_text = result["content"][0]["text"]
        timestamp = datetime.datetime.utcnow().isoformat()

        # ---------- Upload ----------
        out_key = f"{prefix}/report.{REPORT_FORMAT}"
        s3.put_object(
            Bucket=REPORTS_BUCKET,
            Key=out_key,
            Body=report_text.encode("utf-8"),
            ContentType="text/markdown",
        )

        print(f"Report generated → s3://{REPORTS_BUCKET}/{out_key}")
        return {
            "statusCode": 200,
            "report_uri": f"s3://{REPORTS_BUCKET}/{out_key}",
            "generated_at": timestamp,
        }

    except Exception as e:
        print("❌ Report generator failed:", repr(e))
        traceback.print_exc()
        return {"statusCode": 500, "error": str(e)}
