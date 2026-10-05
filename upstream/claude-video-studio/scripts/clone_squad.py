#!/usr/bin/env python3
"""One dancer becomes a crew (「一人成团」): copies of her split off and dance behind her in a V formation, each row a beat
fraction later, like a canon; at the end they slide back into her.

What makes it read as a real crew instead of stickers:
  mattes     person_matte.py --drop-static (Apple Vision on macOS; MediaPipe elsewhere): hair and limbs stay complete,
             and a mural or poster of a person in the background is not cloned along.
  staging    a clone that stands further back is scaled about the HORIZON line (--horizon, fraction of the height where
             the camera's eye level cuts the frame), so its feet rise towards the horizon and its head sinks: real depth.
             Scaling about the feet instead makes small people standing on the same line.
  fit        the sideways offsets are clamped from the dancer's real extents over the whole clip, so no clone is ever
             cut by the frame edge.
  grounding  a soft contact shadow under every clone; far clones a little darker; drawn far-to-near, the live dancer last.
Row k is the dancer from k*--delay seconds ago. Clones split off one by one on the beats after --intro (--bpm/--offset)
and merge back --outro seconds before the end.
Needs a locked-off shot of ONE person with her feet in frame.
Usage: python clone_squad.py in.mp4 out.mp4 [--t0 S] [--dur S] [--width 1920] [--mattes DIR] [--rows 2] [--delay 0.3125]
                             [--spread 0.15] [--scale 0.82] [--horizon 0.46] [--dim 0.9] [--intro 1.0] [--outro 1.3]
                             [--bpm 96 --offset 0] [--audio music.wav [--audio-start S]] [--label "AI 拓展 · 一人成团"]
--mattes: a folder made by `person_matte.py in.mp4 DIR --t0 .. --dur .. --drop-static` (made automatically when omitted;
          --t0/--dur/--width then come from that folder).
Needs numpy, opencv, Pillow (for --label), ffmpeg; person_matte.py next to this file."""
import os, sys, json, subprocess, shutil, tempfile
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_HERE = os.path.dirname(os.path.abspath(__file__))
_REQ = os.path.normpath(os.path.join(_HERE, "..", "requirements-edit.txt"))
try:
    import numpy as np, cv2
    from PIL import Image, ImageDraw, ImageFont
except ImportError as e:
    sys.exit(f"clone_squad.py: missing Python package '{e.name}'. Install (~250 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("clone_squad.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
T0, DUR, OW, MATTES = opt("--t0", 0.0), opt("--dur", 0.0), opt("--width", 1920), opt("--mattes", "")
ROWS, DELAY, SPREAD, SCALE, HORIZON, DIM = opt("--rows", 2), opt("--delay", 0.3125), opt("--spread", 0.15), opt("--scale", 0.82), opt("--horizon", 0.46), opt("--dim", 0.9)
INTRO, OUTRO, BPM, OFFSET = opt("--intro", 1.0), opt("--outro", 1.3), opt("--bpm", 0.0), opt("--offset", 0.0)
AUDIO, ASTART, LABEL = opt("--audio", ""), opt("--audio-start", 0.0), opt("--label", "")
tmpdir = None
if not MATTES:
    tmpdir = tempfile.mkdtemp(prefix="clone_squad_"); MATTES = tmpdir
    cmd = [sys.executable, os.path.join(_HERE, "person_matte.py"), src, MATTES, "--t0", str(T0), "--width", str(OW), "--drop-static"] + (["--dur", str(DUR)] if DUR else [])
    subprocess.check_call(cmd)
META = json.load(open(os.path.join(MATTES, "meta.json")))
N, FPS, RATE, W, H = META["frames"], META["fps"], META["rate"], META["width"], META["height"]
frame = lambda i: cv2.imread(os.path.join(MATTES, "frames", f"{i:05d}.jpg"))
def mask_raw(i):
    m = cv2.imread(os.path.join(MATTES, "masks", f"{i:05d}.png"), 0)
    return m if m.shape == (H, W) else cv2.resize(m, (W, H), interpolation=cv2.INTER_LINEAR)


def clean(i, f=None):
    """The subject's soft mask as float 0..1 (person_matte.py --drop-static already removed murals and stray blobs)."""
    return mask_raw(i).astype(np.float32) / 255


# ---- the dancer's box in every frame (for the fit) and her floor contact
box = np.zeros((N, 5), np.float32)                     # x0, x1, y0, y1, cx
for i in range(N):
    b = clean(i) > 0.5
    ys, xs = np.where(b)
    if len(xs) < 200: box[i] = box[i - 1] if i else (W * 0.4, W * 0.6, H * 0.2, H * 0.95, W / 2); continue
    box[i] = (xs.min(), xs.max(), ys.min(), ys.max(), np.median(xs))
YH = HORIZON * H
if box[:, 3].max() < H * 0.6: print("warning: the feet never reach the lower part of the frame; --horizon staging assumes a full-body shot")
# formation: row k -> scale SCALE**k, delay k*DELAY, sideways offset fitted to the frame
lag = [int(round(k * DELAY * FPS)) for k in range(ROWS + 1)]
slots = []                                             # (row k, side, scale, offset px)
MARGIN = 0.012 * W
for k in range(1, ROWS + 1):
    s = SCALE ** k
    j = np.arange(max(0, int(INTRO * FPS) - lag[k]), max(1, min(N, int((N / FPS - OUTRO + 0.4) * FPS) - lag[k])))  # source frames this row shows
    x0 = s * box[j, 0] + (1 - s) * box[j, 4]; x1 = s * box[j, 1] + (1 - s) * box[j, 4]
    room = min((W - MARGIN - x1).min(), (x0 - MARGIN).min())
    want = SPREAD * W * k * (1 + 0.08 * (k - 1))
    d = max(0.0, min(want, room))
    if d < want * 0.999: print(f"row {k}: offset clamped {want:.0f} -> {d:.0f} px so the clones stay inside the frame")
    slots += [(k, -1, s, d), (k, 1, s, d)]
if BPM:
    bt = 60 / BPM; first = OFFSET + np.ceil((INTRO - OFFSET) / bt - 1e-6) * bt
    entry = {c[:2]: first + i * bt for i, c in enumerate(slots)}
else:
    entry = {c[:2]: INTRO + i * 0.5 for i, c in enumerate(slots)}
T_END = N / FPS; T_MERGE = T_END - OUTRO
SPLIT, MERGE = 0.42, 0.38                              # seconds for a clone to slide out / back in
ease = lambda u: 1 - (1 - np.clip(u, 0, 1)) ** 3
font = None
if LABEL:
    import glob
    for fp, ix in [(p, 11) for p in glob.glob("/System/Library/AssetsV2/com_apple_MobileAsset_Font*/*/AssetData/PingFang.ttc")] + \
                  [("/System/Library/Fonts/PingFang.ttc", 0), ("/System/Library/Fonts/STHeiti Medium.ttc", 1),
                   ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 0)]:
        if os.path.exists(fp):
            try: font = ImageFont.truetype(fp, int(H * 0.034), index=ix); break
            except Exception: pass
