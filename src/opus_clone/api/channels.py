import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opus_clone.config import get_settings
from opus_clone.db import get_db
from opus_clone.logging import get_logger
from opus_clone.models.db import Channel, PlatformType
from opus_clone.models.domain import ChannelCreate, ChannelResponse, ChannelUpdate

router = APIRouter(prefix="/api/channels", tags=["channels"])
logger = get_logger("channels")


@router.post("", response_model=ChannelResponse, status_code=201)
async def create_channel(data: ChannelCreate, db: AsyncSession = Depends(get_db)):
    channel = Channel(
        platform=data.platform.value,
        external_id=data.external_id,
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
