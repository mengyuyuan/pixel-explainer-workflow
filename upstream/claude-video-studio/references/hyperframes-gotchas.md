# HyperFrames gotchas: rules for every frame worker

These were learned the hard way on real renders. Paste them into the `WORKER-NOTES.md` that parallel sub-agents read.

## Visibility and seeking
1. **Never write `visibility: visible`**, in CSS or in `tl.set`.
   - It leaks the element over the **whole render**, even though snapshots look fine.
   - Use `autoAlpha`, `opacity`, or `visibility: inherit`.
2. **Hidden images need both `visibility: hidden` and `opacity: 0`.** Otherwise they reappear on a backward seek.
3. **One `tl.set` per property per instant.**
   - Two sets on the same property at the same time break backward seeks.
   - Merge them into one function-based set (e.g. `autoAlpha: (i, el) => el === show ? 1 : 0`), or offset them by 1 ms.
4. **End every timeline with `tl.seek(tl.duration()); tl.seek(0);`** so that t=0 sets actually paint.
5. In GSAP `fromTo`, a property present only in the from-vars is applied late under seeking. Put it in both ends.

## Motion
6. **Animate transforms only**: `x`, `y`, `scale`, `rotation`, `opacity`, `autoAlpha`.
   - Never tween `left`, `top`, `width`, `height`, `bottom` or `fontSize`: `check` flags them, and they jitter.
   - A 0 ms `tl.set` of layout is fine.
7. **Deterministic only.**
   - No `Math.random`, `Date`, timers, `requestAnimationFrame`, or CSS keyframes and transitions.
   - Derive jitter from the index, e.g. `sin(i * 12.9898)`.

## Structure
8. **One paused timeline per composition**, registered at `window.__timelines["<id>"]`. `data-duration` must equal the span.
9. **Deliberately layered text** (outlines, stamps over subtitles) must carry `data-layout-allow-overlap` on the actual elements. The attribute isn't inherited. Set it with JS right before the final seeks.
10. An **outline-only text layer** must use the panel colour as its fill, never `transparent`; `check` reports `text_not_painted`.
11. **No literal `<style>` or `<template>` text inside CSS or JS comments.** It trips the `unbalanced_style_tags` lint in every frame that pastes the kit.
12. Namespace ids and classes per frame (`#f3-...`). Keep it light: at most about 12 animated rigs per frame, and no `filter: blur()` on large layers.
13. **three.js or WebGL inside a composition:**
    - resolve `window.__hf.buildReady[...]` only after the textures load;
    - render on the `hf-seek` event;
    - with a module-scoped three.js, the loader wait doesn't see it, so gate readiness yourself.

## CLI
14. Pin the version: `npx hyperframes@0.8.70 ...`. If the first-run skill fetch hangs on GitHub, init with `HYPERFRAMES_SKIP_SKILLS=1`.
15. Swap GSAP from the CDN to a local `assets/gsap.min.js` after assembly, so offline renders work.
16. Run `check --no-contrast`, then `snapshot --at t1,t2,… --no-end --describe false -o dir`, then `render --quality looks --fps 30`.
17. **The final QA is on the MP4 itself.** Extract frames one by one with `ffmpeg -ss`, and never trust the preview alone.
18. **External `<script src>` files run before the composition DOM exists.**
    - Put only function definitions in external files.
    - Call them from an inline `<script>` at the end of `<body>`, which is where the elements get built and the timeline gets registered.
19. **Video layers need dense keyframes.**
    - A `<video>` with sparse keyframes (e.g. a 2.5 s GOP) makes HyperFrames' seeks freeze frames. `check` warns "sparse keyframes".
    - Re-encode first: `ffmpeg -i in.mp4 -c:v libx264 -r 30 -g 15 -keyint_min 15 out.mp4`.
    - Then prove there are no freezes by scanning consecutive-frame differences in the rendered MP4.
20. **Render at the footage frame rate.**
    - A 24 fps video layer in a 30 fps render repeats every 4th frame, which reads as a judder.
    - When the AI footage is 24 fps, use `render --fps 24`, and seek-check with a frozen-frame scan.
21. **Clean frames for covers.**
    - Copy the project, hide the overlay layer (lyrics, stamps, labels) with one CSS rule, and snapshot the copy.
    - Never edit the real project for this.
22. **Keyed characters as VP9-alpha WebM layers.** They composite fine between the background and foreground.
    - Encode with `-c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -g 15`.
    - When decoding them with ffmpeg, force `-c:v libvpx-vp9` before `-i`: the native decoder drops the alpha plane.