tmp = out + ".video.mp4"
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", RATE, "-i", "-",
                        "-c:v", "libx264", "-crf", "17", "-preset", "medium", "-pix_fmt", "yuv420p", "-g", "12", tmp], stdin=subprocess.PIPE)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
ring = {}                                              # frame index -> (bgr float, clean mask)
for i in range(N):
    t = i / FPS
    f8 = frame(i); m = clean(i, f8)
    f = f8.astype(np.float32) / 255
    ring[i] = (f, m)
    for old in [q for q in ring if q < i - lag[-1] - 1]: del ring[old]
    base = f.copy(); flash = 0.0
    for k, side, s_full, d_full in sorted(slots, key=lambda c: -c[0]):   # far rows first
        te = entry[(k, side)]
        if t < te or t > T_MERGE + MERGE: continue
        u = ease((t - te) / SPLIT) * (1 - ease((t - T_MERGE) / MERGE))    # 0 = inside her, 1 = in formation
        j = i - lag[k]
        if j not in ring: continue
        cf, cm = ring[j]
        s = 1 + (s_full - 1) * u; d = side * d_full * u
        cx = box[j, 4]
        M = np.float32([[s, 0, (1 - s) * cx + d], [0, s, (1 - s) * YH]])   # scale about (cx, horizon) + sideways
        a = cv2.warpAffine(cm, M, (W, H), flags=cv2.INTER_LINEAR)
        img = cv2.warpAffine(cf, M, (W, H), flags=cv2.INTER_LINEAR) * (DIM ** (k * u))
        # contact shadow: an ellipse under the clone's floor contact
        fy = s * box[j, 3] + (1 - s) * YH
        x0 = s * box[j, 0] + (1 - s) * cx + d; x1 = s * box[j, 1] + (1 - s) * cx + d
        low = a[max(0, int(fy - 0.05 * H * s)):int(fy) + 1]
        cols = np.where(low.max(0) > 0.5)[0]
        if len(cols): x0, x1 = cols.min(), cols.max()
        sh = np.exp(-(((xx - (x0 + x1) / 2) / max(40.0, (x1 - x0) * 0.62)) ** 2 + ((yy - fy + 4 * s) / (20 * s)) ** 2)) * 0.5 * u
        base *= (1 - sh[..., None])
        a3 = a[..., None]
        base = base * (1 - a3) + img * a3
        if 0 <= t - te < 0.12: flash = max(flash, 1 - (t - te) / 0.12)
    mm = m[..., None]
    base = base * (1 - mm) + f * mm                    # the live dancer in front
    if 0 <= t - (T_MERGE + MERGE * 0.6) < 0.14: flash = max(flash, 1 - (t - T_MERGE - MERGE * 0.6) / 0.14)
    if flash: base = np.clip(base + 0.16 * flash, 0, 1)
    img8 = (np.clip(base, 0, 1) * 255 + 0.5).astype(np.uint8)
    if font:
        im = Image.fromarray(img8[..., ::-1]); dr = ImageDraw.Draw(im); pad = int(H * 0.014)
        tw = dr.textlength(LABEL, font=font); x0, y0 = int(W * 0.025), int(H * 0.035)
        dr.rounded_rectangle([x0, y0, x0 + tw + 2 * pad, y0 + font.size + 2 * pad], radius=pad * 2, fill=(14, 18, 28))
        dr.text((x0 + pad, y0 + pad * 0.6), LABEL, font=font, fill=(255, 255, 255))
        img8 = np.asarray(im)[..., ::-1]
    enc.stdin.write(np.ascontiguousarray(img8).tobytes())
enc.stdin.close(); enc.wait()
if AUDIO:
    subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ss", f"{ASTART:.3f}", "-i", AUDIO, "-map", "0:v:0", "-map", "1:a:0",
                           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-af", f"afade=t=out:st={max(0, N / FPS - 0.6):.2f}:d=0.6",
                           "-shortest", "-movflags", "+faststart", out])
    os.remove(tmp)
else: os.replace(tmp, out)
if tmpdir: shutil.rmtree(tmpdir, ignore_errors=True)
print(f"wrote {out}: {N} frames {W}x{H} @ {FPS:.3f} fps, {len(slots)} clones in {ROWS} rows, matte backend {META.get('backend')}")
