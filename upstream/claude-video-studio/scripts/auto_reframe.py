#!/usr/bin/env python3
"""Landscape to portrait that follows the subject (「横转竖」): a 9:16 window rides along with the person, like a camera
operator re-framing the shot, instead of a fixed centre crop that loses them.

Pass 1: MediaPipe Pose on every frame (analysis copy, --analyze px wide) gives the subject's centre (mean of the visible
shoulder/hip/head landmarks); gaps are interpolated. The path is then smoothed forwards AND backwards (zero-lag Gaussian,
--smooth seconds), so the frame anticipates the move instead of chasing it, then clamped to stay inside the picture.
--lead shifts the window towards where the subject is heading (look room).
Pass 2: crop at full resolution and scale to --height (default 1920 -> 1080x1920).
--preview also writes a 16:9 side-by-side explainer: the original with the moving window drawn on it + the portrait result.
Usage: python auto_reframe.py in.mp4 out.mp4 [--t0 S] [--dur S] [--aspect 9:16] [--height 1920] [--smooth 0.5] [--lead 0.15]
                              [--analyze 960] [--preview preview.mp4] [--label "AI 拓展 · 横屏自动转竖屏"]
Needs numpy, opencv, mediapipe 0.10.x, Pillow, ffmpeg (requirements-face.txt)."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-face.txt"))
try:
    import numpy as np, cv2, mediapipe as mp
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"auto_reframe.py: missing Python package '{e.name}'. Install (~600 MB): python3 -m pip install -r {_REQ}")
if not hasattr(mp, "solutions"):
    sys.exit(f"auto_reframe.py: mediapipe {mp.__version__} has no legacy solutions API; python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("auto_reframe.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
T0, DUR, OUTH, SMOOTH, LEAD, AW = opt("--t0", 0.0), opt("--dur", 0.0), opt("--height", 1920), opt("--smooth", 0.5), opt("--lead", 0.15), opt("--analyze", 960)
AX, AY = [float(v) for v in opt("--aspect", "9:16").split(":")]
PREVIEW, LABEL = opt("--preview", ""), opt("--label", "")
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                           "stream=width,height,r_frame_rate:format=duration", "-of", "json", src]))
W, H = info["streams"][0]["width"], info["streams"][0]["height"]; RATE = info["streams"][0]["r_frame_rate"]
num, den = map(int, RATE.split("/")); FPS = num / den
DUR = DUR or float(info["format"]["duration"]) - T0
CW = int(round(H * AX / AY / 2) * 2)                         # crop window, full height
OUTW = int(round(OUTH * AX / AY / 2) * 2)
if CW > W: sys.exit(f"a {AX:g}:{AY:g} window at full height ({CW}px) is wider than the video ({W}px)")


def frames(width):
    h = int(round(width * H / W / 2) * 2)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{T0:.3f}", "-i", src, "-t", f"{DUR:.3f}", "-vf", f"scale={width}:{h}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
    while True:
        b = p.stdout.read(width * h * 3)
        if len(b) < width * h * 3: break
        yield np.frombuffer(b, np.uint8).reshape(h, width, 3)
    p.wait()


# ---- pass 1: where is the subject?
pose = mp.solutions.pose.Pose(static_image_mode=False, model_complexity=1, min_detection_confidence=0.4, min_tracking_confidence=0.4)
KEY = [0, 11, 12, 23, 24]                                       # nose, shoulders, hips
xs = []
for f in frames(AW):
    r = pose.process(f)
    if r.pose_landmarks:
        pts = [r.pose_landmarks.landmark[i] for i in KEY if r.pose_landmarks.landmark[i].visibility > 0.5]
        xs.append(np.mean([p.x for p in pts]) * W if pts else np.nan)
    else: xs.append(np.nan)
xs = np.array(xs, np.float64); n = len(xs)
ok = ~np.isnan(xs)
if ok.sum() == 0: sys.exit("no person found in the clip (MediaPipe Pose); try --analyze 1280 or a different clip")
xs = np.interp(np.arange(n), np.where(ok)[0], xs[ok])
vel = np.gradient(xs) * FPS                                    # px/s, for look room
sig = max(1.0, SMOOTH * FPS); k = np.arange(-int(3 * sig), int(3 * sig) + 1); g = np.exp(-0.5 * (k / sig) ** 2); g /= g.sum()
smooth = lambda v: np.convolve(np.pad(v, len(k) // 2, mode="edge"), g, "valid")
cx = smooth(xs + np.clip(smooth(vel) * LEAD, -CW * 0.25, CW * 0.25))
x0 = np.clip(np.round(cx - CW / 2), 0, W - CW).astype(int)
print(f"pass 1: {n} frames, subject found in {ok.mean() * 100:.0f}%, window moves {x0.min()}..{x0.max()} px")

# ---- pass 2: crop (and optional explainer)
font = None
for fp in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"):
    if os.path.exists(fp): font = fp; break
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUTW}x{OUTH}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
pv = None
if PREVIEW:
    PW, PH = 1920, 1080; LW = 1180; LH = int(LW * H / W); RH = 1000; RW = int(RH * AX / AY)
    LX, LY = 40, (PH - LH) // 2 + 30; RX, RY = PW - 40 - RW, 40
    pv = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{PW}x{PH}", "-r", RATE, "-i", "-",
                           "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", PREVIEW + ".video.mp4"], stdin=subprocess.PIPE)
    F1, F2 = (ImageFont.truetype(font, 34), ImageFont.truetype(font, 26)) if font else (None, None)
for i, f in enumerate(frames(W)):
    if i >= n: break
    a = x0[i]; crop = f[:, a:a + CW]
    enc.stdin.write(cv2.resize(crop, (OUTW, OUTH), interpolation=cv2.INTER_AREA).tobytes())
    if pv:
        canvas = np.full((PH, PW, 3), (16, 18, 24), np.uint8)
        small = cv2.resize(f, (LW, LH), interpolation=cv2.INTER_AREA).astype(np.float32)
        sx0, sx1 = int(a * LW / W), int((a + CW) * LW / W)
        small[:, :sx0] *= 0.35; small[:, sx1:] *= 0.35
        canvas[LY:LY + LH, LX:LX + LW] = small.astype(np.uint8)
        canvas[RY:RY + RH, RX:RX + RW] = cv2.resize(crop, (RW, RH), interpolation=cv2.INTER_AREA)
        im = Image.fromarray(canvas); d = ImageDraw.Draw(im)
        d.rectangle([LX + sx0, LY, LX + sx1 - 1, LY + LH - 1], outline=(255, 214, 0), width=4)
        if F1:
            d.text((LX, LY - 52), "原片 16:9（暗处是会被裁掉的部分）", font=F2, fill=(200, 205, 215))
            if LABEL: d.text((LX, 40), LABEL, font=F1, fill=(255, 255, 255))
            tw = d.textlength("AI 取景框", font=F2)
            d.rectangle([LX + sx0, LY, LX + sx0 + tw + 20, LY + 42], fill=(255, 214, 0))
            d.text((LX + sx0 + 10, LY + 6), "AI 取景框", font=F2, fill=(20, 20, 20))
            d.text((RX + 16, RY + RH - 50), "竖屏 9:16 成片", font=F2, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        pv.stdin.write(np.asarray(im).tobytes())
enc.stdin.close(); enc.wait()
if pv:
    pv.stdin.close(); pv.wait(); os.replace(PREVIEW + ".video.mp4", PREVIEW)
print(f"wrote {out}: {n} frames {OUTW}x{OUTH}" + (f" and {PREVIEW}" if PREVIEW else ""))
