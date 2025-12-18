# FootyBitez Automation

Fully automated system to create and upload YouTube Shorts about football facts.

## Features
- **Topic Generation**: Automatically selects from 50+ classic football topics.
- **Scripting**: Uses Google Gemini AI (Free Tier) to write viral scripts (Hooks & Facts).
- **Voiceover**: Uses `edge-tts` for high-quality, free AI narration (British English).
- **Video**: Assembles video with `MoviePy`, syncing text overlays to audio.
- **Upload**: Automatically uploads to YouTube Shorts via YouTube Data API v3.
- **CI/CD**: Runs daily via GitHub Actions.

## Prerequisites
1. **Python 3.10+** (if running locally)
2. **Google Cloud Project** with:
   - YouTube Data API v3 enabled.
   - Generative Language API (Gemini) enabled.
3. **API Keys**:
   - `Gemini API Key` (Get from aistudio.google.com)
   - `client_secret.json` (OAuth 2.0 Client ID for Desktop)

## Setup

### 1. Installation
```bash
pip install -r footybitez/requirements.txt
```

### 2. Authentication Setup
1. Place your `client_secret.json` in the project root.
2. Run the setup script to generate your OAuth token:
   ```bash
   python setup_auth.py
   ```
3. Copy the output JSON string. You will need this for GitHub Secrets.
4. It also saves `token.json` locally, allowing you to run the script on your machine.

### 3. Environment Variables
Create a `.env` file in the root directory:
```
GEMINI_API_KEY=your_gemini_key_here
PEXELS_API_KEY=your_pexels_key_here
ENABLE_UPLOAD=true
```

## Running Locally
To generate and upload a video immediately:
```bash
python footybitez/main.py
```
Check `footybitez/output/` for the generated `final_short.mp4`.

## GitHub Actions Deployment
1. Go to your GitHub Repository -> Settings -> Secrets and variables -> Actions.
2. Add the following Repository Secrets:
   - `GEMINI_API_KEY`: Your Gemini API Key.
   - `PEXELS_API_KEY`: Your Pexels API Key.
   - `YOUTUBE_TOKEN_JSON`: The JSON string you copied from `setup_auth.py`.

The system will now run automatically every day at 12:00 UTC.

## Folder Structure
- `footybitez/content`: Logic for topics and scripts.
- `footybitez/media`: Assets (Images, Voice) and logic.
- `footybitez/video`: Video creation engine.
- `footybitez/youtube`: Upload logic.
