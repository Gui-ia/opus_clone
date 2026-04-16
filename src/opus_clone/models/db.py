import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ========== Enums ==========

class PlatformType(str, enum.Enum):
    youtube = "youtube"
    instagram = "instagram"
    tiktok = "tiktok"


class SourceType(str, enum.Enum):
    feed = "feed"
    stories = "stories"
    reels = "reels"
    shorts = "shorts"
    video = "video"
    live = "live"


class VideoStatus(str, enum.Enum):
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


class ClipStatus(str, enum.Enum):
    planned = "planned"
    rendering = "rendering"
    ready = "ready"
    approved = "approved"
    rejected = "rejected"
    publishing = "publishing"
    published = "published"
    failed = "failed"


class JobType(str, enum.Enum):
    transcribe = "transcribe"
    analyze_video = "analyze_video"
    score_clips = "score_clips"
    render_clip = "render_clip"
    generate_broll = "generate_broll"
    generate_thumbnail = "generate_thumbnail"
    generate_voiceover = "generate_voiceover"


class JobStatus(str, enum.Enum):
    queued = "queued"
    dispatched = "dispatched"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    timeout = "timeout"


# ========== Models ==========

class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    platform: Mapped[str] = mapped_column(Enum(PlatformType, name="platform_type"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    poll_interval_seconds: Mapped[int] = mapped_column(Integer, default=900)
    source_types: Mapped[list | None] = mapped_column(ARRAY(Enum(SourceType, name="source_type")), default=["video"])
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_content_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pubsub_subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pubsub_secret: Mapped[str | None] = mapped_column(String(64))
    preferred_clip_duration_s: Mapped[list | None] = mapped_column(ARRAY(Integer), default=[20, 70])
    min_viral_score: Mapped[int] = mapped_column(Integer, default=65)
    max_clips_per_video: Mapped[int] = mapped_column(Integer, default=8)
    style_preset: Mapped[str] = mapped_column(String(64), default="default")
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    source_videos: Mapped[list["SourceVideo"]] = relationship(back_populates="channel", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_channels_active_polled", "is_active", "last_polled_at", postgresql_where=is_active),
        Index("idx_channels_platform_username", "platform", "username"),
    )


class SourceVideo(Base):
    __tablename__ = "source_videos"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    channel_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(Enum(SourceType, name="source_type"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int | None] = mapped_column(BigInteger)
    like_count: Mapped[int | None] = mapped_column(BigInteger)
    comment_count: Mapped[int | None] = mapped_column(BigInteger)
    heatmap: Mapped[dict | None] = mapped_column(JSONB)
    comments_with_timestamps: Mapped[dict | None] = mapped_column(JSONB)
    minio_bucket: Mapped[str | None] = mapped_column(String(64))
    minio_key: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Numeric(5, 2))
    transcript_file_id: Mapped[str | None] = mapped_column(String(128))
    transcript_json: Mapped[dict | None] = mapped_column(JSONB)
    language_detected: Mapped[str | None] = mapped_column(String(8))
    speakers_count: Mapped[int | None] = mapped_column(Integer)
    scene_analysis: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Enum(VideoStatus, name="video_status"), default=VideoStatus.discovered)
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    channel: Mapped["Channel"] = relationship(back_populates="source_videos")
    clips: Mapped[list["Clip"]] = relationship(back_populates="source_video", cascade="all, delete-orphan")
    gpu_jobs: Mapped[list["GpuJob"]] = relationship(back_populates="source_video", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_source_status", "status"),
        Index("idx_source_channel_published", "channel_id", published_at.desc()),
    )


class Clip(Base):
    __tablename__ = "clips"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    source_video_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("source_videos.id", ondelete="CASCADE"), nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    hook_text: Mapped[str | None] = mapped_column(Text)
    transcript_slice: Mapped[dict | None] = mapped_column(JSONB)
    title_suggestion: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    hashtags: Mapped[list | None] = mapped_column(ARRAY(Text))
    viral_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    hook_type: Mapped[str | None] = mapped_column(String(64))
    category: Mapped[str | None] = mapped_column(String(64))
    target_audience: Mapped[str | None] = mapped_column(String(64))
    rationale: Mapped[str | None] = mapped_column(Text)
    edl: Mapped[dict] = mapped_column(JSONB, nullable=False)
    render_job_id: Mapped[str | None] = mapped_column(String(128))
    minio_key: Mapped[str | None] = mapped_column(Text)
    final_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    published_to: Mapped[dict | None] = mapped_column(JSONB, default=[])
    status: Mapped[str] = mapped_column(Enum(ClipStatus, name="clip_status"), default=ClipStatus.planned)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    rendered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source_video: Mapped["SourceVideo"] = relationship(back_populates="clips")
    gpu_jobs: Mapped[list["GpuJob"]] = relationship(back_populates="clip", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_clips_source", "source_video_id"),
        Index("idx_clips_status", "status"),
    )


class GpuJob(Base):
    __tablename__ = "gpu_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    job_type: Mapped[str] = mapped_column(Enum(JobType, name="job_type"), nullable=False)
    source_video_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("source_videos.id", ondelete="CASCADE"))
    clip_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("clips.id", ondelete="CASCADE"))
    gpu_job_id: Mapped[str | None] = mapped_column(String(128))
    request_payload: Mapped[dict | None] = mapped_column(JSONB)
    response_payload: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(Enum(JobStatus, name="job_status"), default=JobStatus.queued)
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_video: Mapped["SourceVideo | None"] = relationship(back_populates="gpu_jobs")
    clip: Mapped["Clip | None"] = relationship(back_populates="gpu_jobs")

    __table_args__ = (
        Index("idx_gpu_jobs_status", "status"),
    )


class StylePreset(Base):
    __tablename__ = "style_presets"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    captions_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reframe_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    overlay_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    audio_config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ViralReferenceClip(Base):
    __tablename__ = "viral_reference_clips"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    platform: Mapped[str] = mapped_column(Enum(PlatformType, name="platform_type"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    hook_type: Mapped[str | None] = mapped_column(String(64))
    real_views: Mapped[int | None] = mapped_column(BigInteger)
    real_engagement_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PublishingAccount(Base):
    __tablename__ = "publishing_accounts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    platform: Mapped[str] = mapped_column(Enum(PlatformType, name="platform_type"), nullable=False)
    account_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str | None] = mapped_column(Text)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list | None] = mapped_column(ARRAY(Text))
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, default={})
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
