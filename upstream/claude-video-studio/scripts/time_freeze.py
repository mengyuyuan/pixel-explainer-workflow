#!/usr/bin/env python3
"""Time-freeze gag (「时间暂停」) from ONE locked-off take: a person and whatever they threw (water, confetti…) hang frozen
mid-action while the rest of the shot keeps playing, then time resumes.

Shoot it like this: tripod, nobody touches the camera; the action (e.g. a splash) happens near the END of the take; the
frozen person stays roughly in their own area while the other person talks; finish with a few seconds of the empty set.

How it works (all in source pixel coordinates, rendered at --width):
  E   empty background = median of frames around --empty-at (nobody in the zone);
  Fz  the freeze frame at --freeze-at (the splash at its most photogenic, e.g. the water arc at full extension);
  U   union of every pose the frozen person takes while the freeze is on screen ([--from, --freeze-at], 4 samples/s):
      |frame - E| (gain-normalised) inside --zone, cleaned, small blobs dropped. Covering EVERY pose matters: a region
      built from the throw alone leaks a ghost arm when the person bends down to pick something up later. Only blobs
      connected to the freeze frame's content are kept, so another person walking through the zone is not frozen;
  W   what the freeze frame adds (|Fz - E| inside the zone: the water);
  alpha = (U ∪ W) dilated, closed and feathered; U itself (slightly dilated) is forced fully opaque.
Each output frame t in [--from, --freeze-at): live frame with Fz composited through alpha, Fz gain-matched per channel on a
ring of background around the region (clouds change the light). From --freeze-at the source simply plays on for --tail s
(the action resumes); the source audio runs straight through.
Writes out.mp4 (+ out.alpha.png and out.preview.jpg for checking).
Usage: python time_freeze.py in.mp4 out.mp4 --freeze-at 135.2 --from 7.7 --empty-at 144.6 --zone 700,100,2300,1750
                             [--tail 4] [--width 1920] [--thr 34]
Needs numpy, scipy, opencv, ffmpeg (requirements-edit.txt)."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-edit.txt"))
try:
    import numpy as np, cv2
    from scipy import ndimage as ndi
except ImportError as e:
    sys.exit(f"time_freeze.py: missing Python package '{e.name}'. Install (~250 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("time_freeze.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d=None, f=float: f(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
TF, T0, TE = opt("--freeze-at"), opt("--from"), opt("--empty-at")
if TF is None or T0 is None or TE is None: sys.exit("need --freeze-at, --from and --empty-at")
TAIL, OW, THR = opt("--tail", 4.0), opt("--width", 1920, int), opt("--thr", 34.0)
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                           "-of", "json", src]))["streams"][0]
DUR = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", src]))
SW, SH = info["width"], info["height"]; OH = int(round(OW * SH / SW / 2) * 2); K = OW / SW
num, den = map(int, info["r_frame_rate"].split("/")); SFPS = num / den; FPS = min(30.0, SFPS)
zone_s = [float(v) for v in sys.argv[sys.argv.index("--zone") + 1].split(",")] if "--zone" in sys.argv else [0, 0, SW, SH]
ZX0, ZY0, ZX1, ZY1 = [int(round(v * K)) for v in zone_s]


def grab(t, w=OW, h=OH):
    t = min(max(0.0, t), DUR - 3.0 / SFPS)
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", src, "-frames:v", "1", "-vf", f"scale={w}:{h}:flags=area",
                                   "-f", "rawvideo", "-pix_fmt", "bgr24", "-"])
    return np.frombuffer(raw, np.uint8).reshape(h, w, 3).astype(np.float32)


# ---- analysis at quarter output resolution ----
q = 4; w4, h4 = OW // q, OH // q
E4 = np.median(np.stack([grab(TE + d, w4, h4) for d in (-0.4, -0.25, -0.1, 0.05, 0.2)]), 0)
zone4 = np.zeros((h4, w4), bool); zone4[ZY0 // q:ZY1 // q, ZX0 // q:ZX1 // q] = True
raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{T0:.3f}", "-i", src, "-t", f"{TF - T0:.3f}", "-vf",
                               f"fps=4,scale={w4}:{h4}:flags=area", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"])
S4 = np.frombuffer(raw, np.uint8).reshape(-1, h4, w4, 3).astype(np.float32)
outside = ~zone4


def presence(F):
    g = E4[outside].sum(0) / np.maximum(F[outside].sum(0), 1) if outside.any() else 1.0
    d = np.abs(cv2.GaussianBlur(F * g, (0, 0), 1.2) - cv2.GaussianBlur(E4, (0, 0), 1.2)).max(2)
    m = ((d > THR) & zone4).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    lab, n = ndi.label(m)
    if n: sizes = ndi.sum(m, lab, range(1, n + 1)); m = np.isin(lab, 1 + np.nonzero(sizes >= max(60, 0.002 * w4 * h4))[0])
    return m.astype(np.uint8)


U = np.zeros((h4, w4), np.uint8)
for F in S4: U |= presence(F)
Fz4 = grab(TF + 0.001, w4, h4)
W4 = presence(Fz4)
# keep only what is connected to the freeze frame's content: someone else walking through the zone is not frozen
lab, n = ndi.label(cv2.dilate(U | W4, np.ones((5, 5), np.uint8)))
keep_ids = np.unique(lab[(W4 > 0) & (lab > 0)])
conn = np.isin(lab, keep_ids)
dropped = int(((U > 0) & ~conn).sum())
U = (U & conn).astype(np.uint8)
reg = cv2.dilate(U | W4, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.018 * w4) | 1,) * 2))
reg = cv2.morphologyEx(reg, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.032 * w4) | 1,) * 2))
alpha = cv2.GaussianBlur(cv2.resize(reg.astype(np.float32), (OW, OH), interpolation=cv2.INTER_LINEAR), (0, 0), 0.0075 * OW)
core = cv2.dilate(cv2.resize(U * 255, (OW, OH), interpolation=cv2.INTER_NEAREST), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.013 * OW) | 1,) * 2)) > 0
alpha[core] = 1.0
alpha = np.clip(alpha, 0, 1)
ys, xs = np.nonzero(alpha > 0.01)
if not len(xs): sys.exit("nothing to freeze: check --zone / --empty-at (the zone must be empty at --empty-at)")
X0, Y0, X1, Y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
A = alpha[Y0:Y1, X0:X1, None]
ringm = (cv2.dilate((alpha > 0.03).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.06 * OW) | 1,) * 2)) > 0) & (alpha <= 0.03)
RING = ringm[Y0:Y1, X0:X1]
Fz = grab(TF + 0.001)
FZ = Fz[Y0:Y1, X0:X1]
cv2.imwrite(out.rsplit(".", 1)[0] + ".alpha.png", (alpha * 255).astype(np.uint8))
prev = (Fz * (1 - 0.45 * alpha[..., None]) + np.array([0, 230, 255]) * 0.45 * alpha[..., None]).astype(np.uint8)
cv2.imwrite(out.rsplit(".", 1)[0] + ".preview.jpg", cv2.resize(prev, (min(1280, OW), int(min(1280, OW) * OH / OW))), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(f"freeze region x {X0}-{X1} y {Y0}-{Y1} (output px), {len(S4)} pose samples, {dropped} px of unrelated motion dropped")

# ---- render ----
dur = TF + TAIL - T0
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{T0:.4f}", "-i", src, "-t", f"{dur:.4f}", "-vf", f"fps={FPS},scale={OW}:{OH}:flags=area",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
tmp = out + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", f"{FPS}", "-i", "-",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "15", tmp], stdin=subprocess.PIPE)
g_s, n = None, 0
while True:
    b = dec.stdout.read(OW * OH * 3)
    if len(b) < OW * OH * 3: break
    f = np.frombuffer(b, np.uint8).reshape(OH, OW, 3).copy()
    t = T0 + n / FPS
    if t < TF - 1e-4:
        L = f[Y0:Y1, X0:X1].astype(np.float32)
        if RING.any():
            g = L[RING].sum(0) / np.maximum(FZ[RING].sum(0), 1)
            g_s = g if g_s is None else 0.85 * g_s + 0.15 * g
        else: g_s = np.ones(3, np.float32)
        f[Y0:Y1, X0:X1] = (L * (1 - A) + np.clip(FZ * g_s, 0, 255) * A + 0.5).astype(np.uint8)
    enc.stdin.write(f.tobytes()); n += 1
enc.stdin.close(); enc.wait(); dec.wait()
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ss", f"{T0:.4f}", "-t", f"{dur:.4f}", "-i", src, "-map", "0:v:0", "-map", "1:a:0?",
                       "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out])
os.remove(tmp)
print(f"wrote {out}: {n} frames ({dur:.2f}s) @ {FPS:g} fps; frozen until {TF:.2f}s, then {TAIL:g}s of the action")
