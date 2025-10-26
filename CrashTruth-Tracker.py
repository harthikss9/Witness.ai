import os, json, math, boto3

s3 = boto3.client("s3")

FPS = float(os.environ.get("FPS", "5"))  # we extracted at 5 fps
IOU_THRESH = float(os.environ.get("IOU_THRESH", "0.3"))

def parse_jsonl(b: bytes):
    for line in b.splitlines():
        line = line.strip()
        if line:
            yield json.loads(line)

def iou(a, b):
    ax1, ay1, ax2, ay2 = a["xmin"], a["ymin"], a["xmax"], a["ymax"]
    bx1, by1, bx2, by2 = b["xmin"], b["ymin"], b["xmax"], b["ymax"]
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, inter_x2 - inter_x1), max(0, inter_y2 - inter_y1)
    inter = iw * ih
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter + 1e-6
    return inter / union

def center_wh(box):
    x1, y1, x2, y2 = box["xmin"], box["ymin"], box["xmax"], box["ymax"]
    cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
    w, h = max(1, x2 - x1), max(1, y2 - y1)
    return cx, cy, w, h

def ttc_from_heights(h_prev, h_curr, dt):
    # distance proxy ~ 1/h; TTC = distance / speed ≈ (1/h_curr) / ((1/h_prev - 1/h_curr)/dt)
    if h_prev <= 0 or h_curr <= 0: 
        return None
    d_prev, d_curr = 1.0 / h_prev, 1.0 / h_curr
    v = (d_prev - d_curr) / dt  # positive if approaching
    if v <= 1e-6:
        return None
    return d_curr / v  # seconds

def lambda_handler(event, _):
    # S3 trigger on detections_all.jsonl
    rec = event["Records"][0]["s3"]
    bucket = rec["bucket"]["name"]
    key = rec["object"]["key"]  # <video_id>/detections_all.jsonl
    prefix = key.rsplit("/", 1)[0]

    body = s3.get_object(Bucket=bucket, Key=key)["Body"].read()
    frames = list(parse_jsonl(body))  # [{frame, detections:[{label,score,box:{...}},..]},..]
    # sort by frame name to maintain order
    frames.sort(key=lambda f: f["frame"])

    # Build simple per-frame car boxes
    seq = []
    for i, f in enumerate(frames):
        cars = [d for d in f.get("detections", []) if d.get("label") == "car"]
        boxes = []
        for c in cars:
            b = c.get("box", {})
            boxes.append({
                "xmin": float(b.get("xmin", 0)), "ymin": float(b.get("ymin", 0)),
                "xmax": float(b.get("xmax", 0)), "ymax": float(b.get("ymax", 0)),
                "score": float(c.get("score", 0.0))
            })
        seq.append({"idx": i, "frame": f["frame"], "boxes": boxes})

    # Track with greedy IoU matching
    tracks = []  # [{id, states:[{idx, frame, box, cx,cy,w,h}], ttc_seconds:..., mean_speed_pxps:...}]
    next_id = 1
    active = {}  # track_id -> last(box)

    for step in seq:
        assigned = set()
        # try match each active track to best IoU box
        for tid, last in list(active.items()):
            best_j, best_iou = None, 0.0
            for j, b in enumerate(step["boxes"]):
                if j in assigned: 
                    continue
                i = iou(last, b)
                if i > best_iou:
                    best_iou, best_j = i, j
            if best_j is not None and best_iou >= IOU_THRESH:
                b = step["boxes"][best_j]
                cx, cy, w, h = center_wh(b)
                # append to that track
                for t in tracks:
                    if t["id"] == tid:
                        t["states"].append({"idx": step["idx"], "frame": step["frame"], "box": b, "cx": cx, "cy": cy, "w": w, "h": h})
                        break
                active[tid] = b
                assigned.add(best_j)
            else:
                # no match → retire track
                active.pop(tid, None)

        # any unassigned boxes start new tracks
        for j, b in enumerate(step["boxes"]):
            if j in assigned: 
                continue
            cx, cy, w, h = center_wh(b)
            tracks.append({"id": next_id, "states": [{"idx": step["idx"], "frame": step["frame"], "box": b, "cx": cx, "cy": cy, "w": w, "h": h}]})
            active[next_id] = b
            next_id += 1

    # compute speeds & TTC per track
    for t in tracks:
        states = sorted(t["states"], key=lambda s: s["idx"])
        speeds = []
        ttcs = []
        for a, b in zip(states, states[1:]):
            dt = (b["idx"] - a["idx"]) / FPS
            if dt <= 0: 
                continue
            # pixel speed = center displacement / dt
            dx, dy = (b["cx"] - a["cx"]), (b["cy"] - a["cy"])
            px_speed = math.hypot(dx, dy) / dt  # pixels per second
            speeds.append(px_speed)
            # TTC from box height growth (approach)
            ttc = ttc_from_heights(a["h"], b["h"], dt)
            if ttc:
                ttcs.append(ttc)
        t["mean_speed_pxps"] = round(sum(speeds)/len(speeds), 2) if speeds else 0.0
        t["min_ttc_s"] = round(min(ttcs), 2) if ttcs else None
        # keep only first/last frames and a few samples to limit payload
        t["states"] = states[::max(1, len(states)//10 or 1)]

    out = {
        "video_prefix": prefix,
        "fps": FPS,
        "tracks": tracks,
        "tracks_count": len(tracks)
    }

    out_key = f"{prefix}/tracks.json"
    s3.put_object(Bucket=bucket, Key=out_key, Body=json.dumps(out, indent=2).encode("utf-8"),
                  ContentType="application/json")
    return {"statusCode": 200, "tracks_uri": f"s3://{bucket}/{out_key}"}