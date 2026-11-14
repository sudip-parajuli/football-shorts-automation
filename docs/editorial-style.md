# FootyBitez Matchroom

The profile is shared by Shorts, documentary graphics, captions and social image
posts through `remotion-video/src/editorialStyle.json`. Real photographs remain
available alongside narration-derived graphics. A missing photograph can now
produce a statement, a decision or a number reveal using the narrated words.

## Reference review

Two public reference thumbnails were inspected on 11 November 2026.

| Reference | Observed thumbnail treatment | FootyBitez application |
| --- | --- | --- |
| [Tifo — How much does it cost to sack a manager?](https://www.youtube.com/watch?v=DQyJUP_BDJo) | Illustrated contract being torn, a green field and one clear visual metaphor | Use a literal, relevant visual explanation of the subject |
| [FourFourTwo — Is This The Most Underrated Team In The Premier League?](https://www.youtube.com/watch?v=qPTcwY1lhFw) | Two player cutouts, saturated purple, a short yellow keyword on a black strip | Strong subject hierarchy, brief headlines and high contrast |

The direct excerpt download returned HTTP 403. A subsequent vidIQ video analysis
completed for the Tifo example. Its automated walkthrough reported the following
concrete observations, which informed the editing rules.

| Time in the Tifo reference | Reported editing treatment | Applied principle |
| --- | --- | --- |
| 00:08–00:15 | Left-aligned table with highlighted rows | Keep an obvious reading hierarchy |
| 00:44–01:13 | Illustrated contracts, cross-outs and expanding bars | Make the visual explain the narrated mechanism |
| 02:30–02:42 | Contract-period timeline | Use sourced dates when showing chronological information |
| 02:46, 03:10 | Large metrics inside bordered badges | Give a real number one clear focal area |
| 04:04–04:18 | Sequential key terms with icons | Align reveals with spoken points |
| Overall | Heavy geometric sans type, flat colour themes, brief cuts around narration, subtle entrance sounds under voice | Use concise graphics and restrained sound cues |

Exact font names and raw cut intervals were not independently measured. The
profile below is FootyBitez's own design direction. On 11 November, vidIQ reported
356,205 views and a 2.54 outlier multiplier for the Tifo reference. These are a
current snapshot, not a prediction for FootyBitez. The reference calls used 30
vidIQ credits in total. Production rendering does not depend on that service.

## Applied design

| Element | Rule |
| --- | --- |
| Font | Bundled Barlow Condensed Bold, measured to fit each safe text box |
| Colours | Dark ink `#101b24`, cream `#f4efe4`, amber `#f7c64d`, teal `#7dc7c0`; cream number cards and blue decision cards |
| Short captions | Up to four words per page, current word in amber, bottom and right controls kept clear |
| Graphics | Statement excerpts, actual numbers, and decision labels drawn from narration |
| Transitions | Brief text/line entrances, readable content visible on the first frame |
| Sound | Original quiet tick/accent waveforms on decision/number reveals, at least four seconds apart, at most six cues per Short |
| Documentary | Same graphics and word captions in landscape, narration snippets retained for scene alignment |
| Social images | Relevant photo with fitted headline, or an original editorial image with a title and two complete context points |
| Social text | Short paragraphs, topic-specific tags, cited source URLs and one relevant closing question |

## Tools and runtime

Remotion renders the shared graphics and FFmpeg handles media encoding,
narration mastering and reference analysis. [HyperFrames](https://github.com/heygen-com/hyperframes)
was reviewed as an alternative HTML renderer. The production implementation uses
the existing Remotion project and its normal entry points.

Provider word marks remain the first caption timing source. When they are
missing, [faster-whisper](https://github.com/SYSTRAN/faster-whisper) transcribes
locally on CPU. Only matching words anchor the authored narration. Low matching
coverage falls back to interpolation and is reported in the narration artifact.
The first Whisper use downloads `base.en`. `WHISPER_ALIGNMENT_MODEL`,
`WHISPER_CACHE_DIR` and `ENABLE_WHISPER_ALIGNMENT` control this fallback.
Failed model initialization is remembered for the rest of the run.

The existing optional Claude writer accepts `ANTHROPIC_SCRIPT_MODEL` and defaults
to `claude-sonnet-4-6` when an Anthropic key is already supplied to the process.
Narration-derived graphics are constructed locally and do not require another
model request for every edit.

For repeatable reference inspection, run the command below with a direct public
video URL. It uses [yt-dlp](https://github.com/yt-dlp/yt-dlp), downloads an excerpt
of up to 60 seconds, and uses FFmpeg to extract sample frames and detect cuts.
It writes `analysis.json` under `footybitez/data/references`, separate from
production media. Sites can deny downloads, as happened during this review.

```bash
python -m footybitez.tools.analyze_reference VIDEO_URL --start 30 --seconds 30
```

Manual workflows retain their preview defaults. Inspect the generated video,
`visual-plan.json`, `visual-coverage.json` and `narration-report.json` artifacts.
Graphics can cover the complete video, so public uploads no longer require a
minimum fraction of photographs.

## Topic and script history

Every YouTube upload, social video publication and photo/text post uses the shared
publication history. It compares normalized topics, highly overlapping headlines,
script fingerprints and near-matching script vocabulary. Re-rendering a published
piece reuses its stored platform result. The same finished video can go to its
intended platforms. Distinct match dates and changed scores stay eligible.

In Actions, the history is stored on the dedicated `content-history` branch at
`footybitez/data/content_history.json`. The normal `GITHUB_TOKEN` with contents
write permission is required. Updates use the current file SHA and retry conflicts
so concurrent workflow runs cannot overwrite another run's claim. Existing used
normal topics, RSS headline hashes and successful photo-post records seed the
history. No automatic expiration is applied to that history. Local publishing uses
the same JSON path with an atomic file lock.

Topics are reserved before the publishing API call. A pending result after an
ambiguous failure remains blocked for review, to prevent duplicate uploads. Photo
post retries can resume through their saved per-platform ledger. Automated topic
selection chooses unused topics and stops when the configured pool is exhausted.
Manual preview rendering does not reserve a new topic.


## Documentary publication results

A successful YouTube upload remains successful if optional social cross-posting
fails. The documentary artifact includes `publication-results.json` and the run
summary links to the published video. `partial_success` means social publication
failed or needs review; it does not mean that YouTube should be uploaded again.
The shared history continues to block ambiguous repeat publication attempts.

Large Facebook files use Meta's start/transfer/finish protocol on
`graph-video.facebook.com`, with server-requested byte ranges. Instagram videos
use local-file resumable upload and processing polling; generated videos are no
longer committed to a Git hosting branch. This avoids GitHub's 100 MiB repository
file limit. The same FootyBitez credentials are retained. Meta requests default to
Graph API v25.0, configurable through `META_GRAPH_API_VERSION`.


## Complete text and uncropped photographs

Editorial briefs retain the full narrated passage. The renderer divides it into
short, fitted pages, changing pages at word timestamps when available. No text is
silently discarded after eighteen words. Landscape and portrait layouts reserve
separate areas for the copy, illustrations, footer and spoken captions.

Photographs use a contained foreground over a blurred backdrop. The entire source
stays visible throughout a gentle zoom that never exceeds its safe frame. This
also applies to secondary photo badges and Short photo scenes. The backdrop may
crop; the foreground does not crop faces or other source content.

Narrated contract, trophy, calendar/retirement, injury recovery and passing terms
can select original animated SVG illustrations. These are neutral explanations,
not fabricated player reactions or reconstructions of match events. Unmatched
passages retain a clean text treatment.


## Open-ended narration SVG director

The five built-in drawings are fallbacks, not the subject catalogue. Before
rendering Shorts and documentaries, `SvgDirector` batches editorial passages and
asks the existing Groq/Gemini providers for original illustrations of the objects,
settings, relationships or mechanisms actually narrated. New subjects require no
new React component or keyword entry. Matching real photographs stay in use.

Each generated drawing must cite a contiguous subject phrase from its passage.
The validator permits only bounded geometric SVG primitives; it rejects scripts,
links, external assets, embedded text, styling and executable SVG elements. The
renderer loads accepted geometry as an inert image and supplies draw, float or
pulse motion. The authored narration supplies factual text and numbers separately.
Illustration relevance still depends on the model; inspect the visual-plan and
preview artifacts rather than treating structural validation as a factual check.

`svg-report.json` records eligible scenes, generated/cache hits, rejections and
provider requests. Cache entries are revalidated before reuse. API errors and
rejected drawings keep the existing clean graphic fallback and do not stop a
video. `ENABLE_GENERATED_SVG=false` disables new generation. `SVG_MAX_REQUESTS`
defaults to six provider calls per video (at most twelve); each batch contains up
to four distinct passages. Existing API credentials are reused, so generation uses
their normal quota. The cache is local to the runner and not committed to Git.
