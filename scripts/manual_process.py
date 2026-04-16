#!/usr/bin/env python3
"""Manual end-to-end pipeline test.

Usage:
    python scripts/manual_process.py --mock
    python scripts/manual_process.py --video-url "https://youtube.com/watch?v=..."
"""
import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def main():
    parser = argparse.ArgumentParser(description="Manual video processing pipeline")
    parser.add_argument("--mock", action="store_true", help="Use mock mode (no real GPU/scraper)")
    parser.add_argument("--video-url", type=str, help="YouTube URL to process")
    parser.add_argument("--source-video-id", type=str, help="Existing source_video_id to process")
    args = parser.parse_args()

    if args.mock:
        os.environ["GPU_API_MOCK"] = "true"
        os.environ["SCRAPER_AGENT_MOCK"] = "true"

    from opus_clone.logging import setup_logging
    setup_logging()

    from opus_clone.logging import get_logger
    logger = get_logger("manual_process")

    if args.source_video_id:
        logger.info("processing_existing_video", source_video_id=args.source_video_id)
        from opus_clone.agent.graph import run_pipeline
        result = await run_pipeline(args.source_video_id)
        logger.info("pipeline_result", result=result)
    else:
        logger.info("manual_process_start", mock=args.mock, url=args.video_url)
        logger.info("To process a video, first create a channel and source_video via the API, then pass --source-video-id")


if __name__ == "__main__":
    asyncio.run(main())
