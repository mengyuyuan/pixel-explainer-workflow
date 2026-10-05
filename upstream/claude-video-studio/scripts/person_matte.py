#!/usr/bin/env python3
"""Per-frame mattes for a clip, with the best segmenter this machine has: out_dir/frames/%05d.jpg + out_dir/masks/%05d.png
(soft 8-bit alpha, same size) + out_dir/meta.json. Other scripts take the folder with --mattes (clone_squad.py,
pop_out.py, echo_trail.py).

Backends (--backend auto picks the first that works):
  vision      macOS 12+: Apple Vision person segmentation, quality "accurate". Clean hair and limbs, no model download;
              a short Swift helper is compiled once with swiftc (Xcode command line tools) into ~/.cache.
  vision-fg   macOS 14+: Vision foreground-instance masks ("lift subject"): people AND what they hold or ride
              (skateboard, ball). Class-agnostic, so parked cars etc. can come along: check a few frames.
  mediapipe   anywhere: selfie segmentation + guided filter. Blocky on hair and fast limbs; fine for silhouettes.
--drop-static   for a MOVING subject in a locked-off shot: remove what is "always masked and never changing" (a mural or
                poster of a person, a parked car) and every blob that looks like the empty scene or is tiny next to the
                subject. Do not use it on someone who stands still (they would be removed too).
Usage: python person_matte.py in.mp4 out_dir [--t0 S] [--dur S] [--width 1920] [--backend auto|vision|vision-fg|mediapipe]
                              [--drop-static] [--preview sheet.jpg]
--preview writes a contact sheet of the cut-outs on magenta: look at it before building on the mattes.
Needs ffmpeg, numpy, opencv (requirements-edit.txt); mediapipe only for that backend (requirements-face.txt)."""
import os, sys, json, subprocess, shutil, glob
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_HERE = os.path.dirname(os.path.abspath(__file__))
_REQ = os.path.normpath(os.path.join(_HERE, "..", "requirements-edit.txt"))
try:
    import numpy as np, cv2
except ImportError as e:
    sys.exit(f"person_matte.py: missing Python package '{e.name}'. Install (~250 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit("person_matte.py: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg)")
sys.path.insert(0, _HERE)
import vision_matte
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
T0, DUR, OW, BACKEND, PREVIEW = opt("--t0", 0.0), opt("--dur", 0.0), opt("--width", 1920), opt("--backend", "auto"), opt("--preview", "")
DROP = "--drop-static" in sys.argv
info = json.loads(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                           "stream=width,height,r_frame_rate:format=duration", "-of", "json", src]))
W0, H0 = info["streams"][0]["width"], info["streams"][0]["height"]; RATE = info["streams"][0]["r_frame_rate"]
num, den = map(int, RATE.split("/")); FPS = num / den
DUR = DUR or float(info["format"]["duration"]) - T0
OH = int(round(OW * H0 / W0 / 2) * 2)
FR, MK = os.path.join(out, "frames"), os.path.join(out, "masks")
for d in (FR, MK):
    shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
subprocess.check_call(["ffmpeg", "-v", "error", "-ss", f"{T0:.3f}", "-i", src, "-t", f"{DUR:.3f}", "-vf", f"scale={OW}:{OH}:flags=area",
                       "-q:v", "2", "-start_number", "0", os.path.join(FR, "%05d.jpg")])
n = len(glob.glob(os.path.join(FR, "*.jpg")))
used = None
for kind in ([BACKEND] if BACKEND != "auto" else ["vision", "mediapipe"]):
    if kind in vision_matte.SWIFT:
        if vision_matte.run_dir(kind, FR, MK) and len(glob.glob(os.path.join(MK, "*.png"))) == n: used = kind; break
        if BACKEND != "auto": sys.exit(f"person_matte.py: backend {kind} needs macOS with swiftc (xcode-select --install)")
    else:
        try:
            import mediapipe as mp
            assert hasattr(mp, "solutions")
        except Exception:
            sys.exit("person_matte.py: no backend available. macOS: install the Xcode command line tools; elsewhere: "
                     "python3 -m pip install -r " + _REQ.replace("-edit", "-face"))
        seg = mp.solutions.selfie_segmentation.SelfieSegmentation(model_selection=1)
        GF = hasattr(cv2, "ximgproc") and hasattr(cv2.ximgproc, "guidedFilter"); prev = None
        for i in range(n):
            rgb = cv2.cvtColor(cv2.imread(os.path.join(FR, f"{i:05d}.jpg")), cv2.COLOR_BGR2RGB)
            m = seg.process(rgb).segmentation_mask.astype(np.float32)
            m = cv2.ximgproc.guidedFilter(rgb, m, 8, 1e-3) if GF else cv2.GaussianBlur(m, (0, 0), 2)
            m = np.clip((m - 0.25) / 0.5, 0, 1); m = m if prev is None else 0.65 * m + 0.35 * prev; prev = m
            cv2.imwrite(os.path.join(MK, f"{i:05d}.png"), (m * 255 + 0.5).astype(np.uint8))
        used = "mediapipe"; break
