-- Opus Clone — Initial Schema
-- Apply: docker exec -i opus-postgres psql -U opus -d opus_clone < migrations/001_initial.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ========== CANAIS MONITORADOS ==========
CREATE TYPE platform_type AS ENUM ('youtube', 'instagram', 'tiktok');
CREATE TYPE source_type AS ENUM ('feed', 'stories', 'reels', 'shorts', 'video', 'live');

CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform platform_type NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    poll_interval_seconds INT DEFAULT 900,
    source_types source_type[] DEFAULT ARRAY['video']::source_type[],
    last_polled_at TIMESTAMPTZ,
    last_content_at TIMESTAMPTZ,
    pubsub_subscription_expires_at TIMESTAMPTZ,
    pubsub_secret VARCHAR(64),
    preferred_clip_duration_s INT[] DEFAULT ARRAY[20,70],
    min_viral_score INT DEFAULT 65,
    max_clips_per_video INT DEFAULT 8,
    style_preset VARCHAR(64) DEFAULT 'default',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(platform, external_id)
);
CREATE INDEX idx_channels_active_polled ON channels(is_active, last_polled_at) WHERE is_active;
CREATE INDEX idx_channels_platform_username ON channels(platform, username);

-- ========== VÍDEOS FONTE ==========
CREATE TYPE video_status AS ENUM (
    'discovered', 'downloading', 'downloaded',
    'transcribing', 'analyzing', 'scoring',
    'ready_to_clip', 'clipping',
    'completed', 'failed', 'skipped'
);

CREATE TABLE source_videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    external_id VARCHAR(255) NOT NULL,
    source_type source_type NOT NULL,
    url TEXT NOT NULL,
    title TEXT, description TEXT,
    published_at TIMESTAMPTZ,
    duration_s INT,
    view_count BIGINT, like_count BIGINT, comment_count BIGINT,
    heatmap JSONB,
    comments_with_timestamps JSONB,
    minio_bucket VARCHAR(64),
    minio_key TEXT,
    file_size_bytes BIGINT,
    width INT, height INT, fps NUMERIC(5,2),
    transcript_file_id VARCHAR(128),
    transcript_json JSONB,
    language_detected VARCHAR(8),
    speakers_count INT,
    scene_analysis JSONB,
    status video_status DEFAULT 'discovered',
    error_message TEXT,
    retry_count INT DEFAULT 0,
    discovered_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    UNIQUE(channel_id, external_id)
);
CREATE INDEX idx_source_status ON source_videos(status);
CREATE INDEX idx_source_channel_published ON source_videos(channel_id, published_at DESC);

-- ========== CLIPES GERADOS ==========
CREATE TYPE clip_status AS ENUM (
    'planned', 'rendering', 'ready',
    'approved', 'rejected',
    'publishing', 'published', 'failed'
);

CREATE TABLE clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_video_id UUID NOT NULL REFERENCES source_videos(id) ON DELETE CASCADE,
    start_ms INT NOT NULL,
    end_ms INT NOT NULL,
    duration_ms INT GENERATED ALWAYS AS (end_ms - start_ms) STORED,
    hook_text TEXT,
    transcript_slice JSONB,
    title_suggestion TEXT,
    description TEXT,
    hashtags TEXT[],
    viral_score NUMERIC(5,2),
    confidence NUMERIC(4,3),
    hook_type VARCHAR(64),
    category VARCHAR(64),
    target_audience VARCHAR(64),
    rationale TEXT,
    edl JSONB NOT NULL,
    render_job_id VARCHAR(128),
    minio_key TEXT,
    final_url TEXT,
    thumbnail_url TEXT,
    file_size_bytes BIGINT,
    published_to JSONB DEFAULT '[]'::jsonb,
    status clip_status DEFAULT 'planned',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    rendered_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ
);
CREATE INDEX idx_clips_source ON clips(source_video_id);
CREATE INDEX idx_clips_status ON clips(status);
CREATE INDEX idx_clips_viral_score ON clips(viral_score DESC) WHERE status = 'ready';

-- ========== JOBS (rastreamento de chamadas à API GPU) ==========
CREATE TYPE job_type AS ENUM (
    'transcribe', 'analyze_video', 'score_clips',
    'render_clip', 'generate_broll', 'generate_thumbnail',
    'generate_voiceover'
);
CREATE TYPE job_status AS ENUM (
    'queued', 'dispatched', 'processing',
    'completed', 'failed', 'timeout'
);

CREATE TABLE gpu_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_type job_type NOT NULL,
    source_video_id UUID REFERENCES source_videos(id) ON DELETE CASCADE,
    clip_id UUID REFERENCES clips(id) ON DELETE CASCADE,
    gpu_job_id VARCHAR(128),
    request_payload JSONB,
    response_payload JSONB,
    status job_status DEFAULT 'queued',
    error_message TEXT,
    retry_count INT DEFAULT 0,
    dispatched_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_gpu_jobs_status ON gpu_jobs(status);
CREATE INDEX idx_gpu_jobs_external ON gpu_jobs(gpu_job_id) WHERE gpu_job_id IS NOT NULL;

-- ========== STYLE PRESETS ==========
CREATE TABLE style_presets (
    name VARCHAR(64) PRIMARY KEY,
    captions_config JSONB NOT NULL,
    reframe_config JSONB NOT NULL,
    overlay_config JSONB NOT NULL,
    audio_config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========== VIRAL REFERENCE BANK (few-shot retrieval) ==========
CREATE TABLE viral_reference_clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform platform_type NOT NULL,
    url TEXT NOT NULL,
    transcript TEXT NOT NULL,
    hook_type VARCHAR(64),
    real_views BIGINT,
    real_engagement_rate NUMERIC(5,4),
    embedding vector(768),
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_viral_ref_embedding ON viral_reference_clips
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ========== PUBLISHING ACCOUNTS (OAuth) ==========
CREATE TABLE publishing_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform platform_type NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    access_token TEXT NOT NULL,
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    scopes TEXT[],
    metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========== TRIGGERS ==========
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_channels_updated BEFORE UPDATE ON channels
FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_publishing_accounts_updated BEFORE UPDATE ON publishing_accounts
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
