import asyncio
from datetime import datetime, timezone
from uuid import uuid4

import dramatiq
from sqlalchemy import select

from opus_clone.config import get_settings
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import SourceVideo, VideoStatus

logger = get_logger("worker.ingest")


@dramatiq.actor(max_retries=3, min_backoff=10_000, max_backoff=300_000)
def ingest_video(source_video_id: str):
    """Download a video via scraper-agent and upload to MinIO."""
    asyncio.get_event_loop().run_until_complete(_ingest_video(source_video_id))


async def _ingest_video(source_video_id: str):
    from opus_clone.clients.scraper_agent import ScraperAgentClient
    from opus_clone.services.minio import generate_presigned_put

    settings = get_settings()
    client = ScraperAgentClient()

    logger.info("ingest_start", source_video_id=source_video_id)

    # Update status to downloading
    async with get_db_session() as session:
        result = await session.execute(
            select(SourceVideo).where(SourceVideo.id == source_video_id)
        )
        video = result.scalar_one_or_none()
        if not video:
            logger.error("video_not_found", source_video_id=source_video_id)
            return

        video.status = VideoStatus.downloading
        video.started_at = datetime.now(timezone.utc)
        url = video.url
        video_id = video.id

    try:
        # Generate presigned URLs for MinIO
        video_key = f"raw/{video_id}.mp4"
        info_key = f"raw/{video_id}.info.json"
        presigned_put = generate_presigned_put(settings.minio_bucket_raw, video_key)
        presigned_info = generate_presigned_put(settings.minio_bucket_raw, info_key)

        # Download via scraper-agent
        result = await client.download_youtube(
            url=url,
            minio_presigned_put_url=presigned_put,
            minio_presigned_info_url=presigned_info,
        )

        # Update video with downloaded info
        async with get_db_session() as session:
            res = await session.execute(
                select(SourceVideo).where(SourceVideo.id == source_video_id)
            )
            video = res.scalar_one()
            video.status = VideoStatus.downloaded
            video.minio_bucket = settings.minio_bucket_raw
            video.minio_key = video_key
            video.duration_s = result.duration_s
            video.file_size_bytes = result.bytes_uploaded
            video.heatmap = result.heatmap
            if result.title:
                video.title = result.title
            if result.description:
                video.description = result.description
            if result.view_count:
                video.view_count = result.view_count
            if result.like_count:
                video.like_count = result.like_count

        logger.info(
            "ingest_complete",
            source_video_id=source_video_id,
            minio_key=video_key,
            duration_s=result.duration_s,
        )

        # Enqueue processing
        from opus_clone.workers.process import process_video
        process_video.send(source_video_id)

    except Exception as e:
        logger.error("ingest_failed", source_video_id=source_video_id, error=str(e))
        async with get_db_session() as session:
            res = await session.execute(
                select(SourceVideo).where(SourceVideo.id == source_video_id)
            )
            video = res.scalar_one()
            video.status = VideoStatus.failed
            video.error_message = str(e)
            video.retry_count += 1
        raise
