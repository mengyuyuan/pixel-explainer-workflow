#!/usr/bin/env python3
"""Excerpt reel of someone's tutorial for a "manual vs AI" write-up: THEIR EFFECT first at normal speed, then THEIR
TEACHING PART in fast-forward next to a step list that fills up as the steps go by, then a hold with the step total.
The reader sees what the effect looks like and how many manual steps it takes without leaving the article.

16:9 canvas (1920x1080, 30 fps). Phase 1: the effect, cropped from the tutorial (config effect.crop) and shown large.
Phase 2: the whole tutorial frame as a phone on the left, the steps on the right: each appears (with a pop) when the
tutorial reaches it; one column up to 11 steps, two columns above. End: all steps lit + the summary lines.
Credit is burned in (author, title, likes, "版权归原作者") - keep it, keep the excerpt short, and link the original.
config.json:
  {"video": "tutorial.mp4", "author": "东方的阳", "title": "超有趣的泼水定格教程", "stats": "3.2 万赞 · 2.7 万收藏",
   "effect": {"range": [0.3, 7.8], "crop": [0, 653, 1080, 1262], "caption": "泼出去的水停在半空，人照常说话"},
   "teach": {"range": [7.85, 47.9], "speed": 4.5},
   "steps": [[7.85, "固定机位拍一条"], [16.0, "拖到准备泼水的位置，点「分割」"], ...],     # tutorial time, text
   "total": "10 步，约 20~30 次操作", "repeat": "每多定格一次，全套重来", "hold": 2.4}
  effect.range may also be a list of ranges; "effect_after": true when the tutorial shows the result at its end.
Usage: python tutorial_reel.py config.json out.mp4
Needs numpy, Pillow, ffmpeg."""
import os, sys, json, subprocess, shutil, glob
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
try:
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"tutorial_reel.py: missing Python package '{e.name}'. Install: python3 -m pip install numpy pillow")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("tutorial_reel.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
C = json.load(open(sys.argv[1])); out = sys.argv[2]
base = os.path.dirname(os.path.abspath(sys.argv[1]))
VIDEO = C["video"] if os.path.isabs(C["video"]) else os.path.join(base, C["video"])
W, H, FPS, SR = 1920, 1080, 30, 48000
BG, INK, MUTED, YEL, ORANGE, LINE = (14, 16, 20), (240, 242, 246), (150, 156, 170), (255, 214, 0), (255, 138, 76), (42, 46, 56)
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", VIDEO]))
VW, VH = info["streams"][0]["width"], info["streams"][0]["height"]


def font(size, bold=False):
    cands = [(p, 11 if bold else 3) for p in glob.glob("/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc")]
    cands += [("/System/Library/Fonts/PingFang.ttc", 0), ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2 if bold else 0),
              ("/System/Library/Fonts/STHeiti Medium.ttc", 1), ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc" if bold else
                                                              "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 0),
              ("C:/Windows/Fonts/msyhbd.ttc" if bold else "C:/Windows/Fonts/msyh.ttc", 0)]
    for p, ix in cands:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size, index=ix)
            except Exception: pass
    return ImageFont.load_default()


def fit(d, text, size, maxw, bold=False, floor=20):
    f = font(size, bold)
    while d.textlength(text, font=f) > maxw and size > floor: size -= 1; f = font(size, bold)
    return f


def header(d, phase):
    """Top line: source pill, author, stats; the two phase chips on the right."""
    f1, f2, f3 = font(30, True), font(34, True), font(28)
    x, y = 60, 34
    tw = d.textlength("抖音原作品", font=f1)
    d.rounded_rectangle([x, y, x + tw + 32, y + 50], radius=25, fill=YEL); d.text((x + 16, y + 6), "抖音原作品", font=f1, fill=(20, 20, 20))
    x += tw + 32 + 20
    d.text((x, y + 3), "@" + C["author"], font=f2, fill=INK); x += d.textlength("@" + C["author"], font=f2) + 18
    d.text((x, y + 9), C.get("stats", ""), font=f3, fill=MUTED)
    chips = [("① 先看效果", phase == 1), (f"② 教学部分 · {C['teach']['speed']:g} 倍速快进", phase == 2)]
    xr = W - 60
    for text, on in reversed(chips):
        tw = d.textlength(text, font=f3)
        d.rounded_rectangle([xr - tw - 36, y, xr, y + 50], radius=25, outline=YEL if on else LINE, width=3 if on else 2, fill=(40, 36, 10) if on else BG)
        d.text((xr - tw - 18, y + 8), text, font=f3, fill=YEL if on else MUTED); xr -= tw + 36 + 14
    credit = f"来源：抖音 @{C['author']}《{C['title']}》 · 节选用于对比说明，版权归原作者"
    d.text((60, H - 44), credit, font=fit(d, credit, 22, W - 120), fill=(110, 116, 130))


