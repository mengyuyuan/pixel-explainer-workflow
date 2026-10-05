#!/usr/bin/env python3
"""Time-warp scan (「时间扫描」) on an already-shot video: a glowing line sweeps across the frame, and every pixel the line has
passed freezes at the moment it was passed. Whatever moves while the line crosses it gets stretched, bent or duplicated.
Phone apps only offer this live while filming; this works on any clip after the fact.

Per frame: rows (scan "down"/"up") or columns ("right"/"left") between the line's previous and current position are copied
from the current frame into a frozen canvas; the output is the canvas behind the line and the live frame ahead of it. When
a sweep ends, the fully frozen frame holds for --hold seconds, then a flash returns to live video until the next sweep.
Usage: python time_scan.py in.mp4 out.mp4 --scans down:1.0:4.0[,right:7.0:3.5 ...] [--t0 S] [--dur S] [--width 1920]
                           [--hold 1.2] [--color 40,220,255] [--audio music.wav [--audio-start S]] [--label "AI 拓展 · 时间扫描"]
--scans: direction:start:duration, times on the output clock. Needs numpy, opencv, Pillow (for --label), ffmpeg."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-edit.txt"))
try:
    import numpy as np, cv2
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"time_scan.py: missing Python package '{e.name}'. Install (~250 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("time_scan.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
T0, DUR, OW, HOLD = opt("--t0", 0.0), opt("--dur", 0.0), opt("--width", 1920), opt("--hold", 1.2)
COLOR = np.array([float(v) for v in opt("--color", "40,220,255").split(",")], np.float32) / 255
AUDIO, ASTART, LABEL = opt("--audio", ""), opt("--audio-start", 0.0), opt("--label", "")
if "--scans" not in sys.argv: sys.exit("need --scans direction:start:duration[,...], e.g. --scans down:1:4,right:7:3.5")
SCANS = []
for s in opt("--scans", "").split(","):
    d, a, b = s.split(":"); assert d in ("down", "up", "right", "left"), d
    SCANS.append((d, float(a), float(b)))
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                           "stream=width,height,r_frame_rate:format=duration", "-of", "json", src]))
W0, H0 = info["streams"][0]["width"], info["streams"][0]["height"]; RATE = info["streams"][0]["r_frame_rate"]
num, den = map(int, RATE.split("/")); FPS = num / den
DUR = DUR or float(info["format"]["duration"]) - T0
OH = int(round(OW * H0 / W0 / 2) * 2)
font = None
if LABEL:
    for fp in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"):
        if os.path.exists(fp): font = ImageFont.truetype(fp, int(OH * 0.034)); break


def active(t):
    for i, (d, a, b) in enumerate(SCANS):
        if a <= t < a + b + HOLD: return i
    return None


def ease(u): return u * u * (3 - 2 * u) * 0.25 + u * 0.75     # mostly linear, soft start and stop


dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{T0:.3f}", "-i", src, "-t", f"{DUR:.3f}", "-vf", f"scale={OW}:{OH}:flags=area",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
tmp = out + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "12", tmp], stdin=subprocess.PIPE)
canvas, cur, done, n, last_end = None, None, 0, 0, -9.0
glow = None
while True:
    buf = dec.stdout.read(OW * OH * 3)
    if len(buf) < OW * OH * 3: break
    f = np.frombuffer(buf, np.uint8).reshape(OH, OW, 3)
    t = n / FPS
    i = active(t)
    if i is None:
        img = f.astype(np.float32)
        if cur is not None: last_end, cur = t, None
    else:
        d, a, b = SCANS[i]
        L = OH if d in ("down", "up") else OW
        if cur != i: canvas, cur, done = f.copy(), i, 0
        u = min(1.0, (t - a) / b); pos = int(round(ease(u) * L))
        if pos > done:                                           # freeze the strip the line just crossed
            sl = slice(done, pos) if d in ("down", "right") else slice(L - pos, L - done)
            if d in ("down", "up"): canvas[sl] = f[sl]
            else: canvas[:, sl] = f[:, sl]
            done = pos
        img = f.astype(np.float32).copy()
        if d == "down": img[:done] = canvas[:done]
        elif d == "up": img[OH - done:] = canvas[OH - done:]
        elif d == "right": img[:, :done] = canvas[:, :done]
        else: img[:, OW - done:] = canvas[:, OW - done:]
        if u < 1:                                                # the scan line: bright core + soft glow
            p = done if d in ("down", "right") else L - done
            ax = np.arange(L, dtype=np.float32)
            g = np.exp(-((ax - p) / 3.0) ** 2) * 1.0 + np.exp(-((ax - p) / 26.0) ** 2) * 0.45
            g = g[:, None, None] if d in ("down", "up") else g[None, :, None]
            img = img * (1 - np.clip(g, 0, 1) * 0.6) + np.clip(g, 0, 1) * COLOR * 255 * 1.1
        elif t - (a + b) < 0.1:                                  # done: small flash
            img = img + 60 * (1 - (t - (a + b)) / 0.1)
    if 0 <= t - last_end < 0.15: img = img + 110 * (1 - (t - last_end) / 0.15)   # back to live: flash
    img = np.clip(img, 0, 255).astype(np.uint8)
    if font:
        im = Image.fromarray(img); dr = ImageDraw.Draw(im); pad = int(OH * 0.014)
        tw = dr.textlength(LABEL, font=font); x0, y0 = int(OW * 0.025), int(OH * 0.035)
        dr.rounded_rectangle([x0, y0, x0 + tw + 2 * pad, y0 + font.size + 2 * pad], radius=pad * 2, fill=(14, 18, 28))
        dr.text((x0 + pad, y0 + pad * 0.6), LABEL, font=font, fill=(255, 255, 255))
        img = np.asarray(im)
    enc.stdin.write(img.tobytes()); n += 1
enc.stdin.close(); enc.wait(); dec.wait()
if AUDIO:
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ss", f"{ASTART:.3f}", "-i", AUDIO, "-map", "0:v:0", "-map", "1:a:0",
                           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={max(0, n / FPS - 0.6):.2f}:d=0.6",
                           "-shortest", out])
    os.remove(tmp)
else: os.replace(tmp, out)
print(f"wrote {out}: {n} frames {OW}x{OH} @ {FPS:.3f} fps, {len(SCANS)} sweeps")
