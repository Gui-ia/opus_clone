from datetime import datetime, timezone

from sqlalchemy import select

from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import Channel, PlatformType, SourceType, SourceVideo, VideoStatus

logger = get_logger("poller")


async def poll_youtube_channels():
    """Poll YouTube channels for new videos via scraper agent."""
    from opus_clone.clients.scraper_agent import ScraperAgentClient

    client = ScraperAgentClient()

    async with get_db_session() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.is_active.is_(True),
                Channel.platform == PlatformType.youtube,
            )
        )
        channels = result.scalars().all()

    for channel in channels:
        try:
            videos = await client.get_channel_latest(channel.external_id)
            for video_info in videos:
                async with get_db_session() as session:
                    existing = await session.execute(
                        select(SourceVideo).where(
                            SourceVideo.channel_id == channel.id,
                            SourceVideo.external_id == video_info.external_id,
                        )
                    )
                    if existing.scalar_one_or_none():
                        continue

                    video = SourceVideo(
                        channel_id=channel.id,
                        external_id=video_info.external_id,
                        source_type=SourceType.video,
                        url=video_info.url,
                        title=video_info.title,
                        published_at=video_info.published_at,
                        duration_s=video_info.duration_s,
                        view_count=video_info.view_count,
                        status=VideoStatus.discovered,
                    )
                    session.add(video)
                    await session.flush()

                    logger.info(
                        "new_video_discovered",
                        channel_id=channel.id,
                        video_id=video.id,
                        external_id=video_info.external_id,
                    )

                    try:
                        from opus_clone.workers.ingest import ingest_video
                        ingest_video.send(str(video.id))
                    except Exception:
                        logger.warning("enqueue_failed", video_id=video.id)

            # Update last_polled_at
            async with get_db_session() as session:
                result = await session.execute(select(Channel).where(Channel.id == channel.id))
                ch = result.scalar_one()
                ch.last_polled_at = datetime.now(timezone.utc)

        except Exception as e:
            logger.error("poll_error", channel_id=channel.id, error=str(e))