def rounded(im, r):
    m = Image.new("L", im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], radius=r, fill=255)
    return m


# ---------- layout
E = C["effect"]; ranges = E["range"] if isinstance(E["range"][0], (list, tuple)) else [E["range"]]
cx0, cy0, cx1, cy1 = E.get("crop", [0, 0, VW, VH]); cw, ch = cx1 - cx0, cy1 - cy0
EW = 1480; EH = int(round(EW * ch / cw / 2) * 2)
if EH > 830: EH = 830; EW = int(round(EH * cw / ch / 2) * 2)
EX, EY = (W - EW) // 2, 112 + (840 - EH) // 2
PH_H = 872; PH_W = int(round(PH_H * VW / VH / 2) * 2)
if PH_W > 640: PH_W = 640; PH_H = int(round(PH_W * VH / VW / 2) * 2)
PX, PY = 70, 112 + (880 - PH_H) // 2
LX = PX + PH_W + 64                                        # the step list starts here
T = C["teach"]; t0, t1 = T["range"]; SPEED = float(T["speed"])
steps = C["steps"]; NS = len(steps)
TA = sum(b - a for a, b in ranges); TB = (t1 - t0) / SPEED; HOLD = float(C.get("hold", 2.4)); XF = 0.4
AFTER = bool(C.get("effect_after"))                        # the tutorial shows its result at the end -> still play it first
TOTAL = TA + TB + HOLD
step_t = [TA + (max(t0, s[0]) - t0) / SPEED for s in steps]   # reel time each step appears


def panel(k, final=False):
    """Phase-2 canvas with steps 1..k shown (k-th highlighted); final adds the summary."""
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im); header(d, 2)
    d.text((LX, 118), "手动步骤", font=font(30, True), fill=MUTED)
    cols = 1 if NS <= 11 else 2
    rows = (NS + cols - 1) // cols
    top, bottom = 172, 850
    pitch = min(72, (bottom - top) / rows)
    size = int(min(38, pitch * 0.56)) if cols == 1 else int(min(31, pitch * 0.56))
    colw = (W - 60 - LX - (cols - 1) * 26) / cols
    for i, (_, text) in enumerate(steps[:k]):
        c, r = divmod(i, rows)
        x, y = LX + c * (colw + 26), top + r * pitch
        cur = (i == k - 1) and not final
        if cur: d.rounded_rectangle([x - 10, y - 4, x + colw, y + pitch - 8], radius=12, fill=(44, 40, 12))
        bs = size + 12
        d.ellipse([x, y + (pitch - 12 - bs) / 2, x + bs, y + (pitch - 12 - bs) / 2 + bs], fill=YEL if cur else (58, 62, 74))
        fn = font(int(size * 0.72), True); num = str(i + 1)
        d.text((x + bs / 2 - d.textlength(num, font=fn) / 2, y + (pitch - 12 - bs) / 2 + bs * 0.13), num, font=fn, fill=(20, 20, 20) if cur else INK)
        ft = fit(d, text, size, colw - bs - 26, bold=cur)
        d.text((x + bs + 14, y + (pitch - 12 - ft.size) / 2 - 3), text, font=ft, fill=YEL if cur else INK)
    if final:
        d.line([LX, 872, W - 60, 872], fill=LINE, width=2)
        ft = fit(d, C["total"], 50, W - 60 - LX, bold=True); d.text((LX, 888), C["total"], font=ft, fill=ORANGE)
        if C.get("repeat"):
            fr = fit(d, C["repeat"], 32, W - 60 - LX); d.text((LX, 956), C["repeat"], font=fr, fill=INK)
    else:
        d.text((LX, 900), f"第 {k} / {NS} 步" if k else "", font=font(34, True), fill=MUTED)
    d.rounded_rectangle([PX - 3, PY - 3, PX + PH_W + 2, PY + PH_H + 2], radius=22, outline=LINE, width=3)
    return im


