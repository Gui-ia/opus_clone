from typing import TypedDict


class PipelineState(TypedDict, total=False):
    source_video_id: str
    channel_id: str
    minio_key: str
    gpu_file_id: str | None
    transcript: dict | None
    analysis: dict | None
    viral_candidates: list[dict] | None
    clips: list[dict] | None
    edls: list[dict] | None
    render_job_ids: list[str] | None
    current_step: str
    error: str | None
