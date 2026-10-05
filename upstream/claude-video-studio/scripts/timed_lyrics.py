#!/usr/bin/env python3
"""Turn lyrics into an exact bar-by-bar timeline for an AI music app, plus lyrics.json and lyrics.srt.

Input format (UTF-8 text):
    [Intro | beat enters, spoken hype voice]
    Yo, this is the intro
    [Verse 1 | full trap beat, fast confident flow]
    First line of the verse
    Second line takes two bars *2
    (blank line = one bar of beat only)

One line = one bar unless it ends with "*N" (N bars). A section header is "[Name | feel]".

Usage:
    python3 timed_lyrics.py lyrics.txt --bpm 96 --title "My Song" --style "Chinese hype hip-hop, male rapper, trap drums"
Writes prompt.txt, lyrics.json and lyrics.srt next to the input.
"""
import argparse, json, os, re

ap = argparse.ArgumentParser()
ap.add_argument("lyrics"); ap.add_argument("--bpm", type=float, default=96); ap.add_argument("--beats-per-bar", type=int, default=4)
ap.add_argument("--title", default=""); ap.add_argument("--style", default="clear vocals, steady drums")
a = ap.parse_args()
BAR = 60.0 / a.bpm * a.beats_per_bar

def mmss(t): return f"{int(t // 60)}:{t % 60:04.1f}"
def srt(t): return f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}:{int(t % 60):02d},{int(round(t * 1000)) % 1000:03d}"

sections, cur = [], None
for raw in open(a.lyrics, encoding="utf-8").read().splitlines():
    s = raw.strip()
    m = re.match(r"^\[(.+?)(?:\|(.+))?\]$", s)
    if m:
        cur = {"name": m.group(1).strip(), "feel": (m.group(2) or "").strip(), "rows": []}; sections.append(cur); continue
    if cur is None: cur = {"name": "Song", "feel": "", "rows": []}; sections.append(cur)
    bars = 1
    mb = re.search(r"\*(\d+)\s*$", s)
    if mb: bars = int(mb.group(1)); s = s[:mb.start()].strip()
    cur["rows"].append((s, bars))

t, lines, blocks = 0.0, [], []
for sec in sections:
    s0, rows = t, []
    for text, bars in sec["rows"]:
        e = t + bars * BAR
        if text: lines.append({"section": sec["name"], "start": round(t, 3), "end": round(e, 3), "text": text})
        rows.append(f"  [{mmss(t)}–{mmss(e)}] {text or '(beat only)'}"); t = e
    blocks.append(f"[{mmss(s0)}–{mmss(t)}] {sec['name'].upper()}" + (f" — {sec['feel']}" if sec["feel"] else "") + "\n" + "\n".join(rows))

prompt = (f"{a.style}. Tempo exactly {a.bpm:g} BPM in {a.beats_per_bar}/4 (one bar = {BAR:g} seconds). Total length {mmss(t)}. "
          "Each lyric line fills exactly one bar unless marked longer; start vocals right at 0:00. Follow this timeline:\n\n" + "\n\n".join(blocks))
out = os.path.dirname(os.path.abspath(a.lyrics))
open(os.path.join(out, "prompt.txt"), "w", encoding="utf-8").write((f"Title: {a.title}\n" if a.title else "") + prompt + "\n")
json.dump({"title": a.title, "bpm": a.bpm, "bar_sec": BAR, "duration": round(t, 3), "lines": lines},
          open(os.path.join(out, "lyrics.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(os.path.join(out, "lyrics.srt"), "w", encoding="utf-8").write(
    "\n".join(f"{i}\n{srt(l['start'])} --> {srt(l['end'])}\n{l['text']}\n" for i, l in enumerate(lines, 1)))
print(prompt); print(f"\n{len(lines)} lines · {mmss(t)} · bar = {BAR:g}s → prompt.txt, lyrics.json, lyrics.srt")
