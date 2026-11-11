import os
import sys
import logging
import subprocess
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

    def _host_video_on_github(self, local_video_path):
        """
        Pushes the generated video to a temporary orphan branch 'temp-video-host' on GitHub.
        Exposes a raw.githubusercontent.com public URL for Meta's servers to fetch.
        Overwrites the branch completely on every run to keep repo size at zero growth.
        """
        if not self.is_ci:
            logger.warning("Not running in GitHub Actions CI. Cannot host video on Git automatically.")
            return None

        repo_slug = os.getenv("GITHUB_REPOSITORY")
        if not repo_slug:
            logger.error("GITHUB_REPOSITORY environment variable not found.")
            return None

        # Clean git URL for raw content download
        raw_url = f"https://raw.githubusercontent.com/{repo_slug}/temp-video-host/hosted_video.mp4"
        logger.info(f"Preparing to host video on Git. Targeted URL: {raw_url}")

        # Isolate hosting from the content checkout: no stash, orphan checkout,
        # git rm, global config or hard-coded restoration branch.
        import tempfile
        import shutil
        from pathlib import Path
        source = Path(local_video_path).resolve()
        try:
            with tempfile.TemporaryDirectory(prefix="footybitez-host-") as temporary:
                def run(args):
                    result = subprocess.run(["git", *args], cwd=temporary,
                                            capture_output=True, text=True)
                    if result.returncode:
                        raise RuntimeError("Temporary video hosting Git operation failed")
                run(["init", "--initial-branch=temp-video-host"])
                run(["config", "user.name", "github-actions[bot]"])
                run(["config", "user.email", "github-actions[bot]@users.noreply.github.com"])
                shutil.copy2(source, Path(temporary) / "hosted_video.mp4")
                run(["add", "hosted_video.mp4"])
                run(["commit", "-m", "Host video for Instagram fetch"])
                token = os.getenv("GITHUB_TOKEN")
                remote = (f"https://x-access-token:{token}@github.com/{repo_slug}.git"
                          if token else f"https://github.com/{repo_slug}.git")
                run(["push", remote, "temp-video-host", "--force"])
            return raw_url
        except Exception:
            # Do not expose a credential-bearing command or subprocess error.
            logger.error("Temporary video hosting failed; content checkout was preserved")
            return None

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

        # 2. Publish to Instagram Reels (Requires git hosting)
        logger.info("--- Publishing to Instagram Reels ---")
        if not self.dry_run and not self.meta.preflight_instagram():
            logger.error("Instagram token/account preflight failed; skipping video hosting")
            results["instagram"] = None
        elif self.dry_run:
            ig_id = self.meta.publish_to_instagram_reel("https://example.com/video.mp4", title)
            results["instagram"] = ig_id
        else:
            public_url = self._host_video_on_github(local_video_path)
            if public_url:
                # Wait 5 seconds to ensure GitHub CDN has indexed the file
                import time
                time.sleep(5)
                ig_id = self.meta.publish_to_instagram_reel(public_url, desc)
                results["instagram"] = ig_id
            else:
                logger.error("Skipping Instagram Reels publishing because video hosting failed.")
                results["instagram"] = None

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
