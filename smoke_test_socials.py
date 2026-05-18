import os
import sys
import logging
from dotenv import load_dotenv

# Ensure root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from footybitez.socials.social_orchestrator import SocialOrchestrator

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger("smoke_test_socials")

    logger.info("Initializing Social Media Publishing Smoke Test...")
    load_dotenv()

    # Create a dummy video file if it doesn't exist to test the flow
    dummy_video = "dummy_test_video.mp4"
    if not os.path.exists(dummy_video):
        logger.info("Creating a dummy video file for testing...")
        with open(dummy_video, "wb") as f:
            f.write(b"dummy mp4 video bytes context")

    # Set DRY_RUN = True for testing without calling real APIs
    os.environ["DRY_RUN"] = "true"
    logger.info("Running under DRY_RUN mode (no real API requests will be fired)...")

    orchestrator = SocialOrchestrator()
    
    title = "Test Football documentary facts #shorts"
    description = "Did you know these amazing football facts? Find out here!\n\n#football #soccer #shorts #test"

    try:
        results = orchestrator.publish_to_all(dummy_video, title, description)
        logger.info(f"Smoke test completed successfully. Results: {results}")
    except Exception as e:
        logger.error(f"Smoke test FAILED with exception: {e}", exc_info=True)
    finally:
        # Cleanup dummy video
        if os.path.exists(dummy_video):
            os.remove(dummy_video)
            logger.info("Cleaned up dummy video file.")

if __name__ == "__main__":
    main()
