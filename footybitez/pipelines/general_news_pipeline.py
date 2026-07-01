"""
General Football Breaking News Pipeline.
Crawls free, high-volume football RSS feeds (Sky Sports, ESPN FC),
filters them using a persistent state file, uses Gemini/Groq to identify
the absolute hottest/most viral headline, drafts a premium script,
generates a short-form video, and uploads it to YouTube + Facebook + Instagram + TikTok!
"""

import os
import sys
import json
import hashlib
import random

import logging
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("general_news_pipeline")

STATE_FILE = "footybitez/data/general_news_state.json"
FEEDS = [
    "https://www.skysports.com/rss/12040",        # Sky Sports Football
    "https://www.espn.com/espn/rss/soccer/news",  # ESPN FC Soccer
]


class GeneralNewsPipeline:

    def __init__(self):
        from footybitez.content.script_generator import ScriptGenerator
        from footybitez.media.media_sourcer import MediaSourcer
        from footybitez.video.remotion_video_creator import RemotionVideoCreator
        from footybitez.youtube.uploader import YouTubeUploader
        from footybitez.socials.social_orchestrator import SocialOrchestrator

        self.script_gen = ScriptGenerator()
        self.media_sourcer = MediaSourcer()
        self.video_creator = RemotionVideoCreator()
        self.uploader = YouTubeUploader()
        self.socials = SocialOrchestrator()

        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        self.state = self._load_state()

    def _load_state(self) -> dict:
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load general news state: {e}")
        return {"processed_hashes": []}

    def _save_state(self):
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save general news state: {e}")

    def crawl_rss_headlines(self) -> list:
        """Fetches the latest headlines from global RSS football feeds."""
        articles = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        for feed_url in FEEDS:
            try:
                logger.info(f"Crawling feed: {feed_url}...")
                req = urllib.request.Request(feed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    xml_data = response.read()
                
                root = ET.fromstring(xml_data)
                for item in root.findall(".//item")[:15]:
                    title = item.find("title")
                    desc = item.find("description")
                    link = item.find("link")
                    
                    t_text = title.text.strip() if title is not None else ""
                    d_text = desc.text.strip() if desc is not None else ""
                    l_text = link.text.strip() if link is not None else ""
                    
                    if t_text:
                        # Clean HTML tags from description if any
                        import re
                        d_text = re.sub('<[^<]+?>', '', d_text)
                        
                        articles.append({
                            "title": t_text,
                            "description": d_text,
                            "link": l_text
                        })
            except Exception as e:
                logger.error(f"Failed parsing feed {feed_url}: {e}")

        logger.info(f"Successfully scraped {len(articles)} total articles.")
        return articles

    def select_viral_headline(self, articles: list) -> dict | None:
        """Uses Gemini/Groq model to inspect recent headlines and choose the most viral/breaking one."""
        # Deduplicate already processed headlines
        unprocessed = []
        for art in articles:
            h = hashlib.sha256(art["title"].encode("utf-8")).hexdigest()
            if h not in self.state["processed_hashes"]:
                art["hash"] = h
                unprocessed.append(art)

        if not unprocessed:
            logger.info("All scraped articles have already been processed previously.")
            return None

        logger.info(f"Filtering {len(unprocessed)} unprocessed articles to select the hottest story...")
        
        # Prepare list for AI inspection (Limit to top 15 to avoid context blowup)
        articles_list_str = ""
        for idx, art in enumerate(unprocessed[:15]):
            articles_list_str += f"Index [{idx}]: {art['title']} - {art['description'][:150]}\n\n"

        prompt = f"""
        You are a football social media news director. Examine the following list of active football headlines and descriptions:
        
        {articles_list_str}

        Task:
        Select the SINGLE most viral, breaking, or highly trending story from the list.
        Look for major events like:
        - Blockbuster player transfers or heavy rumors involving tier-1 players (e.g., Mbappe, Haaland, Lewandowski, Messi, Salah).
        - Shocking match results of huge clubs (Real Madrid, Barca, Man Utd, Arsenal, Liverpool, Bayern, etc.).
        - Sacking or hiring of famous managers.
        
        If there are multiple hot topics, pick the absolute most dramatic or exciting one for a short-form video audience.
        
        Return ONLY valid JSON in this exact structure:
        {{
            "selected_index": <integer of selected index, or null if none are interesting>,
            "reasoning": "Brief explanation of why this topic is the most viral right now"
        }}
        """

        # Query LLM
        selected_data = None
        if self.script_gen.groq_keys:
            try:
                from groq import Groq
                client = Groq(api_key=self.script_gen.groq_keys[0])
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                selected_data = json.loads(completion.choices[0].message.content)
            except Exception as e:
                logger.error(f"Groq headline selection failed: {e}")

        if not selected_data and self.script_gen.gemini_keys:
            # Fallback to Gemini
            selected_data = self.script_gen._try_gemini(prompt)

        if not selected_data:
            # Fallback to first article if LLM fails
            logger.warning("All LLM selection options failed. Selecting the first unprocessed article.")
            return unprocessed[0]

        idx = selected_data.get("selected_index")
        if idx is not None and 0 <= idx < len(unprocessed[:15]):
            chosen = unprocessed[idx]
            logger.info(f"AI selected viral headline: '{chosen['title']}'. Reasoning: {selected_data.get('reasoning')}")
            return chosen

        logger.warning("AI did not make a valid selection. Defaulting to first article.")
        return unprocessed[0]

    def run(self, skip_upload: bool = False):
        logger.info("Executing General Football Breaking News Pipeline...")
        
        articles = self.crawl_rss_headlines()
        if not articles:
            logger.error("No articles retrieved. Stopping pipeline.")
            return

        chosen_story = self.select_viral_headline(articles)
        if not chosen_story:
            logger.info("No new exciting stories found to report today. Shutting down cleanly.")
            return

        topic = chosen_story["title"]
        desc = chosen_story["description"]
        logger.info(f"Building video short about: {topic}")

        # Generate breaking news script
        script = self.script_gen.generate_script(f"{topic}: {desc}", category="Money & Transfers")
        if not script:
            logger.error("Failed to generate video script for story.")
            return

        # Sourcing visual media assets automatically
        title_card_path = self.media_sourcer.get_title_card_image(topic)
        
        entity_query = script.get('primary_entity')
        if not entity_query:
            entity_query = topic
        profile_image_path = self.media_sourcer.get_profile_image(entity_query)
        if not profile_image_path and title_card_path:
            profile_image_path = title_card_path

        segment_media = []
        for segment in script.get("segments", []):
            keyword = segment.get("visual_keyword", entity_query)
            logger.info(f"Searching media assets for visual keyword: '{keyword}'")
            paths = self.media_sourcer.get_media(keyword, count=3)
            segment_media.append(paths)

        visual_assets = {
            "title_card": title_card_path,
            "profile_image": profile_image_path,
            "segment_media": segment_media
        }



        if not visual_assets.get("title_card"):
            logger.error("No title card asset found — cannot compile video.")
            self.media_sourcer.cleanup()
            return


        # Select background music from local library
        music_dir = "footybitez/music"
        bg_music = None
        if os.path.exists(music_dir):
            files = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
            if files:
                bg_music = os.path.join(music_dir, random.choice(files))

        # Render video
        logger.info("Starting video compilation using RemotionVideoCreator...")
        video_path = self.video_creator.create_video(script, visual_assets, background_music_path=bg_music)
        logger.info(f"Successfully generated video: {video_path}")

        # Post-upload routines
        if not skip_upload:
            title = f"{topic[:60]} 🔴 BREAKING FOOTBALL NEWS #shorts"
            description = (
                f"{script.get('full_text', '')}\n\n"
                f"Source: {chosen_story.get('link', '')}\n\n"
                "#footballnews #transfernews #soccer #shorts #footybitez"
            )
            tags = ["footballnews", "transfernews", "breakingnews", "soccer", "shorts", "footybitez"]
            
            logger.info("Uploading general football short to YouTube...")
            self.uploader.upload_video(video_path, title, description, tags)

            # Push cross-platform to Facebook/Instagram/TikTok
            should_publish_socials = os.getenv("ENABLE_SOCIAL_PUBLISHING", "false").lower() == "true"
            if should_publish_socials:
                logger.info("Pushing general breaking news video cross-platform...")
                self.socials.publish_to_all(video_path, title, description)

        # Record this headline hash in the processed state file
        self.state["processed_hashes"].append(chosen_story["hash"])
        self._save_state()
        logger.info("Headline hash saved. General news pipeline complete!")

        self.media_sourcer.cleanup()
        return video_path


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-upload", action="store_true", help="Generate video but do not upload")
    args = parser.parse_args()

    pipeline = GeneralNewsPipeline()
    pipeline.run(skip_upload=args.skip_upload)
