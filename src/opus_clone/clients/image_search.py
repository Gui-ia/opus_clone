import httpx

from opus_clone.config import get_settings
from opus_clone.logging import get_logger

logger = get_logger("image_search")

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


async def search_image(query: str) -> bytes | None:
    """Search for an image using Google Custom Search and return its bytes.

    Returns None if search fails or no results found.
    """
    settings = get_settings()
    api_key = settings.google_cse_api_key
    cse_id = settings.google_cse_id

    if not api_key or not cse_id:
        logger.warning("image_search_not_configured", query=query)
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # Search for images
            response = await client.get(
                GOOGLE_CSE_URL,
                params={
                    "key": api_key,
                    "cx": cse_id,
                    "q": query,
                    "searchType": "image",
                    "num": 1,
                    "imgSize": "large",
                    "safe": "active",
                },
            )
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                logger.info("image_search_no_results", query=query)
                return None

            image_url = items[0].get("link")
            if not image_url:
                return None

            # Download the image
            img_response = await client.get(image_url, follow_redirects=True, timeout=15)
            img_response.raise_for_status()

            content_type = img_response.headers.get("content-type", "")
            if not content_type.startswith("image/"):
                logger.warning("image_search_not_image", url=image_url, content_type=content_type)
                return None

            logger.info("image_search_success", query=query, url=image_url, size=len(img_response.content))
            return img_response.content

    except Exception as e:
        logger.warning("image_search_error", query=query, error=str(e))
        return None
