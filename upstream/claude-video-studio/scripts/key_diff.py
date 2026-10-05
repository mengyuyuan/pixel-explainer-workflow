"""Colour-difference keyer for AI green-screen video (Gemini / Veo, Kling, 即梦) -> VP9-alpha WebM for HyperFrames.
Why not ffmpeg chromakey: AI greens are desaturated (Veo gave #189E50), so black / grey / white costume parts sit only
~0.17 UV-distance from the key and come out half transparent. The classic colour-difference matte keys on how much
green exceeds the other two channels, which neutral colours, skin, orange and yellow hair never do:
    g = G - max(R, B);  alpha = 1 - clamp((g - LO) / (HI - LO))
Semi-transparent edge pixels are un-mixed against the key colour (F = (C - (1 - a) * K) / a), so the fringe keeps the
character's own colour instead of green (no global despill: it turns yellow hair orange). Small alpha specks off the body
are dropped (largest components kept).
Usage: python scripts/key_diff.py in.mp4 out.webm [--lo 12] [--hi 40] [--scale 1] [--fps 30] [--corner WxH]"""
import os, shutil, sys
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-2d.txt"))
try:
    import numpy as np, scipy.ndimage as ndi
except ImportError as e:
    sys.exit(f"{os.path.basename(__file__)}: missing Python package '{e.name}'. Install (~150 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit(f"{os.path.basename(__file__)}: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg)")
import subprocess, json
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
LO, HI, SCALE, FPS, CORNER = opt("--lo", 12.0), opt("--hi", 40.0), opt("--scale", 1.0), opt("--fps", 0), opt("--corner", "")
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                           "-of", "json", src]))["streams"][0]
W0, H0 = info["width"], info["height"]; W, H = int(round(W0 * SCALE / 2) * 2), int(round(H0 * SCALE / 2) * 2)
num, den = map(int, info["r_frame_rate"].split("/")); rate = FPS or num / den
vf = [f"scale={W}:{H}:flags=lanczos"] if (W, H) != (W0, H0) else []
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src] + (["-vf", ",".join(vf)] if vf else []) + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                       stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", f"{num}/{den}", "-i", "-"]
                       + (["-vf", f"fps={FPS}"] if FPS else []) +
                       ["-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "10M", "-g", "15", out], stdin=subprocess.PIPE)
key, n, stats = None, 0, []
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    f = np.frombuffer(buf, np.uint8).reshape(H, W, 3).astype(np.float32)
    g = f[..., 1] - np.maximum(f[..., 0], f[..., 2])
    a = 1 - np.clip((g - LO) / (HI - LO), 0, 1)
    if key is None:                                            # key colour: median of clearly-background pixels, frame 0
        key = np.median(f[g > HI + 10], axis=0); print("key colour", "#%02X%02X%02X" % tuple(int(v) for v in key))
    lab, nl = ndi.label(a > 0.5)                               # drop specks: keep components >= 2% of the largest
    if nl > 1:
        sizes = ndi.sum(np.ones_like(a), lab, range(1, nl + 1)); keep = np.zeros(nl + 1, bool); keep[1:] = sizes >= 0.02 * sizes.max()
        body = ndi.binary_dilation(keep[lab], iterations=3); a = np.where(body, a, 0)
    if CORNER:
        cw, ch = map(int, CORNER.split("x")); a[H - int(ch * SCALE):, W - int(cw * SCALE):] = 0
    edge = (a > 0.02) & (a < 0.98)                             # un-mix the fringe against the key colour
    af = np.maximum(a[..., None], 0.02)
    fg = np.where(edge[..., None], np.clip((f - (1 - af) * key) / af, 0, 255), f)
    stats.append(float((a > 0.5).mean()))
    enc.stdin.write(np.dstack([fg, a[..., None] * 255]).astype(np.uint8).tobytes()); n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print(f"wrote {out}: {n} frames {W}x{H} @ {rate:g} fps, opaque area {min(stats):.3f}..{max(stats):.3f}")
