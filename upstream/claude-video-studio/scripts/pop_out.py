#!/usr/bin/env python3
"""Pop-out / 「裸眼 3D」: the subject comes out of the picture. Two looks:
  --mode bars    two white bars are laid over the video like the edges of a screen; the scene stays behind them, the
                 subject passes IN FRONT of them and casts a soft shadow on them, so it seems to leave the screen.
                 Works when the subject is cut by the real frame edge (a skater flying over a low camera).
  --mode frame   the video sits in a white-bordered frame on a blurred, darkened copy of itself; whatever part of the
                 subject leaves the frame is drawn outside it. Needs a subject that is whole in the shot. The pop-out
                 switches on at the first frame where the subject is entirely inside the frame, so nothing appears suddenly.
Everything depends on the matte: make it with person_matte.py (--backend vision-fg when the subject holds or rides
something; add --drop-static). Slow motion sells the moment: ramp the clip first with speed_ramp.py ("readout": false,
"punch": false), then matte THAT clip and run this on it.
Usage: python pop_out.py in.mp4 out.mp4 --mattes DIR [--mode bars|frame] [--bars 0.34,0.66] [--bar-width 0.011]
                         [--window 0.14,0.15,0.86,0.85] [--shadow 0.5] [--label "AI 拓展 · 冲出画框"]
in.mp4 must be the clip the mattes were made from (same frames, --t0 0); its audio is copied.
Needs numpy, opencv, Pillow (for --label), ffmpeg."""
import os, sys, json, subprocess, shutil, glob
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-edit.txt"))
try:
    import numpy as np, cv2
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"pop_out.py: missing Python package '{e.name}'. Install (~250 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("pop_out.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
MATTES, MODE, LABEL, SHADOW = opt("--mattes", ""), opt("--mode", "bars"), opt("--label", ""), opt("--shadow", 0.5)
BARS = [float(v) for v in opt("--bars", "0.34,0.66").split(",")]; BARW = opt("--bar-width", 0.011)
WIN = [float(v) for v in opt("--window", "0.14,0.15,0.86,0.85").split(",")]
if not MATTES: sys.exit("pop_out.py: needs --mattes DIR (python person_matte.py in.mp4 DIR --backend vision-fg --drop-static)")
META = json.load(open(os.path.join(MATTES, "meta.json")))
N, FPS, RATE, W, H = META["frames"], META["fps"], META["rate"], META["width"], META["height"]
frame = lambda i: cv2.imread(os.path.join(MATTES, "frames", f"{i:05d}.jpg"))
def mask(i):
    m = cv2.imread(os.path.join(MATTES, "masks", f"{i:05d}.png"), 0)
    return (m if m.shape == (H, W) else cv2.resize(m, (W, H))).astype(np.float32) / 255


font = None
if LABEL:
    for fp, ix in [(p, 11) for p in glob.glob("/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc")] + \
                  [("/System/Library/Fonts/PingFang.ttc", 0), ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
                   ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0)]:
        if os.path.exists(fp):
            try: font = ImageFont.truetype(fp, int(H * 0.034), index=ix); break
            except Exception: pass
# the "screen plane" layer: where bars / border / outside area sit, as alpha + colour
if MODE == "bars":
    plane = np.zeros((H, W), np.float32)
    bw = max(4, int(round(BARW * W)))
    for bx in BARS:
        x = int(round(bx * W - bw / 2)); plane[:, x:x + bw] = 1
    plane = cv2.GaussianBlur(plane, (0, 0), 0.6)
    start = 0
else:
    x0, y0, x1, y1 = int(WIN[0] * W), int(WIN[1] * H), int(WIN[2] * W), int(WIN[3] * H)
    inside = np.zeros((H, W), np.float32); inside[y0:y1, x0:x1] = 1
    bd = max(4, int(0.004 * W))
    border = np.zeros((H, W), np.float32); border[y0 - bd:y1 + bd, x0 - bd:x1 + bd] = 1; border -= inside
    fshadow = cv2.GaussianBlur(np.pad(inside, ((0, 0), (0, 0)))[...], (0, 0), 0.02 * W)       # the frame's own drop shadow
    fshadow = np.roll(fshadow, (int(0.012 * H), int(0.006 * W)), (0, 1)) * (1 - inside) * 0.55
    start = N
    for i in range(N):                                    # pop out only after the subject was once entirely inside
        m = mask(i) > 0.5
        if m.sum() > 400 and not (m & (inside < 0.5)).any(): start = i; break
    if start == N: start = 0
tmp = out + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "15", tmp], stdin=subprocess.PIPE)
off = (int(0.007 * W), int(0.012 * H))                    # subject shadow offset (right, down)
for i in range(N):
    f = frame(i).astype(np.float32); m = mask(i)
    sh = np.roll(cv2.GaussianBlur(m, (0, 0), 0.008 * W), (off[1], off[0]), (0, 1)) * SHADOW
    if MODE == "bars":
        base = f * (1 - plane[..., None]) + 255.0 * plane[..., None]             # bars over the whole scene
        base *= (1 - (sh * plane)[..., None])                                    # her shadow falls on the bars only
        pop = m
    else:
        small = cv2.resize(f, (W // 8, H // 8), interpolation=cv2.INTER_AREA)
        bg = cv2.resize(cv2.GaussianBlur(small, (0, 0), 6), (W, H), interpolation=cv2.INTER_LINEAR)
        g = bg.mean(2, keepdims=True); bg = (g + (bg - g) * 0.6) * 0.38                # blurred, desaturated, dark
        bg *= (1 - fshadow[..., None])
        base = bg * (1 - inside[..., None]) + f * inside[..., None]
        base = base * (1 - border[..., None]) + 250.0 * border[..., None]
        pop = m if i >= start else m * inside
        base *= (1 - (sh * (1 - inside) * (1.0 if i >= start else 0.0))[..., None])   # shadow on the border and outside
    p3 = pop[..., None]
    img = np.clip(base * (1 - p3) + f * p3, 0, 255).astype(np.uint8)
    if font:
        im = Image.fromarray(img[..., ::-1]); dr = ImageDraw.Draw(im); pad = int(H * 0.014)
        tw = dr.textlength(LABEL, font=font); lx, ly = int(W * 0.025), int(H * 0.035)
        dr.rounded_rectangle([lx, ly, lx + tw + 2 * pad, ly + font.size + 2 * pad], radius=pad * 2, fill=(14, 18, 28))
        dr.text((lx + pad, ly + pad * 0.6), LABEL, font=font, fill=(255, 255, 255))
        img = np.asarray(im)[..., ::-1]
    enc.stdin.write(np.ascontiguousarray(img).tobytes())
enc.stdin.close(); enc.wait()
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", src, "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                       "-shortest", "-movflags", "+faststart", out])
os.remove(tmp)
print(f"wrote {out}: {N} frames {W}x{H} @ {FPS:.3f} fps, mode {MODE}" + (f", pop-out from frame {start}" if MODE == "frame" else ""))
