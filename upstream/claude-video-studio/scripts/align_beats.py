#!/usr/bin/env python3
"""Measure where the planned bar grid (bars from t=0) lands in the real, AI-generated song.

AI music apps rarely start the first downbeat exactly at 0:00. Measure the offset once and add it to every lyric and cut
time: real_time = plan_time + offset.

Usage:
    python3 align_beats.py audiomap.json --bpm 96 [--lyrics lyrics.json]
audiomap.json comes from HyperFrames' analyze-beatgrid.py (music-to-video skill: `npx hyperframes skills update
music-to-video`; that analyzer needs librosa, soundfile, numpy). This script itself is stdlib-only. With --lyrics it writes
lyrics-audio.json with the shifted times.
"""
import argparse, json, statistics as st

ap = argparse.ArgumentParser()
ap.add_argument("audiomap"); ap.add_argument("--bpm", type=float, default=96); ap.add_argument("--beats-per-bar", type=int, default=4)
ap.add_argument("--lyrics", default=None)
a = ap.parse_args()
d = json.load(open(a.audiomap))
beats = d["grid"]["beats_sec"]; dur = d["audio"]["duration_sec"]; B = 60.0 / a.bpm; BAR = B * a.beats_per_bar

def resid(off, pts, per): return [((b - off + per / 2) % per) - per / 2 for b in pts]
# Align bar lines to the detected downbeats when present (a beat-only fit can land a whole beat off), then refine on
# every beat; fall back to beats only.
ds0 = d["grid"].get("downbeats_sec", [])
pts, per = (ds0, BAR) if len(ds0) >= 4 else (beats, B)
best = min((st.median([abs(r) for r in resid(o / 1000, pts, per)]), o / 1000) for o in range(-int(per * 500), int(per * 500) + 1, 5))
off = best[1]; off += st.median(resid(off, pts, per))
off += st.median(resid(off, beats, B)); r = resid(off, beats, B)
print(f"duration {dur:.2f}s · detected bpm {d.get('tempo', {}).get('bpm')} · beats {len(beats)}")
print(f"beat offset = {off:+.3f}s   median |residual| = {st.median([abs(x) for x in r]) * 1000:.0f} ms")
for w in range(0, int(dur) + 1, 20):
    rs = [x for b, x in zip(beats, r) if w <= b < w + 20]
    if rs: print(f"  {w:3d}-{w + 20:3d}s  drift {st.median(rs) * 1000:+5.0f} ms  (n={len(rs)})")
ds = d["grid"].get("downbeats_sec", [])
if ds:
    ph = st.median([((x - off) / BAR) % 1 for x in ds])
    print(f"downbeat phase vs planned bar lines: {ph:.2f} (0 or 1 = on the bar line; ~0.25/0.5/0.75 = shifted by 1/2/3 beats)")
if a.lyrics:
    L = json.load(open(a.lyrics))
    for l in L["lines"]: l["audio_start"] = round(l["start"] + off, 3); l["audio_end"] = round(l["end"] + off, 3)
    L["offset"] = round(off, 3); L["audio_duration"] = dur
    json.dump(L, open("lyrics-audio.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    late = [l for l in L["lines"] if l["audio_end"] > dur + 0.05]
    print(f"wrote lyrics-audio.json (offset {off:+.3f}s)" + (f" · WARNING: {len(late)} lines end after the audio — re-time the ending" if late else ""))
