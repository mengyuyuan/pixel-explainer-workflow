"""Place a cut-out character (RGBA PNG) on a flat chroma-green canvas, framed to match a driving video's first frame.
Motion-transfer tools (Kling 「动作控制」, 即梦 「动作模仿」) and image-to-video (Gemini / Veo) keep the input image's framing,
so the image must put the character where the driver's first frame has it: same head height, same feet or chin line,
same centre line.

Usage:
  python make_green.py cut.png wide  --head-y 201.7 --feet-y 978.3 --cx 938.4 [--out green-wide.png]
  python make_green.py cut.png close --head-y 43 --chin-y 301 --cx 960 [--src-chin 266] [--out green-close.png]
wide:  scale so the cut-out's head top and lowest opaque row (soles) land on --head-y / --feet-y (full body).
close: scale so the head top and the chin land on --head-y / --chin-y (waist-up; the body below the frame is cut).
Source rows are measured from the alpha automatically (head top = first opaque row, soles = last opaque row, centre =
middle of the opaque columns across the top 12 % of the figure). The chin can't be found from alpha: pass --src-chin
(the chin row on the cut-out) for close framing. Override any of them with --src-head / --src-feet / --src-cx.
Read the driver's numbers off its first frame (or the renderer's framing export)."""
import os, shutil, sys
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-2d.txt"))
try:
    import numpy as np
    from PIL import Image
except ImportError as e:
    sys.exit(f"{os.path.basename(__file__)}: missing Python package '{e.name}'. Install (~150 MB): python3 -m pip install -r {_REQ}")
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("cut"); ap.add_argument("mode", choices=["wide", "close"])
ap.add_argument("--head-y", type=float, required=True); ap.add_argument("--feet-y", type=float); ap.add_argument("--chin-y", type=float)
ap.add_argument("--cx", type=float, default=960); ap.add_argument("--w", type=int, default=1920); ap.add_argument("--h", type=int, default=1080)
ap.add_argument("--src-head", type=float); ap.add_argument("--src-feet", type=float); ap.add_argument("--src-chin", type=float); ap.add_argument("--src-cx", type=float)
ap.add_argument("--green", default="00B140", help="canvas colour, hex (#00B140 is far from skin, hair and most costumes)")
ap.add_argument("--out", default=None)
a = ap.parse_args()
im = Image.open(a.cut).convert("RGBA")
alpha = np.asarray(im)[..., 3] > 128
rows = np.nonzero(alpha.any(1))[0]
head = a.src_head if a.src_head is not None else float(rows[0])
feet = a.src_feet if a.src_feet is not None else float(rows[-1] + 1)
if a.src_cx is None:
    top = alpha[rows[0]:rows[0] + max(4, int(0.12 * (rows[-1] - rows[0])))]
    cols = np.nonzero(top.any(0))[0]; src_cx = (cols[0] + cols[-1] + 1) / 2
else: src_cx = a.src_cx
if a.mode == "wide":
    if a.feet_y is None: ap.error("wide needs --feet-y")
    s = (a.feet_y - a.head_y) / (feet - head)
else:
    if a.chin_y is None or a.src_chin is None: ap.error("close needs --chin-y and --src-chin")
    s = (a.chin_y - a.head_y) / (a.src_chin - head)
sw, sh = round(im.width * s), round(im.height * s)
im = im.resize((sw, sh), Image.LANCZOS)
x0 = round(a.cx - src_cx * s); y0 = round(a.head_y - head * s)
g = tuple(int(a.green[i:i + 2], 16) for i in (0, 2, 4))
canvas = Image.new("RGBA", (a.w, a.h), g + (255,))
canvas.paste(im, (x0, y0), im)
out = a.out or f"green-{a.mode}.png"
canvas.convert("RGB").save(out)
print(f"{out}: source head {head:.0f} feet {feet:.0f} cx {src_cx:.1f}; scale {s:.3f}, placed at ({x0},{y0}), character {sw}x{sh}")
