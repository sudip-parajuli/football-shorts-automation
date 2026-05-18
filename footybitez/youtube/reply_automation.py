import sys
import logging
import argparse
from footybitez.youtube.comment_manager import CommentManager
from footybitez.socials.social_comment_manager import SocialCommentManager

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("reply_automation")

    parser = argparse.ArgumentParser(description="Automate replies to YouTube, Facebook, and Instagram comments.")
    parser.add_argument("--video-id", type=str, help="Specific YouTube Video ID to process.", default=None)
    parser.add_argument("--limit", type=int, help="Number of recent videos to check.", default=20)
    args = parser.parse_args()

    # 1. YouTube Comments Auto-Reply
    try:
        manager = CommentManager()
        if args.video_id:
            logger.info(f"Running auto-reply for specific video ID: {args.video_id}")
            manager.auto_reply(video_id=args.video_id)
        else:
            logger.info(f"Fetching up to {args.limit} recent videos to check for comments...")
            recent_videos = manager.get_recent_videos(limit=args.limit)
            
            if not recent_videos:
                logger.warning("No recent videos found or failed to fetch.")
            else:
                logger.info(f"Found {len(recent_videos)} recent videos. Processing each...")
                for vid in recent_videos:
                    logger.info(f"Processing video ID: {vid}")
                    manager.auto_reply(video_id=vid)
    except Exception as e:
        logger.error(f"Error executing YouTube comment automation: {e}")

    # 2. Facebook & Instagram Comments Auto-Reply
    logger.info("Starting Facebook and Instagram comment auto-reply pipeline...")
    try:
        social_manager = SocialCommentManager()
        logger.info("Executing Facebook Page comment replies...")
        social_manager.auto_reply_facebook()
        logger.info("Executing Instagram Reels comment replies...")
        social_manager.auto_reply_instagram()
    except Exception as e:
        logger.error(f"Error executing Facebook/Instagram comment automation: {e}")

    logger.info("Auto-reply process completed.")


if __name__ == "__main__":
    main()
