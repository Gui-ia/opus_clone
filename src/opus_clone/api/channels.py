import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opus_clone.config import get_settings
from opus_clone.db import get_db
from opus_clone.logging import get_logger
from opus_clone.models.db import Channel, PlatformType, SourceType, SourceVideo, VideoStatus
from opus_clone.models.domain import ChannelCreate, ChannelResponse, ChannelUpdate, SourceVideoResponse

router = APIRouter(prefix="/api/channels", tags=["channels"])
logger = get_logger("channels")


@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(data: ChannelCreate, db: AsyncSession = Depends(get_db)):
    external_id = data.external_id

    # Auto-resolve YouTube handle/username to channel ID
    if data.platform == PlatformType.youtube and not external_id.startswith("UC"):
        try:
            from opus_clone.clients.youtube_data import resolve_channel_id

            resolved = await resolve_channel_id(external_id)
            if resolved:
                logger.info("channel_id_resolved", input=external_id, resolved=resolved)
                external_id = resolved
            else:
                logger.warning("channel_id_resolve_failed", input=external_id)
        except Exception as e:
            logger.warning("channel_id_resolve_error", input=external_id, error=str(e))

    channel = Channel(
        platform=data.platform.value,
        external_id=external_id,
        username=data.username,
        display_name=data.display_name,
        poll_interval_seconds=data.poll_interval_seconds,
        source_types=[s.value for s in data.source_types],
        preferred_clip_duration_s=data.preferred_clip_duration_s,
        min_viral_score=data.min_viral_score,
        max_clips_per_video=data.max_clips_per_video,
        style_preset=data.style_preset,
        pubsub_secret=secrets.token_hex(16),
    )
    db.add(channel)
    await db.flush()

    logger.info("channel_created", channel_id=channel.id, platform=data.platform, username=data.username)

    # Subscribe to PubSubHubbub for YouTube channels
    if data.platform == PlatformType.youtube:
        try:
            from opus_clone.clients.youtube_data import subscribe_pubsub

            settings = get_settings()
            success = await subscribe_pubsub(
                channel_id=data.external_id,
                callback_url=settings.youtube_pubsub_callback_url,
                secret=channel.pubsub_secret,
            )
            if success:
                from datetime import datetime, timedelta, timezone

                channel.pubsub_subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=5)
                logger.info("pubsub_subscribed", channel_id=channel.id)
            else:
                logger.warning("pubsub_subscription_failed", channel_id=channel.id)
        except Exception as e:
            logger.warning("pubsub_subscription_error", channel_id=channel.id, error=str(e))

    return ChannelResponse.model_validate(channel)


@router.get("", response_model=list[ChannelResponse])
async def list_channels(
    platform: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Channel)
    if platform:
        stmt = stmt.where(Channel.platform == platform)
    if is_active is not None:
        stmt = stmt.where(Channel.is_active == is_active)
    stmt = stmt.order_by(Channel.created_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    channels = result.scalars().all()
    return [ChannelResponse.model_validate(c) for c in channels]


@router.get("/{channel_id}", response_model=ChannelResponse)
async def get_channel(channel_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return ChannelResponse.model_validate(channel)


@router.patch("/{channel_id}", response_model=ChannelResponse)
async def update_channel(channel_id: str, data: ChannelUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "source_types" and value is not None:
            value = [s.value for s in value]
        setattr(channel, key, value)

    logger.info("channel_updated", channel_id=channel_id, fields=list(update_data.keys()))
    return ChannelResponse.model_validate(channel)


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(channel_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    channel.is_active = False
    logger.info("channel_deactivated", channel_id=channel_id)


@router.post("/{channel_id}/fetch-videos", response_model=list[SourceVideoResponse])
async def fetch_channel_videos(channel_id: str, db: AsyncSession = Depends(get_db)):
    """Fetch latest videos from a channel without auto-processing.

    For YouTube, uses the Data API directly (no scraper needed).
    Creates SourceVideo records with status=discovered so the user
    can manually select which ones to process.
    """
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")

    platform = str(channel.platform).replace("PlatformType.", "")
    external_id = channel.external_id

    # Auto-resolve YouTube handle if needed
    if platform == "youtube" and not external_id.startswith("UC"):
        try:
            from opus_clone.clients.youtube_data import resolve_channel_id

            resolved = await resolve_channel_id(external_id)
            if resolved:
                logger.info("channel_id_resolved", input=external_id, resolved=resolved)
                channel.external_id = resolved
                external_id = resolved
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Nao foi possivel resolver o canal '{external_id}'. Verifique o handle/username.",
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.warning("channel_id_resolve_error", input=external_id, error=str(e))
            raise HTTPException(status_code=502, detail=f"Erro ao resolver canal: {str(e)}")

    video_data_list: list[dict] = []

    try:
        if platform == "youtube":
            # Use YouTube Data API directly - no scraper needed
            from opus_clone.clients.youtube_data import list_channel_videos

            video_data_list = await list_channel_videos(external_id)
        else:
            # Fallback to scraper for other platforms
            from opus_clone.clients.scraper_agent import ScraperAgentClient

            client = ScraperAgentClient()
            if platform == "instagram":
                infos = await client.get_ig_posts(channel.username)
            elif platform == "tiktok":
                infos = await client.get_tk_videos(channel.username)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")
            video_data_list = [
                {
                    "external_id": i.external_id,
                    "url": i.url,
                    "title": i.title,
                    "published_at": i.published_at.isoformat() if i.published_at else None,
                    "duration_s": i.duration_s,
                    "view_count": i.view_count,
                }
                for i in infos
            ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("fetch_videos_error", channel_id=channel_id, error=str(e))
        raise HTTPException(status_code=502, detail=f"Erro ao buscar videos: {str(e)}")

    if not video_data_list:
        logger.warning("no_videos_found", channel_id=channel_id, external_id=external_id)

    created = []
    for vdata in video_data_list:
        existing = await db.execute(
            select(SourceVideo).where(
                SourceVideo.channel_id == channel_id,
                SourceVideo.external_id == vdata["external_id"],
            )
        )
        if existing.scalar_one_or_none():
            continue

        published_at = None
        if vdata.get("published_at"):
            try:
                from datetime import datetime
                raw = vdata["published_at"]
                # Handle YouTube's format: 2024-01-15T10:30:00Z
                published_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:
                pass

        video = SourceVideo(
            channel_id=channel_id,
            external_id=vdata["external_id"],
            source_type=SourceType.video,
            url=vdata["url"],
            title=vdata.get("title"),
            published_at=published_at,
            duration_s=vdata.get("duration_s"),
            view_count=vdata.get("view_count"),
            status=VideoStatus.discovered,
        )
        db.add(video)
        created.append(video)

    if created:
        await db.flush()
        logger.info("videos_fetched", channel_id=channel_id, count=len(created))

    # Return ALL channel videos (including previously discovered)
    all_result = await db.execute(
        select(SourceVideo)
        .where(SourceVideo.channel_id == channel_id)
        .order_by(SourceVideo.discovered_at.desc())
    )
    all_videos = all_result.scalars().all()
    return [SourceVideoResponse.model_validate(v) for v in all_videos]
