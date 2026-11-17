# Editing tools reviewed — 17 November 2026

The production pipeline keeps its existing Remotion renderer. This change adds
original native code; none of the repositories below is vendored or installed.
The public repositories were read as research sources, not run as instructions.

| Repository | Finding | Integration decision |
| --- | --- | --- |
| [Hyperframes](https://github.com/heygen-com/hyperframes) | HTML/CSS video rendering with seekable, deterministic animation; Apache-2.0 | Keep the working Remotion engine and use frame-driven motion and browser layout checks |
| [OneTake](https://github.com/feitangyuan/onetake) | Continuous motion films; PolyForm Noncommercial licence | No code, skill, or assets imported. Use independently implemented stable staging and visual holds |
| [gbro-collage-broll](https://github.com/pyang5166/gbro-collage-broll) | Editorial collage workflow; its video generation uses a billed Gemini API | Implement photo-paper compositions in React using existing verified photos, without video-model calls |
| [ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) | p5.js/p5.brush animation starter with storyboard and rendered-frame review; MIT | Add original staged component reveals and contact sheets; do not import its mascot or brush renderer |
| [Lemo-Opuscar](https://github.com/lemomo-ai/lemo-opuscar) | Broad style gallery; code and documentation have different licences | No docs, style prompts, assets, or demo code copied. Keep an independently authored football visual profile |

## Concrete output changes

- Career/history passages can use photo-paper framing with complete photographs.
- Documentary comparisons can show two independently sourced entity photos only
  when both subjects are explicitly named in that narrated scene.
- Generated SVGs can contain two to four independently validated components.
  The first establishes context; later components enter on their spoken phrase
  anchors and remain visible. Invalid layer metadata falls back to the full SVG.
- Shorts and documentaries create a sampled contact sheet and JSON visual review
  after rendering. Samples include scene entrances, middles and endings. This is
  review material, not proof that every image is semantically correct.

## Text overflow protection

The screenshot regression originated in a legacy single-line raster fallback.
That fallback no longer truncates to forty characters. It measures and wraps the
complete text. Generic hash-named fallback cards are not treated as documentary
media; narration-derived graphics replace them. Verified match data cards remain
eligible and their raster text is measured before drawing.

The Remotion roots wait for the bundled font before measuring text. Every rendered
frame checks visible DOM text against the canvas and clipping ancestors. Overflow
cancels the render, so that invalid render cannot proceed to publishing. CI checks
both a safe heading and an intentionally oversized unbroken line in Chromium.
This checks the text the browser can inspect; external photographs with embedded
lettering still require visual review. Source photographs remain contained.

## Files to review in Actions

`visual-review/contact-sheet.jpg` and `visual-review/visual-review.json` accompany
the existing video, visual plan, render log and SVG-generation report. Possible
blank-frame flags are sampled warnings. Layout violations are render errors.
