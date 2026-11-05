# Content quality changes and operational notes

## Incident diagnosis

The supplied November 3 log shows successful encoding, not a missing narration
track. The generated narration was the generic emergency fallback. The narration
filter used substring matching: `mma` matched **teammate**, rejecting the valid
Gemini back-pass explanation. Groq had already failed JSON validation. When the
remaining model and Wikipedia lookup failed, hardcoded filler was accepted.
The fallback's `full_text` also contained only its hook, hiding the body in logs.
The actual uploaded video has not been retrieved or listened to during this audit.

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
- Missing narration or verified short-segment visuals abort rendering. YouTube
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
