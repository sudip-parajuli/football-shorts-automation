# Content quality changes and operational notes

## Incident diagnosis

The supplied November 3 log shows successful encoding, not a missing narration
track. The generated narration was the generic emergency fallback. The narration
filter used substring matching: `mma` matched **teammate**, rejecting the valid
Gemini back-pass explanation. Groq had already failed JSON validation. When the
remaining model and Wikipedia lookup failed, hardcoded filler was accepted.
The fallback's `full_text` also contained only its hook, hiding the body in logs.
The actual uploaded video has not been retrieved or listened to during this audit.

## November 6 follow-up

The test run failed because Gemini vision requests used `/v1` with JSON mode
(which returned 400), then the project hit its 20-request daily free quota.
Wikimedia's previous fail-open policy admitted an abandoned station and old
football photos for current kit queries. One segment had no image at all and
rendering correctly stopped before publication. The generated Juventus anecdote
and Messi/PSG/2026 query were not substantiated by the visible log.

Follow-up fixes:
- Shared Gemini client explicitly selects `v1beta` for structured output.
- Permanent 400 errors are remembered, vision has an eight-call per-run budget
  (`GEMINI_VISION_MAX_CALLS`), and unavailable verification skips photo downloads.
- Commons metadata must match the detailed query, including any requested year;
  broad first-word fallback searches were removed. Commons and stock search
  downloads require vision verification rather than assuming moderation implies
  relevance. Vision results require all three fields to be actual booleans.
- Missing Shorts photos become locally rendered, clearly labelled narration
  graphics; blank videos and unrelated title-image reuse remain disallowed.
  Documentary image scenes use the same graphic fallback rather than generating
  a fake documentary photograph. These layouts do not consume an image API quota.
- Researched Shorts require exact source quotes per segment and reject numbers
  absent from those quotes and unsupported named/date combinations in visual
  queries. Conceptual questions use web research before biography-style lookup.
  Research URLs and context are saved with the generated script. These checks
  improve traceability; they do not prove that paraphrases logically follow from
  a quote or establish that a source itself is reliable.
- Manual daily/documentary runs default to `publish: false` and upload previews
  as workflow artifacts. Scheduled publishing behavior is unchanged.

- Captions strip single/double/escaped asterisk markers before display, including
  the Shorts hook, long-form scene labels/typewriter/quiz text and match graphics.
  Highlight weights and original narration remain available internally.
- TypeScript is pinned to 5.9.3: Remotion's bundler uses the JavaScript compiler
  API, which is absent from the TypeScript 7 package. Fresh bundle verification
  is now part of the local follow-up checks, alongside type checking.

The daily quota itself still needs to reset, or be increased on the provider
account, before verified remote images are available again. Graphics continue to
work during that outage. The previous missing music warning is informational:
add a manifest to enable music; it did not cause this render failure.

