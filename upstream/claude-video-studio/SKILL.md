---
name: claude-video-studio
description: Make short videos (Douyin/TikTok/Reels/Shorts) with Claude Code as a code-driven animator. Use it when the user wants a music video, lyric MV, pixel-art or flat-cutout animation, a narrated explainer or PSA, or asks which video style Claude does well. It also edits real footage (cuts from a local transcript, time-freeze gags, subtitles with keyword emphasis, step cards, de-watermarking, face mosaics, popular Douyin effects like afterimages, freeze intros and speed ramps). It picks a style by what renders reliably (pixel and flat cutout first; 2D characters by AI motion transfer on a Claude-rendered driver; 3D only with caveats), writes timed lyrics for AI music, builds pixel characters from photos, cuts to the beat with HyperFrames, and QA-checks the MP4 before publishing.
---

# Claude Video Studio

Claude makes video by **writing code that draws every frame**: HTML, CSS and GSAP, rendered to MP4 by [HyperFrames](https://hyperframes.heygen.com). It does not generate pixels the way Sora, Kling or Veo do. Pick styles that code can draw well, and be honest about the rest.
For 2D character animation, pair the two: Claude renders the motion and does all the post work, and a video model redraws the character every frame (section 5).

## 0. Prerequisites — check first, install nothing without asking

**Before the first build, run `python3 scripts/check_env.py [--project <video dir>]`.** It uses only the standard library
and installs nothing. It prints what each workflow needs, what is missing, the install command and the rough disk size.
Show the user the missing items for the workflow they want, and **ask before installing anything**. Some items are large
(mediapipe with OpenCV/jax is about 600 MB, headless Chrome about 400 MB, Blender about 1 GB).

| Workflow | Needs | Install (only after the user agrees) |
|---|---|---|
| Pixel / flat MV (core) | Python 3.9+, ffmpeg + ffprobe, Node 18+, HyperFrames skills | `brew install ffmpeg` (or apt) · `npx skills add heygen-com/hyperframes -s '*' -a claude-code -y` |
| Beat sync from a real song | HyperFrames' `music-to-video` skill (its `analyze-beatgrid.py`) + librosa, soundfile, numpy | `npx hyperframes skills update music-to-video` (in the project) · `pip install librosa soundfile numpy` (~280 MB) |
| Voice-over, re-dub (`redub.py`) | edge-tts (+ soundfile for redub) | `pip install edge-tts soundfile` (~10 MB; needs network while synthesising) |
| 2D motion transfer | numpy, scipy, Pillow; ffmpeg with libvpx-vp9 | `pip install -r requirements-2d.txt` (~150 MB) |
| 2D lip / iris checks | mediapipe **0.10.14** (legacy FaceMesh API; Python 3.9–3.12) | `pip install -r requirements-face.txt` (~600 MB); mediapipe 1.x is untested |
| Editing real footage | numpy, scipy, Pillow, OpenCV (contrib for the guided filter); noisereduce | `pip install -r requirements-edit.txt` (~250 MB) · `pip install noisereduce` |
| Face mosaic, person cutouts | mediapipe **0.10.14**; on macOS the cut-outs use Apple Vision instead (needs `swiftc` from the Xcode command line tools, no model download) | `pip install -r requirements-face.txt` (~600 MB) · `xcode-select --install` |
| Chinese transcription | FunASR + torch (Python 3.10–3.12) | `pip install -r requirements-asr.txt` (~1 GB; models 1–3 GB from ModelScope on first run) |
| 3D / driver videos | Blender 4.5 LTS | blender.org LTS download (~1 GB) |

**What downloads by itself** (say so before the first run):
- `npx hyperframes@0.8.70 …` fetches the HyperFrames CLI from npm on first use. Pin the version so re-renders stay identical. If the skill fetch hangs during `init`, set `HYPERFRAMES_SKIP_SKILLS=1`.
- The first `check` / `snapshot` / `render` downloads HyperFrames' headless Chrome (about 400 MB) when it isn't cached. `npx hyperframes@0.8.70 browser ensure` does this up front.
- Nothing else installs itself. The scripts in `scripts/` stop with the exact install command when a package or ffmpeg is missing, and they print their usage with `--help`.
- The standard-library scripts need no packages at all: `timed_lyrics.py`, `align_beats.py`, `pixel_sprite.py` and `check_env.py`.

Load `/hyperframes` for the core authoring contract:

```bash
npx --yes hyperframes@0.8.70 init my-video
```

## 1. Choose the style first

Answer with this table before building anything. Don't promise a style that will disappoint.

| Style | Reliability | Typical time | Use for |
|---|---|---|---|
| **Pixel art** (characters as sprite sheets, game UI) | ★★★★★ | 2-min MV ≈ 1–2 h | lyric MVs, personal stories, PSAs, game-style narratives |
| **Flat cutout / motion graphics** (shapes, flat characters, kinetic type) | ★★★★★ | 1-min ≈ 1.5–2 h | famous-moment remakes, product launches, explainers, data |
| **2D character from ONE illustration, AI motion transfer** (Kling 「动作控制」 on a Claude-rendered driver; Veo as a fallback) | ★★★★ | driver ≈ 1 h, generation in the user's app, post ≈ 0.5 h | dance and rap clips that keep the illustration's style; see `references/2d-motion-transfer.md` |
| **2D rig animation of an existing illustration** (mesh deformation, like Live2D or Spine) | ★★ | 20 s ≈ 1–3 h incl. per-frame QA | small idle or talking loops only: the joints read as a puppet in dance; see `references/2d-rig-lessons.md` |
| **2D character drawn from scratch in code** | ★★ | varies | TV cut-out puppet level only. **Not** frame-by-frame hand-drawn motion |
| **3D realistic** (three.js or Blender) | ★ | 20 s ≈ 10–30+ h | only with a **high-quality ready-made model**; scenes can be real (scans, Poly Haven) |

Rules of thumb:

- **Realism of a specific person in 3D depends almost entirely on the model.** Re-dressing a generic game avatar never becomes that person. Say so up front, and offer:
  - a downloaded high-quality model (Sketchfab CC0/CC-BY, MetaHuman, Character Creator);
  - or an AI video model for the human shots, with Claude doing edit, captions and packaging.
- A few or low-res photos of a person → draw a **pixel character** from them instead of using the photos directly.
- Real people's likeness: don't make a photoreal double of a real person without their real consent. Use a fictional or AI-generated person, or a stylised character.

## 2. Music with an exact timeline (for lyric MVs)

AI music apps (Gemini/Lyria, Suno, …) follow timing much better when you give it bar by bar.

1. Write the lyrics as **one line per bar**. Fix the tempo: 96 BPM gives 1 bar = 2.5 s; 120 BPM gives 2.0 s.
2. `python3 scripts/timed_lyrics.py lyrics.txt --bpm 96 --title "…" --style "…"` writes:
   - `prompt.txt` to paste into the music app;
   - `lyrics.json` with start and end per line;
   - `lyrics.srt`.
3. The user generates the song and hands you the MP3.
4. Run HyperFrames' `analyze-beatgrid.py` on it → `audiomap.json`. The script ships with the `music-to-video` skill (`npx hyperframes skills update music-to-video`) and needs librosa, soundfile and numpy; see section 0.
5. `python3 scripts/align_beats.py audiomap.json --bpm 96` measures the **offset** between the plan grid and the real downbeats. It is usually +0.1 to +0.3 s. Every lyric and cut time is then `plan + offset`.
6. If the generated song is shorter, or stops early, re-time the ending to the real audio. Never stretch the music.

## 3. Pixel pipeline

- **Characters.**
  - Hand-author sprite grids in Python: `scripts/pixel_sprite.py` is a stdlib PNG writer with a palette, an auto-outline and preview sheets.
  - Use 15–25 poses per hero: idle, blink, talk, walk-a/b, jump/squat, cheer, sad, point, plus actions specific to the story.
  - Draw from the photo's traits: hair shape and colour, glasses, outfit.
- **Rig (seek-safe).**
  - Stack one `<img>` per pose.
  - A pose swap is **one** `tl.set(list, {autoAlpha: i => el === show ? 1 : 0}, t)`. Two sets at the same instant break backward seeking.
  - Hidden poses start with `visibility: hidden; opacity: 0`.
  - Scale by integers only, with `image-rendering: pixelated`.
- **Structure.**
  - Split the song into 6–8 frames (sub-compositions) by section, and let sub-agents write them in parallel from a shared kit (CSS, rig, HUD) and a `WORKER-NOTES.md` with the hard rules (see `references/hyperframes-gotchas.md`).

## 4. Flat cutout / motion-graphics pipeline

- **Kit.** Keep all drawing in `assets/kit.js`: characters as SVG/DOM parts, stadium, UI chrome. Put one file per scene in `assets/scene1..N.js` and beat times in `assets/data.js`.
- **Timing.** Hit the beat grid: every cut, hit and text pop lands on `beats[i] + offset`.
- **Reference-driven.** When the user sends a reference video, describe its structure beat by beat first, then rebuild it in your own drawing style. Don't copy assets.

## 5. 2D character animation: AI motion transfer — see `references/2d-motion-transfer.md`

Use this when the user has one illustration and wants it to dance or rap. A mesh rig of one front view reads as a puppet.

1. **Driver video.** Render the choreography with a 3D stand-in (section 9's model and motion): one person, a static camera, 3–30 s.
   - A full-body take for the dance.
   - A waist-up take with lyric gestures and a lip-synced mouth (MuseTalk on the driver).
   - A clean plate: the same camera with the character hidden.
2. **Frame the illustration to the driver's first frame.** Run `scripts/make_green.py cut.png wide|close …` to place it on #00B140.
3. **Rehearse the camera plan before any credits are spent.** Key the driver into a stand-in with `scripts/standin_from_driver.py`, then check every frame for clipped hands and visible take edges.
4. **Hand the user the pack** (images, drivers, prompt, settings).
   - Kling 「动作控制」, 人物朝向「与视频一致」, gives 20 s in the illustration's own style.
   - Veo (Gemini app) is the no-Kling fallback: 10 s at 720p/24 fps; it drifts to 3D-toon and the mouth isn't synced.
5. **Post.**
   - Key with `scripts/key_diff.py` (a colour-difference matte; `--corner` for the watermark).
   - Measure the lag against the driver; Kling was 2 frames early.
   - Check the mouth against the vocals with `scripts/lip_sync_check.py`.
   - Edit on the beat, and render at the footage fps.
6. **Keep one generator per character.** Kling cel and Veo 3D-toon side by side read as two different drawings. Compare faces across clips; `scripts/recolor_iris.py` fixes eye-colour drift.

## 6. Editing real footage (AI editing) — see `references/ai-editing.md`

Use this when the user hands over their own footage ("cut my slip, add subtitles, remove the logo, add effects").

1. **Transcribe locally.** `scripts/transcribe_zh.py` gives per-character timestamps, pauses and slip candidates (`--nano` for dialects). The cuts go into an EDL; snap them to whole frames and put short dissolves on the joins.
2. **Framing.** Keep one fixed framing unless camera moves are asked for.
3. **Time freeze.** `scripts/time_freeze.py`: the frozen region is the union of all the subject's poses, so no ghost limbs.
4. **Watermarks.** `scripts/dewatermark.py`: a temporal-min stroke mask plus a texture transplant.
5. **Graphics.** Do them in HyperFrames: subtitles under the speaker with keyword emphasis, step cards plus a tracker, impact words, stickers, an end card.
6. **Audio.** `noisereduce` with a noise print taken from the pauses, then loudnorm at −16 LUFS, plus synthesised SFX at the cue times.
7. **Re-dub** (dialect → Mandarin, or a voice that must not be published). `scripts/redub.py`:
   - one edge-tts call per sentence group, the rate fitted to the original span;
   - the subtitles re-timed from WordBoundary events;
   - the bed is level-matched room tone cut from voice-free pauses, never the original voice;
   - also rewrite dialect words in stickers and labels.
8. **Privacy.** `scripts/face_mosaic.py` before showing people who did not agree to appear.
9. **Mattes.** `scripts/person_matte.py` writes per-frame mattes that the effects below take with `--mattes`:
   - on macOS it uses Apple Vision (no model download; hair and fingers stay clean), elsewhere MediaPipe;
   - `--backend vision-fg` also keeps what the person holds or rides (a skateboard);
   - `--drop-static` removes a mural, a poster or a parked car that gets detected as the subject;
   - look at the `--preview` sheet before building on the mattes. MediaPipe mattes are too blocky for cut-outs.
10. **Popular edits.**
    - `scripts/echo_trail.py` (舞蹈残影; pass `--mattes`);
    - `scripts/freeze_intro.py` (人物定格出场, which works in group shots; Vision mattes on macOS);
    - `scripts/speed_ramp.py` (曲线变速卡点, with flow-interpolated slow motion).
11. **Extensions.**
    - `scripts/clone_squad.py` (一人成团): clones stand BEHIND the dancer, scaled about the horizon line, with offsets fitted so no clone is cut by the frame edge.
    - `scripts/pop_out.py` (冲出画框 / 裸眼 3D): white bars over the scene, the subject passes in front of them. Ramp the clip to slow motion first.
    - Utilities that make weak showcases: `scripts/auto_reframe.py` (横屏转竖屏) and `scripts/time_scan.py` (时间扫描).
12. **Show the result against the source.** `scripts/before_after.py` builds an 原片 → AI 成片 reel:
    - the raw clip, labelled and silent;
    - a title card;
    - the result with its own audio.
13. **"Manual vs AI" write-ups.** Go effect by effect, each in the same order:
    - their original first: `scripts/tutorial_reel.py` cuts a tutorial into "the effect at normal speed, then the teaching part in fast-forward next to a step list";
    - then a step figure: one numbered screenshot per manual step;
    - then our version with `before_after.py`.
    - Do not put all the tutorials in one section and all the AI results in another. A link alone does not show the effect.
14. **Rights.**
    - Someone else's video: link it by default. Embed an excerpt only when the user decides to; then keep it short, keep the burned-in credit (author, title, 版权归原作者), link the original, and say in the hand-off notes how to swap it for a link.
    - Put quotes from tutorials or comments in quotation marks only when they are verbatim; check them against the transcript.
    - Use licensed stock (e.g. Mixkit's free licence) and the user's own music.

## 7. Voice-over and SFX (explainers / PSAs)

- **Script.** Take the user's script **verbatim**; don't paraphrase medical or legal text.
- **Voices** (edge-tts):
  - narrator `zh-CN-YunyangNeural`;
  - young man `zh-CN-YunxiNeural`;
  - young woman `zh-CN-XiaoyiNeural`;
  - elder sister `zh-CN-XiaoxiaoNeural`;
  - doctor `zh-CN-YunjianNeural`.
  - Generate per line, trim the silence, then place each line on a timeline.
- **Timing.** The picture follows the voice: build `timeline.json` from the real line durations, then animate.
- **SFX.** Synthesize 8-bit SFX with numpy (blips, steps, heartbeat, rewind) and mix them into one voice track. Offer a no-voice version too, with the music louder and loudnorm at −16 LUFS.

## 8. QA — never trust the preview alone

Run the checklist in `references/qa-checklist.md`. The essentials:

- `npx hyperframes check --no-contrast` passes, and snapshots are reviewed.
- **Extract frames from the rendered MP4 one by one** (`ffmpeg -ss T -i out.mp4 -frames:v 1`). Renders can differ from snapshots: a stray `visibility: visible` showed one frame over the whole video.
- Scan every frame for black or blank frames (`signalstats` YAVG).
- **Cover.** The first frame must be a designed cover, never black. Add 1 s of cover plus 1 s of silence at the start. Embed the cover as `attached_pic`. Export 16:9, 4:3 and 3:4 cover PNGs.
- **AI label.** Burn in 「AI 合成」 / "AI-generated" for the whole clip. China's labeling rules are in force since 2025-09-01. Tick the platform's AI declaration when posting.
- Put credits for CC-BY assets (models, scenes, motion data) in the description.
- **AI footage** (Kling, Veo): run the checks in the checklist's last section: keying, timing against the driver, mouth against the vocals, face consistency across clips, and a render fps equal to the footage fps.

## 9. 3D (only if the user insists) — see `references/3d-lessons.md`

- Scenes:
  - real scans (Sketchfab CC-BY);
  - Poly Haven (CC0);
  - NVIDIA ORCA Bistro (CC-BY);
  - rendered in Blender EEVEE (a few seconds to 20 s per frame).
- Characters: a ready-made high-quality rigged model (Mixamo-style rigs retarget cleanly). Retarget by direction matching, not raw rest deltas.
- Motion:
  - dance from mocap (AIST++ is CC-BY, but its source DB is research-only, so check before monetising);
  - close-ups need upright, face-clear "rap stance" gestures.
- Lip-sync on AI-generated, reverb-heavy rap stays weak. JoyVASA, MuseTalk and LatentSync all scored SyncNet ≈ 1.6–1.8 on it (a static mouth scored 0.9). Say so honestly.
- Budget: disk (models of 4–10 GB each) and hours. **Ask before any multi-GB download.**

## 10. Working style (lessons from real sessions)

- Show a storyboard or a still first, and render after approval.
- Give honest limits early. Don't burn hours polishing a dead end: the 3D re-dress was.
- Keep the user posted with short progress lines during long runs.
- Delete intermediates and ask before large downloads. Disk fills fast.
- Paid AI tools are the user's call. Prepare the pack (aligned images, driver videos, step-by-step instructions with the prompt) and let the user generate. Never assume they have an account; offer the route they already have (e.g. the Gemini app), and say what it costs in quality.
