#!/usr/bin/env python3
"""Remove a static burned-in overlay (a camera watermark like 「DJI OSMO POCKET 3」, a date stamp, a logo) from a
locked-off or moving video.

Stroke mask: inside --box, the overlay is the one thing that never changes, so the temporal MINIMUM luminance over many
frames stays high only on a white overlay (use --dark for a dark one: temporal MAXIMUM stays low). The mask is dilated and
feathered so the anti-aliased edges go too.
Fill, per frame:
  transplant (default) - copy the same-shaped patch from --shift (dx,dy px away, e.g. foliage just above the text) and
                         blend it in through the mask: real texture, temporally coherent (it moves with the scene);
  inpaint              - OpenCV Telea inpainting of the strokes: for flat or smooth backgrounds (sky, walls).
Usage: python dewatermark.py in.mp4 out.mp4 --box x0,y0,x1,y1 [--shift 0,-122] [--method transplant|inpaint]
                            [--thr 170] [--dark] [--samples 40] [--debug mask.png]
Coordinates are source pixels. Check the result at 100 % on the busiest background part of the clip.
Needs numpy, opencv, ffmpeg (requirements-edit.txt)."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-edit.txt"))
try:
    import numpy as np, cv2
except ImportError as e:
    sys.exit(f"dewatermark.py: missing Python package '{e.name}'. Install (~250 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("dewatermark.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
if "--box" not in sys.argv: sys.exit("need --box x0,y0,x1,y1 around the watermark")
X0, Y0, X1, Y1 = [int(float(v)) for v in opt("--box").split(",")]
DX, DY = [int(float(v)) for v in opt("--shift", f"0,{-(Y1 - Y0) - 8}").split(",")]
METHOD, THR, DARK, NS, DBG = opt("--method", "transplant"), float(opt("--thr", 170)), "--dark" in sys.argv, int(opt("--samples", 40)), opt("--debug")
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate:format=duration",
                                           "-of", "json", src]))
W, H = info["streams"][0]["width"], info["streams"][0]["height"]; RATE = info["streams"][0]["r_frame_rate"]; DUR = float(info["format"]["duration"])
if METHOD == "transplant" and not (0 <= X0 + DX and X1 + DX <= W and 0 <= Y0 + DY and Y1 + DY <= H):
    sys.exit("--shift moves the box outside the frame; pick another shift or --method inpaint")
bw, bh = X1 - X0, Y1 - Y0
stack = []
for t in np.linspace(0.5, max(0.6, DUR - 0.5), NS):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", src, "-frames:v", "1", "-vf", f"crop={bw}:{bh}:{X0}:{Y0}",
                                   "-f", "rawvideo", "-pix_fmt", "gray", "-"])
    if len(raw) == bw * bh: stack.append(np.frombuffer(raw, np.uint8).reshape(bh, bw))
S = np.stack(stack)
m = (S.max(0) < 255 - THR) if DARK else (S.min(0) > THR)
m = cv2.dilate(m.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
print(f"overlay strokes: {int(m.sum())} px in a {bw}x{bh} box, from {len(stack)} samples")
if DBG: cv2.imwrite(DBG, m * 255)
M = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.6)[..., None]
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
tmp = out + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
n = 0
while True:
    b = dec.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3).copy()
    win = f[Y0:Y1, X0:X1].astype(np.float32)
    if METHOD == "inpaint":
        fill = cv2.inpaint(f[Y0:Y1, X0:X1], m, 5, cv2.INPAINT_TELEA).astype(np.float32)
    else:
        fill = f[Y0 + DY:Y1 + DY, X0 + DX:X1 + DX].astype(np.float32)
    f[Y0:Y1, X0:X1] = (win * (1 - M) + fill * M + 0.5).astype(np.uint8)
    enc.stdin.write(f.tobytes()); n += 1
enc.stdin.close(); enc.wait(); dec.wait()
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", src, "-map", "0:v:0", "-map", "1:a:0?", "-c:v", "copy", "-c:a", "copy", out])
os.remove(tmp)
print(f"wrote {out}: {n} frames ({METHOD})")
