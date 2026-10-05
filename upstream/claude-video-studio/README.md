# claude-video-studio

A Claude Code skill for making short videos (Douyin / TikTok / Reels / Shorts) with **Claude as a code-driven animator**. Claude writes HTML/GSAP that draws every frame, and [HyperFrames](https://hyperframes.heygen.com) renders it to MP4.

It comes out of one week of real projects: five pixel-art MVs and PSAs, flat-cutout World Cup edits, seven rounds of 3D experiments, and four 2D approaches to one anime illustration. It encodes what worked, what didn't, and the checks that stop broken renders from shipping.

## What it's good at

| Style | Verdict | Typical time |
|---|---|---|
| Pixel-art MV / explainer | ✅ publish-ready | 2-min MV in ~1–2 h |
| Flat cutout / motion graphics | ✅ publish-ready | 1-min in ~1.5–2 h |
| Editing real footage: cuts from a transcript, time freeze, subtitles, de-watermark, face mosaic, popular effects | ✅ publish-ready | a 2.5-min take in under 2 h |
| 2D character via AI motion transfer (Kling 「动作控制」 on a Claude-rendered driver) | ✅ keeps the illustration's style; needs a Kling account | driver ~1 h + post ~0.5 h |
| 2D rig animation of one illustration | ⚠️ idle or talking loops only; dance reads as a puppet | 20 s in ~1–3 h |
| 3D realistic | ❌ unless you bring a high-quality model | 20 s in 10–30+ h |

## Install

```bash
# 1) HyperFrames skills (the rendering engine and its authoring rules)
npx skills add heygen-com/hyperframes -s '*' -a claude-code -y

# 2) this skill
git clone https://github.com/a252937166/claude-video-studio ~/.claude/skills/claude-video-studio
```

Then ask Claude Code something like:

- 「用像素风给这首歌做个 MV」 — a pixel-art MV for this song
- 「把这个 docx 剧本做成科普动画，要配音」 — a narrated explainer from a docx script
- 「照着这个参考视频，用扁平风重做」 — remake a reference video in flat cutout style

## What's inside

- `SKILL.md` — the workflow:
  - pick the style first;
  - timed lyrics for AI music;
  - beat alignment;
  - the pixel and flat pipelines;
  - voice-over and SFX;
  - QA;
  - 3D caveats.
- `scripts/check_env.py` — environment check per workflow (installs nothing; prints install commands and sizes).
- `scripts/timed_lyrics.py` — lyrics → a bar-by-bar music prompt, plus `lyrics.json` and `.srt`.
- `scripts/align_beats.py` — measures the real song's offset against the planned bar grid (uses HyperFrames' `audiomap.json`).
- `scripts/pixel_sprite.py` — a stdlib pixel-sprite kit: palette grids → PNG, auto-outline, preview sheet.
- `scripts/qa_video.sh` — probes the MP4, scans every frame for black frames, and builds a contact sheet from frames extracted one by one.
- `scripts/add_cover.sh` — prepends a 1 s designed cover (sync-safe), embeds it as cover art, and exports 16:9, 4:3 and 3:4 covers.
- `scripts/transcribe_zh.py` — local Chinese ASR (FunASR): per-character timestamps, an SRT, pauses and slip candidates; `--nano` for dialects.
- `scripts/time_freeze.py` — the time-freeze gag from one locked-off take; the frozen region covers every pose, so there are no ghost limbs.
- `scripts/dewatermark.py` — removes a static burned-in watermark (temporal-min stroke mask, texture transplant or inpaint).
- `scripts/face_mosaic.py` — pixelates every face with tile detection, pose-based heads and tracking, plus an audit of frames that came up short.
- `scripts/echo_trail.py` — dance afterimage (「残影」) with beat flashes.
- `scripts/freeze_intro.py` — 「人物定格出场」: beat freezes, per-person cutouts that work in group shots, name cards, a group freeze.
- `scripts/speed_ramp.py` — 「曲线变速卡点」: speed curves with the highlight on the beat, flow-interpolated slow motion.
- `scripts/person_matte.py` — per-frame mattes for a clip with the best segmenter on the machine: Apple Vision on macOS (no download; also "lift subject" masks that keep a skateboard), MediaPipe elsewhere; `--drop-static` removes murals, posters and parked cars.
- `scripts/vision_matte.py` — the Apple Vision helper behind it (a short Swift tool compiled once into `~/.cache`), importable.
- `scripts/pop_out.py` — 「冲出画框 / 裸眼 3D」: white bars over the scene, the subject passes in front of them and casts a shadow on them.
- `scripts/tutorial_reel.py` — cuts someone's tutorial into "their effect first, then the teaching part in fast-forward next to a step list", with the credit burned in.
- `scripts/redub.py` — re-voices a video line by line with edge-tts (dialect → Mandarin, or a voice that must not be published): sentence groups, the rate fitted to the original timing, and re-timed subtitles.
- `scripts/clone_squad.py` — 「一人成团」: delayed clones of one dancer in a V formation behind her (scaled about the horizon, fitted inside the frame, contact shadows), like a canon.
- `scripts/time_scan.py` — 「时间扫描」 on an already-shot clip: a scan line freezes every pixel it passes.
- `scripts/auto_reframe.py` — landscape → 9:16 with a window that follows the subject (zero-lag smoothing, look room) and an optional explainer preview.
- `scripts/before_after.py` — an 原片 → AI 成片 reel: the labelled, silent source first, a title card, then the result.
- `scripts/make_green.py` — frames a cut-out character on flat green to match a driver video's first frame (for Kling / Veo).
- `scripts/standin_from_driver.py` — difference-keys a driver video against its clean plate into an alpha stand-in, so the camera plan can be rehearsed before paying for generation.
- `scripts/key_diff.py` — colour-difference keyer for AI green-screen footage, writing VP9-alpha WebM. Unlike chromakey, it keeps dark clothes solid; it also blanks a watermark corner.
- `scripts/lip_sync_check.py` — mouth openness against the vocal envelope with a lag scan. FaceMesh runs on 2× head crops, and an `area` metric handles drawn anime mouths.
- `scripts/recolor_iris.py` — recolours irises across a clip when an AI generator changes a character's eye colour.
- `references/hyperframes-gotchas.md` — seek-safety and render-leak rules for parallel frame workers.
- `references/qa-checklist.md` — pre-publish checklist, including China's AI-content labeling rule (2025-09-01).
- `references/3d-lessons.md` — seven 3D iterations of the same 20 s chorus, why the model is the bottleneck, and the per-frame motion and lip checks.
- `references/2d-motion-transfer.md` — the 2D pipeline that worked: driver → aligned image → Kling / Veo → keying, timing and lip checks → edit. It also covers the consistency traps.
- `references/ai-editing.md` — the AI-editing pipeline for real footage, recipes for popular edits, sourcing and rights, and lessons learned.
- `references/2d-rig-lessons.md` — the mesh-rig route and its per-frame QA, and why dance still reads as a puppet.

## Requirements

Run `python3 scripts/check_env.py` after cloning. It checks everything below, installs nothing, and prints the install
command and rough size for whatever is missing.

- Claude Code (tested with Opus 5.5).
- Core, for pixel and flat MVs:
  - Python 3.9+, Node 18+, ffmpeg;
  - the HyperFrames skills.
  - HyperFrames downloads its CLI from npm, and on the first render a headless Chrome (about 400 MB).
- Optional, by workflow:
  - beat sync: HyperFrames' `music-to-video` skill plus librosa and soundfile (about 280 MB);
  - voice-over: `edge-tts`;
  - 2D motion transfer: `requirements-2d.txt` (about 150 MB);
  - lip and iris checks: `requirements-face.txt`, which pins mediapipe 0.10.14 (about 600 MB, Python 3.9–3.12);
  - 3D: Blender 4.5 LTS.

## Responsible use

- Label AI-generated videos (「AI 合成」 / "AI-generated").
- Don't make photoreal doubles of real people without their consent.
- Respect IP: fan-art characters, athletes and brands.
- Credit CC-BY assets.

## License

MIT
