import os
import logging
from footybitez.socials.meta_publisher import MetaPublisher
from footybitez.socials.tiktok_publisher import TikTokPublisher

logger = logging.getLogger(__name__)

class SocialOrchestrator:
    def __init__(self, use_footybitez=True, skip_tiktok=False):
        # Meta targets FootyBitez in every pipeline. TikTok remains independent.
        self.use_footybitez = True
        self.skip_tiktok = skip_tiktok
        self.meta = MetaPublisher(use_footybitez=use_footybitez)
        self.tiktok = TikTokPublisher()
        self.dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        self.is_ci = os.getenv("GITHUB_ACTIONS") == "true"

    def publish_to_all(self, local_video_path, title, description=None, content_text=None, topic=None):
        """
        Coordinates the publishing of videos to Facebook, Instagram Reels, and TikTok.
        """
        if not os.path.exists(local_video_path):
            logger.error(f"Cannot publish: Local video file not found at '{local_video_path}'")
            return

        logger.info(f"=== Starting Cross-Platform Social Publishing ===")
        logger.info(f"Title: {title}")

        # Fallback description
        desc = description if description else f"{title}\n\n#football #soccer #shorts #footybitez"

        if not self.dry_run:
            from footybitez.video.preflight import inspect_video
            inspect_video(local_video_path)
        history = None
        claim = None
        if not self.dry_run:
            from footybitez.content.history import ContentHistory, media_identity
            history = ContentHistory()
            claim = history.claim(topic or title, content_text if content_text is not None else desc, 'social', piece_id=media_identity(local_video_path))
            if claim['previous'] is not None:
                logger.info('This piece has already been sent to its social platforms.')
                return claim['previous']
        results = {}

        # 1. Publish to Facebook
        logger.info("--- Publishing to Facebook Pages ---")
        fb_id = self.meta.publish_to_facebook(local_video_path, title, desc)
        results["facebook"] = fb_id

        # 2. Upload the local file directly to Instagram; no Git hosting limit.
        logger.info("--- Publishing to Instagram Reels ---")
        if not self.dry_run and not self.meta.preflight_instagram():
            logger.error("Instagram token/account preflight failed; skipping upload")
            results["instagram"] = None
        elif self.dry_run:
            ig_id = self.meta.publish_to_instagram_reel("https://example.com/video.mp4", title)
            results["instagram"] = ig_id
        else:
            results['instagram'] = self.meta.publish_to_instagram_reel(None, desc, local_file=local_video_path)

        # 3. Publish to TikTok
        if not self.skip_tiktok:
            logger.info("--- Publishing to TikTok ---")
            tt_id = self.tiktok.publish_video(local_video_path, title)
            results["tiktok"] = tt_id
        else:
            logger.info("Skipping TikTok publishing (skip_tiktok=True).")
            results["tiktok"] = None

        logger.info("=== Cross-Platform Social Publishing Completed ===")
        logger.info(f"Publishing Results: {results}")
        if not self.dry_run and not any(results.values()):
            raise RuntimeError("No social platform published successfully; check credentials and results")
        if history is not None:
            history.complete(claim['key'], 'social', results)
        return results

if __name__ == "__main__":
    # Test script entry
    logging.basicConfig(level=logging.INFO)
    orchestrator = SocialOrchestrator()
