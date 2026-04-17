import httpx

from opus_clone.config import get_settings
from opus_clone.logging import get_logger

logger = get_logger("image_search")

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"


async def search_image(query: str) -> bytes | None:
    """Search for an image using Pexels API and return its bytes.

    Returns None if search fails or no results found.
    """
    settings = get_settings()
    api_key = settings.pexels_api_key

    if not api_key:
        logger.warning("image_search_not_configured", query=query)
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Search for photos on Pexels
            response = await client.get(
                PEXELS_SEARCH_URL,
                headers={"Authorization": api_key},
                params={
                    "query": query,
                    "per_page": 1,
                    "orientation": "portrait",
                    "size": "medium",
                },
            )
            response.raise_for_status()
            data = response.json()

            photos = data.get("photos", [])
            if not photos:
                logger.info("image_search_no_results", query=query)
                return None

            # Use the "large" size (940x650) — good quality for overlay
            image_url = photos[0].get("src", {}).get("large")
            if not image_url:
                return None

            # Download the image
            img_response = await client.get(image_url, follow_redirects=True, timeout=15)
            img_response.raise_for_status()

            logger.info("image_search_success", query=query, url=image_url, size=len(img_response.content))
            return img_response.content

    except Exception as e:
        logger.warning("image_search_error", query=query, error=str(e))
        return None
