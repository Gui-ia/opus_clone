from datetime import datetime

import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from opus_clone.config import get_settings
from opus_clone.logging import get_logger

logger = get_logger("scraper_agent")


class VideoInfo(BaseModel):
    external_id: str
    url: str
    title: str | None = None
    published_at: datetime | None = None
    duration_s: int | None = None
    view_count: int | None = None


class DownloadResult(BaseModel):
    status: str
    duration_s: int | None = None
    bytes_uploaded: int | None = None
    video_key: str | None = None
    info_json_key: str | None = None
    heatmap: list | None = None
    title: str | None = None
    description: str | None = None
    published_at: datetime | None = None
    view_count: int | None = None
    like_count: int | None = None


class RetryableScraperError(Exception):
    pass


class ScraperAgentClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.scraper_agent_url
        self.mock = self.settings.scraper_agent_mock

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.settings.scraper_agent_token}"},
            timeout=httpx.Timeout(self.settings.scraper_agent_timeout_s),
        )

    async def _handle_response(self, response: httpx.Response) -> dict:
        if response.status_code >= 500:
            raise RetryableScraperError(f"Scraper {response.status_code}")
        response.raise_for_status()
        return response.json()

    async def check_health(self) -> bool:
        if self.mock:
            return True
        try:
            async with self._client() as client:
                response = await client.get("/health")
                return response.status_code == 200
        except Exception:
            return False

    @retry(
        retry=retry_if_exception_type(RetryableScraperError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=10, max=120),
    )
    async def download_youtube(
        self,
        url: str,
        minio_presigned_put_url: str,
        minio_presigned_info_url: str | None = None,
        format_: str = "best[ext=mp4][height<=1080]/best[height<=1080]",
        extract_heatmap: bool = True,
    ) -> DownloadResult:
        if self.mock:
            return DownloadResult(
                status="completed",
                duration_s=1800,
                bytes_uploaded=150_000_000,
                video_key="raw/mock-video.mp4",
                info_json_key="raw/mock-video.info.json",
                heatmap=[[0.01, 0.3], [0.02, 0.5], [0.03, 0.8]],
                title="Mock Video Title",
                description="Mock description",
                view_count=50000,
                like_count=2000,
            )

        async with self._client() as client:
            payload = {
                "url": url,
                "minio_presigned_put_url": minio_presigned_put_url,
                "format": format_,
                "extract_heatmap": extract_heatmap,
            }
            if minio_presigned_info_url:
                payload["minio_presigned_info_url"] = minio_presigned_info_url
            payload["write_info_json"] = minio_presigned_info_url is not None

            response = await client.post("/yt/download", json=payload)
            data = await self._handle_response(response)
            return DownloadResult(**data)

    @retry(
        retry=retry_if_exception_type(RetryableScraperError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=10, max=60),
    )
    async def get_channel_latest(self, channel_id: str) -> list[VideoInfo]:
        if self.mock:
            return [
                VideoInfo(
                    external_id="mock_vid_001",
                    url="https://www.youtube.com/watch?v=mock001",
                    title="Mock Latest Video",
                    duration_s=1800,
                    view_count=10000,
                ),
            ]

        async with self._client() as client:
            response = await client.post(f"/yt/channel/{channel_id}/latest")
            data = await self._handle_response(response)
            return [VideoInfo(**v) for v in data.get("videos", data if isinstance(data, list) else [])]

    @retry(
        retry=retry_if_exception_type(RetryableScraperError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=10, max=60),
    )
    async def get_ig_posts(self, username: str) -> list[VideoInfo]:
        if self.mock:
            return []
        async with self._client() as client:
            response = await client.post(f"/ig/user/{username}/posts")
            data = await self._handle_response(response)
            return [VideoInfo(**v) for v in data.get("posts", [])]

    @retry(
        retry=retry_if_exception_type(RetryableScraperError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=10, max=60),
    )
    async def get_ig_stories(self, username: str) -> list[VideoInfo]:
        if self.mock:
            return []
        async with self._client() as client:
            response = await client.post(f"/ig/user/{username}/stories")
            data = await self._handle_response(response)
            return [VideoInfo(**v) for v in data.get("stories", [])]

    @retry(
        retry=retry_if_exception_type(RetryableScraperError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=10, max=60),
    )
    async def get_tk_videos(self, username: str) -> list[VideoInfo]:
        if self.mock:
            return []
        async with self._client() as client:
            response = await client.post(f"/tk/user/{username}/videos")
            data = await self._handle_response(response)
            return [VideoInfo(**v) for v in data.get("videos", [])]
