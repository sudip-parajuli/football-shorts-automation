# FootyBitez — Football Media Automation

A Python and Remotion system for creating football videos and coordinating
scheduled publishing. It connects topic selection, AI-assisted scripting,
narration, visual assets, captions, rendering and platform upload workflows.

## Engineering areas

- Football topics and news-driven pre/post-match pipelines.
- Script generation and provider fallback handling.
- Narration, timed captions, images, clips, music and sound effects.
- React/Remotion compositions for vertical and horizontal video.
- GitHub Actions workflows and configurable platform integrations.

## Run locally

Use Python 3.10+, Node.js and FFmpeg. From the repository root:

```sh
python -m venv .venv
```

Activate the environment, then:

```sh
python -m pip install -r footybitez/requirements.txt
cd remotion-video
npm install
```

Configure only the providers you intend to use, following the retained
[provider/setup guide](docs/PROVIDER_SETUP.md). For the basic entry point, set
`ENABLE_UPLOAD=false` and `ENABLE_SOCIAL_PUBLISHING=false` in your local
environment before running from the repository root:

```sh
python footybitez/main.py
```

Generation still makes external provider requests. Other entry points and
scheduled workflows have their own publication configuration; inspect the
selected workflow before running it.

## Preview and source map

```sh
cd remotion-video
npm start
```

| Path | Responsibility |
| --- | --- |
| `footybitez/content/` | Topics, scripts and content preparation |
| `footybitez/media/` | Narration and visual/media assembly |
| `footybitez/youtube/` | YouTube upload integration |
| `remotion-video/` | Video compositions and rendering |
| `.github/workflows/` | Scheduled and manually triggered jobs |

## Validation and boundaries

Root-level `test_*.py` files include fallback, routing, API and media experiments.
Some contact real services; inspect their inputs before running them. Scheduled
pipeline runs are operational checks, not a complete isolated regression suite.

Review factual claims, media provenance, captions and provider/platform terms
before publication. Retries and fallbacks improve resilience but do not guarantee
factually correct scripts, licensed assets or successful platform distribution.
Keep credentials and OAuth artifacts outside Git.
