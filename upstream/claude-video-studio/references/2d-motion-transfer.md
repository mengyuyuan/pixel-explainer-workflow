# 2D character animation by AI motion transfer

> **Dependencies:**
> - The scripts below need `requirements-2d.txt` (numpy, scipy, Pillow; about 150 MB) and an ffmpeg with libvpx-vp9.
> - The lip and iris checks also need `requirements-face.txt` (mediapipe 0.10.14; about 600 MB).
> - Driver videos need Blender.
> - Run `python3 scripts/check_env.py` and ask the user before installing any of it.

This comes from making one 20 s rap chorus with a single anime illustration. Four approaches were tried:

1. **A character drawn in code.** It came out at TV cut-out puppet level.
2. **A mesh-deformed rig of the illustration.** It passed per-frame QA but was rejected: "the joints look like a puppet, the arms fling around". One front view has no turns, no fists and no cloth folds, and no rig can invent them.
3. **Gemini (Veo) image-to-video.** The motion was natural, but the style drifted toward 3D and the lip-sync was wrong.
4. **Kling 「动作控制」 (motion control) on a driver video Claude rendered.** This gave the illustration's own 2D cel look, natural motion, and a mouth that follows the driver.

The split that works: **Claude makes the motion and does all the post work; the video model redraws the character every frame.**

## Pipeline

1. **Driver video (motion reference).** Render it with a 3D stand-in whose proportions are close to the character's. The rigged model and the dance from `3d-lessons.md` work well.
   - One person and one continuous shot: a static camera, no cuts. Kling accepts 3–30 s.
   - A full-body take for dance: pro choreography (AIST++), feet planted, never touching the frame edges.
   - A waist-up take for the rap bars: lyric gestures, both hands in frame on every frame, and the hands never over the mouth. **Lip-sync the driver** (a MuseTalk pass) so the transferred mouth follows the lyrics.
   - Leave head-room for spiky hair. For the close take, pull the camera back rather than cropping the hair.
   - Also render a **clean plate**: the same camera with the character hidden. It is needed for step 3.
2. **Character image framed to the driver's first frame.** `scripts/make_green.py cut.png wide|close …` puts the cut-out on flat `#00B140` at the driver's head-top, feet or chin line and centre line. The models keep the image's framing, so a mismatch shows up as a scaled or shifted character.
3. **Rehearse before spending credits.**
   - `scripts/standin_from_driver.py driver.mp4 plate.png standin.webm` difference-keys the driver against its plate into an alpha take.
   - Drop the stand-ins into the composition and check every frame of the camera plan: raised hands clipped at the letterbox, feet in the lyric band, take edges visible.
   - One pass found 5 shots that would clip raised arms. They were fixed before generation.
4. **Generate (the user does this in the app).**
   - **Kling:** 视频生成 → 动作控制 (2.6/3.0) → the image plus the driver → 人物朝向「与视频一致」 (matches the video, up to 30 s; 「与图片一致」 is 10 s max) → highest resolution. Download without the watermark if the plan allows it.
   - Prompt: 「保持原图二维日漫赛璐璐画风，人物形象、服装、发型与原图一致；动作流畅自然，手部正常，符合物理规律；背景保持纯绿色不变，没有其他物体」. Add 「口型和表情跟随参考视频」 for the waist-up take.
   - **Kling output measured:** 1280×720, 30 fps, exactly the driver's frame count. It was **2 frames early** against the driver. The bottom-right watermark reads 「可灵AI 3.0」.
   - **Gemini (Veo) instead (no Kling account):** image-to-video from the same green image.
     - 10 s clips, 1280×720, 24 fps, no visible watermark.
     - Motion is natural but the moves are casual (walk, wave, hands together) and **the style drifts to 3D-toon**.
     - Its mouth follows its own audio, not your song.
     - Some prompts get refused. Naming the IP character may be the trigger, so describe 「图中的动漫少年」 instead.
5. **Key.** Use `scripts/key_diff.py in.mp4 out.webm --scale 1.5 [--corner 300x90]`, a colour-difference matte: `alpha = 1 − clamp((G − max(R,B) − lo) / (hi − lo))`.
   - **Not ffmpeg chromakey.** AI greens are desaturated (Veo gave #14A150), which leaves black and grey clothing only ~0.17 UV-distance from the key, so the jacket came out half transparent.
   - **No global despill.** It turns yellow hair orange. Edge pixels are un-mixed against the key colour instead.
   - Small specks off the body are dropped. `--corner` blanks a watermark box.
   - `--scale 1.5` brings 720p to 1080 take pixels, so the framing numbers from step 2 still apply.
6. **Timing.**
   - **Against the driver.** Correlate silhouette motion (the frame-to-frame alpha XOR count) with the driver's. Kling's lag was −2 frames, fixed by delaying the take 2 frames (`tpad=start=2:start_mode=clone`).
   - **Against the song.** Run `scripts/lip_sync_check.py take.mp4 --audio song.wav --metric area|gap`. After the shift the mouth led the vocals by 2 frames, which is natural.
   - Measuring anime faces:
     - FaceMesh needs a **2× head crop**: 0/240 faces were found at full frame, 240/240 on crops.
     - On **drawn mouths the lip-gap metric fails** (r ≈ 0.14), because both lips are one ink line. Count teeth and mouth-interior pixels instead (`--metric area`).
7. **Edit.**
   - **Non-aligned clips (Veo):** an EDL (source, in-point, timeline slot) builds a timeline-aligned green take per layer, frame-exact at the source fps. Then key it.
   - Match moves to lyric beats: a head-scratch on 「对不起」, palms together on 「表里如一」, a T-pose freeze on 「死机」.
   - Pick waist-up in-points by mouth-vs-vocal correlation. The chosen segments reached r 0.49–0.62, against about 0 for a random in-point.
   - **Timeline-aligned takes (Kling from our driver):** play them in sync; the lip-sync is already there.
8. **Render at the footage frame rate.**
   - Veo is 24 fps. A 30 fps render repeats every 4th frame, a visible judder, so render with `--fps 24`.
   - Kling's 30 fps inside a 24 fps render is a clean subsample.
   - Veo also has a small 4-frame judder from its video VAE: every 4th transition moves ~1.5× more. It is mild; leave it.

## Consistency rules (defects found on real footage)
- **Don't mix generators for one character without checking.** Kling kept the flat cel look; Veo made the same illustration 3D-toon, with paler hair and soft shading. Cutting between them reads as two different renderings. Generate every shot of a character with the same tool.
- **The face follows the input image.** A clip generated from a 3D render came back with that model's yellow-green irises; the others had blue ones. Compare faces across clips before editing. `scripts/recolor_iris.py` fixes eye colour (FaceMesh iris landmarks; only iris-coloured pixels change). Face shape can't be fixed, so regenerate from the illustration.
- **720p sources limit the camera.** Keep upscales under ~1.6× of the source: full shots and gentle push-ins are fine, but a 2.5× cowboy shot looks soft.
- **Lip-sync expectations.** Kling transfers the driver's mouth moderately (r ≈ 0.2–0.25 on an anime face). Veo mouths are unrelated to your song, so use them only where the mouth is small, or pick segments by correlation.

## Credits
- In the description: 「本视频为 AI 合成内容：角色动画由可灵 AI（动作控制）/ Google Gemini（Veo）生成」.
- Keep the burned-in 「AI 合成」 label for the whole clip.
- Credit any CC-BY model whose **render** was used as an input image. If it was only a motion reference, no credit is needed.
- Fan-art IP: flag the risk before any monetised use.
