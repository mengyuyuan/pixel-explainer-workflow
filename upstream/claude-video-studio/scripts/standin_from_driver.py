"""Stand-in take from a Blender driver video (static camera, clean background plate): a difference key against the plate ->
VP9-alpha WebM, so the composition's camera plan can be checked with the real choreography before the Kling takes exist.
The driver and the green character image share the framing (scripts/make_green.py), so a stand-in shows where the
real AI take will sit. Needs a clean background plate: render the driver scene once with the character hidden.
Usage: python scripts/standin_from_driver.py <driver.mp4> <plate.png> <out.webm> [--lo 7] [--hi 14]"""
import os, shutil, sys
if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-2d.txt"))
try:
    import numpy as np, scipy.ndimage as ndi
    from PIL import Image
except ImportError as e:
    sys.exit(f"{os.path.basename(__file__)}: missing Python package '{e.name}'. Install (~150 MB): python3 -m pip install -r {_REQ}")
if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):
    sys.exit(f"{os.path.basename(__file__)}: needs ffmpeg + ffprobe on PATH (macOS: brew install ffmpeg; Debian/Ubuntu: apt install ffmpeg)")
import subprocess
src, plate, out = sys.argv[1:4]
opt = lambda n, d: float(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
LO, HI = opt("--lo", 7), opt("--hi", 14)                   # max channel difference: <= LO transparent, >= HI opaque
P = np.asarray(Image.open(plate).convert("RGB"), np.int16); H, W = P.shape[:2]
dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                        "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-auto-alt-ref", "0", "-b:v", "8M", "-g", "15", out], stdin=subprocess.PIPE)
n = 0
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    f = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    d = np.abs(f.astype(np.int16) - P).max(2)
    a = np.clip((d - LO) * (1.0 / (HI - LO)), 0, 1)
    a = (np.maximum(a, ndi.binary_fill_holes(a > 0.5)) * 255).astype(np.uint8)       # fill skin that is close to the grey plate
    enc.stdin.write(np.dstack([f, a]).tobytes()); n += 1
enc.stdin.close(); enc.wait(); dec.wait()
print("wrote", out, n, "frames")
