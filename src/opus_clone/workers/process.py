import asyncio

import dramatiq

from opus_clone.logging import get_logger

logger = get_logger("worker.process")


@dramatiq.actor(max_retries=2, min_backoff=30_000, max_backoff=600_000, time_limit=1_200_000)
def process_video(source_video_id: str):
    """Run the full LangGraph pipeline for a downloaded video."""
    asyncio.get_event_loop().run_until_complete(_process_video(source_video_id))


async def _process_video(source_video_id: str):
    from opus_clone.agent.graph import run_pipeline

    logger.info("process_start", source_video_id=source_video_id)

    try:
        await run_pipeline(source_video_id)
        logger.info("process_complete", source_video_id=source_video_id)
    except Exception as e:
        logger.error("process_failed", source_video_id=source_video_id, error=str(e))
        raise
