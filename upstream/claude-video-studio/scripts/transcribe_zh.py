#!/usr/bin/env python3
"""Chinese speech -> per-character timestamps, sentences, an SRT, and edit candidates (long pauses, repeated phrases),
all local (FunASR, no API).

Engines (models download from ModelScope on first use, roughly 1-3 GB in total; say so before running):
  paraformer (default) - Paraformer-zh + FSMN-VAD + CT punctuation: per-character timestamps, good Mandarin;
  --nano               - also runs Fun-ASR-Nano-2512 (accent/dialect robust, e.g. Sichuanese) and prints its text per
                         speech segment next to Paraformer's, to decode accent words before writing subtitles.
Edit candidates (for the human/agent to judge, never cut blindly):
  pauses   - gaps between characters longer than --pause s (dead air to trim);
  repeats  - the same 2-4 character phrase said twice within 6 s, or the same characters in another order (a
             garbled restart such as 「消口伤毒…消毒伤口」).
Output JSON: {"chars": [{"c", "s", "e"}], "sentences": [{"s", "e", "text"}], "pauses": [...], "repeats": [...], "nano": [...]}
Usage: python transcribe_zh.py in.(wav|mp4|m4a) out.json [--srt out.srt] [--hotwords "碘伏 狂犬疫苗"] [--pause 1.2] [--nano]
Needs: pip install -r requirements-asr.txt (torch + funasr + modelscope, ~1 GB), ffmpeg."""
import os, sys, json, re, subprocess, tempfile, shutil
if len(sys.argv) < 3 or sys.argv[1] in ("-h", "--help"): print(__doc__); sys.exit(0 if len(sys.argv) > 1 else 2)
_REQ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "requirements-asr.txt"))
try:
    from funasr import AutoModel
except ImportError as e:
    sys.exit(f"transcribe_zh.py: missing Python package '{e.name}'. Install (~1 GB, torch + funasr): python3 -m pip install -r {_REQ}")
if not shutil.which("ffmpeg"): sys.exit("transcribe_zh.py: needs ffmpeg on PATH (macOS: brew install ffmpeg)")
src, out = sys.argv[1], sys.argv[2]
opt = lambda n, d=None: sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d
SRT, HOT, PAUSE, NANO = opt("--srt"), opt("--hotwords", ""), float(opt("--pause", 1.2)), "--nano" in sys.argv
wav = os.path.join(tempfile.mkdtemp(), "a16k.wav")
subprocess.check_call(["ffmpeg", "-v", "error", "-y", "-i", src, "-vn", "-ac", "1", "-ar", "16000", wav])
m = AutoModel(model="paraformer-zh", vad_model="fsmn-vad", punc_model="ct-punc-c", disable_update=True, device="cpu")
r = m.generate(input=wav, batch_size_s=60, sentence_timestamp=True, hotword=HOT)[0]
PUNC = "，。？、！,.?!；;：:"
chars = [c for c in r["text"].replace(" ", "") if c not in PUNC]
ts = r.get("timestamp", [])
C = [{"c": c, "s": round(a / 1000, 3), "e": round(b / 1000, 3)} for c, (a, b) in zip(chars, ts)]
S = [{"s": round(x["start"] / 1000, 3), "e": round(x["end"] / 1000, 3), "text": x["text"]} for x in r.get("sentence_info", [])]
pauses = [{"after": C[i]["c"], "s": C[i]["e"], "e": C[i + 1]["s"], "dur": round(C[i + 1]["s"] - C[i]["e"], 2)}
          for i in range(len(C) - 1) if C[i + 1]["s"] - C[i]["e"] >= PAUSE]
text = "".join(x["c"] for x in C)
reps, seen = [], set()
for n in (4, 3, 2):
    for i in range(len(text) - n):
        g = text[i:i + n]
        if not re.fullmatch(r"[一-鿿]+", g): continue
        j = text.find(g, i + n)
        if j > 0 and C[j]["s"] - C[i]["s"] <= 6.0 and not any(abs(C[i]["s"] - a) < 1 for a, _ in seen):
            reps.append({"phrase": g, "first": C[i]["s"], "again": C[j]["s"], "kind": "repeat", "context": text[max(0, i - 6):j + n + 6]})
            seen.add((C[i]["s"], g))
        if n >= 3:                                                   # scrambled restart: same characters, other order
            for k in range(i + n, min(len(text) - n + 1, i + 40)):      # starts after the first one ends
                h = text[k:k + n]
                if h != g and sorted(h) == sorted(g) and C[k]["s"] - C[i]["s"] <= 6.0 and not any(abs(C[i]["s"] - a) < 1 for a, _ in seen):
                    reps.append({"phrase": g, "first": C[i]["s"], "again": C[k]["s"], "kind": "scrambled", "context": text[max(0, i - 6):k + n + 6]})
                    seen.add((C[i]["s"], g)); break
nano = []
if NANO:
    mn = AutoModel(model="FunAudioLLM/Fun-ASR-Nano-2512", vad_model="fsmn-vad", vad_kwargs={"max_single_segment_time": 15000},
                   disable_update=True, device="cpu", hub="ms")
    rn = mn.generate(input=wav, batch_size_s=0, language="中文", hotwords=HOT.split() if HOT else None)[0]
    nano = [{"text": rn.get("text", ""), "ctc_text": rn.get("ctc_text", "")}]
json.dump({"chars": C, "sentences": S, "pauses": pauses, "repeats": reps, "nano": nano}, open(out, "w"), ensure_ascii=False, indent=1)
if SRT:
    def ts_(x): h, rem = divmod(x, 3600); mi, se = divmod(rem, 60); return f"{int(h):02d}:{int(mi):02d}:{int(se):02d},{int(round((se % 1) * 1000)):03d}"
    open(SRT, "w", encoding="utf-8").write("".join(f"{k + 1}\n{ts_(x['s'])} --> {ts_(x['e'])}\n{x['text']}\n\n" for k, x in enumerate(S)))
print(f"wrote {out}: {len(C)} chars, {len(S)} sentences, {len(pauses)} pauses >= {PAUSE}s, {len(reps)} repeat candidates"
      + (", Fun-ASR-Nano text included" if nano else ""))
for p in pauses[:12]: print(f"  pause {p['s']:7.2f}-{p['e']:7.2f} ({p['dur']}s) after 「{p['after']}」")
for x in sorted(reps, key=lambda r: r["kind"] != "scrambled")[:10]: print(f"  {x['kind']} 「{x['phrase']}」 at {x['first']:.2f} and {x['again']:.2f}: …{x['context']}…")
