"""Recolour a character's irises across a green-screen clip, so the eyes match the other shots.
Why: AI video generators copy the input image's face. One clip generated from a 3D render came back with that model's
yellow-green irises while the clips generated from the illustration had blue ones. Per frame: find the head from the
green-excess matte, run MediaPipe FaceMesh (refined; iris landmarks 468-477) on a 2x head crop, then inside each iris disc
recolour only iris-coloured pixels (hue 20-120, some saturation). Eyelid skin (pink), eye whites (unsaturated) and the
pupil (dark) are left alone. Input: green-screen footage, any size. Needs mediapipe, scipy, Pillow.
Usage: python scripts/recolor_iris.py <in.mp4> <out.mp4> [--hue 205] [--debug dir]"""
import os, shutil, sys
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-face.txt"))
try:
    import numpy as np, mediapipe as mp
    from PIL import Image
    from scipy.ndimage import gaussian_filter
except ImportError as e:
    sys.exit(f"{os.path.basename(__file__)}: missing Python package '{e.name}'. Install (~600 MB, mediapipe 0.10.14 + OpenCV/jax): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit(f"{os.path.basename(__file__)}: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg)")
if not hasattr(mp, "solutions"):
    sys.exit(f"{os.path.basename(__file__)}: mediapipe {mp.__version__} has no legacy FaceMesh API; install the tested version: python3 -m pip install -r {_REQ}")
import subprocess, json
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
HUE, DBG = opt("--hue", 205.0) / 360.0, opt("--debug", "")
W, H = map(int, subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                         "-of", "csv=p=0:s=x", src]).decode().strip().split("x"))
C = int(round(0.39 * H))                                      # head crop side (280 px at 720p)
raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
F = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
fps = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0", src]).decode().strip()
fm = mp.solutions.face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.2)
eyes = []                                                     # per frame: [(cx, cy, r) left, (cx, cy, r) right] in 720p px, or None
for f in F:
    g = f[..., 1].astype(np.int16) - np.maximum(f[..., 0], f[..., 2]).astype(np.int16)
    a = g < 30; top = int(np.nonzero(a.sum(1) >= 3)[0][0]); cx = int(np.median(np.nonzero(a[top:top + 120])[1]))
    x0 = int(np.clip(cx - C // 2, 0, W - C)); y0 = int(np.clip(top - 10, 0, H - C))
    crop = np.ascontiguousarray(np.asarray(Image.fromarray(f[y0:y0 + C, x0:x0 + C]).resize((C * 2, C * 2), Image.LANCZOS)))
    r = fm.process(crop)
    if not r.multi_face_landmarks: eyes.append(None); continue
    L = r.multi_face_landmarks[0].landmark; P = lambda k: np.array([x0 + L[k].x * C, y0 + L[k].y * C])
    e = []
    for c, ring in ((468, (469, 470, 471, 472)), (473, (474, 475, 476, 477))):
        pc = P(c); e.append((float(pc[0]), float(pc[1]), float(np.mean([np.linalg.norm(P(k) - pc) for k in ring]))))
    eyes.append(e)
found = [i for i, e in enumerate(eyes) if e]
if len(found) < len(eyes) * 0.9: sys.exit(f"iris landmarks on only {len(found)}/{len(eyes)} frames")
for i, e in enumerate(eyes):                                  # fill misses from the nearest detected frame
    if e is None: eyes[i] = eyes[min(found, key=lambda j: abs(j - i))]
E = np.array(eyes)                                            # (frames, 2, 3): light temporal smoothing of centre + radius
E = np.stack([np.convolve(np.pad(E[:, k, q], 1, mode="edge"), np.ones(3) / 3, "valid") for k in range(2) for q in range(3)], 1).reshape(-1, 2, 3)


def rgb2hsv(x):
    mx, mn = x.max(-1), x.min(-1); d = mx - mn + 1e-9
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6
    return np.stack([np.where(mx == mn, 0, h), np.where(mx > 0, (mx - mn) / (mx + 1e-9), 0), mx], -1)


def hsv2rgb(x):
    h, s, v = x[..., 0] * 6, x[..., 1], x[..., 2]; i = np.floor(h).astype(int) % 6; f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    return np.stack([np.choose(i, [v, q, p, p, t, v]), np.choose(i, [t, v, v, q, p, p]), np.choose(i, [p, p, t, v, v, q])], -1)


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", fps, "-i", "-",
                        "-c:v", "libx264", "-crf", "8", "-preset", "medium", "-pix_fmt", "yuv444p", out], stdin=subprocess.PIPE)
stats = []
for i, f in enumerate(F):
    o = f.astype(np.float32) / 255
    for (cx, cy, r) in E[i]:
        R = int(r * 1.6) + 3; xa, xb, ya, yb = int(cx) - R, int(cx) + R + 1, int(cy) - R, int(cy) + R + 1
        patch = o[ya:yb, xa:xb]; hsv = rgb2hsv(patch)
        yy, xx = np.mgrid[ya:yb, xa:xb]; disc = np.clip((r * 1.12 - np.hypot(xx - cx, yy - cy)) / 1.2 + 0.5, 0, 1)
        hue_ok = (hsv[..., 0] > 20 / 360) & (hsv[..., 0] < 120 / 360) & (hsv[..., 1] > 0.1) & (hsv[..., 2] > 0.18)
        m = gaussian_filter(disc * hue_ok, 0.6)
        new = hsv.copy(); new[..., 0] = HUE; new[..., 1] = np.clip(hsv[..., 1] * 1.5 + 0.12, 0, 0.62); new[..., 2] = hsv[..., 2] * 0.9
        o[ya:yb, xa:xb] = patch * (1 - m[..., None]) + hsv2rgb(new) * m[..., None]
        stats.append(float((m > 0.5).sum()))
    if DBG and i % 40 == 0:
        cx, cy = E[i].mean(0)[:2]
        Image.fromarray((o[int(cy) - 40:int(cy) + 40, int(cx) - 70:int(cx) + 70] * 255).astype(np.uint8)).resize((560, 320), Image.NEAREST).save(f"{DBG}/iris-{i:03d}.png")
    enc.stdin.write((o * 255 + 0.5).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()
print(f"wrote {out}: {len(F)} frames, iris landmarks found on {len(found)}, recoloured px per eye median {np.median(stats):.0f}")