def canvas_a():
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im); header(d, 1)
    cap = "效果：" + E.get("caption", "")
    f = fit(d, cap, 40, W - 160, bold=True)
    d.text(((W - d.textlength(cap, font=f)) / 2, EY + EH + 26), cap, font=f, fill=INK)
    d.rounded_rectangle([EX - 3, EY - 3, EX + EW + 2, EY + EH + 2], radius=18, outline=LINE, width=3)
    return im


A = np.asarray(canvas_a()).copy()
PAN = [np.asarray(panel(k)).copy() for k in range(NS + 1)]
FIN = np.asarray(panel(NS, True)).copy()
maskA = np.asarray(rounded(Image.new("L", (EW, EH)), 16), np.float32)[..., None] / 255
maskP = np.asarray(rounded(Image.new("L", (PH_W, PH_H)), 20), np.float32)[..., None] / 255
badge = Image.new("RGBA", (170, 50), (0, 0, 0, 0)); db = ImageDraw.Draw(badge)   # fast-forward badge on the phone
db.rounded_rectangle([0, 0, 169, 49], radius=25, fill=(0, 0, 0, 180))
for bx in (20, 40): db.polygon([(bx, 14), (bx + 18, 25), (bx, 36)], fill=YEL + (255,))
db.text((70, 7), f"×{SPEED:g}", font=font(28, True), fill=YEL + (255,))
badge = np.asarray(badge, np.float32)


def reader(args, w, h):
    p = subprocess.Popen(["ffmpeg", "-v", "error"] + args + ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, bufsize=10 ** 8)
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3: break
        yield np.frombuffer(b, np.uint8).reshape(h, w, 3)
    p.wait()


def frames_a():
    for a, b in ranges:
        yield from reader(["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", VIDEO, "-vf",
                           f"crop={cw}:{ch}:{cx0}:{cy0},scale={EW}:{EH}:flags=lanczos,fps={FPS}"], EW, EH)


def frames_b():
    yield from reader(["-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", VIDEO, "-vf",
                       f"setpts=PTS/{SPEED},scale={PH_W}:{PH_H}:flags=lanczos,fps={FPS}"], PH_W, PH_H)


tmp = out + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "19", "-preset", "slow", "-pix_fmt", "yuv420p", "-g", "30", tmp], stdin=subprocess.PIPE)
n = 0; lastA = None
for f in frames_a():
    img = A.copy(); img[EY:EY + EH, EX:EX + EW] = (img[EY:EY + EH, EX:EX + EW] * (1 - maskA) + f * maskA).astype(np.uint8)
    if n < 6: img = (img * ((n + 1) / 6)).astype(np.uint8)
    enc.stdin.write(img.tobytes()); lastA = img; n += 1
nA = n; nb = 0; lastB = None
for f in frames_b():
    t = n / FPS
    k = sum(1 for s in step_t if s <= t + 1e-6)
    img = PAN[k].astype(np.float32)
    if k and t - step_t[k - 1] < 0.16:                          # the new row fades in
        u = (t - step_t[k - 1]) / 0.16; img = PAN[k - 1] * (1 - u) + img * u
    fr = f.astype(np.float32)
    fr[14:64, 14:184] = fr[14:64, 14:184] * (1 - badge[..., 3:] / 255) + badge[..., :3] * (badge[..., 3:] / 255)
    img[PY:PY + PH_H, PX:PX + PH_W] = img[PY:PY + PH_H, PX:PX + PH_W] * (1 - maskP) + fr * maskP
    if nb < XF * FPS and lastA is not None:                     # dissolve from the effect
        u = (nb + 1) / (XF * FPS); img = lastA * (1 - u) + img * u
    lastB = f; enc.stdin.write(img.astype(np.uint8).tobytes()); n += 1; nb += 1
