#!/usr/bin/env python3
"""Environment check for claude-video-studio. Standard library only; it INSTALLS NOTHING.

It reports, per workflow, what is ready, what is missing, the command that would install it and roughly how much disk it
takes, plus what HyperFrames downloads by itself on first use. Show the missing items to the user and ask before
installing anything: some of them are large.

Usage: python3 scripts/check_env.py [--project DIR]    (DIR = the video project, for project-level HyperFrames skills)
Exit code: 0 when the core pixel/flat MV workflow is ready, 1 otherwise."""
import glob, importlib.util, os, platform, re, shutil, subprocess, sys

if any(a in ("-h", "--help") for a in sys.argv[1:]): print(__doc__); sys.exit(0)
PROJECT = sys.argv[sys.argv.index("--project") + 1] if "--project" in sys.argv else os.getcwd()
HOME = os.path.expanduser("~")
MAC = platform.system() == "Darwin"
PKG = "brew install" if MAC else "sudo apt install"


def run(cmd):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception: return ""


def mod(name): return importlib.util.find_spec(name) is not None


def ok(flag): return "OK  " if flag else "MISS"


rows = []                                    # (workflow, item, ready, how to get it)
py_ok = sys.version_info >= (3, 9)
rows.append(("core", f"Python {platform.python_version()} (3.9+)", py_ok, "install Python 3.9-3.12 (3.12 max for mediapipe 0.10.14)"))
ff = shutil.which("ffmpeg") and shutil.which("ffprobe")
enc = run(["ffmpeg", "-hide_banner", "-encoders"]) if ff else ""
rows.append(("core", "ffmpeg + ffprobe", bool(ff), f"{PKG} ffmpeg  (~100 MB)"))
rows.append(("core", "ffmpeg encoder libx264", "libx264" in enc, f"an ffmpeg build with libx264 ({PKG} ffmpeg)"))
node = shutil.which("node") or glob.glob(f"{HOME}/.nvm/versions/node/*/bin/node")
nv = run([node if isinstance(node, str) else node[-1], "--version"]).strip() if node else ""
node_ok = bool(nv) and int(re.sub(r"\D.*", "", nv.lstrip("v")) or 0) >= 18
rows.append(("core", f"Node.js 18+ {nv}".strip(), node_ok, "https://nodejs.org or nvm install 20  (~100 MB)"))
hf_skill = [p for p in (f"{HOME}/.claude/skills/hyperframes/SKILL.md", f"{PROJECT}/.claude/skills/hyperframes/SKILL.md",
                        f"{HOME}/.agents/skills/hyperframes/SKILL.md") if os.path.exists(p)]
rows.append(("core", "HyperFrames skills (/hyperframes)", bool(hf_skill), "npx skills add heygen-com/hyperframes -s '*' -a claude-code -y"))
chrome = glob.glob(f"{HOME}/.cache/hyperframes/chrome/*")
rows.append(("core", "HyperFrames headless Chrome", bool(chrome),
             "downloaded automatically on the first check/snapshot/render (~400 MB), or up front: npx hyperframes@0.8.70 browser ensure"))

m2v = [p for p in (f"{PROJECT}/.claude/skills/music-to-video/scripts/analyze-beatgrid.py", f"{HOME}/.claude/skills/music-to-video/scripts/analyze-beatgrid.py",
                   f"{PROJECT}/.agents/skills/music-to-video/scripts/analyze-beatgrid.py") if os.path.exists(p)]
rows.append(("beat sync", "music-to-video skill (analyze-beatgrid.py)", bool(m2v), "npx hyperframes skills update music-to-video  (in the video project)"))
beat_mods = all(mod(m) for m in ("librosa", "soundfile", "numpy"))
rows.append(("beat sync", "librosa + soundfile + numpy", beat_mods, "python3 -m pip install librosa soundfile numpy  (~280 MB incl. numba/llvmlite/scipy)"))

rows.append(("voice-over", "edge-tts", mod("edge_tts") or bool(shutil.which("edge-tts")), "python3 -m pip install edge-tts  (~5 MB; needs network at synthesis time)"))

