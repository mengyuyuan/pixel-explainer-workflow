#!/usr/bin/env python3
"""Before -> after reel: the untouched source footage first (labelled), a short title card, then the finished effect.
Lets viewers judge the edit against what was actually shot, instead of only seeing the polished result.

The before part is one or more source ranges, scaled and centre-cropped to the after video's size, played at normal speed
with a pill label (default 「原片 · 没加任何特效」) and no sound (the source audio may be private or just noise). The card
shows the after video's first frame dimmed with a big title. The after video keeps its own audio.
Usage: python before_after.py out.mp4 --after effect.mp4 --before raw.mp4@T0-T1 [--before raw2.mp4@T0-T1 ...]
                              [--label "原片 · 没加任何特效"] [--note "Mixkit 免费素材"] [--card "AI 处理后"] [--card-dur 0.8] [--crf 18]
Needs numpy, Pillow, ffmpeg."""
import os, sys, json, subprocess, shutil
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"before_after.py: missing Python package '{e.name}'. Install: python3 -m pip install numpy pillow")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("before_after.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
out = sys.argv[1]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
AFTER, LABEL, NOTE, CARD, CARD_DUR = opt("--after", ""), opt("--label", "原片 · 没加任何特效"), opt("--note", ""), opt("--card", "AI 处理后"), opt("--card-dur", 0.8)
CRF = opt("--crf", 18)
BEFORE = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--before"]
if not AFTER or not BEFORE: sys.exit("need --after effect.mp4 and at least one --before raw.mp4@T0-T1")
probe = lambda p: json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                                      "stream=width,height,r_frame_rate:format=duration", "-of", "json", p]))
ia = probe(AFTER); W, H = ia["streams"][0]["width"], ia["streams"][0]["height"]; RATE = ia["streams"][0]["r_frame_rate"]
num, den = map(int, RATE.split("/")); FPS = num / den
has_audio = bool(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", AFTER]).strip())
FONT = next((f for f in ("/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
                         "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc") if os.path.exists(f)), None)
f_lab = ImageFont.truetype(FONT, int(H * 0.036)) if FONT else ImageFont.load_default()
f_note = ImageFont.truetype(FONT, int(H * 0.024)) if FONT else ImageFont.load_default()
f_card = ImageFont.truetype(FONT, int(H * 0.085)) if FONT else ImageFont.load_default()


def frames(path, t0=None, t1=None):
    pre = ["-ss", f"{t0:.3f}"] if t0 is not None else []
    dur = ["-t", f"{t1 - t0:.3f}"] if t1 is not None else []
    p = subprocess.Popen(["ffmpeg", "-v", "error"] + pre + ["-i", path] + dur +
                         ["-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=area,crop={W}:{H},fps={RATE}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
    while True:
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        yield np.frombuffer(b, np.uint8).reshape(H, W, 3)
    p.wait()


def pill(img, text, font, xy, fg=(255, 255, 255), bg=(14, 18, 28)):
    d = ImageDraw.Draw(img); pad = int(font.size * 0.42)
    tw = d.textlength(text, font=font); x0, y0 = xy
    d.rounded_rectangle([x0, y0, x0 + tw + 2 * pad, y0 + font.size + 2 * pad], radius=pad * 2, fill=bg)
    d.text((x0 + pad, y0 + pad * 0.6), text, font=font, fill=fg)


tmp = out + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", str(CRF), "-preset", "slow", "-pix_fmt", "yuv420p", "-g", "30", tmp], stdin=subprocess.PIPE)
nb = 0
for spec in BEFORE:
    path, rng = spec.rsplit("@", 1); a, b = (float(v) for v in rng.split("-"))
    for f in frames(path, a, b):
        im = Image.fromarray(f); pill(im, LABEL, f_lab, (int(W * 0.025), int(H * 0.035)), fg=(20, 20, 20), bg=(255, 214, 0))
        if NOTE: pill(im, NOTE, f_note, (int(W * 0.025), int(H * 0.035) + int(f_lab.size * 1.9)))
        enc.stdin.write(np.asarray(im).tobytes()); nb += 1
first = np.frombuffer(subprocess.check_output(["ffmpeg", "-v", "error", "-i", AFTER, "-frames:v", "1", "-vf",
                                             f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]), np.uint8).reshape(H, W, 3)
nc = int(round(CARD_DUR * FPS))
for i in range(nc):
    u = i / max(1, nc - 1)
    im = Image.fromarray((first.astype(np.float32) * (0.3 + 0.25 * u)).astype(np.uint8)); d = ImageDraw.Draw(im)
    tw = d.textlength(CARD, font=f_card)
    d.text(((W - tw) / 2, H * 0.44), CARD, font=f_card, fill=(255, 255, 255))
    d.text(((W - tw) / 2, H * 0.44 + f_card.size * 1.25), "▼", font=f_note, fill=(255, 214, 0))
    enc.stdin.write(np.asarray(im).tobytes())
na = 0
for f in frames(AFTER):
    enc.stdin.write(f.tobytes()); na += 1
enc.stdin.close(); enc.wait()
lead = (nb + nc) / FPS
if has_audio:
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", AFTER, "-filter_complex",
                           f"[1:a]adelay={int(lead * 1000)}|{int(lead * 1000)},apad[a]", "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out])
    os.remove(tmp)
else: os.replace(tmp, out)
print(f"wrote {out}: before {nb / FPS:.2f}s + card {nc / FPS:.2f}s + after {na / FPS:.2f}s")