nH = int(round(HOLD * FPS))
for j in range(nH):
    u = min(1.0, (j + 1) / 8)
    img = PAN[NS] * (1 - u) + FIN.astype(np.float32) * u
    if lastB is not None: img[PY:PY + PH_H, PX:PX + PH_W] = img[PY:PY + PH_H, PX:PX + PH_W] * (1 - maskP) + lastB * maskP * (1 - 0.35 * u)
    if j >= nH - 8: img = img * ((nH - j) / 8)
    enc.stdin.write(img.astype(np.uint8).tobytes()); n += 1
enc.stdin.close(); enc.wait()

# ---------- audio: the effect at 1x, the teaching sped up and quiet, a pop per step, a chime on the total
def pcm(args):
    r = subprocess.run(["ffmpeg", "-v", "error"] + args + ["-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True)
    return np.frombuffer(r.stdout, np.float32).reshape(-1, 2).copy()


def fade(x, ms=30):
    k = min(len(x) // 2, int(SR * ms / 1000))
    if k: r = np.linspace(0, 1, k, dtype=np.float32)[:, None]; x[:k] *= r; x[-k:] *= r[::-1]
    return x


mix = np.zeros((int(n / FPS * SR) + SR, 2), np.float32); o = 0
for a, b in ranges:
    x = fade(pcm(["-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", VIDEO])); mix[o:o + len(x)] += x; o += int(round((b - a) * SR))
chain = []; sp = SPEED
while sp > 2.0: chain.append("atempo=2.0"); sp /= 2.0
chain.append(f"atempo={sp:.4f}")
x = fade(pcm(["-ss", f"{t0:.3f}", "-t", f"{t1 - t0:.3f}", "-i", VIDEO, "-af", ",".join(chain)]), 120) * 10 ** (-17 / 20)
o = int(nA / FPS * SR); mix[o:o + len(x)] += x[:len(mix) - o]
eff = mix[:int(nA / FPS * SR)]                              # level the excerpt: the effect part to about -19 dBFS RMS
rms = np.sqrt(np.mean(eff ** 2)) if len(eff) else 0.0
if rms > 1e-4: mix *= 10 ** (-19 / 20) / rms
tt = np.arange(int(0.09 * SR)) / SR
pop = (np.sin(2 * np.pi * np.cumsum(700 * (1500 / 700) ** (tt / 0.09)) / SR) * np.minimum(1, tt / 0.004) * np.exp(-tt / 0.05)).astype(np.float32)
for s in step_t:
    o = int(s * SR); mix[o:o + len(pop)] += pop[:, None] * 10 ** (-15 / 20)
tc = np.arange(int(1.4 * SR)) / SR
chime = sum(np.sin(2 * np.pi * fq * tc) * np.minimum(1, np.maximum(0, tc - dt) / 0.003) * np.exp(-np.maximum(0, tc - dt) / 0.45) * (tc > dt)
            for fq, dt in ((784, 0), (988, 0.09), (1175, 0.18))).astype(np.float32) * 0.2
o = int((nA + nb) / FPS * SR); mix[o:o + len(chime)] += chime[:len(mix) - o, None]
mix = mix[:int(n / FPS * SR)]
peak = np.abs(mix).max()
if peak > 0.97: mix = np.tanh(mix / 0.97 * 1.2) / np.tanh(1.2) * 0.97 if peak < 2.5 else mix * (0.97 / peak)
wav = out + ".wav"
with open(wav, "wb") as fh:
    import struct
    pcm16 = (np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes()
    fh.write(b"RIFF" + struct.pack("<I", 36 + len(pcm16)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 2, SR, SR * 4, 4, 16) + b"data" + struct.pack("<I", len(pcm16)) + pcm16)
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", wav, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                       "-shortest", "-movflags", "+faststart", out])
os.remove(tmp); os.remove(wav)
print(f"wrote {out}: effect {nA / FPS:.1f}s + teaching {nb / FPS:.1f}s (x{SPEED:g}) + hold {nH / FPS:.1f}s, {NS} steps")
