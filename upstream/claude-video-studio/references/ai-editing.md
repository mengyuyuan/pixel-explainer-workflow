# Editing real footage with Claude (AI editing)

This comes from one real job. The input was a 2:25 locked-off 4K60 take of a rabies first-aid explainer: one person talks, the other throws a basin of water in the last seconds.

The output was a 2:08 "time freeze" edit: the thrower and her water hang in mid-air until the talk ends, then the splash plays in slow motion. It has subtitles, step cards, stickers, SFX and an end card. Raw file to export took 1 h 47 min, including model downloads and one rework.

Three popular Douyin edits were then recreated on free stock footage: 舞蹈残影, 人物定格出场 and 曲线变速卡点.

Later additions:
- the PSA was re-dubbed from Sichuanese into Mandarin (`redub.py`);
- effects of our own were built: 一人成团 and 冲出画框 (kept), 时间扫描 and 横屏转竖屏 (dropped from the article);
- every result was shown as an 原片 → AI 成片 reel, next to an excerpt of the Douyin tutorial it answers.

> **Dependencies** (run `python3 scripts/check_env.py`, then ask the user before installing anything):
> - `requirements-edit.txt`: OpenCV and friends, about 250 MB.
> - `requirements-face.txt`: mediapipe, about 600 MB.
> - `requirements-asr.txt`: FunASR and torch, about 1 GB, plus 1–3 GB of models on first run.
> - `noisereduce` for speech cleanup.

## Pipeline for talking-head and explainer footage
1. **Look first.**
   - Make a 540p proxy: `ffmpeg -hwaccel videotoolbox -i raw.mp4 -vf scale=960:540,fps=30 …`.
   - Make contact sheets: the whole take at 1 fps, then the start and end at 2–6 fps.
   - Find where the talk really starts (e.g. once the speaker sits down), where it ends, and the action moment.
2. **Transcribe.** Run `scripts/transcribe_zh.py raw.mp4 asr.json --srt asr.srt --hotwords "…"`.
   - It gives per-character timestamps, pauses of 1.2 s or more, and repeat candidates. Candidates include scrambled restarts like 「消口伤毒…消毒伤口」.
   - For dialects (e.g. Sichuanese), add `--nano` and cross-check the two models' readings. One model heard 「科普」 as 「泡泡」 and the other as 「客泼」; together they decode it.
   - whisper hallucinates on short dialect chunks: repeated words, and fake "subtitle volunteer" credits. Don't trust it alone for Chinese dialects.
3. **Cuts, as an EDL in JSON** (source ranges, speed, camera).
   - Trim the head and tail, cut the slips, and cut dead pauses of about 3 s. Keep natural breaths.
   - Snap every segment to whole output frames, so audio placed at the EDL times stays frame-locked.
   - With one fixed framing, put 8-frame dissolves on the jump cuts.
4. **Framing.** Use one fixed crop (e.g. 1.4×, everyone in frame, feet clear) unless the user asks for camera moves.
   - Auto push-ins and zoom punches were rejected: 「视频不要放大缩小」.
5. **Time freeze.** Run `scripts/time_freeze.py raw.mp4 out.mp4 --freeze-at T --from A --empty-at E --zone …`.
   - Pick the freeze frame by stepping through the action at the source fps, and take the most photogenic one (the water arc at full extension).
   - The region is the union of every pose the frozen person takes while the freeze is on screen, plus the freeze frame's own content (the water).
   - Only blobs connected to the freeze frame are kept, so another person walking through the zone is not frozen.
   - Per channel, the frozen patch is gain-matched to a ring of background, because clouds change the light.
6. **Watermark.** Run `scripts/dewatermark.py in.mp4 out.mp4 --box … --shift 0,-H`.
   - The stroke mask comes from the temporal-minimum luminance.
   - Texture is transplanted from just above the box, so it moves with the scene. Use `--method inpaint` on flat backgrounds.
7. **Graphics layer in HyperFrames.** The EDL feeds a `data.js`.
   - Subtitles go under the speaker, with keywords enlarged: yellow, or red for warnings.
   - Step cards slam in on 「第X步」 and collapse into a top tracker.
   - Use impact words that dim the frame, stickers at cue times, a pause/play tag on the freeze, and an end card that summarises the steps.
