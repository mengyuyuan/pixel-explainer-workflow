#!/usr/bin/env python3
"""Dance afterimage (「残影」): neon copies of the dancer trail behind her, pulsing on the beat.

Per frame: person mask from MediaPipe selfie segmentation (landscape model), refined with a guided filter (edges follow
the image) and smoothed over time; a ring buffer keeps the last copies*delay frames. The ghosts (frame t - k*delay) are
recoloured along a neon gradient, faded with age and screen-blended behind the live dancer, who is re-composited on top.
Beat-synced (with --bpm/--offset or --beats): every beat boosts the trail for 0.3 s and gives a small zoom punch; every
downbeat (bar start) also freezes a white silhouette that stays and fades over 0.7 s.
Works best on a locked-off shot of one person (the background must not move with her).
Usage: python echo_trail.py in.mp4 out.mp4 [--t0 S] [--dur S] [--width 1920] [--copies 5] [--delay 4] [--dim 0.72] [--model 1]
                            [--mattes DIR] [--bpm 96 --offset 0 | --beats beats.json] [--beats-per-bar 4]
                            [--audio music.wav [--audio-start S]] [--label "AI 复刻 · 舞蹈残影"]
--mattes: a folder made by `person_matte.py in.mp4 DIR --t0 .. --dur .. --drop-static` (Apple Vision on macOS): crisp ghost
          outlines with hair and fingers instead of MediaPipe's soft blobs; --t0/--dur/--width then come from that folder.
Needs numpy, opencv-contrib (guided filter; falls back to a blur), Pillow for --label, ffmpeg; mediapipe 0.10.x unless
--mattes is given."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-face.txt"))
MATTES = sys.argv[sys.argv.index("--mattes") + 1] if "--mattes" in sys.argv else ""
try:
    import numpy as np, cv2
    from PIL import Image, ImageDraw, ImageFont
    if not MATTES: import mediapipe as mp
except ImportError as e:
    sys.exit(f"echo_trail.py: missing Python package '{e.name}'. Install (~600 MB): python3 -m pip install -r {_REQ}")
if not MATTES and not hasattr(mp, "solutions"):
    sys.exit(f"echo_trail.py: mediapipe {mp.__version__} has no legacy solutions API; python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("echo_trail.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
T0, DUR, OW, COPIES, DELAY, MODEL = opt("--t0", 0.0), opt("--dur", 0.0), opt("--width", 1920), opt("--copies", 5), opt("--delay", 4), opt("--model", 1)
DIM = opt("--dim", 0.72)                                   # background brightness under the trail (1 = untouched)
BPM, OFFSET, BPB, BEATS = opt("--bpm", 0.0), opt("--offset", 0.0), opt("--beats-per-bar", 4), opt("--beats", "")
AUDIO, ASTART, LABEL = opt("--audio", ""), opt("--audio-start", 0.0), opt("--label", "")
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                           "stream=width,height,r_frame_rate:format=duration", "-of", "json", src]))
W0, H0 = info["streams"][0]["width"], info["streams"][0]["height"]; RATE = info["streams"][0]["r_frame_rate"]
num, den = map(int, RATE.split("/")); FPS = num / den
DUR = DUR or float(info["format"]["duration"]) - T0
OH = int(round(OW * H0 / W0 / 2) * 2)
N = int(DUR * FPS)
if MATTES:
    META = json.load(open(os.path.join(MATTES, "meta.json")))
    OW, OH, RATE, FPS, N, DUR = META["width"], META["height"], META["rate"], META["fps"], META["frames"], META["frames"] / META["fps"]
if BEATS: beats = json.load(open(BEATS))
elif BPM: beats = [OFFSET + i * 60 / BPM for i in range(int(DUR * BPM / 60) + 2)]
else: beats = []
seg = None if MATTES else mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=MODEL)
GF = hasattr(cv2, "ximgproc") and hasattr(cv2.ximgproc, "guidedFilter")
NEON = np.array([[255, 40, 200], [170, 60, 255], [70, 110, 255], [30, 210, 255], [40, 255, 190], [255, 220, 60]], np.float32)  # RGB, newest first
font = None
if LABEL:
    for fp in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"):
        if os.path.exists(fp): font = ImageFont.truetype(fp, int(OH * 0.034)); break


def mask_of(rgb, prev):
    m = seg.process(rgb).segmentation_mask.astype(np.float32)
    if GF: m = cv2.ximgproc.guidedFilter(rgb, m, 8, 1e-3)
    else: m = cv2.GaussianBlur(m, (0, 0), 2)
    m = np.clip((m - 0.25) / 0.5, 0, 1)
    return m if prev is None else 0.65 * m + 0.35 * prev


def beat_phase(t):
    """(time since last beat, is that beat a downbeat, index) or (None, False, -1)."""
    past = [i for i, b in enumerate(beats) if b <= t]
    if not past: return None, False, -1
    i = past[-1]; return t - beats[i], i % BPB == 0, i


def source():
    """(rgb frame, mask or None) pairs: from the mattes folder, or decoded and segmented on the fly."""
    if MATTES:
        for i in range(N):
            f = cv2.imread(os.path.join(MATTES, "frames", f"{i:05d}.jpg"))[..., ::-1]
            m = cv2.imread(os.path.join(MATTES, "masks", f"{i:05d}.png"), 0)
            if m.shape != (OH, OW): m = cv2.resize(m, (OW, OH))
            yield np.ascontiguousarray(f), m.astype(np.float32) / 255
        return
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{T0:.3f}", "-i", src, "-t", f"{DUR:.3f}", "-vf", f"scale={OW}:{OH}:flags=area",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
    while True:
        buf = dec.stdout.read(OW * OH * 3)
        if len(buf) < OW * OH * 3: break
        yield np.frombuffer(buf, np.uint8).reshape(OH, OW, 3), None
    dec.wait()


tmp = out + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "12", tmp], stdin=subprocess.PIPE)
ring, prev_m, frozen, n = [], None, [], 0
for rgb, pm in source():
    t = n / FPS
    m = pm if pm is not None else mask_of(rgb, prev_m); prev_m = m
    f = rgb.astype(np.float32) / 255
    ring.append((f, m)); ring = ring[-(COPIES * DELAY + 1):]
    dt, down, bi = beat_phase(t)
    boost = 1 + (0.9 * np.exp(-dt / 0.12) if dt is not None and dt < 0.3 else 0)
    if dt is not None and down and dt < 1 / FPS: frozen.append((t, f.copy(), m.copy()))
    frozen = [x for x in frozen if t - x[0] < 0.7]
    base = f * DIM
    for k in range(COPIES, 0, -1):                                # oldest first
        j = len(ring) - 1 - k * DELAY
        if j < 0: continue
        gf, gm = ring[j]
        lum = gf.mean(2, keepdims=True)
        col = NEON[(k - 1) % len(NEON)] / 255
        ghost = np.clip((0.45 + 1.1 * lum) * col, 0, 1)
        a = (gm * (0.78 * (1 - (k - 1) / (COPIES + 1))) * boost)[..., None].clip(0, 0.92)
        base = base * (1 - a) + ghost * a                          # saturated neon copies
    for (tf, ff, fm) in frozen:                                   # downbeat white silhouettes
        age = (t - tf) / 0.7
        a = (fm * 0.55 * (1 - age))[..., None]
        base = 1 - (1 - base) * (1 - np.clip(0.55 + ff.mean(2, keepdims=True), 0, 1) * a)
    mm = m[..., None]
    base = base * (1 - mm) + f * mm                               # the live dancer stays on top
    if dt is not None and dt < 0.25:                              # zoom punch + flash on every beat
        z = 1 + 0.035 * np.exp(-dt / 0.08) * (1.6 if down else 1)
        base = cv2.warpAffine(base, np.float32([[z, 0, (1 - z) * OW / 2], [0, z, (1 - z) * OH / 2]]), (OW, OH), flags=cv2.INTER_LINEAR)
        base = np.clip(base + 0.10 * np.exp(-dt / 0.06) * (1.5 if down else 1), 0, 1)
    img = (base * 255 + 0.5).astype(np.uint8)
    if font:
        im = Image.fromarray(img); d = ImageDraw.Draw(im); pad = int(OH * 0.014)
        tw = d.textlength(LABEL, font=font); x0, y0 = int(OW * 0.025), int(OH * 0.035)
        d.rounded_rectangle([x0, y0, x0 + tw + 2 * pad, y0 + font.size + 2 * pad], radius=pad * 2, fill=(14, 18, 28))
        d.text((x0 + pad, y0 + pad * 0.6), LABEL, font=font, fill=(255, 255, 255))
        img = np.asarray(im)
    enc.stdin.write(img.tobytes()); n += 1
enc.stdin.close(); enc.wait()
if AUDIO:
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ss", f"{ASTART:.3f}", "-i", AUDIO, "-map", "0:v:0", "-map", "1:a:0",
                           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={max(0, n / FPS - 0.6):.2f}:d=0.6",
                           "-shortest", out])
    os.remove(tmp)
else: os.replace(tmp, out)
print(f"wrote {out}: {n} frames {OW}x{OH} @ {FPS:.3f} fps, {len(beats)} beats, mattes: {'folder' if MATTES else 'mediapipe'}")