d2 = all(mod(m) for m in ("numpy", "scipy", "PIL"))
rows.append(("2D motion transfer", "numpy + scipy + Pillow", d2, "python3 -m pip install -r requirements-2d.txt  (~150 MB)"))
rows.append(("2D motion transfer", "ffmpeg encoder libvpx-vp9 (alpha WebM)", "libvpx-vp9" in enc, f"an ffmpeg build with libvpx ({PKG} ffmpeg)"))
mp_ok, mp_note = False, "python3 -m pip install -r requirements-face.txt  (mediapipe==0.10.14 + OpenCV/jax, ~600 MB; Python 3.9-3.12)"
if mod("mediapipe"):
    v = run([sys.executable, "-c", "import mediapipe as m; print(m.__version__, hasattr(m, 'solutions'))"]).split()
    mp_ok = len(v) == 2 and v[1] == "True"
    if not mp_ok: mp_note = f"installed mediapipe {v[0] if v else '?'} lacks the legacy FaceMesh API; " + mp_note
rows.append(("2D lip/iris checks", "mediapipe 0.10.x with FaceMesh", mp_ok, mp_note))

ed = all(mod(m) for m in ("numpy", "scipy", "PIL", "cv2"))
rows.append(("AI editing (real footage)", "numpy + scipy + Pillow + OpenCV", ed, "python3 -m pip install -r requirements-edit.txt  (~250 MB)"))
xi = mod("cv2") and bool(run([sys.executable, "-c", "import cv2; print(hasattr(cv2, 'ximgproc'))"]).strip() == "True")
rows.append(("AI editing (real footage)", "OpenCV contrib (guided filter, optional)", xi, "python3 -m pip install opencv-contrib-python  (replaces opencv-python)"))
rows.append(("AI editing (real footage)", "face / pose / person masks: mediapipe 0.10.x", mp_ok, "python3 -m pip install -r requirements-face.txt  (~600 MB)"))
rows.append(("AI editing (real footage)", "noisereduce (speech denoise)", mod("noisereduce"), "python3 -m pip install noisereduce  (~5 MB)"))
rows.append(("AI editing (real footage)", "clean person mattes: Apple Vision via swiftc (macOS only; else MediaPipe)",
             platform.system() == "Darwin" and bool(shutil.which("swiftc")), "macOS: xcode-select --install  (no model download); other systems fall back to MediaPipe"))
rows.append(("AI editing (real footage)", "re-dub (redub.py): edge-tts + soundfile", mod("edge_tts") and mod("soundfile"),
             "python3 -m pip install edge-tts soundfile  (~10 MB; edge-tts needs network at synthesis time)"))
asr = mod("funasr") and mod("torch")
rows.append(("Chinese transcription", "FunASR + torch (transcribe_zh.py)", asr,
             "python3 -m pip install -r requirements-asr.txt  (~1 GB; models 1-3 GB download from ModelScope on first run; Python 3.10-3.12)"))

blender = (os.environ.get("BLENDER") if os.path.exists(os.environ.get("BLENDER", "")) else None) or shutil.which("blender") \
    or next(iter(glob.glob("/Applications/Blender*.app/Contents/MacOS/Blender")), None)
rows.append(("3D / drivers", "Blender 4.5 LTS", bool(blender), "https://www.blender.org/download/lts/  (~1 GB); a portable copy works too: set BLENDER=/path/to/Blender"))

w = max(len(r[1]) for r in rows)
cur = None
for wf, item, ready, how in rows:
    if wf != cur: print(f"\n[{wf}]"); cur = wf
    print(f"  {ok(ready)}  {item.ljust(w)}" + ("" if ready else f"\n        -> {how}"))
core_ok = all(r[2] for r in rows if r[0] == "core" and "Chrome" not in r[1])
print("\nAuto-downloads you should mention before the first run:")
print("  - `npx hyperframes@0.8.70 ...` fetches the HyperFrames CLI from npm on first use (npx asks unless --yes).")
print("  - The first check/snapshot/render downloads HyperFrames' headless Chrome (~400 MB) if it is not cached.")
print("  - Nothing else downloads by itself: every MISS above needs an explicit install, so ask the user first.")
print(f"\ncore pixel/flat MV workflow: {'READY' if core_ok else 'NOT READY'}")
sys.exit(0 if core_ok else 1)
