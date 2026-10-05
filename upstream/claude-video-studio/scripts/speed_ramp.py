#!/usr/bin/env python3
"""「曲线变速卡点」speed ramps: each clip runs fast, dips into slow motion around its highlight (a jump peak, a trick) and
speeds up again, with the highlight landing exactly on a beat.

Speed curve per segment (output time t): speed(t) = fast - (fast - slow) * exp(-((t - hit_out) / width)^2), with an optional
different fast speed after the hit (fast_after). Source time = hit_src + integral of speed from hit_out to t, so the hit frame
lands on hit_out (put it on a beat). Rendering at a fixed output fps:
  speed < 0.9  -> optical-flow frame interpolation (OpenCV DIS flow, both directions, warped and blended): smooth slow-mo
                  from 24/30 fps sources;
  speed > 1.4  -> motion blur by averaging the source frames inside the shutter interval;
  otherwise    -> the nearest frame, cross-faded.
Extras: zoom punch + white flash on each hit, a flash on each cut, a live speed readout, optional label and end title,
synthesised whoosh / impact SFX mixed over the music.
Config (JSON): {"fps": 30, "width": 1920, "audio": "music.wav", "audio_start": 0, "label": "...",
  "segments": [{"video": "a.mp4", "out": [0, 5.0], "hit_out": 2.5, "hit_src": 5.7, "fast": 2.0, "slow": 0.25, "width": 0.55,
                "fast_after": 2.0}, ...],
  "end_hold": 1.25, "end_title": "..."}
  "readout": false hides the speed readout and "punch": false the zoom punch and flashes: a clean ramped clip to feed into
  another effect (pop_out.py).
Usage: python speed_ramp.py config.json out.mp4      (prints each segment's source range; errors if it leaves the clip)
Needs numpy, opencv, Pillow, ffmpeg (requirements-edit.txt)."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-edit.txt"))
try:
    import numpy as np, cv2
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"speed_ramp.py: missing Python package '{e.name}'. Install (~250 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("speed_ramp.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
C = json.load(open(sys.argv[1])); OUT = sys.argv[2]
FPS = C.get("fps", 30); OW = C.get("width", 1920); OH = int(round(OW * 9 / 16 / 2) * 2)
FONT = next((p for p in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
                         "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc") if os.path.exists(p)), None)
IDX = 5 if FONT and FONT.endswith("PingFang.ttc") else 0
fnt = lambda px: ImageFont.truetype(FONT, int(px), index=IDX) if FONT else ImageFont.load_default()
DIS = cv2.DISOpticalFlow_create(cv2.DISOPTICAL_FLOW_PRESET_MEDIUM)


def probe(v):
    s = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate:format=duration",
                                            "-of", "json", v]))
    n, d = map(int, s["streams"][0]["r_frame_rate"].split("/")); return n / d, float(s["format"]["duration"])


def src_times(seg, n_out):
    """Source time for each output frame of the segment (numerical integration of the speed curve)."""
    t0, t1 = seg["out"]; h = seg["hit_out"]; fast, slow, w = seg.get("fast", 2.0), seg.get("slow", 0.25), seg.get("width", 0.5)
    fa = seg.get("fast_after", fast)
    sp = lambda t: (fast if t < h else fa) - ((fast if t < h else fa) - slow) * np.exp(-((t - h) / w) ** 2)
    ts = t0 + np.arange(n_out) / FPS
    out, dt = [], 1 / (FPS * 20)
    for t in ts:
        a, b = (h, t) if t >= h else (t, h)
        grid = np.arange(a, b, dt); integ = float(np.sum([sp(x + dt / 2) for x in grid]) * dt) if len(grid) else 0.0
        out.append(seg["hit_src"] + (integ if t >= h else -integ))
    return np.array(out), np.array([sp(t) for t in ts])


def load(video, s0, s1, vfps):
    i0 = max(0, int(np.floor(s0 * vfps)) - 2); i1 = int(np.ceil(s1 * vfps)) + 3
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{i0 / vfps:.4f}", "-i", video, "-frames:v", str(i1 - i0),
                          "-vf", f"scale={OW}:{OH}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
    fr = []
    while True:
        b = p.stdout.read(OW * OH * 3)
        if len(b) < OW * OH * 3: break
        fr.append(np.frombuffer(b, np.uint8).reshape(OH, OW, 3))
    p.wait(); return i0, fr


_flow = {}
def flow(fr, i, j):
    if (i, j) not in _flow:
        a = cv2.cvtColor(cv2.resize(fr[i], (OW // 2, OH // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        b = cv2.cvtColor(cv2.resize(fr[j], (OW // 2, OH // 2), interpolation=cv2.INTER_AREA), cv2.COLOR_RGB2GRAY)
        _flow[(i, j)] = cv2.resize(DIS.calc(a, b, None), (OW, OH)) * 2
    return _flow[(i, j)]


GX, GY = np.meshgrid(np.arange(OW, dtype=np.float32), np.arange(OH, dtype=np.float32))
def interp(fr, x):
    i = int(np.floor(x)); a = x - i
    i = min(max(i, 0), len(fr) - 2)
    if a < 0.02: return fr[i].astype(np.float32)
    if a > 0.98: return fr[i + 1].astype(np.float32)
    f01, f10 = flow(fr, i, i + 1), flow(fr, i + 1, i)
    w0 = cv2.remap(fr[i], GX - a * f01[..., 0], GY - a * f01[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    w1 = cv2.remap(fr[i + 1], GX - (1 - a) * f10[..., 0], GY - (1 - a) * f10[..., 1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return w0.astype(np.float32) * (1 - a) + w1.astype(np.float32) * a


def overlay(img, texts):
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    for kind, txt, x, y, size, col in texts:
        f = fnt(size)
        if kind == "pill":
            pad = int(size * 0.4); tw = d.textlength(txt, font=f)
            d.rounded_rectangle([x, y, x + tw + 2 * pad, y + size + 2 * pad * 0.9], radius=pad * 2, fill=(14, 18, 28))
            d.text((x + pad, y + pad * 0.5), txt, font=f, fill=col)
        else:
            tw = d.textlength(txt, font=f)
            d.text((x - tw / 2 if kind == "center" else x, y), txt, font=f, fill=col, stroke_width=max(2, size // 12), stroke_fill=(18, 22, 34))
    return np.asarray(im).astype(np.float32)


def zoom(img, z, cx=OW / 2, cy=OH / 2):
    if abs(z - 1) < 1e-3: return img
    M = np.float32([[z, 0, (1 - z) * cx], [0, z, (1 - z) * cy]]); return cv2.warpAffine(img, M, (OW, OH), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)


enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", str(FPS // 2), OUT + ".video.mp4"],
                       stdin=subprocess.PIPE)
cues, last = [], None
for k, seg in enumerate(C["segments"]):
    vfps, vdur = probe(seg["video"])
    n_out = int(round((seg["out"][1] - seg["out"][0]) * FPS))
    st, spd = src_times(seg, n_out)
    print(f"segment {k}: {os.path.basename(seg['video'])} src {st[0]:.2f}-{st[-1]:.2f}s of {vdur:.2f}s, speed {spd.min():.2f}-{spd.max():.2f}x")
    if st[0] < 0 or st[-1] > vdur - 0.05: sys.exit(f"segment {k} leaves the clip: adjust hit_src / fast / width")
    i0, fr = load(seg["video"], st[0], st[-1], vfps); _flow.clear()
    cues.append(("hit", seg["hit_out"])); cues.append(("whoosh", seg["out"][0] + (0.0 if k else 0.4)))
    if spd[-1] > 1.3: cues.append(("whoosh", seg["out"][1] - 0.45))
    for j in range(n_out):
        t = seg["out"][0] + j / FPS; x = st[j] * vfps - i0; v = spd[j]
        if v > 1.4:                                                  # motion blur: average the frames under a 180° shutter
            span = 0.5 * v / FPS * vfps
            xs = np.linspace(x - span / 2, x + span / 2, max(2, int(np.ceil(span)) + 1))
            img = np.mean([fr[min(max(int(round(q)), 0), len(fr) - 1)].astype(np.float32) for q in xs], 0)
        elif v < 0.9:
            img = interp(fr, x)
        else:
            i = min(max(int(np.floor(x)), 0), len(fr) - 2); a = x - i
            img = fr[i].astype(np.float32) * (1 - a) + fr[i + 1].astype(np.float32) * a
        dh = t - seg["hit_out"]
        if C.get("punch", True):
            if 0 <= dh < 0.45: img = zoom(img, 1 + 0.07 * np.exp(-dh / 0.12))
            if 0 <= dh < 0.12: img = img + (255 - img) * 0.55 * (1 - dh / 0.12)
            dc = t - seg["out"][0]
            if k and dc < 0.1: img = img + (255 - img) * 0.7 * (1 - dc / 0.1)
        txt = []
        if C.get("label"): txt.append(("pill", C["label"], int(OW * 0.025), int(OH * 0.035), int(OH * 0.034), (255, 255, 255)))
        if C.get("readout", True):
            txt.append(("pill", f"速度 ×{v:.2f}", int(OW * 0.80), int(OH * 0.035), int(OH * 0.034), (255, 217, 61) if v < 0.9 else (255, 255, 255)))
        if txt: img = overlay(img, txt)
        last = img
        enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    del fr
hold = C.get("end_hold", 0.0)
for j in range(int(round(hold * FPS))):
    u = j / FPS
    img = zoom(last, 1 + 0.03 * u / max(hold, 0.01)) * (1 - min(0.45, u * 1.5))
    if C.get("end_title"):
        img = overlay(img, [("center", C["end_title"], OW // 2, int(OH * 0.42), int(OH * 0.075), (255, 217, 61))])
    enc.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
enc.stdin.close(); enc.wait()
total = C["segments"][-1]["out"][1] + hold
SR = 48000; rng = np.random.default_rng(5)
def env(n, a, d): t = np.arange(n) / SR; return np.minimum(1, t / a) * np.exp(-t / d)
def whoosh():
    n = int(0.45 * SR); x = rng.standard_normal(n); S = np.fft.rfft(x); fq = np.fft.rfftfreq(n, 1 / SR); S[(fq < 300) | (fq > 7000)] = 0
    x = np.fft.irfft(S, n); return x / np.abs(x).max() * np.sin(np.pi * np.arange(n) / n) ** 3 * 0.4
def hit():
    n = int(0.6 * SR); t = np.arange(n) / SR; f = 110 * (38 / 110) ** (t / 0.6)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.2) + rng.standard_normal(n) * env(n, 0.001, 0.03) * 0.5
N = int(total * SR); sfx = np.zeros(N, np.float32)
for name, t in cues:
    x = (whoosh if name == "whoosh" else hit)(); o = int(t * SR); m = min(len(x), N - o)
    if m > 0 and o >= 0: sfx[o:o + m] += x[:m]
music = np.zeros((N, 2), np.float32)
if C.get("audio"):
    p = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(C.get("audio_start", 0)), "-i", C["audio"], "-t", f"{total:.3f}", "-ac", "2", "-ar", str(SR),
                        "-f", "f32le", "-"], capture_output=True)
    a = np.frombuffer(p.stdout, np.float32).reshape(-1, 2); music[:min(N, len(a))] = a[:N]
    fo = int(0.8 * SR); music[-fo:] *= np.linspace(1, 0, fo)[:, None]
mix = music * 0.85 + sfx[:, None] * 0.55; mix /= max(1.0, np.abs(mix).max() / 0.97)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-", "-i", OUT + ".video.mp4", "-map", "1:v", "-map", "0:a",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", OUT], input=mix.astype(np.float32).tobytes())
os.remove(OUT + ".video.mp4")
print(f"wrote {OUT}: {total:.2f}s {OW}x{OH} @ {FPS} fps, {len(cues)} sfx")
