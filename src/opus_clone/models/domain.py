from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ========== Enums ==========

class PlatformEnum(str, Enum):
    youtube = "youtube"
    instagram = "instagram"
    tiktok = "tiktok"


class SourceTypeEnum(str, Enum):
    feed = "feed"
    stories = "stories"
    reels = "reels"
    shorts = "shorts"
    video = "video"
    live = "live"


class VideoStatusEnum(str, Enum):
    discovered = "discovered"
    downloading = "downloading"
    downloaded = "downloaded"
    transcribing = "transcribing"
    analyzing = "analyzing"
    scoring = "scoring"
    ready_to_clip = "ready_to_clip"
    clipping = "clipping"
    completed = "completed"
    failed = "failed"
    skipped = "skipped"


class ClipStatusEnum(str, Enum):
    planned = "planned"
    rendering = "rendering"
    ready = "ready"
    approved = "approved"
    rejected = "rejected"
    publishing = "publishing"
    published = "published"
    failed = "failed"


# ========== Channel ==========

class ChannelCreate(BaseModel):
    platform: PlatformEnum
    external_id: str = Field(max_length=255)
    username: str = Field(max_length=255)
    display_name: str | None = None
    poll_interval_seconds: int = 900
    source_types: list[SourceTypeEnum] = [SourceTypeEnum.video]
    preferred_clip_duration_s: list[int] = [20, 70]
    min_viral_score: int = 65
    max_clips_per_video: int = 8
    style_preset: str = "default"


class ChannelUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    poll_interval_seconds: int | None = None
    source_types: list[SourceTypeEnum] | None = None
    min_viral_score: int | None = None
    max_clips_per_video: int | None = None
    style_preset: str | None = None


class ChannelResponse(BaseModel):
    id: str
    platform: PlatformEnum
    external_id: str
    username: str
    display_name: str | None
    is_active: bool
    poll_interval_seconds: int
    source_types: list[str] | None
    last_polled_at: datetime | None
    last_content_at: datetime | None
    min_viral_score: int
    max_clips_per_video: int
    style_preset: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========== Source Video ==========

class SourceVideoResponse(BaseModel):
    id: str
    channel_id: str
    external_id: str
    source_type: str
    url: str
    title: str | None
    published_at: datetime | None
    duration_s: int | None
    view_count: int | None
    status: VideoStatusEnum
    error_message: str | None
    retry_count: int
    discovered_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


# ========== Clip ==========

class ClipResponse(BaseModel):
    id: str
    source_video_id: str
    start_ms: int
    end_ms: int
    hook_text: str | None
    title_suggestion: str | None
    hashtags: list[str] | None
    viral_score: float | None
    confidence: float | None
    hook_type: str | None
    category: str | None
    rationale: str | None
    minio_key: str | None
    final_url: str | None
    thumbnail_url: str | None
    status: ClipStatusEnum
    created_at: datetime
    rendered_at: datetime | None
    approved_at: datetime | None

    model_config = {"from_attributes": True}


class ClipApproval(BaseModel):
    title: str | None = None
    description: str | None = None
    hashtags: list[str] | None = None
    schedule_at: datetime | None = None


# ========== Pagination ==========

class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
