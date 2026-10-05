#!/usr/bin/env python3
"""Privacy mosaic: find every face in a video and pixelate it, frame by frame, with tracking so no frame slips through.

Detection, per frame:
  - MediaPipe face detection (full-range model) on the whole frame AND on overlapping 2x-upscaled tiles, so small faces
    (60-90 px in a wide 1080p shot) are found;
  - optional --pose: MediaPipe Pose on each tile adds a head box from nose/eyes/ears, which still works when the face is
    half covered (surgical masks, sunglasses, hands) or turned away.
Tracking: detections are matched to tracks by centre distance; boxes are smoothed; a track keeps its last box for --hold
frames after it stops being detected (no one-frame unmasking), and new tracks are back-filled --backfill frames.
Mosaic: the box is padded (--pad) and pixelated in blocks (--block, as a fraction of the face width) under a feathered
ellipse. An audit JSON lists per-frame box counts; frames with fewer boxes than --expect are reported.
Usage: python face_mosaic.py in.mp4 out.mp4 [--block 0.2] [--pad 1.7] [--pose] [--expect N] [--hold 20] [--backfill 10]
                              [--keep-audio] [--debug dir]
Needs: mediapipe 0.10.x (legacy solutions API), numpy, opencv. See requirements-face.txt."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-face.txt"))
try:
    import numpy as np, cv2, mediapipe as mp
except ImportError as e:
    sys.exit(f"face_mosaic.py: missing Python package '{e.name}'. Install (~600 MB): python3 -m pip install -r {_REQ}")
if not hasattr(mp, "solutions"):
    sys.exit(f"face_mosaic.py: mediapipe {mp.__version__} has no legacy solutions API; python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("face_mosaic.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")

src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
BLOCK, PAD, EXPECT, HOLD, BACK = opt("--block", 0.2), opt("--pad", 1.7), opt("--expect", 0), opt("--hold", 20), opt("--backfill", 10)
POSE, KEEPA, DBG = "--pose" in sys.argv, "--keep-audio" in sys.argv, opt("--debug", "")
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                           "-of", "json", src]))["streams"][0]
W, H = info["width"], info["height"]; RATE = info["r_frame_rate"]
fd = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.45)
pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1, min_detection_confidence=0.4) if POSE else None
TW, TH = W // 2 + W // 8, H                        # two overlapping vertical tiles (left / right), upscaled 2x
TILES = [(0, 0), (W - TW, 0)]
poses = [mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1, min_detection_confidence=0.4) for _ in TILES] if POSE else []


def detect(f):
    rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB); boxes = []
    def add(res, ox, oy, sx, sy, sc):
        for d in (res.detections or []):
            b = d.location_data.relative_bounding_box
            boxes.append([ox + b.xmin * sx, oy + b.ymin * sy, b.width * sx, b.height * sy, d.score[0] * sc])
    add(fd.process(rgb), 0, 0, W, H, 1.0)
    for k, (x0, y0) in enumerate(TILES):
        tile = cv2.resize(rgb[y0:y0 + TH, x0:x0 + TW], (TW * 2, TH * 2), interpolation=cv2.INTER_LINEAR)
        add(fd.process(tile), x0, y0, TW, TH, 1.0)
        if POSE:
            r = poses[k].process(cv2.resize(rgb[y0:y0 + TH, x0:x0 + TW], (TW, TH)))
            if r.pose_landmarks:
                L = r.pose_landmarks.landmark
                pts = [(x0 + L[i].x * TW, y0 + L[i].y * TH) for i in (0, 2, 5, 7, 8) if L[i].visibility > 0.5]
                if len(pts) >= 3:
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    s = max(max(xs) - min(xs), 0.6 * (max(ys) - min(ys)), 12) * 1.25
                    cx, cy = (max(xs) + min(xs)) / 2, np.mean(ys) + 0.1 * s
                    boxes.append([cx - s / 2, cy - 0.55 * s, s, 1.15 * s, 0.6])
    # merge overlapping boxes (keep the larger, higher score union)
    boxes.sort(key=lambda b: -b[4]); merged = []
    for b in boxes:
        hit = None
        for m in merged:
            ix = max(0, min(b[0] + b[2], m[0] + m[2]) - max(b[0], m[0])); iy = max(0, min(b[1] + b[3], m[1] + m[3]) - max(b[1], m[1]))
            if ix * iy > 0.25 * min(b[2] * b[3], m[2] * m[3]): hit = m; break
        if hit:
            x0, y0 = min(hit[0], b[0]), min(hit[1], b[1]); x1, y1 = max(hit[0] + hit[2], b[0] + b[2]), max(hit[1] + hit[3], b[1] + b[3])
            hit[:4] = [x0, y0, x1 - x0, y1 - y0]
        else: merged.append(list(b))
    return [b for b in merged if 8 < b[2] < W * 0.6]


# ---- pass 1: detect + track (boxes per frame) ----
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
tracks, frames_boxes, n = [], [], 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    f = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    dets = detect(f)
    for t in tracks: t["matched"] = False
    for d in dets:
        cx, cy = d[0] + d[2] / 2, d[1] + d[3] / 2
        best = min(tracks, key=lambda t: np.hypot(t["c"][0] - cx, t["c"][1] - cy), default=None)
        if best is not None and not best["matched"] and np.hypot(best["c"][0] - cx, best["c"][1] - cy) < 1.2 * max(best["s"], d[2]):
            a = 0.55
            best["c"] = [best["c"][0] * (1 - a) + cx * a, best["c"][1] * (1 - a) + cy * a]
            best["s"] = best["s"] * (1 - a) + max(d[2], d[3] / 1.15) * a
            best["last"] = n; best["matched"] = True; best["hits"] += 1
        else:
            tracks.append({"c": [cx, cy], "s": max(d[2], d[3] / 1.15), "last": n, "first": n, "matched": True, "hits": 1, "id": len(tracks)})
    live = [t for t in tracks if n - t["last"] <= HOLD and t["hits"] >= 2 or (t["last"] == n)]
    frames_boxes.append([[t["id"], t["c"][0], t["c"][1], t["s"]] for t in live])
    n += 1
dec.wait()
# back-fill: a track that appears at frame k also covers frames k-BACK..k-1 at its first position
first_box = {}
for i, fb in enumerate(frames_boxes):
    for b in fb:
        if b[0] not in first_box: first_box[b[0]] = (i, b)
for tid, (i, b) in first_box.items():
    for j in range(max(0, i - BACK), i):
        if not any(x[0] == tid for x in frames_boxes[j]): frames_boxes[j].append(b)
counts = [len(fb) for fb in frames_boxes]
audit = {"frames": n, "fps": RATE, "tracks": len(tracks), "min_boxes": min(counts) if counts else 0,
         "frames_below_expect": [i for i, c in enumerate(counts) if c < EXPECT] if EXPECT else []}

# ---- pass 2: pixelate ----
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
tmp = out + ".video.mp4" if KEEPA else out
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "15", tmp], stdin=subprocess.PIPE)
for i in range(n):
    f = np.frombuffer(dec.stdout.read(W * H * 3), np.uint8).reshape(H, W, 3).copy()
    for _, cx, cy, s in frames_boxes[i]:
        w, h = s * PAD, s * PAD * 1.2
        x0, y0, x1, y1 = int(max(0, cx - w / 2)), int(max(0, cy - h / 2)), int(min(W, cx + w / 2)), int(min(H, cy + h / 2))
        if x1 - x0 < 4 or y1 - y0 < 4: continue
        roi = f[y0:y1, x0:x1]
        bs = max(8, int(s * BLOCK))                     # >= 8 px and ~5 blocks across the face: features unreadable
        small = cv2.resize(roi, (max(1, (x1 - x0) // bs), max(1, (y1 - y0) // bs)), interpolation=cv2.INTER_AREA)
        pix = cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
        m = np.zeros((y1 - y0, x1 - x0), np.float32)
        cv2.ellipse(m, ((x1 - x0) // 2, (y1 - y0) // 2), (max(1, (x1 - x0) // 2), max(1, (y1 - y0) // 2)), 0, 0, 360, 1, -1)
        m = cv2.GaussianBlur(m, (0, 0), max(1, bs * 0.4))[..., None]
        f[y0:y1, x0:x1] = (roi * (1 - m) + pix * m).astype(np.uint8)
    if DBG and i % max(1, n // 24) == 0:
        os.makedirs(DBG, exist_ok=True); cv2.imwrite(f"{DBG}/f{i:05d}.jpg", cv2.resize(f, (W // 2, H // 2)))
    enc.stdin.write(f.tobytes())
enc.stdin.close(); enc.wait(); dec.wait()
if KEEPA:
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", src, "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "copy", "-c:a", "copy", "-shortest", out])
    os.remove(tmp)
json.dump(audit, open(out + ".audit.json", "w"), indent=1)
print(f"wrote {out}: {n} frames, {len(tracks)} face tracks, min boxes/frame {audit['min_boxes']}"
      + (f", frames below {EXPECT}: {len(audit['frames_below_expect'])}" if EXPECT else ""))
