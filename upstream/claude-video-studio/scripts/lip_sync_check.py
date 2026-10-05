"""Lip-sync check: how closely does a character's mouth follow the vocals, and at what lag?

Mouth metric per frame, from MediaPipe FaceMesh on a 2x crop around the head. Small and stylised faces are missed when
the whole frame is passed in, so the head is cropped first:
  --metric gap    inner-lip gap / face height (landmarks 13-14 over 10-152). Realistic and 3D faces.
  --metric area   teeth + mouth-interior pixels in a box at the mouth centre. Drawn anime mouths: the lip landmarks sit
                  on one ink line, so the gap metric reads "closed" even when teeth show.
Head location: from the green-excess matte (green-screen footage), or --head-box x,y,w,h for composited video.
Vocal envelope: band-passed (250-3500 Hz) RMS per video frame of --audio (default: the video's own audio).
Output: r (mouth vs vocals) at lags -6..+6 frames. Negative lag = the mouth moves before the sound.
Reading it: a real match peaks at about -1 to -2 (lips open slightly before the sound) with r around 0.3 or more. A peak far
from 0 means the clip is offset (shift it, e.g. Kling came back 2 frames early vs its driver); r near 0 means no sync.
Usage: python lip_sync_check.py clip.mp4 [--audio song.wav] [--metric gap|area] [--t0 S --t1 S] [--head-box x,y,w,h]"""
import os, shutil, sys
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-face.txt"))
try:
    import numpy as np, mediapipe as mp
    from PIL import Image
    from scipy.ndimage import gaussian_filter1d
except ImportError as e:
    sys.exit(f"{os.path.basename(__file__)}: missing Python package '{e.name}'. Install (~600 MB, mediapipe 0.10.14 + OpenCV/jax): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit(f"{os.path.basename(__file__)}: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg)")
if not hasattr(mp, "solutions"):
    sys.exit(f"{os.path.basename(__file__)}: mediapipe {mp.__version__} has no legacy FaceMesh API; install the tested version: python3 -m pip install -r {_REQ}")
import subprocess, json
src = sys.argv[1]
opt = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
AUDIO, METRIC, T0, T1, BOX = opt("--audio", src), opt("--metric", "gap"), float(opt("--t0", 0)), opt("--t1"), opt("--head-box")
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                           "stream=width,height,r_frame_rate:format=duration", "-of", "json", src]))
W, H = info["streams"][0]["width"], info["streams"][0]["height"]
num, den = map(int, info["streams"][0]["r_frame_rate"].split("/")); FPS = num / den
T1 = float(T1) if T1 else float(info["format"]["duration"])
raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", str(T0), "-t", str(T1 - T0), "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
F = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
fm = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.2)
C = int(round(0.4 * H)); vals, found = [], 0
for f in F:
    if BOX: x0, y0, bw, bh = map(int, BOX.split(",")); side = max(bw, bh)
    else:
        g = f[..., 1].astype(np.int16) - np.maximum(f[..., 0], f[..., 2]).astype(np.int16); a = g < 30
        rows = np.nonzero(a.sum(1) >= 3)[0]
        if not len(rows): vals.append(np.nan); continue
        top = int(rows[0]); cx = int(np.median(np.nonzero(a[top:top + int(0.17 * H)])[1]))
        side = C; x0 = int(np.clip(cx - side // 2, 0, W - side)); y0 = int(np.clip(top - 10, 0, H - side))
    crop = np.ascontiguousarray(np.asarray(Image.fromarray(f[y0:y0 + side, x0:x0 + side]).resize((side * 2, side * 2), Image.LANCZOS)))
    r = fm.process(crop)
    if not r.multi_face_landmarks: vals.append(np.nan); continue
    found += 1; L = r.multi_face_landmarks[0].landmark; P = lambda k: np.array([x0 + L[k].x * side, y0 + L[k].y * side])
    fh = np.linalg.norm(P(10) - P(152))
    if METRIC == "gap": vals.append(float(np.linalg.norm(P(13) - P(14)) / fh)); continue
    mc = (P(13) + P(14)) / 2; mw = np.linalg.norm(P(61) - P(291)); hw, hh = int(max(10, 0.8 * mw)), int(max(7, 0.5 * mw))
    box = f[int(mc[1]) - hh:int(mc[1]) + hh, int(mc[0]) - hw:int(mc[0]) + hw].astype(np.float32)
    ring = np.concatenate([box[0], box[-1], box[:, 0], box[:, -1]]); skin = np.median(ring, 0)
    far = np.abs(box - skin).max(-1) > 45                                  # clearly not skin: teeth, interior, lip ink
    mx, mn = box.max(-1), box.min(-1); sat = (mx - mn) / (mx + 1e-6)
    vals.append(float((far & ((sat < 0.2) & (mx > 150) | (mx < 150))).sum()))
m = np.array(vals); ok = ~np.isnan(m)
print(f"{src}: {len(m)} frames @ {FPS:g} fps, face found on {found}/{len(m)} ({METRIC})")
if ok.sum() < 0.5 * len(m): sys.exit("too few faces found; pass --head-box x,y,w,h around the head")
m = gaussian_filter1d(np.where(ok, m, np.nanmedian(m)), 0.8)
sr = 48000
pcm = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", str(T0), "-t", str(T1 - T0), "-i", AUDIO, "-vn", "-ac", "1", "-ar", str(sr),
                               "-af", "highpass=f=250,lowpass=f=3500", "-f", "s16le", "-"])
x = np.frombuffer(pcm, np.int16).astype(float)
edges = (np.arange(len(m) + 1) * sr / FPS).astype(int)
v = np.array([np.sqrt((x[edges[i]:edges[i + 1]] ** 2).mean()) if edges[i + 1] <= len(x) else 0 for i in range(len(m))])
v = gaussian_filter1d(v, 0.8); n = len(m)
best = (0, -2)
for k in range(-6, 7):
    a_, b_ = m[max(0, k):n + min(0, k)], v[max(0, -k):n - max(0, k)]
    r = float(np.corrcoef(a_, b_)[0, 1]); best = max(best, (r, k))
    print(f"  lag {k:+d} frames (negative = mouth before sound): r = {r:+.3f}")
print(f"best: lag {best[1]:+d} frames ({best[1] / FPS * 1000:+.0f} ms), r = {best[0]:.2f}")