if not used: sys.exit("person_matte.py: no backend produced masks")
frame = lambda i: cv2.imread(os.path.join(FR, f"{i:05d}.jpg"))
def mask(i):
    m = cv2.imread(os.path.join(MK, f"{i:05d}.png"), 0)
    return m if m.shape == (OH, OW) else cv2.resize(m, (OW, OH), interpolation=cv2.INTER_LINEAR)
for i in range(n):                                      # normalise the mask size once (Vision can be a pixel off)
    m = cv2.imread(os.path.join(MK, f"{i:05d}.png"), 0)
    if m.shape != (OH, OW): cv2.imwrite(os.path.join(MK, f"{i:05d}.png"), cv2.resize(m, (OW, OH), interpolation=cv2.INTER_LINEAR))
dropped = 0.0
if DROP:
    hw, hh = OW // 2, OH // 2; idx = list(range(0, n, 3))
    G = np.stack([cv2.resize(cv2.cvtColor(frame(i), cv2.COLOR_BGR2GRAY), (hw, hh), interpolation=cv2.INTER_AREA) for i in idx]).astype(np.float32)
    P = np.stack([cv2.resize(mask(i), (hw, hh), interpolation=cv2.INTER_AREA) > 100 for i in idx])
    plate = cv2.resize(np.median(G, 0), (OW, OH), interpolation=cv2.INTER_LINEAR)
    static = cv2.dilate(((P.mean(0) > 0.5) & (G.std(0) < 8)).astype(np.uint8), np.ones((15, 15), np.uint8))
    S = cv2.resize(static, (OW, OH), interpolation=cv2.INTER_NEAREST).astype(bool); dropped = float(S.mean())
    del G, P
    for i in range(n):
        m = mask(i).astype(np.float32) / 255
        diff = np.abs(cv2.cvtColor(frame(i), cv2.COLOR_BGR2GRAY).astype(np.float32) - plate)
        if S.any(): m = np.where(S, m * np.clip((diff - 10) / 20, 0, 1), m)
        num_, lab, st, _ = cv2.connectedComponentsWithStats((m > 0.4).astype(np.uint8), 8)
        if num_ > 2:
            areas = st[:, cv2.CC_STAT_AREA].astype(np.float32); areas[0] = 0
            moving = np.zeros(num_, bool)
            for c in range(1, num_):
                if areas[c] < 400: continue
                x, y, w, h = st[c, :4]
                moving[c] = diff[y:y + h, x:x + w][lab[y:y + h, x:x + w] == c].mean() > 7
            if not moving.any(): moving[int(np.argmax(areas))] = True
            keep = moving & (areas >= 0.04 * (areas * moving).max())
            m = m * cv2.dilate(keep[lab].astype(np.uint8), np.ones((21, 21), np.uint8))
        cv2.imwrite(os.path.join(MK, f"{i:05d}.png"), (m * 255 + 0.5).astype(np.uint8))
json.dump({"source": os.path.abspath(src), "t0": T0, "dur": DUR, "fps": FPS, "rate": RATE, "width": OW, "height": OH, "frames": n,
           "backend": used, "drop_static": DROP}, open(os.path.join(out, "meta.json"), "w"), indent=1)
if PREVIEW:
    cells = []
    for i in np.linspace(0, n - 1, 8).astype(int):
        f = frame(i); a = (mask(i).astype(np.float32) / 255)[..., None]; bg = np.zeros_like(f); bg[:] = (200, 60, 200)
        cells.append(cv2.resize((f * a + bg * (1 - a)).astype(np.uint8), (640, int(640 * OH / OW))))
    cv2.imwrite(PREVIEW, np.vstack([np.hstack(cells[:4]), np.hstack(cells[4:])]), [cv2.IMWRITE_JPEG_QUALITY, 88])
print(f"wrote {out}: {n} frames {OW}x{OH} @ {FPS:.3f} fps, backend {used}"
      + (f", static false positives removed ({dropped * 100:.1f}% of the frame)" if DROP else "") + (f", preview {PREVIEW}" if PREVIEW else ""))
