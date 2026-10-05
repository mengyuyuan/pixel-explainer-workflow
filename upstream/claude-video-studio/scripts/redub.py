#!/usr/bin/env python3
"""Re-voice a video line by line with edge-tts: dialect -> Mandarin, or replace a voice that must not be published.
Every line is said again at the moment the original line was said, and the subtitles are re-timed to the new voice.

lines.json - a list of lines on the output clock:
  [{"t0": 0.9, "t1": 2.0, "say": "等一下！", "show": "等一下！", "group": 0}, ...]
  t0/t1  when the original line was spoken (from your transcript, e.g. transcribe_zh.py char times)
  say    text for the voice (punctuation shapes the prosody); show = subtitle text (defaults to say; "" = no subtitle,
         e.g. a step title already on a card)
  group  lines with the same group are said in one breath (one TTS call, natural intonation across a sentence that the
         subtitles split); WordBoundary events give each line's own start/end back. Default: one group per line.
Per group the speaking rate is fitted so the new line covers about the original span (no slower than --min-rate, no
faster than --max-rate) and never runs into the next group; ffmpeg atempo only as a last resort.
Outputs: out.wav = the voice alone (48 kHz stereo, two-pass loudnorm to --lufs) and --subs = re-timed subtitles
[{t0, t1, text}]. Mix it with music / SFX / a voice-free room tone yourself; never leave the original voice under it.
Usage: python redub.py lines.json out.wav [--voice zh-CN-XiaoxiaoNeural] [--total S] [--subs subs.json] [--lufs -16]
                       [--min-rate -10] [--max-rate 60] [--cache dub_cache/]
Voices: edge-tts --list-voices | grep zh-CN (XiaoxiaoNeural warm female, YunxiNeural male, YunyangNeural news male).
Needs edge-tts (pip install edge-tts; free, online, no key), numpy, soundfile, ffmpeg."""
import os, sys, json, asyncio, subprocess, shutil, hashlib
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
try:
    import numpy as np, soundfile as sf, edge_tts
except ImportError as e:
    sys.exit(f"redub.py: missing Python package '{e.name}'. Install: python3 -m pip install edge-tts numpy soundfile")
if not shutil.which("ffmpeg"): sys.exit("redub.py: needs ffmpeg on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d: type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d
VOICE, TOTAL, SUBS, LUFS = opt("--voice", "zh-CN-XiaoxiaoNeural"), opt("--total", 0.0), opt("--subs", ""), opt("--lufs", -16.0)
RMIN, RMAX, CACHE = opt("--min-rate", -10), opt("--max-rate", 60), opt("--cache", os.path.splitext(out)[0] + "_cache")
SR = 48000
PUNCT = set("，。？！、：；…,.?!:;~～ “”\"'（）()《》—-")
lines = json.load(open(src))
for i, l in enumerate(lines):
    l.setdefault("show", l.get("say", "")); l.setdefault("say", l["show"]); l.setdefault("group", f"_{i}")
groups = []
for l in lines:
    if groups and groups[-1][0]["group"] == l["group"]: groups[-1].append(l)
    else: groups.append([l])
TOTAL = TOTAL or max(l["t1"] for l in lines) + 2.0
N = int(round(TOTAL * SR))
os.makedirs(CACHE, exist_ok=True)


async def _synth(text, rate, path):
    words, audio = [], bytearray()
    async for ch in edge_tts.Communicate(text, VOICE, rate=f"{rate:+d}%", boundary="WordBoundary").stream():
        if ch["type"] == "audio": audio += ch["data"]
        elif ch["type"] == "WordBoundary": words.append([ch["offset"] / 1e7, (ch["offset"] + ch["duration"]) / 1e7, ch["text"]])
    open(path, "wb").write(audio); json.dump(words, open(path + ".json", "w"), ensure_ascii=False)


def tts(text, rate):
    """(trimmed mono float32 @48k, trim offset s, word boundaries) - cached by voice/rate/text."""
    key = hashlib.md5(f"{VOICE}|{text}".encode()).hexdigest()[:12] + f"_r{rate:+d}"
    path = os.path.join(CACHE, key + ".mp3")
    if not (os.path.exists(path) and os.path.exists(path + ".json")):
        for attempt in range(4):
            try: asyncio.run(_synth(text, rate, path)); break
            except Exception as e:
                if attempt == 3: sys.exit(f"edge-tts failed for 「{text}」: {e} (it needs internet)")
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                                     capture_output=True, check=True).stdout, np.float32).copy()
    w = int(0.01 * SR); r = 20 * np.log10(np.sqrt(np.convolve(x ** 2, np.ones(w) / w, "same")) + 1e-9)
    on = np.where(r > r.max() - 38)[0]
    a, b = max(0, on[0] - int(0.015 * SR)), min(len(x), on[-1] + int(0.06 * SR))
    return x[a:b], a / SR, json.load(open(path + ".json"))


