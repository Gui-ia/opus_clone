import httpx

from opus_clone.config import get_settings
from opus_clone.logging import get_logger

logger = get_logger("youtube_data")


async def subscribe_pubsub(channel_id: str, callback_url: str, secret: str) -> bool:
    """Subscribe to YouTube PubSubHubbub for a channel."""
    settings = get_settings()
    topic = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            settings.youtube_pubsub_hub,
            data={
                "hub.callback": callback_url,
                "hub.topic": topic,
                "hub.verify": "async",
                "hub.mode": "subscribe",
                "hub.secret": secret,
                "hub.lease_seconds": "432000",  # 5 days
            },
        )

    success = response.status_code in (202, 204)
    logger.info(
        "pubsub_subscribe",
        channel_id=channel_id,
        status_code=response.status_code,
        success=success,
    )
    return success


async def unsubscribe_pubsub(channel_id: str, callback_url: str) -> bool:
    """Unsubscribe from YouTube PubSubHubbub."""
    settings = get_settings()
    topic = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={channel_id}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            settings.youtube_pubsub_hub,
            data={
                "hub.callback": callback_url,
                "hub.topic": topic,
                "hub.verify": "async",
                "hub.mode": "unsubscribe",
            },
        )
    return response.status_code in (202, 204)


async def resolve_channel_id(username_or_handle: str) -> str | None:
    """Resolve a YouTube handle/username to a channel ID using Data API v3."""
    settings = get_settings()
    if not settings.youtube_api_key:
        logger.warning("youtube_api_key_not_set")
        return None

    # Remove @ prefix if present
    query = username_or_handle.lstrip("@")

    async with httpx.AsyncClient(timeout=15) as client:
        # Try search by handle
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": query,
                "type": "channel",
                "maxResults": 1,
                "key": settings.youtube_api_key,
            },
        )

    if response.status_code != 200:
        logger.warning("youtube_api_error", status=response.status_code)
        return None

    data = response.json()
    items = data.get("items", [])
    if not items:
        return None

    return items[0]["snippet"]["channelId"]
