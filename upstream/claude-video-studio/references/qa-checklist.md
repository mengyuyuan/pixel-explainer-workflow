# Pre-publish QA checklist

Run `scripts/qa_video.sh out.mp4`, then look at the contact sheet yourself.

## Picture
- [ ] `hyperframes check --no-contrast` passes, and warnings have been reviewed.
- [ ] Snapshots at every shot or section were looked at.
- [ ] **Frames extracted from the MP4** (not the preview) match the snapshots. No frame from another section is leaking over the video.
- [ ] No black or blank frames (`qa_video.sh` reports dark frames 0), except intended fades.
- [ ] Subtitles are verbatim: no paraphrasing, and full-width punctuation where the source has it. Each line is on screen when it is sung or said.
- [ ] Faces, text and the AI label never overlap badly. Text stays off faces.

## Sound
- [ ] Audio stream present and at the expected loudness. For voice versions, loudnorm to about −16 LUFS.
- [ ] Sync spot-checked at three points (start, middle, end). If a 1 s cover was prepended, the audio is shifted by exactly 1 s.
- [ ] The music is not cut mid-phrase at the end. If the generated song is shorter than planned, re-time the ending.

## Packaging
- [ ] **First frame is a designed cover**, never black (Finder and Douyin show the first frame).
- [ ] The cover is embedded as `attached_pic`, and 16:9, 4:3 and 3:4 cover PNGs are exported.
- [ ] Bitrate is reasonable. Film grain bloats CRF encodes, so cap it with `-maxrate 16M`.

## Compliance
- [ ] 「AI 合成」 / "AI-generated" is burned in for the whole clip (China's AI content labeling rules are in force since 2025-09-01), and the platform's AI declaration is ticked when posting.
- [ ] No photoreal double of a real person without their consent. No red-cross emblem (it is protected). No third-party brand logos.
- [ ] Credits for CC-BY assets (models, scenes, mocap, music if any) go in the description, including "modified" notes.
- [ ] Fan-art IP (anime characters, sports stars): OK for fan posts, but flag the risk before any monetised or sponsored use.

## AI-generated footage (Kling / Veo / 即梦)
- [ ] Keyed with a colour-difference matte (`scripts/key_diff.py`), not chromakey. Over magenta, dark clothing is solid and there is no green fringe.
- [ ] The watermark corner is blanked (`--corner`), or a watermark-free download was used.
- [ ] **Timing against the driver** is measured by silhouette-motion correlation, and the take is shifted if the lag is not 0. Kling came back 2 frames early.
- [ ] **Mouth against the vocals** is measured with `scripts/lip_sync_check.py`. The peak lag is −1 to −2 frames, and r is noted. For drawn mouths use `--metric area`.
- [ ] **Faces are compared across clips**: eye colour, face shape, hair colour, line style. Every shot of a character uses the same generator, unless the user accepts the gap.
- [ ] The render's fps equals the footage fps (24 for Veo). The frozen-frame scan counts only intended holds.
- [ ] Framing is re-checked on every frame with the real takes. Upscales stay at or below about 1.6× of the source.
- [ ] The description names the AI tools, alongside the burned-in 「AI 合成」 label.