References: [Google SDK API selection](https://googleapis.github.io/python-genai/#api-selection),
[Google structured output](https://ai.google.dev/gemini-api/docs/generate-content/structured-output).

## Post-render dependency fix

The full November 6 Actions log shows all 971 frames were rendered and encoded;
then `inspect_video()` failed because `ffprobe` was absent from PATH. The apparent
906-frame stop was truncated progress output, not the failure location.

All eight video workflows now use a shared action to install and verify system
FFmpeg and ffprobe. Daily and documentary entry points check these dependencies
before research/generation. CI includes real generated-media tests for audible,
silent and absent audio, plus a missing-ffprobe setup test. Render progress is
summarized at the end and the full render log and any generated video are retained
as artifacts even on a later failure.

The same run also exposed inaccurate historical claims in a What If script.
Counterfactual topics now require research and source-quote checks for their real
historical baseline rather than bypassing grounding altogether. Alternate outcomes
must be labelled hypothetical; normal source-validation limitations still apply.

## Implemented

- Whole-word sport filters across narration, grounding, visual query sanitation
  and image metadata. Football handball remains a valid image topic.
- No automatic publication of encyclopedic summaries or invented generic
  biographies. Provider exhaustion skips the topic; three daily-topic failures
  produce a failed job. No ungrounded normal-topic generation.
- Bounded Groq JSON retry, substantive segment and narration length checks,
  canonical full narration, duplicate/filler rejection, precise visual queries.
- Short prompts require tension, an early answer, evidence, consequence and a
  topic-specific payoff. Titles come from the script rather than hashtag stuffing.
- Documentary research context, structural validation, ordered exact narration
  snippets with full coverage, consistent visual-density instructions. Removed
  generic category-based title replacement.
- Real-photo thumbnail composition is now the default; AI thumbnails require
  `ENABLE_AI_THUMBNAILS=true`. Thumbnail text is capped at five words and fitted.
- Long-form starts directly on narration. Later chapter cards last one second.
  Scene cuts no longer overlap and shorten the spoken timeline. Proportional
  fallback timing no longer donates image narration time to unrelated charts.
- Smaller transition duration for Shorts; reduced long-form effects volume and
  frequency. Music loops, with a conservative level below narration.
- Optional music manifest selects by mood and confirmed usage rights. Without a
  manifest, narration plays without music instead of selecting a random file.
- Rejected URL/context pairs are not repeatedly sent to vision. Distinct search
  results have distinct filenames. Tiny preview images are rejected before vision.
- Missing narration aborts rendering; absent segment photos use labelled graphics. YouTube
  and social uploads inspect streams, duration and decoded mean audio volume.
  This detects absent/silent mixes, **not** factual accuracy or correct speech.
- Daily and documentary runs save script/render quality JSON alongside output.
- Instagram account access is checked before hosting. Temporary Git hosting runs
  in an isolated directory without modifying the content checkout or logging a
  credential-bearing push. Total social publishing failure raises an error.
- Locked npm installs throughout video workflows; manual documentary topic is
  passed through an environment variable rather than interpolated as shell code.
- Regression CI covers the incident and core quality failure cases.

## Music configuration

Create `footybitez/music/manifest.json` as an array, using your own licensed files:

```json
[
  {
    "file": "licensed-track.mp3",
    "moods": ["tense", "neutral"],
    "rights_confirmed": true
  }
]
```

Keep proof of each track's license. For future work, extend the manifest with
attribution and platform restrictions; the current selector checks only explicit
rights confirmation, mood and a local file within the music directory.

## Required account fixes

Meta error 190/subcode 467 in the log means the session was invalidated. Code
cannot restore that login: reauthorize the Meta account and update the relevant
GitHub Actions access-token secrets. TikTok was skipped because credentials were
missing; configure its client key, client secret and refresh token. Verify actual
publishing in each platform after replacing credentials. No credentials were
changed and no content was uploaded as part of this change.

## Validation and limits

Run `python -m unittest test_content_quality -v` and
`python -m compileall -q footybitez`. Provider/media calls need real credentials;
offline regression tests do not demonstrate end-to-end production success.
The new checks deliberately prefer a missed upload over filler. They do not
constitute semantic fact checking, image licensing verification, speech-to-text
verification or a guarantee of visual relevance. Documentary scene-plan validation
is strict; inspect rejected outputs before relaxing it.

The old compilation generator and MoviePy renderer remain legacy paths. The
scheduled documentary workflow uses `DocumentaryGenerator` and Remotion. Local
match fallback helpers still contain historical defaults, but normal generation
no longer invokes them after provider failure. Audit any direct callers before
reusing those helpers.

## Measure content performance

For the first production runs, inspect the saved script, title, scene plan and
render before enabling public upload in that environment. Compare similar topics
and durations at consistent ages (24 hours and seven days): viewed versus swiped
away, average view duration, average percentage viewed and subscriber conversion
for Shorts; impressions, click-through rate and early retention for long form.
Use the opening retention drop to revise the hook and the later drops to revise
exposition or visual pacing. Change one editorial variable at a time; no measured
growth claim is possible without channel analytics.

Official references:
- [YouTube Shorts discovery](https://support.google.com/youtube/answer/11914225)
- [YouTube Shorts analytics](https://support.google.com/youtube/answer/12942217)
- [Remotion audio and video](https://www.remotion.dev/docs/video-and-audio)
