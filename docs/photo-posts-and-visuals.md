# Football photo posts and visual updates

`Football Facebook and Instagram Posts` runs daily at 08:30 UTC (14:15 Nepal).
Run it manually with **publish=false** first. Download `football-photo-post` for
the 1080×1350 JPEG, caption, evidence, source metadata and publishing state.
Choose a category, optional topic and photo/text/auto format. Auto chooses
Facebook text-only every fourth UTC day; Instagram is skipped on text-only days.
The automatic topic rotation covers players, coaches, lifestyle, trophies,
historical stats and matches. With a football-data key, results also join the
automatic rotation. Choose **results** manually for a verified recent
finished-match result; `FOOTBALL_DATA_API_KEY` is required. No guessed scores,
possession figures or player statistics are inserted.

Photo captions use the existing evidence-backed writer. Image sourcing requires
an exact football entity article and a supported Commons reuse license. Cropped
and overlaid images include author, source and license links in the caption.
The image is an entity portrait, not proof of a particular match or event.
No suitable photo means a failed preview rather than an unrelated photograph.

Every Facebook/Instagram workflow, including video uploads, news, match posts,
backfill and auto-replies, uses `FOOTYBITEZ_META_ACCESS_TOKEN`, `FOOTYBITEZ_FACEBOOK_PAGE_ID`
(or optional comma-separated `FOOTYBITEZ_FACEBOOK_PAGE_IDS`), and
`FOOTYBITEZ_INSTAGRAM_BUSINESS_ACCOUNT_ID`. The Page ID filter is required;
only the configured FootyBitez Pages are targeted. Generic Meta secrets are
not used as fallbacks by this workflow. A token error applies to the selected
secret; check credential routing before replacing any token.
`META_GRAPH_API_VERSION` can override the default v26.0.

Instagram fetches a publicly hosted JPEG. Actions hosts it in an isolated
`temp-photo-host` Git branch; it does not checkout or stash the main working tree.
`PUBLIC_POST_IMAGE_URL` may instead provide a public image URL outside Actions.
The `social_posts_state.json` ledger is committed even after partial failure.
Each UTC date is one publishing slot. Reruns reuse its saved topic/caption and
skip successful platforms. An ambiguous timeout leaves a pending marker: check
the account before removing that marker, to avoid duplicate posts. A definite
Meta rejection may be retried after credentials/configuration are corrected.

## Video layouts and narration

Shorts use measured headlines, brief captions, relevant real photos and supported
explanatory diagrams. Photos are never replaced by graphics on a fixed rotation.
A diagram is allowed only for a matching spoken explanation (currently contract
negotiation or kit design). Selection news, biographies, results, pressure and
transfer announcements do not automatically trigger diagrams. Missing relevant
media stops the Short before rendering/uploading, with `visual-gaps.json`, rather
than inserting unrelated filler. Explicit match-data cards remain supported.
Stock clips are not used as substitute portraits of named people.
Scene boundaries follow word timestamps rather
than dividing paragraphs into equal time slices. Missing timing marks are
interpolated and reported. Daily public uploads require at least 25% real-media
coverage; `MIN_REAL_MEDIA_FRACTION` can change that threshold. Previews remain
available when coverage is insufficient. Inspect `render-props.json`,
`visual-plan.json`, `visual-coverage.json`, and `narration-report.json` artifacts.

The shared narration defaults to `en-GB-Neural2-B`, conversational rate 1.0 and
neutral pitch, with sentence-aware SSML and word marks. Edge UK Ryan is the next
provider, then configured Hume. A successful provider stays selected for the
video. Basic gTTS requires explicit opt-in via `TTS_PROVIDER_ORDER`. Narration is
normalized using ffmpeg. Repository variables `GOOGLE_CLOUD_TTS_VOICE`,
`EDGE_TTS_VOICE` and `NARRATION_RATE` override daily workflow defaults; other
workflows use the same code defaults unless they set environment overrides.

## Football asset providers

`football_assets.py` resolves exact club names against football-logos.cc's public
index, reads actual PNG URLs, caches decoded images and records attribution.
Unavailable/403 assets are skipped. Badges are used for editorial identification
in Short branding and documentary motion graphics, not as background photos.
The provider's [usage page](https://football-logos.cc/license/) retains club rights
and restricts promotional/merchandise use.

[SportsAPI Pro V1 images](https://docs.sportsapipro.com/api-reference/v1-legacy/images)
need no API key, but do require the correct provider ID and imageVersion. The
verified registry `footybitez/data/football_image_ids.json` starts with the
documented Barcelona badge. Add verified athletes/teams/competitions there with
their name, type, ID, imageVersion and verification source. Athlete IDs must not
come from another provider or a language model. Public image access is separate
from the authenticated name-search API and underlying image rights.
