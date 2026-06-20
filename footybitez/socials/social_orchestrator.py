import os
import sys
import logging
import subprocess
from footybitez.socials.meta_publisher import MetaPublisher
from footybitez.socials.tiktok_publisher import TikTokPublisher

logger = logging.getLogger(__name__)

class SocialOrchestrator:
    def __init__(self, use_footybitez=False):
        self.use_footybitez = use_footybitez
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

        try:
            # We must run git commands securely
            def git_run(args, check=True):
                cmd = ["git"] + args
                logger.info(f"Running git command: {' '.join(cmd)}")
                res = subprocess.run(cmd, capture_output=True, text=True, check=check)
                if res.stdout:
                    logger.debug(res.stdout)
                if res.stderr:
                    logger.debug(res.stderr)
                return res

            # Configure Git credentials in runner
            git_run(["config", "--global", "user.name", "github-actions[bot]"])
            git_run(["config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"])

            # Stash any local working directory edits to avoid conflicts
            git_run(["stash", "-u"], check=False)

            # Create an orphan branch 'temp-video-host'
            git_run(["checkout", "--orphan", "temp-video-host"], check=False)
            
            # Clear all current staging area files
            git_run(["rm", "-rf", "."], check=False)

            # Copy our local video into root directory under target name 'hosted_video.mp4'
            import shutil
            shutil.copy(local_video_path, "hosted_video.mp4")

            # Add, commit, and force-push to remote temp-video-host branch
            git_run(["add", "hosted_video.mp4"])
            git_run(["commit", "-m", "Host temporary video for Instagram Reels API fetch"])
            
            # Use GITHUB_TOKEN if available, otherwise just use standard remote push
            github_token = os.getenv("GITHUB_TOKEN")
            if github_token:
                remote_url = f"https://x-access-token:{github_token}@github.com/{repo_slug}.git"
                git_run(["push", remote_url, "temp-video-host", "--force"])
            else:
                git_run(["push", "origin", "temp-video-host", "--force"])

            # Revert back to main branch to leave working copy clean for subsequent workflow steps
            git_run(["checkout", "main"], check=False)
            git_run(["stash", "pop"], check=False)

            logger.info(f"SUCCESS: Video successfully hosted on Git branch. Serving URL: {raw_url}")
            return raw_url

        except Exception as e:
            logger.error(f"Git-hosting failed: {e}", exc_info=True)
            # Make sure we checkout main branch back on failure
            try:
                subprocess.run(["git", "checkout", "main"], capture_output=True)
            except:
                pass
            return None

    def publish_to_all(self, local_video_path, title, description=None):
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

        results = {}

        # 1. Publish to Facebook
        logger.info("--- Publishing to Facebook Pages ---")
        fb_id = self.meta.publish_to_facebook(local_video_path, title, desc)
        results["facebook"] = fb_id

        # 2. Publish to Instagram Reels (Requires git hosting)
        logger.info("--- Publishing to Instagram Reels ---")
        if self.dry_run:
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
        if not self.use_footybitez:
            logger.info("--- Publishing to TikTok ---")
            tt_id = self.tiktok.publish_video(local_video_path, title)
            results["tiktok"] = tt_id
        else:
            logger.info("Skipping TikTok publishing for FootyBitez channel.")
            results["tiktok"] = None

        logger.info("=== Cross-Platform Social Publishing Completed ===")
        logger.info(f"Publishing Results: {results}")
        return results

if __name__ == "__main__":
    # Test script entry
    logging.basicConfig(level=logging.INFO)
    orchestrator = SocialOrchestrator()
