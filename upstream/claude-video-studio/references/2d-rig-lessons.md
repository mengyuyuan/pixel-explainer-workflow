# 2D character animation: lessons from one 20 s chorus

> **Verdict after user review (2026-09-29).** Rig v3 passed every per-frame check below, and the user still rejected it: 「关节部位都是跟木偶人一样…一甩一甩的」 ("the joints look like a puppet's, the arms fling around").
> A rig of one front view can't turn, clench a fist or fold cloth. For dance and acting, use AI motion transfer (`2d-motion-transfer.md`). Keep the rig for small idle or talking loops.

## What works
**Animate an existing illustration.** Don't draw the character in code. Mesh-deform a good front-view illustration Live2D/Spine-style:
- a cut-out with a soft alpha edge;
- torso and arm layers split along the costume's own outline;
- a triangle mesh on 20–30 bones, with weights measured by distance inside the silhouette so limbs only take weight from what they are connected to;
- elbows and knees rotate around the posed joint so they bend in an arc;
- a mouth patch plus viseme drawings in the same style;
- lids for blinks, and brow offsets for expressions.

A code-drawn SVG character from scratch only reached "TV cut-out puppet" level: rigid stick limbs, flat backgrounds.

## Defects that shipped once, and the checks that now catch them
- **Torn armpit on raised arms.** Background shows through where the arm layer leaves the torso. Fix it with a generous shoulder cap and an **armpit web**: a fabric patch that has no area at rest and opens as the arm lifts.
- **One-frame smeared arm.** The forearm spun 160° in one frame when the dancer's arm pointed at the camera. Shorten limbs that point toward the camera, and cap how far a full-length segment may turn per frame.
- **Per-frame QA on every frame, not samples:**
  1. triangle flips and degenerates: 0; max edge stretch < 1.6;
  2. holes: render over a pure key colour and take closing(alpha) − alpha inside the silhouette; also a **raw-geometry** pass with any ink or gap filling switched off;
  3. limb flail: no full-length segment turning more than about 60° per frame;
  4. no pose more than twice per bar;
  5. crops of both shoulders and elbows for **every** frame with an arm above 45°. Look at all of them.

## Dance
- A handful of hand-keyed poses cycling reads as ugly.
- Use real choreography: AIST++ **advanced** takes (sFM, CC BY 4.0; the source DB is research-only).
- Score windows for frontality, arm activity, beat fit at the target BPM, hit sharpness and repetition, then give each bar its own phrase.
- For a front-view rig, project to the picture plane and clamp to the rig's safe ranges.
- Blend in 1–2 character signature poses on lyric accents.

## Limits to state up front
- Front view only, no turns.
- Hand shapes stay as drawn (no fists).
- Painted folds.
- Lip timing follows vocal peaks, not phonemes.
