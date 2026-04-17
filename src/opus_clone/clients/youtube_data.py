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


async def list_channel_videos(channel_id: str, max_results: int = 50) -> list[dict]:
    """List recent videos from a YouTube channel using Data API v3.

    Returns list of dicts with: external_id, url, title, published_at, duration_s.
    This does NOT require the scraper agent.
    """
    settings = get_settings()
    if not settings.youtube_api_key:
        logger.warning("youtube_api_key_not_set")
        return []

    async with httpx.AsyncClient(timeout=30) as client:
        # Step 1: Search for videos from the channel
        response = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "channelId": channel_id,
                "type": "video",
                "order": "date",
                "maxResults": max_results,
                "key": settings.youtube_api_key,
            },
        )

    if response.status_code != 200:
        logger.warning("youtube_api_error", status=response.status_code, body=response.text)
        return []

    data = response.json()
    items = data.get("items", [])
    if not items:
        return []

    video_ids = [item["id"]["videoId"] for item in items]

    # Step 2: Get video details (duration, view count)
    async with httpx.AsyncClient(timeout=30) as client:
        details_response = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "contentDetails,statistics,snippet",
                "id": ",".join(video_ids),
                "key": settings.youtube_api_key,
            },
        )

    if details_response.status_code != 200:
        logger.warning("youtube_api_details_error", status=details_response.status_code)
        # Fall back to basic info without duration
        results = []
        for item in items:
            vid_id = item["id"]["videoId"]
            snippet = item["snippet"]
            results.append({
                "external_id": vid_id,
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "title": snippet.get("title"),
                "published_at": snippet.get("publishedAt"),
                "duration_s": None,
                "view_count": None,
            })
        return results

    details_map = {}
    for detail in details_response.json().get("items", []):
        details_map[detail["id"]] = detail

    results = []
    shorts_filtered = 0
    for item in items:
        vid_id = item["id"]["videoId"]
        snippet = item["snippet"]
        detail = details_map.get(vid_id, {})
        content = detail.get("contentDetails", {})
        stats = detail.get("statistics", {})

        # Parse ISO 8601 duration (PT1H2M3S)
        duration_s = _parse_iso_duration(content.get("duration", ""))

        # Filter out Shorts (videos under 60 seconds)
        if duration_s is not None and duration_s < 61:
            shorts_filtered += 1
            continue

        results.append({
            "external_id": vid_id,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "title": snippet.get("title"),
            "published_at": snippet.get("publishedAt"),
            "duration_s": duration_s,
            "view_count": int(stats["viewCount"]) if "viewCount" in stats else None,
        })

    logger.info(
        "channel_videos_listed",
        channel_id=channel_id,
        count=len(results),
        shorts_filtered=shorts_filtered,
    )
    return results


def _parse_iso_duration(iso: str) -> int | None:
    """Parse ISO 8601 duration like PT1H2M30S to seconds."""
    if not iso:
        return None
    import re
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not match:
        return None
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


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