8. **Audio.**
   - Cut the speech with the same EDL, using 12 ms fades.
   - Run `noisereduce` with a noise print taken from the pauses (stationary, `prop_decrease` 0.75), then a 110 Hz high-pass, a gentle compressor and `loudnorm` at −16 LUFS. On the real job SNR went from 6.4 to 12.4 dB.
   - Synthesise the SFX with numpy (pop, whoosh, impact, freeze, resume, chime) at the cue times.
9. **Slow motion.**
   - A 60 fps source simply plays at 0.5×.
   - A 24/30 fps source needs optical-flow interpolation (`scripts/speed_ramp.py` does this).
10. **Privacy.** Before footage of people who did not agree to be shown goes into an article or tutorial, run `scripts/face_mosaic.py in.mp4 out.mp4 --pose --expect N`.
    - It detects on 2× tiles plus a pose-based head box (masks, sunglasses, turned heads), tracks, holds and back-fills.
    - The audit JSON lists frames with fewer boxes than expected. Look at those: usually the person has simply left the frame.
11. **QA on the render.**
    - Run a frozen-frame scan.
    - Scan for freeze-zone leaks: the per-frame mean difference inside the frozen zone should stay below about 1/255, and spikes mean live pixels are showing.
    - Check lip sync on the render with `scripts/lip_sync_check.py`, expecting −1 to −2 frames.
    - Check loudness, check that the first frame is a designed cover, and check sync after the cover.

## Popular edits: recipes
| Effect | Script | What matters |
|---|---|---|
| 舞蹈残影 (afterimage) | `echo_trail.py` | Locked-off shot of one dancer. Pass `--mattes` (person_matte.py `--drop-static`): the ghosts then have crisp outlines; the built-in MediaPipe path gives soft blobs. Last N×delay frames recoloured neon behind the live dancer, background dimmed. Beat flash and zoom punch, with white silhouettes on downbeats. |
| 人物定格出场 (freeze intro) | `freeze_intro.py` | Full-frame segmentation fails on groups in low light, and MediaPipe Pose picks the most prominent person. So paint everything outside the target's box with the clean plate (temporal median), segment a square crop, and intersect with a pose envelope. Confident skeleton-core pixels survive the plate check; fill holes. Name cards on stock people: describe clothing, never invent real names. On macOS the crop is matted with Apple Vision instead (cleaner outlines); set `"margin": 8` on a person whose neighbour's shoe or hand sits next to the box. |
| 曲线变速卡点 (speed ramp) | `speed_ramp.py` | Speed is `fast − (fast − slow)·exp(−((t − hit)/w)²)`, with the hit frame on a beat. The script errors if the source range leaves the clip. DIS optical-flow interpolation below 0.9×, frame-blend motion blur above 1.4×. A live 「速度 ×0.25」 readout teaches the curve. |

Typical render times on an M4 Pro, 1080p:
- echo trail, 12.5 s of video: mattes 32 s + render 1 min 25 s;
- freeze intro, 14 s: about 45 s;
- speed ramp, 12.5 s: about 20 s;
- clone squad, 12.5 s: mattes about 30 s + render about 1 min.

## Mattes first: `person_matte.py`
Cut-out quality decides whether an effect looks real. MediaPipe's selfie segmentation gives blocky hair, dissolved arms and halos; the user called the first 一人成团 「质量很差，裁切都不完整」.
- **macOS:** Apple Vision. `--backend vision` is person segmentation at quality "accurate"; `--backend vision-fg` is the foreground-instance ("lift subject") mask, which also keeps a skateboard or a ball. No model download; a short Swift helper is compiled once (`vision_matte.py`). About 0.1 s per 1080p frame.
- **Elsewhere:** MediaPipe (fallback). Good enough for neon silhouettes, not for clean cut-outs.
- **`--drop-static`.** Vision detects a mural or a poster of a person, and vision-fg a parked car. The flag removes what is "always masked and never changing", plus any blob that looks like the empty scene (temporal-median plate). Only for a moving subject in a locked-off shot.
- Always look at the `--preview` sheet (cut-outs on magenta) before compositing.
- `echo_trail.py`, `clone_squad.py` and `pop_out.py` take the folder with `--mattes`. `freeze_intro.py` calls Vision per freeze frame on its plate-painted crop.

