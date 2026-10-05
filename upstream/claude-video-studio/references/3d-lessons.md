# 3D lessons: one 20-second chorus, seven versions

The same 20 s chorus was rebuilt six times over roughly 30+ hours. What each step taught:

| Version | Approach | What went wrong / right |
|---|---|---|
| v1 | three.js, a Rocketbox game avatar, the photo projected onto its head, JoyVASA lips, GFPGAN refine | "Crude, like last century." The lips were far off: JoyVASA opens about 5 times per 2.5 s bar against 14 sung syllables. |
| v2 | Poly Haven scenes (CC0), 22 AIST++ street-dance moves, lip frames re-timed to the vocal | The scenes were a clear step up. The body read "soft", and the mouth still didn't match. |
| v3 | A tee body, a sculpted physique, fur-shell hair, MuseTalk | "Deformed": the muscle sculpt was overdone, the head looked small, the shoulders ballooned under DQS skinning, and the hands were claws. |
| v3.1 | A lean build, arm-only DQS, hand presets, an upright rap stance in close-ups | Still a "rubber man". The model's quality was the ceiling. |
| v4 | Blender: cloth sim, hair curves, SSS skin, Bistro scene; a Naruto costume built on the same avatar | 「一点都不像」: re-dressing a generic avatar never becomes a specific person. |
| v5 | A ready-made high-quality community model (Sketchfab, CC-BY), the same motion retargeted | It finally read as the character. **The model was the bottleneck all along.** |

## Rules
1. **Model first.** Get a high-quality, rigged model before anything else. Sources:
   - Sketchfab: filter for downloadable, CC0/CC-BY; avoid game rips;
   - MetaHuman or Character Creator;
   - a photo-to-3D service, for a specific person who has consented.
   - **Why Claude doesn't build the model itself.** Measured in Blender on the same character:
     - **The downloaded community model** (Naruto by Monhoo, CC BY):
       - 82,107 faces (164k triangles): hair 23,146, head 13,156, teeth 11,999, shoes 8,520, hands 5,604;
       - 65 bones, 40 of them finger bones;
       - 32 texture maps at 4096² (309 MB).
     - **The version Claude built with code (v4):**
       - 29,411 faces, 6,875 of them from a stock game body;
       - 73,600 rule-grown hair strands, and 6-face boxes for the pouches;
       - 2048² stock textures, with a projected face photo.
     - Its jacket (14,336 faces) out-counted the community jacket, so face count isn't the point.
     - The point is sculpted form and edge-flow, which an artist judges by eye: sculpt → retopology → UV → texture painting → rig → weights.
     - Code can place boxes, tubes, strands and cloth. It can't sculpt a character's hair and face. The user's verdict on v4: "a bit like him? Not at all."
2. **Real scenes are easy; real people are hard.**
   - Photogrammetry scans (Sketchfab CC-BY), Poly Haven (CC0) and NVIDIA ORCA Bistro (CC-BY) look real in Blender EEVEE.
   - Scans carry baked light: use them as mostly emissive, light the hero separately, and keep cameras inside the scanned area.
3. **Retarget by direction matching**, not raw rest-pose deltas. Scale the new model to the eye line the cameras frame, and check hands, feet and head against the source joints at the cut frames.
4. **Close-ups need a close-up-safe performance.** Use an upright stance, chest-level gestures and a clear face; save big dance moves for wide shots.
5. **Lip-sync on AI rap is hard.**
   - JoyVASA, MuseTalk 1.5 and LatentSync 1.5/1.6 all scored SyncNet about 1.6–1.8 (a static mouth: 0.9) on a reverb-heavy, doubled, AI-generated rap at 5.6 syllables/s.
   - **Semi-realistic 3D characters: MuseTalk works well as a post-pass on the rendered plates.** On a semi-real Naruto model it gave natural lips.
   - A jaw bone alone exposed the model's pointed teeth, which looked like fangs.
   - Fully stylised or flat 2D characters: swap viseme drawings per syllable, with the timing taken from the vocal envelope peaks.
