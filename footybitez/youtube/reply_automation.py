import sys
import logging
import argparse
from footybitez.youtube.comment_manager import CommentManager

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("reply_automation")

    parser = argparse.ArgumentParser(description="Automate replies to YouTube comments.")
    parser.add_argument("--video-id", type=str, help="Specific YouTube Video ID to process.", default=None)
    parser.add_argument("--limit", type=int, help="Number of recent videos to check.", default=20)
    args = parser.parse_args()

    manager = CommentManager()

    if args.video_id:
        logger.info(f"Running auto-reply for specific video ID: {args.video_id}")
        manager.auto_reply(video_id=args.video_id)
    else:
        logger.info(f"Fetching up to {args.limit} recent videos to check for comments...")
        recent_videos = manager.get_recent_videos(limit=args.limit)
        
        if not recent_videos:
            logger.warning("No recent videos found or failed to fetch.")
            return

        logger.info(f"Found {len(recent_videos)} recent videos. Processing each...")
        for vid in recent_videos:
            logger.info(f"Processing video ID: {vid}")
            manager.auto_reply(video_id=vid)

    logger.info("Auto-reply process completed.")

if __name__ == "__main__":
    main()