## Extensions (our own effects, no tutorial needed)
| Effect | Script | What matters |
|---|---|---|
| 一人成团 (clone squad) | `clone_squad.py` | Row k is the dancer from k × delay ago (half a beat reads as a canon). **Stage it in depth**: scale each clone about the horizon line (`--horizon`, where the camera's eye level cuts the frame, e.g. 0.46), so its feet rise and its head sinks like someone standing further back. Scaling about the feet makes small people on the same line. **Fit**: clamp the sideways offsets from the dancer's box over the whole clip, so no clone is cut by the frame edge. Soft contact shadows; far rows slightly darker; draw far to near, the live dancer last. Clones slide out of her on successive beats and back in at the end. |
| 冲出画框 (pop-out, 裸眼 3D) | `pop_out.py` | Three even white bars over the scene; the subject is drawn in front of them and its blurred shadow falls on the bars only. Ramp the clip to slow motion first (`speed_ramp.py` with `"readout": false, "punch": false`), then matte THAT clip (`--backend vision-fg --drop-static` for a skater + board). `--mode frame` (subject leaves a white-bordered frame) needs a subject that is whole in the shot. |
| 横屏转竖屏 (auto reframe) | `auto_reframe.py` | A useful utility, but a weak showcase (the user: 「没有意思很无趣」). Pose centre per frame, zero-lag forward-backward Gaussian, look-room lead, clamped inside the picture. |
| 时间扫描 (time-warp scan) | `time_scan.py` | Strip-by-strip freeze as a line sweeps. On a dance group the result is chopped-up bodies with stair steps; not shown in the article. |

## Re-dub: dialect to Mandarin, or a voice that must not be published
`redub.py lines.json voice.wav --subs subs.json --total S`

**Lines.** Write them from the transcript, on the output clock.
- Rewrite only the dialect words, e.g. 等一哈→等一下, 啥子→什么, 狗儿和猫儿→小狗、小猫, 板板车→板车.
- Keep the speaker's meaning and order.

**Voice.**
- Match the speaker. Measure the F0 with pyin: about 265 Hz means a woman's voice, so use `zh-CN-XiaoxiaoNeural`.
- Synthesise a sentence that the subtitles split into one group (one TTS call), or each fragment ends with a falling, final-sounding tone.

**Fitting the rate.**
- Slower than −10 % sounds drawled.
- Faster than about +22 % sounds rushed. Exceed it only if the line would otherwise run into the next one.
- Start each group where the original line started. Stickers and gestures then stay in sync.

**Subtitles.**
- edge-tts `boundary="WordBoundary"` gives word offsets. Spread them per character to cut the group back into its subtitle lines.
- Captions lead the voice by about 0.1 s, which reads well.

**Bed.** Never put the original track under the dub.
- Loop room tone cut from pauses of the cleaned original. Check every chunk with pyin first: zero voiced frames.
- Level-match the chunks (about −38.5 dBFS) or the loop pumps.
- Keep the original only where it is voice-free (the splash). Check that with pyin **and** a spectrogram: ASR "hears" words like 没有 or 嗯 in rustle and in SFX sweeps.

**Graphics.** Re-render the subtitles, and grep the composition for dialect text in stickers and labels (板板车 on a cart).

**Check.** Transcribe the dub back with `transcribe_zh.py`. The text should match the script.

## Before / after reels
`before_after.py out.mp4 --after effect.mp4 --before raw.mp4@T0-T1 [...] --note "…" --crf 22`
- Show 3 to 7 s of the untouched source:
  - scaled to the result's size;
  - labelled 「原片 · 没加任何特效」;
  - **silent**, so a private voice or plain noise isn't published.
- Then a 0.8 s card, then the result with its audio.
- Mosaic the faces in the raw part too: run `face_mosaic.py` on a 1080p cut of the raw ranges.
- For a time-freeze job, show both the start of the take and the real throw at the end. Viewers then see that the action happened minutes later.

## A "manual vs AI" write-up: the structure the user asked for
The first two versions were rejected (「不是这样的」, then 「你的文档写的真的不行啊」). What was asked for, in the user's words:
- 「一种类型的应该是先抖音的，再我们ai剪辑的这样对比」;
- 「抖音的原视频应该直接放上去，点过去看就没有效果了」;
- 「教学部分就超快速过一下，说明很麻烦就行了」;
- 「配图说明过程……容易看懂手动多复杂」.

Go effect by effect, each in the same order:
1. **Their original, embedded.** `tutorial_reel.py config.json out.mp4`:
   - the effect part at normal speed, cropped from the tutorial and shown large;
   - then the teaching part in fast-forward (4–6×) as a phone on the left, with a step list that fills up as the steps go by;
   - then a hold with the step total.
   - The credit is burned in (author, title, likes, 版权归原作者), and the article links the original.
2. **A step figure.** One numbered screenshot per manual step (crop the tutorial frame to its UI), a short caption each, and a footer with what has to be repeated. Build it as HTML → PNG.
3. **Our version.** `before_after.py`: the untouched source, then the result.
4. A few sentences: what the AI did differently, what went wrong.

After all effects, add one recap table: manual steps and estimated operations vs what the AI was given and how long it took.

**Getting the tutorial material**
- `douyin-skills get-video-detail` gives likes, collects and comments.
- The page's default stream is about 576p at 200 kbps. Capture the page's own `aweme/detail` response over CDP and download the best `bit_rate` entry (1080p) with a Referer header.
- Transcribe the narration with `transcribe_zh.py`; its sentence times place each step. Check them against the on-screen captions on labelled contact sheets.
- Find the preview area for the effect crop from rows that change over time (`std` over frames). A brightness test fails on dark scenes.
- Level the excerpt (effect part to about −19 dBFS RMS), then add the step pops at a fixed level.

**Counting and quoting**
- Count operations with one rule: each tap, drag, slider move or text entry = 1. Mark the repeated unit (per person, per beat, per layer, per freeze). Say that the totals are estimates.
- Put words in quotation marks only when they are verbatim, from comments or the transcript. A research summary paraphrased two "quotes"; check them before publishing.
- Check the facts shown beside an excerpt. An earlier label said five dancers; there were four.

## Sourcing and rights
- **Stock video.** The Mixkit Stock Video Free License allows commercial and non-commercial use, modification and distribution, with no attribution required (credit is appreciated). Check each clip's licence on Pexels or Pixabay the same way.
- **Someone else's video** (a reference for an effect, a tutorial). Link to it and describe it by default. Embedding an excerpt is the user's decision; when they decide to, keep it short, keep the credit visible, link the original, and say in the hand-off notes that a video can be swapped for its link if the author objects.
- **Music.** Use the user's own tracks or properly licensed ones. Don't put copyrighted song lyrics on screen.
- **Faces.** Mosaic people who didn't agree to appear (see the privacy step).

## Lessons from the real job
- **Ghost arm.** A freeze region built from the throw alone leaked the thrower's arm when she bent down later to pick up the basin. The user caught it from a screenshot. Fix: the union of all poses (now built into `time_freeze.py`).
- **Auto camera moves.** Unrequested zooms were rejected. Default to one fixed framing.
- **Downloads.** Ask before downloading ASR models (1.6–3 GB). ModelScope is much faster than Hugging Face from China.
- **ffmpeg builds without `drawtext`.** Render text with Pillow or HyperFrames instead.
- **Showcase effects are judged on finish.** The first 一人成团 used MediaPipe mattes and let clones run off the frame; it was rejected. Redo with Vision mattes, depth staging and the fit. A correct but plain utility (横屏转竖屏) was rejected as boring.
- **Compare like with like.** Once their original sits next to ours, rough mattes show. The 残影 and 定格出场 recreations were redone with Vision mattes for that reason.
