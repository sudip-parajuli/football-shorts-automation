# FootyBitez Automation

Fully automated system to create and upload YouTube Shorts (and Long-Form Videos) about football facts and history.

## Features
- **Topic Generation**: Automatically selects from topics.
- **Scripting**: Uses Google Gemini AI to write highly-retaining scripts (Chunks & Word Timings).
- **Voiceover & Audio**: Uses `edge-tts` for high-quality voiceover generation and automatically integrates background music + SFX.
- **Cinematic Video Engine (Remotion)**: Uses React-based `Remotion` instead of MoviePy for advanced styling, fast rendering, and infinite scale. Includes TikTok-style highlight captions, Ken Burns asset motion, audio visualizer overlays, and seamless slide/fade cinematic transitions.
- **Multi-Format Architecture**: Native support for building `Shorts` (1080x1920) or `LongForm` (1920x1080) compositions dynamically.
- **Upload**: Automatically uploads to YouTube via YouTube Data API v3.
- **CI/CD**: Runs strictly via GitHub Actions.

## Prerequisites
1. **Node.js**: Required to boot and compile the Remotion video engine.
2. **Python 3.10+**: Back-end scripting, text-to-speech, and API scraping.
3. **Google Cloud Project** with API enabled.

## Setup

### 1. Installation
```bash
# Install Python backend dependencies
pip install -r footybitez/requirements.txt

# Install Remotion Engine dependencies
cd remotion-video
npm install
```

### 2. Authentication Setup
1. Place your `client_secret.json` in the project root.
2. Run `python setup_auth.py` to generate the `token.json` OAuth token for uploads.
3. Create a `.env` in the root:
```
GEMINI_API_KEY=your_gemini_key_here
ENABLE_UPLOAD=true
```

## Running Locally

To manually generate the assets and JSON script instructions (`props.json`):
```bash
python footybitez/main.py
```

### Previewing the Cinematic Engine (Hot Reload)
To test the visual engine or view the output instantly without fully rendering an MP4:
```bash
cd remotion-video
npm start
```
This opens Remotion Studio at `http://localhost:3000`. You can choose between the `Shorts` (9:16) and `LongForm` (16:9) compositions in the left sidebar!

## Folder Structure
- `footybitez/content`: Logic for AI script structures and parsing timings.
- `footybitez/media`: Audio scraping, SFX, background music fetching, and TTS generation.
- `remotion-video`: The complete React-based frontend cinematic rendering engine.
- `footybitez/youtube`: Automatic YouTube metadata population and uploading logic.