6. **Budget honestly.**
   - EEVEE runs about 3–20 s per frame (the Bistro city is the slowest), so a 600-frame clip is about 1.5 h plus shader compile.
   - Each lip-sync model is 4–10 GB on disk. Ask before downloading, and delete what you don't use.
7. **Credits.** CC-BY needs attribution in the description. AIST++ motion is CC-BY, but its source database is research-only, so check before monetising.
8. **Tune MuseTalk on stylised or 3D faces.**
   - **Track the face across frames.** A face detector happily scores a fist or an open palm as a face; taking detection[0] loses the real face on every gesture frame. Try detections nearest the last face first, then the last face region, then the rest.
   - **Thin, closed stylised lips parse as only 40–50 % 'lip' class,** so a realistic-face occlusion threshold fades MuseTalk out on unoccluded frames. Lower it: start the fade at about 8 %, full weight at about 30 %.
   - **Always read the pass's coverage per close shot** (frames at full weight / partial / off) before rendering the overlay. "Full weight on 12 of 600" is a failed pass even when the file renders fine.
9. **Scan joint speeds before rendering.**
   - Compute per-frame joint speeds over the whole clip, excluding the cut frames. Anything above about 12 m/s is a pop, not a dance move.
   - Example: a height cap that swung the whole arm about the shoulder flipped its plane when the arm passed overhead, and the hand jumped 0.8 m in one frame (28 m/s).
   - EEVEE's 1-step vector motion blur then smears background lights across the limb, which reads as a torn, glowing arm.
   - Fix limits by bending the elbow, not by swinging the arm. For fast dance, use 3 motion-blur steps.
10. **Track faces backward in time.** A full-frame face detector finds a face that grows into view (a push-in) only once it is large. After the forward pass, walk back from each first detection using its face region, so lip-sync covers the whole push-in.
11. **Partial re-renders need the raw plates.** Keep the raw plates as an MP4. When only some shots change, check that cameras and joints in the other shots are bit-identical, re-render just the changed shots, and splice them in.
12. **Check bone rotation continuity, not just positions.**
    - In one frame, a forearm rolled 158°. Its twist share had been computed with `atan2`, which wrapped through ±180°.
    - The hand and elbow stayed in place, so the joint-speed and bone-direction scans both missed it.
    - Scan every bone's full world rotation per frame; keep it at or below about 35° per frame outside cuts. Pin each gesture's twist branch.
13. **Rate-limit fast mocap whips.**
    - Krump and waacking arm whips reached 56–92° per frame.
    - Remove the twist jitter, then redistribute time inside each half-beat, so beats stay put, until every bone is at or below 30° per frame.
14. **Keep the dancer's hops.**
    - A ground pass that pins both feet flattens real hops. Snap only planted feet.
    - Let hops leave the floor and land at z = 0.
    - Compare post-landing ankle travel with the source (within about 10 %) to tell choreography from retarget slide.
15. **Lip-sync occlusion guards can be wrong.**
    - MediaPipe Pose placed a hand behind the head in front of the face, and switched MuseTalk off for 13 frames per shot.
    - Use renderer truth instead: project the hand and sleeve geometry through each frame's camera, and keep the guard only where an arm really covers the lower face (a frames list passed to the lip pass).
16. **"Export bit-identical" is not enough for partial re-renders.**
    - A build-code change (the hop fix) also changed shots whose export was identical.
    - Before reusing old plates, diff the *built* pose in world space against the backed-up scene.
17. **Run one GPU job at a time on a 24 GB Mac.**
    - A Bistro render (7.6 GB) plus MuseTalk pushed swap to 31.6/32 GB, and MuseTalk slowed about 3×.
    - Pause the render with `kill -STOP` and resume it with `kill -CONT` while a priority job runs.
