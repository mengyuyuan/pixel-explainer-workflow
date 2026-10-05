#!/usr/bin/env python3
"""「人物定格出场介绍」: the clip plays, freezes on the beat, the chosen person pops out (colour, white outline) over a
dimmed, desaturated freeze-frame with a name card, then the clip plays on; optionally ends on a group freeze.

Person cutouts work in crowded, locked-off shots (one person per box):
  1. everything outside the person's box (+margin) is painted with a clean background plate (temporal median of the clip),
     so MediaPipe Pose and the segmenter only see that person;
  2. selfie segmentation (general model) on a square crop around the box;
  3. a pose-guided body envelope (skeleton drawn as thick limbs + head disc) removes neighbours and props that touch them;
  4. static props that match the plate (a parked car behind an arm) are dropped unless the pixel is a confident person pixel
     on the skeleton core; interior holes are filled; a guided filter makes the edge follow the image.
  On macOS, step 2 uses Apple Vision's person segmentation instead (vision_matte.py, no download): its matte keeps hair and
  loose clothes, so steps 3-4 shrink to "largest blob, holes filled"; a person may set "envelope": true to get the pose
  envelope back when a neighbour touches them, and "margin": px (default 40) to paint closer to the box when a
  neighbour's shoe or hand sits right next to it. "matte": "mediapipe" in the config forces the old path.
Config (JSON):
  {"video": "in.mp4", "audio": "music.wav", "audio_start": 0, "width": 1920, "bpm": 96,
   "timeline": [{"play": [0, 1.25]},
                {"freeze": 1.25, "hold": 1.25, "people": [{"box": [x0, y0, x1, y1], "name": "红裤子", "sub": "MEMBER 01",
                                                           "tag": "节奏担当", "color": "#FF4D8D"}]},
                {"group": 6.25, "hold": 2.5, "title": "全员到齐！", "sub": "...", "people": [{"box": [...]}, ...]}],
   "label": "AI 复刻 · 人物定格出场"}
  Boxes are in output pixels (after scaling to "width"). Freeze/group times are source seconds.
Usage: python freeze_intro.py config.json out.mp4 [--debug dir]
Needs numpy, opencv-contrib, mediapipe 0.10.x, scipy, Pillow, ffmpeg (requirements-face.txt)."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-face.txt"))
try:
    import numpy as np, cv2, mediapipe as mp
    from scipy import ndimage as ndi
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"freeze_intro.py: missing Python package '{e.name}'. Install (~600 MB): python3 -m pip install -r {_REQ}")
if not hasattr(mp, "solutions"):
    sys.exit(f"freeze_intro.py: mediapipe {mp.__version__} has no legacy solutions API; python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("freeze_intro.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
C = json.load(open(sys.argv[1])); OUT = sys.argv[2]
DBG = sys.argv[sys.argv.index("--debug") + 1] if "--debug" in sys.argv else ""
SRC = C["video"]; OW = C.get("width", 1920)
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate",
                                           "-of", "json", SRC]))["streams"][0]
OH = int(round(OW * info["height"] / info["width"] / 2) * 2); RATE = info["r_frame_rate"]
num, den = map(int, RATE.split("/")); FPS = num / den
FONT = next((p for p in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
                         "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc") if os.path.exists(p)), None)
fnt = lambda px, idx=0: ImageFont.truetype(FONT, int(px), index=idx) if FONT else ImageFont.load_default()
SEMIBOLD = 5 if FONT and FONT.endswith("PingFang.ttc") else 0     # PingFang.ttc face index 5 = SC Semibold


def grab(t):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", SRC, "-frames:v", "1", "-vf", f"scale={OW}:{OH}:flags=area",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
    return np.frombuffer(raw, np.uint8).reshape(OH, OW, 3).copy()


def frames(t0, t1):
    n = int(round((t1 - t0) * FPS))
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t0:.4f}", "-i", SRC, "-frames:v", str(n), "-vf", f"scale={OW}:{OH}:flags=area",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
    last = None
    for _ in range(n):
        b = p.stdout.read(OW * OH * 3)
        if len(b) == OW * OH * 3: last = np.frombuffer(b, np.uint8).reshape(OH, OW, 3)
        yield last
    p.wait()


# ---- clean plate: temporal median over the clip ----
dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", SRC]))
raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", SRC, "-vf", f"fps={min(3, 60 / dur):.3f},scale={OW}:{OH}:flags=area",
                               "-f", "rawvideo", "-pix_fmt", "rgb24", "-"])
PLATE = np.median(np.frombuffer(raw, np.uint8).reshape(-1, OH, OW, 3), 0).astype(np.uint8)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import vision_matte
    VISION = C.get("matte", "auto") != "mediapipe" and bool(vision_matte.tool("vision"))
except Exception:
    VISION = False
_seg = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=0)
_pose = mp.solutions.pose.Pose(static_image_mode=True, model_complexity=2, min_detection_confidence=0.3)
LIMBS = [(11, 13), (13, 15), (12, 14), (14, 16), (23, 25), (25, 27), (24, 26), (26, 28), (27, 31), (28, 32), (27, 29), (28, 30),
         (15, 19), (16, 20), (15, 17), (16, 18)]


def person_mask(f, box, margin=40, envelope=False):
    H, W = f.shape[:2]; x0, y0, x1, y1 = box
    keep = np.zeros((H, W), np.float32)
    keep[max(0, y0 - margin):min(H, y1 + margin), max(0, x0 - margin):min(W, x1 + margin)] = 1
    keep = cv2.GaussianBlur(keep, (0, 0), margin / 3)[..., None]
    g = (f * keep + PLATE * (1 - keep)).astype(np.uint8)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    S = int(min(max(x1 - x0, y1 - y0) * 1.2, H, W))
    X0 = int(np.clip(cx - S / 2, 0, W - S)); Y0 = int(np.clip(cy - S / 2, 0, H - S))
    crop = np.ascontiguousarray(g[Y0:Y0 + S, X0:X0 + S])
    vm = vision_matte.mask_of(crop, "vision") if VISION else None
    if vm is not None and not envelope:                       # Apple Vision: the matte is already clean
        b = vm > 0.5
        lab, n = ndi.label(b)
        if n > 1:                                             # the person = the biggest blob + blobs that sit inside the box
            sizes = ndi.sum(b, lab, range(1, n + 1)); main = sizes.max()
            inbox = np.zeros((S, S), bool); inbox[max(0, y0 - Y0):max(0, y1 - Y0), max(0, x0 - X0):max(0, x1 - X0)] = True
            inside = ndi.sum(b & inbox, lab, range(1, n + 1))
            b = np.isin(lab, [k + 1 for k in range(n) if sizes[k] == main or (sizes[k] >= 0.02 * main and inside[k] >= 0.6 * sizes[k])])
        b = ndi.binary_fill_holes(b)
        mm = np.maximum(vm, 0.98 * b) * cv2.GaussianBlur(cv2.dilate(b.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 2)
        out = np.zeros((H, W), np.float32); out[Y0:Y0 + S, X0:X0 + S] = np.clip(mm, 0, 1)
        return out
    m = vm if vm is not None else _seg.process(crop).segmentation_mask.astype(np.float32)
    r = _pose.process(crop)
    env = np.zeros((S, S), np.uint8); core = np.zeros((S, S), np.uint8)
    if r.pose_landmarks:
        L = r.pose_landmarks.landmark
        P = lambda i: (int(L[i].x * S), int(L[i].y * S))
        sh = (np.array(P(11)) + np.array(P(12))) / 2; an = (np.array(P(27)) + np.array(P(28))) / 2
        bh = max(40.0, float(np.linalg.norm(sh - an))); t = max(6, int(0.11 * bh))
        for img, th in ((env, t), (core, max(3, t // 2))):
            cv2.fillPoly(img, [np.array([P(11), P(12), P(24), P(23)], np.int32)], 1)
            for a, b in LIMBS:
                if L[a].visibility > 0.2 and L[b].visibility > 0.2: cv2.line(img, P(a), P(b), 1, th)
            cv2.line(img, P(0), tuple(sh.astype(int)), 1, th)
        hr = int(max(np.linalg.norm(np.array(P(7)) - np.array(P(8))) * 0.85, 0.17 * bh))
        cv2.circle(env, P(0), hr, 1, -1); cv2.circle(core, P(0), int(hr * 0.7), 1, -1)
        env = cv2.dilate(env, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(0.09 * bh) | 1,) * 2))
        envf = cv2.GaussianBlur(env.astype(np.float32), (0, 0), 0.02 * bh)
    else:
        envf = np.ones((S, S), np.float32)
    d = np.abs(cv2.GaussianBlur(f, (0, 0), 1.5).astype(np.int16) - cv2.GaussianBlur(PLATE, (0, 0), 1.5).astype(np.int16)).max(2)
    dyn = cv2.GaussianBlur(cv2.dilate(np.clip((d[Y0:Y0 + S, X0:X0 + S] - 10) / 20.0, 0, 1).astype(np.float32), np.ones((5, 5), np.uint8)), (0, 0), 3)
    sure = ((m > 0.8) & (cv2.dilate(core, np.ones((9, 9), np.uint8)) > 0)).astype(np.float32)
    w = m * envf * np.maximum(dyn, sure)
    mm = cv2.ximgproc.guidedFilter(crop, w.astype(np.float32), 6, 1e-3) if hasattr(cv2, "ximgproc") else w
    b = (mm > 0.5)
    lab, n = ndi.label(b)
    if n > 1:
        sizes = ndi.sum(b, lab, range(1, n + 1)); b = lab == (1 + int(np.argmax(sizes)))
    b = ndi.binary_fill_holes(b)
    mm = np.maximum(mm * cv2.GaussianBlur(b.astype(np.float32), (0, 0), 2), cv2.GaussianBlur(b.astype(np.float32), (0, 0), 1.2) * 0.98)
    out = np.zeros((H, W), np.float32); out[Y0:Y0 + S, X0:X0 + S] = np.clip((mm - 0.3) / 0.4, 0, 1)
    return out


def hexrgb(h): h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32)


def ease_out(u): return 1 - (1 - min(max(u, 0), 1)) ** 3


def back_out(u, s=1.8): u = min(max(u, 0), 1) - 1; return 1 + (s + 1) * u ** 3 + s * u ** 2


def zoom_about(img, z, cx, cy):
    M = np.float32([[z, 0, (1 - z) * cx], [0, z, (1 - z) * cy]])
    return cv2.warpAffine(img, M, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


def card(draw_on, x, y, num_txt, name, sub, tag, col, align, prog):
    """Name card: number + skewed colour band + name + subtitle; wipes in with prog 0..1."""
    im = Image.new("RGBA", (OW, OH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    H1 = int(OH * 0.105); band_w = int(OW * 0.30); sk = int(H1 * 0.35)
    dx = int((1 - ease_out(prog)) * (band_w * 0.9) * (1 if align == "left" else -1))
    x0 = x + dx
    pts = [(x0 + sk, y), (x0 + band_w + sk, y), (x0 + band_w, y + H1), (x0, y + H1)]
    d.polygon(pts, fill=tuple(int(c) for c in col) + (235,))
    f_num = fnt(H1 * 1.15, SEMIBOLD); f_name = fnt(H1 * 0.62, SEMIBOLD); f_sub = fnt(H1 * 0.26, SEMIBOLD); f_tag = fnt(H1 * 0.34, SEMIBOLD)
    d.text((x0 + sk * 0.6, y - H1 * 0.95), num_txt, font=f_num, fill=(255, 255, 255, 0), stroke_width=4, stroke_fill=(255, 255, 255, 255))
    d.text((x0 + sk + H1 * 0.25, y + H1 * 0.12), name, font=f_name, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=(20, 22, 34, 255))
    d.text((x0 + sk + H1 * 0.28, y + H1 * 1.12), sub, font=f_sub, fill=(255, 255, 255, 230))
    if tag:
        tw = d.textlength(tag, font=f_tag); ty = y + H1 * 1.55
        d.rounded_rectangle([x0 + sk * 0.2, ty, x0 + sk * 0.2 + tw + H1 * 0.4, ty + H1 * 0.55], radius=int(H1 * 0.2), fill=(255, 255, 255, 240))
        d.text((x0 + sk * 0.2 + H1 * 0.2, ty + H1 * 0.06), tag, font=f_tag, fill=tuple(int(c) for c in col) + (255,))
    a = np.asarray(im).astype(np.float32) / 255
    alpha = a[..., 3:] * min(1, prog * 3)
    return draw_on * (1 - alpha) + a[..., :3] * 255 * alpha


def title(img, text, sub, prog):
    im = Image.new("RGBA", (OW, OH), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f1 = fnt(OH * 0.112, SEMIBOLD); f2 = fnt(OH * 0.032, SEMIBOLD)
    s = 1.6 - 0.6 * back_out(prog)
    tw = d.textlength(text, font=f1)
    tim = Image.new("RGBA", (int(tw + 60), int(OH * 0.2)), (0, 0, 0, 0)); td = ImageDraw.Draw(tim)
    td.text((30, 10), text, font=f1, fill=(255, 217, 61, 255), stroke_width=10, stroke_fill=(18, 22, 34, 255))
    tim = tim.resize((max(1, int(tim.width * s)), max(1, int(tim.height * s))))
    im.alpha_composite(tim, (int(OW / 2 - tim.width / 2), int(OH * 0.02 - (tim.height - OH * 0.2) / 2)))
    if sub:
        sw = d.textlength(sub, font=f2); sy = OH * 0.19
        d.rounded_rectangle([OW / 2 - sw / 2 - 18, sy - 6, OW / 2 + sw / 2 + 18, sy + f2.size + 10], radius=12, fill=(14, 18, 28, int(200 * min(1, prog * 2))))
        d.text((OW / 2 - sw / 2, sy), sub, font=f2, fill=(255, 255, 255, int(255 * min(1, prog * 2))))
    a = np.asarray(im).astype(np.float32) / 255
    alpha = a[..., 3:] * min(1, prog * 4)
    return img * (1 - alpha) + a[..., :3] * 255 * alpha


def freeze_frames(t, hold, people, group=None):
    f = grab(t).astype(np.float32)
    masks = [person_mask(f.astype(np.uint8), tuple(p["box"]), margin=int(p.get("margin", 40)), envelope=bool(p.get("envelope"))) for p in people]
    if DBG:
        os.makedirs(DBG, exist_ok=True)
        for i, m in enumerate(masks): cv2.imwrite(f"{DBG}/mask-{t:.2f}-{i}.png", (m * 255).astype(np.uint8))
    allm = np.clip(sum(masks), 0, 1)
    ys, xs = np.nonzero(allm > 0.5)
    pcx, pcy = (float(xs.mean()), float(ys.mean())) if len(xs) else (OW / 2, OH / 2)
    gray = f.mean(2, keepdims=True)
    dim = (0.82 * gray + 0.18 * f) * 0.42                          # desaturated, darkened background
    stroke = np.clip(sum(cv2.dilate((m > 0.5).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))).astype(np.float32)
                         for m in masks), 0, 1)
    stroke = cv2.GaussianBlur(stroke, (0, 0), 1.0)
    shadow = cv2.GaussianBlur(stroke, (0, 0), 14)
    n = int(round(hold * FPS))
    for j in range(n):
        u = j / FPS
        z = 1 + 0.07 * ease_out(u / max(hold, 0.01))
        pz = 1 + 0.10 * (1 - back_out(min(1, u / 0.22)))           # cutout pop 1.10 -> 1.0
        bg = zoom_about(dim, z, pcx, pcy)
        fg = zoom_about(f, z * pz, pcx, pcy)
        st = zoom_about(stroke[..., None].repeat(3, 2), z * pz, pcx, pcy)[..., :1]
        sh = zoom_about(shadow[..., None].repeat(3, 2), z * pz, pcx + 10, pcy + 14)[..., :1]
        mk = zoom_about(allm[..., None].repeat(3, 2), z * pz, pcx, pcy)[..., :1]
        img = bg * (1 - 0.55 * sh)
        img = img * (1 - st) + 255 * st
        img = img * (1 - mk) + fg * mk
        if group is None:
            p = people[0]; col = hexrgb(p.get("color", "#FF4D8D"))
            left = pcx > OW * 0.5                                   # card on the side away from the person
            cx = int(OW * 0.06) if left else int(OW * 0.60)
            img = card(img, cx, int(OH * 0.62), p.get("num", ""), p.get("name", ""), p.get("sub", ""), p.get("tag", ""), col,
                       "left" if left else "right", min(1, max(0, (u - 0.05) / 0.3)))
        else:
            img = title(img, group.get("title", ""), group.get("sub", ""), min(1, max(0, (u - 0.05) / 0.35)))
        if u < 0.14: img = img + (255 - img) * (0.85 * (1 - u / 0.14))  # flash
        yield np.clip(img, 0, 255).astype(np.uint8)


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "12", OUT + ".video.mp4"],
                       stdin=subprocess.PIPE)
label_im = None
if C.get("label"):
    li = Image.new("RGBA", (OW, OH), (0, 0, 0, 0)); d = ImageDraw.Draw(li); f = fnt(OH * 0.034, SEMIBOLD); pad = int(OH * 0.014)
    tw = d.textlength(C["label"], font=f); x0, y0 = int(OW * 0.025), int(OH * 0.035)
    d.rounded_rectangle([x0, y0, x0 + tw + 2 * pad, y0 + f.size + 2 * pad], radius=pad * 2, fill=(14, 18, 28, 235))
    d.text((x0 + pad, y0 + pad * 0.6), C["label"], font=f, fill=(255, 255, 255, 255))
    la = np.asarray(li).astype(np.float32) / 255; label_im = (la[..., :3] * 255, la[..., 3:])
cues, t_out = [], 0.0
for k, seg in enumerate(C["timeline"]):
    if "play" in seg:
        a, b = seg["play"]; gen = frames(a, b)
    elif "freeze" in seg:
        gen = freeze_frames(seg["freeze"], seg["hold"], seg["people"]); cues.append(("shutter", t_out)); cues.append(("whoosh", t_out + 0.05))
    else:
        gen = freeze_frames(seg["group"], seg["hold"], seg["people"], group=seg); cues.append(("shutter", t_out)); cues.append(("boom", t_out))
    for fr in gen:
        img = fr.astype(np.float32)
        if label_im is not None: img = img * (1 - label_im[1]) + label_im[0] * label_im[1]
        enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes()); t_out += 1 / FPS
enc.stdin.close(); enc.wait()
total = t_out
# ---- audio: music + synthesised shutter / whoosh / boom ----
SR = 48000
rng = np.random.default_rng(3)
def env(n, a, d): t = np.arange(n) / SR; return np.minimum(1, t / a) * np.exp(-t / d)
def shutter():
    n = int(0.16 * SR); x = rng.standard_normal(n) * env(n, 0.001, 0.012); x[int(0.06 * SR):] += rng.standard_normal(n - int(0.06 * SR)) * env(n - int(0.06 * SR), 0.001, 0.02)
    return x * 0.5
def whoosh():
    n = int(0.35 * SR); x = rng.standard_normal(n); S = np.fft.rfft(x); fq = np.fft.rfftfreq(n, 1 / SR); S[(fq < 400) | (fq > 6000)] = 0
    x = np.fft.irfft(S, n); return x / np.abs(x).max() * np.sin(np.pi * np.arange(n) / n) ** 2 * 0.35
def boom():
    n = int(0.7 * SR); t = np.arange(n) / SR; f = 90 * (40 / 90) ** (t / 0.7); return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.25) * 0.9
SFX = {"shutter": shutter, "whoosh": whoosh, "boom": boom}
N = int(total * SR); sfx = np.zeros(N, np.float32)
for name, t in cues:
    x = SFX[name](); o = int(t * SR); m = min(len(x), N - o)
    if m > 0: sfx[o:o + m] += x[:m]
music = np.zeros((N, 2), np.float32)
if C.get("audio"):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(C.get("audio_start", 0)), "-i", C["audio"], "-t", f"{total:.3f}", "-ac", "2", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, np.float32).reshape(-1, 2); music[:min(N, len(a))] = a[:N]
    fo = int(0.6 * SR); music[-fo:] *= np.linspace(1, 0, fo)[:, None]
mix = music * 0.85 + sfx[:, None] * 0.6
mix /= max(1.0, np.abs(mix).max() / 0.97)
pa = subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-i", OUT + ".video.mp4", "-map", "1:v", "-map", "0:a",
                     "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT], input=mix.astype(np.float32).tobytes())
os.remove(OUT + ".video.mp4")
print(f"wrote {OUT}: {total:.2f}s {OW}x{OH} @ {FPS:.3f} fps, {len(cues)} sfx")
