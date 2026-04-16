from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from opus_clone.config import get_settings
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import Channel, PlatformType

logger = get_logger("pubsub_renewer")


async def renew_pubsub_subscriptions():
    """Renew PubSubHubbub subscriptions expiring within 2 days."""
    from opus_clone.clients.youtube_data import subscribe_pubsub

    settings = get_settings()
    threshold = datetime.now(timezone.utc) + timedelta(days=2)

    async with get_db_session() as session:
        result = await session.execute(
            select(Channel).where(
                Channel.is_active.is_(True),
                Channel.platform == PlatformType.youtube,
                (Channel.pubsub_subscription_expires_at.is_(None))
                | (Channel.pubsub_subscription_expires_at < threshold),
            )
        )
        channels = result.scalars().all()

    for channel in channels:
        try:
            success = await subscribe_pubsub(
                channel_id=channel.external_id,
                callback_url=settings.youtube_pubsub_callback_url,
                secret=channel.pubsub_secret or "",
            )
            if success:
                async with get_db_session() as session:
                    result = await session.execute(select(Channel).where(Channel.id == channel.id))
                    ch = result.scalar_one()
                    ch.pubsub_subscription_expires_at = datetime.now(timezone.utc) + timedelta(days=5)
                logger.info("pubsub_renewed", channel_id=channel.id)
            else:
                logger.warning("pubsub_renewal_failed", channel_id=channel.id)
        except Exception as e:
            logger.error("pubsub_renewal_error", channel_id=channel.id, error=str(e))