def atempo(x, f):
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", f"atempo={f:.4f}",
                        "-f", "f32le", "-ar", str(SR), "-ac", "1", "-"], input=x.astype(np.float32).tobytes(), capture_output=True)
    return np.frombuffer(p.stdout, np.float32).copy()


dub = np.zeros(N, np.float32); subs = []
for gi, g in enumerate(groups):
    text = "".join(l["say"] for l in g)
    s0, s1 = g[0]["t0"], g[-1]["t1"]
    nxt = groups[gi + 1][0]["t0"] if gi + 1 < len(groups) else TOTAL
    span, room = s1 - s0, nxt - 0.12 - s0
    x, off, words = tts(text, 0); d0 = len(x) / SR
    if d0 > span: target = min(room, max(span, d0 / 1.22))     # a bit faster, but do not rush to match a fast speaker
    elif d0 < 0.85 * span: target = min(d0 / 0.9, 0.95 * span)  # a little slower, the rest stays a natural pause
    else: target = d0
    rate = int(np.clip(round((d0 / target - 1) * 100), RMIN, RMAX))
    if rate: x, off, words = tts(text, rate)
    f = 1.0
    if len(x) / SR > room + 0.02: f = (len(x) / SR) / room; x = atempo(x, f)
    fd = int(0.008 * SR); x[:fd] *= np.linspace(0, 1, fd); x[-fd:] *= np.linspace(1, 0, fd)
    o = int(round(s0 * SR)); n = min(len(x), N - o); dub[o:o + n] += x[:n]
    print(f"{s0:7.2f}-{s0 + len(x) / SR:7.2f}  (was {s0:.2f}-{s1:.2f})  rate {rate:+d}%{f' tempo x{f:.2f}' if f != 1 else ''}  {text}")
    chars = []                                       # per spoken character: (start, end) inside the TTS clip
    for ws, we, wt in words:
        cs = [c for c in wt if c not in PUNCT]
        chars += [(ws + (we - ws) * k / len(cs), ws + (we - ws) * (k + 1) / len(cs)) for k in range(len(cs))]
    k = 0
    for l in g:
        nc = sum(c not in PUNCT for c in l["say"]); seg = chars[k:k + nc]; k += nc
        if l["show"] and seg:
            subs.append({"t0": round(s0 + (seg[0][0] - off) / f - 0.05, 3), "t1": round(s0 + (seg[-1][1] - off) / f + 0.25, 3), "text": l["show"]})
for a, b in zip(subs, subs[1:]): a["t1"] = round(min(a["t1"], b["t0"] - 0.03), 3)
raw = out + ".raw.wav"
sf.write(raw, np.repeat(dub[:, None], 2, 1), SR)
m = subprocess.run(["ffmpeg", "-hide_banner", "-i", raw, "-af", f"loudnorm=I={LUFS}:TP=-2:LRA=9:print_format=json", "-f", "null", "-"],
                   capture_output=True, text=True).stderr
m = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af",
                       f"highpass=f=90,loudnorm=I={LUFS}:TP=-2:LRA=9:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
                       f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true",
                       "-ar", str(SR), "-ac", "2", out])
os.remove(raw)
if SUBS: json.dump(subs, open(SUBS, "w"), ensure_ascii=False, indent=0)
print(f"wrote {out} ({TOTAL:.2f}s, {len(groups)} groups, {len(subs)} subtitles{', ' + SUBS if SUBS else ''})")
