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
from footybitez.utils.llm_models import GROQ_SCRIPT_MODEL

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("general_news_pipeline")

STATE_FILE = "footybitez/data/general_news_state.json"
# ESPN and Sky Sports alone have been silently starving this pipeline: Sky
# Sports crashes partway through parsing most runs (see the title.text bug
# fixed below) and ESPN has been failing consistently in CI (works when
# fetched directly from here, so this looks like GitHub Actions' datacenter
# IPs getting bot-blocked, not a dead feed — but a source that fails 100% of
# observed CI runs is not a source worth depending on alone). Added BBC Sport
# and The Guardian as two more independent sources so a single source's
# failure doesn't collapse coverage to whatever Sky Sports happened to parse
# before crashing.
FEEDS = [
    # 12040 (the ID this used to point at) is actually Sky Sports' GENERAL "all
    # sports" feed — horse racing, F1, rugby, cricket, golf, all mixed in with
    # football, confirmed live: https://www.skysports.com/rss/12040 returned
    # "Chepstow, Lingfield and Wolverhampton host today's live racing action"
    # and "Rugby's greatest rivalry?" alongside actual football stories. 11095
    # is their dedicated football-only feed (verified: 15/15 items football).
    "https://www.skysports.com/rss/11095",        # Sky Sports Football (verified football-only)
    "https://www.espn.com/espn/rss/soccer/news",  # ESPN FC Soccer
    "https://feeds.bbci.co.uk/sport/football/rss.xml",  # BBC Sport Football
    "https://www.theguardian.com/football/rss",         # The Guardian Football
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
        self.socials = SocialOrchestrator(use_footybitez=True, skip_tiktok=False)

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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
            "Accept-Language": "en-US,en;q=0.9",
        }

        for feed_url in FEEDS:
            xml_data = b""
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

                    # A tag can be PRESENT but EMPTY (title.text is None even
                    # though `title is not None`) — this used to crash
                    # `.strip()` on None partway through the loop, silently
                    # dropping every remaining item in that feed for the rest
                    # of the run (caught by the outer except below, logged as
                    # "failed parsing" even though most of the feed had
                    # already parsed fine).
                    t_text = (title.text or "").strip() if title is not None else ""
                    d_text = (desc.text or "").strip() if desc is not None else ""
                    l_text = (link.text or "").strip() if link is not None else ""

                    if t_text:
                        # Clean HTML tags from description if any
                        import re
                        d_text = re.sub('<[^<]+?>', '', d_text)

                        # Defense-in-depth: discovered that Sky Sports' feed ID this
                        # used to point at was actually their GENERAL sports feed,
                        # silently mixing horse racing/F1/rugby/cricket headlines in
                        # with football ones, with nothing downstream ever checking
                        # headline TEXT for sport relevance before handing it to the
                        # "pick the hottest story" LLM call. Fixed the feed URL
                        # itself above, but a feed (this one or a future addition)
                        # drifting or occasionally cross-posting off-topic content
                        # shouldn't be able to produce an entire video about the
                        # wrong sport. Reuses ScriptGenerator.BAD_TOPIC_KEYWORDS
                        # rather than MediaSourcer's image-metadata list — that one
                        # includes "handball", which is a routine football term (VAR
                        # decisions) here, not just the separate sport; the
                        # narration-text list already excludes it for that reason.
                        combined_text = f"{t_text} {d_text}".lower()
                        if any(bad in combined_text for bad in self.script_gen.BAD_TOPIC_KEYWORDS):
                            continue

                        articles.append({
                            "title": t_text,
                            "description": d_text,
                            "link": l_text
                        })
            except ET.ParseError as e:
                # "no element found" here typically means the response body
                # wasn't the feed at all (an empty body, a bot-check/redirect
                # page, etc.) rather than a malformed feed — log a snippet so
                # a future failure is diagnosable without re-fetching by hand.
                logger.error(f"Failed parsing feed {feed_url}: {e}. Response started with: {xml_data[:200]!r}")
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

        from footybitez.content.topic_generator import TopicGenerator
        category_names = list(TopicGenerator().categories.keys())
        DEFAULT_CATEGORY = "Shocking Moments"

        prompt = f"""
        You are a football social media news director. Examine the following list of active football headlines and descriptions:

        {articles_list_str}

        Task 1: Select the SINGLE most viral, breaking, or highly trending story from the list.
        Look for major events like:
        - Blockbuster player transfers or heavy rumors involving tier-1 players (e.g., Mbappe, Haaland, Lewandowski, Messi, Salah).
        - Shocking match results of huge clubs (Real Madrid, Barca, Man Utd, Arsenal, Liverpool, Bayern, etc.).
        - Sacking or hiring of famous managers.

        If there are multiple hot topics, pick the absolute most dramatic or exciting one for a short-form video audience.

        Task 2: Classify the story you selected into exactly ONE of these categories
        (pick whichever actually fits the story's content — e.g. a transfer story is
        "Money & Transfers", a dramatic match moment is "Shocking Moments", a
        controversial officiating decision is "Referees, Rules & Weird Laws", a
        derby/rivalry result is "Rivalries & Wars", a scandal is "Mysteries & Dark Side"):
        {", ".join(category_names)}

        Return ONLY valid JSON in this exact structure:
        {{
            "selected_index": <integer of selected index, or null if none are interesting>,
            "category": "<one of the category names listed above, matching the story's actual content>",
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
                    model=GROQ_SCRIPT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                selected_data = json.loads(completion.choices[0].message.content)
            except Exception as e:
                logger.error(f"Groq headline selection failed: {e}")

        if not selected_data and self.script_gen.gemini_keys:
            # Fallback to Gemini. NOTE: uses _try_gemini_raw_json, NOT _try_gemini —
            # _try_gemini gates success on _validate_script_data(), which requires
            # "hook"/"segments" keys that this selected_index/category/reasoning
            # response will never have. That mismatch meant this fallback path
            # silently failed on every single call (even successful ones), always
            # falling through to "just pick the first article" below — the AI
            # selection had never actually been working via this path.
            selected_data = self.script_gen._try_gemini_raw_json(prompt)

        if not selected_data:
            # Fallback to first article if LLM fails
            logger.warning("All LLM selection options failed. Selecting the first unprocessed article.")
            chosen = unprocessed[0]
            chosen["category"] = DEFAULT_CATEGORY
            return chosen

        idx = selected_data.get("selected_index")
        category = selected_data.get("category")
        if category not in category_names:
            category = DEFAULT_CATEGORY

        if idx is not None and 0 <= idx < len(unprocessed[:15]):
            chosen = unprocessed[idx]
            chosen["category"] = category
            logger.info(f"AI selected viral headline: '{chosen['title']}' (category: {category}). Reasoning: {selected_data.get('reasoning')}")
            return chosen

        logger.warning("AI did not make a valid selection. Defaulting to first article.")
        chosen = unprocessed[0]
        chosen["category"] = category
        return chosen

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
        # Was hardcoded to "Money & Transfers" for every single story regardless
        # of content — a last-minute goal, a red card controversy, anything —
        # which pushed the model toward transfer-fee/bidding-war framing
        # (per that category's own prompt instructions) for stories that had
        # nothing to do with transfers. select_viral_headline now classifies
        # the actual category alongside picking the story.
        category = chosen_story.get("category", "Shocking Moments")
        logger.info(f"Building video short about: {topic} (category: {category})")

        # Generate breaking news script
        script = self.script_gen.generate_script(f"{topic}: {desc}", category=category)
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
