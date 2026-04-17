import asyncio
import os
import tempfile
from datetime import datetime, timezone

import dramatiq
from sqlalchemy import select

from opus_clone.config import get_settings
from opus_clone.db import get_worker_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import SourceVideo, VideoStatus

logger = get_logger("worker.ingest")


@dramatiq.actor(max_retries=3, min_backoff=10_000, max_backoff=300_000)
def ingest_video(source_video_id: str):
    """Download a video via yt-dlp and upload to MinIO."""
    asyncio.run(_ingest_video(source_video_id))


async def _ingest_video(source_video_id: str):
    from opus_clone.services.minio import get_minio_client, ensure_buckets

    settings = get_settings()

    logger.info("ingest_start", source_video_id=source_video_id)

    # Update status to downloading
    async with get_worker_db_session() as session:
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
        ensure_buckets()

        # Download with yt-dlp to a temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, f"{video_id}.mp4")
            info = await _download_with_ytdlp(url, output_path)

            # Upload to MinIO
            video_key = f"{video_id}.mp4"
            file_size = os.path.getsize(output_path)

            client = get_minio_client()
            client.fput_object(
                settings.minio_bucket_raw,
                video_key,
                output_path,
                content_type="video/mp4",
            )

            logger.info(
                "upload_complete",
                source_video_id=source_video_id,
                minio_key=video_key,
                file_size=file_size,
            )

        # Update video with downloaded info
        async with get_worker_db_session() as session:
            res = await session.execute(
                select(SourceVideo).where(SourceVideo.id == source_video_id)
            )
            video = res.scalar_one()
            video.status = VideoStatus.downloaded
            video.minio_bucket = settings.minio_bucket_raw
            video.minio_key = video_key
            video.file_size_bytes = file_size
            video.duration_s = info.get("duration")
            if info.get("title"):
                video.title = info["title"]
            if info.get("description"):
                video.description = info["description"]
            if info.get("view_count"):
                video.view_count = info["view_count"]
            if info.get("like_count"):
                video.like_count = info["like_count"]

        logger.info(
            "ingest_complete",
            source_video_id=source_video_id,
            minio_key=video_key,
            duration_s=info.get("duration"),
        )

        # Enqueue processing
        from opus_clone.workers.process import process_video
        process_video.send(source_video_id)

    except Exception as e:
        logger.error("ingest_failed", source_video_id=source_video_id, error=str(e))
        async with get_worker_db_session() as session:
            res = await session.execute(
                select(SourceVideo).where(SourceVideo.id == source_video_id)
            )
            video = res.scalar_one()
            video.status = VideoStatus.failed
            video.error_message = str(e)
            video.retry_count += 1
        raise


async def _download_with_ytdlp(url: str, output_path: str) -> dict:
    """Download a YouTube video using yt-dlp. Returns video info dict."""
    import yt_dlp

    info = {}

    ydl_opts = {
        "format": "best[ext=mp4][height<=1080]/best[height<=1080]/best",
        "outtmpl": output_path,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
        "postprocessors": [
            {
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }
        ],
    }

    def _download():
        nonlocal info
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=True)
            info = {
                "title": result.get("title"),
                "description": result.get("description"),
                "duration": int(result["duration"]) if result.get("duration") else None,
                "view_count": result.get("view_count"),
                "like_count": result.get("like_count"),
                "upload_date": result.get("upload_date"),
                "width": result.get("width"),
                "height": result.get("height"),
                "fps": result.get("fps"),
            }

    # Run in thread to not block the event loop
    await asyncio.to_thread(_download)

    logger.info("ytdlp_download_complete", url=url, duration=info.get("duration"))
    return info
