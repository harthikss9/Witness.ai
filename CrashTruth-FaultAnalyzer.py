import os, json, math, statistics, boto3

s3 = boto3.client("s3")
REPORTS_BUCKET = os.environ.get("REPORTS_BUCKET", "crashtruth-reports")

TTC_DANGER = float(os.environ.get("TTC_DANGER_S", "2.5"))
TTC_WARN   = float(os.environ.get("TTC_WARN_S", "4.0"))
SPEED_FAST = float(os.environ.get("SPEED_FAST_PXPS", "180"))

LOW_TTC_FRAMES   = int(os.environ.get("LOW_TTC_FRAMES", "3"))
TTC_DROP_S       = float(os.environ.get("TTC_DROP_S", "1.0"))
LATERAL_STD_MIN  = float(os.environ.get("LATERAL_STD_MIN", "5.0"))
CUTIN_TTC_S      = float(os.environ.get("CUTIN_TTC_S", "2.2"))
SPEED_SLOW_PXPS  = float(os.environ.get("SPEED_SLOW_PXPS", "20"))

def load_tracks(bucket: str, key: str):
    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    doc = json.loads(body)
    return doc, doc.get("tracks", []), float(doc.get("fps", 5.0))

def risk_bucket(tracks):
    if any(t.get("min_ttc_s") is not None and t["min_ttc_s"] <= TTC_DANGER for t in tracks):
        return "high", [f"TTC ≤ {TTC_DANGER}s detected"]
    reasons = []
    if any(t.get("min_ttc_s") is not None and t["min_ttc_s"] <= TTC_WARN for t in tracks):
        reasons.append(f"TTC ≤ {TTC_WARN}s on some tracks")
    if any(t.get("mean_speed_pxps", 0) >= SPEED_FAST for t in tracks):
        reasons.append(f"High relative speed (≥ {SPEED_FAST} px/s)")
    if reasons:
        return "medium", reasons
    return "low", ["No critical TTC or speed flags"]

def flags_for_track(t, fps: float):
    flags = []
    states = sorted(t.get("states", []), key=lambda s: s["idx"])
    ttcs = []     # recompute rough TTC series from 'h' if available
    cxs  = []
    for a, b in zip(states, states[1:]):
        dt = (b["idx"] - a["idx"]) / max(1e-6, fps)
        if dt <= 0: 
            continue
        # TTC from heights if present
        ha, hb = a.get("h"), b.get("h")
        if ha and hb and ha > 0 and hb > 0:
            d_prev, d_curr = 1.0/ha, 1.0/hb
            v = (d_prev - d_curr) / dt
            if v > 1e-6:
                ttcs.append(d_curr / v)
        cxs.append(b.get("cx", 0.0))

    # Low TTC sustained
    low_ttc_run = 0
    for val in ttcs:
        if val is not None and val <= TTC_WARN:
            low_ttc_run += 1
        else:
            low_ttc_run = 0
        if low_ttc_run >= LOW_TTC_FRAMES:
            flags.append("low_ttc_sustained")
            break

    # Hard approach (big TTC drop)
    for prev, curr in zip(ttcs, ttcs[1:]):
        if prev is not None and curr is not None and (prev - curr) >= TTC_DROP_S and curr <= TTC_WARN:
            flags.append("hard_approach")
            break

    # Lateral weaving: stddev of cx across states
    if len(cxs) >= 4:
        try:
            if statistics.pstdev(cxs) >= LATERAL_STD_MIN:
                flags.append("lateral_instability")
        except statistics.StatisticsError:
            pass

    # Cut-in: very early TTC low (first few samples)
    early_ttcs = [v for v in ttcs[:max(2, LOW_TTC_FRAMES)] if v is not None]
    if early_ttcs and min(early_ttcs) <= CUTIN_TTC_S:
        flags.append("sudden_cutin")

    # Stationary obstacle proxy: this track slow while others show low TTC
    # (decided at video-level later; here we just mark if slow)
    if t.get("mean_speed_pxps", 0.0) <= SPEED_SLOW_PXPS:
        flags.append("very_slow_track")

    return list(sorted(set(flags)))

def infer_causes(all_track_flags):
    causes = set()
    if any("low_ttc_sustained" in f for f in all_track_flags):
        causes.add("tailgating")
    if any("hard_approach" in f for f in all_track_flags):
        causes.add("hard_approach")
    if any("sudden_cutin" in f for f in all_track_flags):
        causes.add("cut_in")
    if any("lateral_instability" in f for f in all_track_flags):
        causes.add("weaving")
    # stationary obstacle heuristic: at least one very slow track AND another track with low TTC
    very_slow = any("very_slow_track" in f for f in all_track_flags)
    low_ttc   = any("low_ttc_sustained" in f or "hard_approach" in f for f in all_track_flags)
    if very_slow and low_ttc:
        causes.add("stationary_obstacle_ahead")
    return sorted(causes)

def lambda_handler(event, _):
    try:
        rec = event["Records"][0]["s3"]
        bucket = rec["bucket"]["name"]      # crashtruth-reports
        key    = rec["object"]["key"]       # <videoId>/tracks.json
        video_prefix = key.rsplit("/", 1)[0]

        print("📥 tracks.json:", bucket, key)
        doc, tracks, fps = load_tracks(bucket, key)

        overall_risk, reasons = risk_bucket(tracks)

        findings = []
        all_flags = []
        for t in tracks:
            flags = flags_for_track(t, fps)
            all_flags.append(flags)
            risk = ("high" if (t.get("min_ttc_s") is not None and t["min_ttc_s"] <= TTC_DANGER)
                    else "medium" if (t.get("min_ttc_s") is not None and t["min_ttc_s"] <= TTC_WARN) or (t.get("mean_speed_pxps", 0) >= SPEED_FAST)
                    else "low")
            findings.append({
                "track_id": t["id"],
                "risk": risk,
                "flags": flags,
                "metrics": {
                    "min_ttc_s": t.get("min_ttc_s"),
                    "mean_speed_pxps": t.get("mean_speed_pxps", 0.0),
                    "lateral_std_px": None  # (kept for future; computed only if needed)
                }
            })

        causes = infer_causes(all_flags)

        out = {
            "video_prefix": video_prefix,
            "fps": fps,
            "summary": {"highest_risk": overall_risk, "reasons": reasons},
            "causes": causes,
            "findings": findings,
            "thresholds": {
                "ttc_danger_s": TTC_DANGER,
                "ttc_warn_s": TTC_WARN,
                "speed_fast_pxps": SPEED_FAST,
                "low_ttc_frames": LOW_TTC_FRAMES,
                "ttc_drop_s": TTC_DROP_S,
                "lateral_std_min": LATERAL_STD_MIN,
                "cutin_ttc_s": CUTIN_TTC_S,
                "speed_slow_pxps": SPEED_SLOW_PXPS
            }
        }

        out_key = f"{video_prefix}/faults.json"
        s3.put_object(
            Bucket=REPORTS_BUCKET,
            Key=out_key,
            Body=json.dumps(out, indent=2).encode("utf-8"),
            ContentType="application/json"
        )
        print(f"✅ wrote s3://{REPORTS_BUCKET}/{out_key}")
        return {"statusCode": 200, "faults_uri": f"s3://{REPORTS_BUCKET}/{out_key}"}

    except Exception as e:
        print("❌ fault lambda error:", repr(e))
        return {"statusCode": 500, "error": str(e)}
