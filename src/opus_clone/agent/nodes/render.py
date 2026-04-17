import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from opus_clone.agent.state import PipelineState
from opus_clone.clients.gpu_api import GpuApiClient
from opus_clone.config import get_settings
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import Clip, ClipStatus, GpuJob, JobStatus, JobType, SourceVideo, VideoStatus
from opus_clone.models.gpu_api import RenderRequest
from opus_clone.services.minio import upload_file

logger = get_logger("node.render")


def _edl_to_render_api(edl: dict, gpu_file_id: str) -> dict:
    """Convert internal EDL format to the render API's expected EDL format.

    Internal EDL has: clip_start_ms, clip_end_ms, output_spec, captions (word-level), reframe, zooms
    Render API expects: clips (file_id + in_point/out_point), output, captions (timed text), loudnorm
    """
    start_ms = edl.get("clip_start_ms", 0)
    end_ms = edl.get("clip_end_ms", 0)
    output_spec = edl.get("output_spec", {})

    # Build clips array — single clip from the source video
    clips = [{
        "file_id": gpu_file_id,
        "in_point": start_ms / 1000.0,
        "out_point": end_ms / 1000.0,
        "volume": 1.0,
    }]

    # Build output spec
    output = {
        "width": output_spec.get("width", 1080),
        "height": output_spec.get("height", 1920),
        "fps": output_spec.get("fps", 30),
        "video_codec": output_spec.get("codec", "h264_nvenc"),
    }

    # Convert word-level captions to timed text segments
    captions_config = edl.get("captions", {})
    caption_words = captions_config.get("words", [])
    captions = _words_to_caption_segments(caption_words, start_ms)

    # Reframe config (if tracks exist, pass as-is for the render worker)
    reframe = edl.get("reframe", {})

    # Zooms
    zooms = edl.get("zooms", [])

    # Loudnorm
    loudnorm_spec = output_spec.get("loudnorm", {})
    loudnorm = {
        "enabled": True,
        "target_i": loudnorm_spec.get("I", -14.0),
        "target_lra": loudnorm_spec.get("LRA", 9.0),
        "target_tp": loudnorm_spec.get("TP", -1.0),
    }

    render_edl = {
        "output": output,
        "clips": clips,
        "loudnorm": loudnorm,
    }

    if captions:
        render_edl["captions"] = captions

    # Pass only reframe tracks (keyframes), not the full config
    reframe_tracks = reframe.get("tracks", [])
    if reframe_tracks:
        render_edl["reframe"] = [
            {
                "start": t.get("start_ms", 0) / 1000.0,
                "end": t.get("end_ms", 0) / 1000.0,
                "cx": t.get("cx_ratio", 0.5),
                "cy": t.get("cy_ratio", 0.4),
                "scale": t.get("scale", 1.0),
            }
            for t in reframe_tracks
        ]

    return render_edl


def _words_to_caption_segments(words: list[dict], clip_start_ms: int) -> list[dict]:
    """Group word-level captions into timed text segments (max 3 words per line)."""
    if not words:
        return []

    max_words = 3
    segments = []
    current_words = []
    current_start = None

    for w in words:
        word_text = w.get("word", "").strip()
        if not word_text:
            continue

        w_start = w.get("start_ms", 0)
        w_end = w.get("end_ms", 0)

        if current_start is None:
            current_start = w_start

        current_words.append(word_text)

        if len(current_words) >= max_words:
            seg_start = max(0, (current_start - clip_start_ms) / 1000.0)
            seg_end = max(seg_start + 0.1, (w_end - clip_start_ms) / 1000.0)
            segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": " ".join(current_words),
            })
            current_words = []
            current_start = None

    # Flush remaining words
    if current_words:
        last_end = words[-1].get("end_ms", 0) if words else 0
        seg_start = max(0, (current_start - clip_start_ms) / 1000.0)
        seg_end = max(seg_start + 0.1, (last_end - clip_start_ms) / 1000.0)
        segments.append({
            "start": seg_start,
            "end": seg_end,
            "text": " ".join(current_words),
        })

    return segments


async def render_node(state: PipelineState) -> PipelineState:
    """Dispatch render jobs for all planned clips and wait for completion."""
    source_video_id = state["source_video_id"]
    gpu_file_id = state["gpu_file_id"]
    clips_data = state.get("clips", [])
    settings = get_settings()

    logger.info("render_start", source_video_id=source_video_id, clips=len(clips_data))

    gpu_client = GpuApiClient()
    render_jobs = []  # (clip_id, gpu_job_id, db_job_id)

    for clip_data in clips_data:
        clip_id = clip_data["id"]

        async with get_db_session() as session:
            result = await session.execute(select(Clip).where(Clip.id == clip_id))
            clip = result.scalar_one()
            clip.status = ClipStatus.rendering
            edl = clip.edl

        # Convert internal EDL to render API format
        render_edl = _edl_to_render_api(edl, gpu_file_id)

        # Create GPU job record
        async with get_db_session() as session:
            job = GpuJob(
                job_type=JobType.render_clip,
                source_video_id=source_video_id,
                clip_id=clip_id,
                status=JobStatus.dispatched,
                dispatched_at=datetime.now(timezone.utc),
            )
            session.add(job)
            await session.flush()
            db_job_id = job.id

        # Dispatch render
        request = RenderRequest(
            edl=render_edl,
            webhook_url=f"{settings.app_base_url}/v1/webhooks/render",
        )
        gpu_job_id = await gpu_client.render_video(request)

        async with get_db_session() as session:
            result = await session.execute(select(GpuJob).where(GpuJob.id == db_job_id))
            job = result.scalar_one()
            job.gpu_job_id = gpu_job_id

        async with get_db_session() as session:
            result = await session.execute(select(Clip).where(Clip.id == clip_id))
            clip = result.scalar_one()
            clip.render_job_id = gpu_job_id

        render_jobs.append((clip_id, gpu_job_id, db_job_id))
        logger.info("render_dispatched", clip_id=clip_id, gpu_job_id=gpu_job_id)

    # Poll all render jobs for completion
    completed = set()
    for attempt in range(120):  # Max 20 min
        if len(completed) == len(render_jobs):
            break

        await asyncio.sleep(10)

        for clip_id, gpu_job_id, db_job_id in render_jobs:
            if clip_id in completed:
                continue

            status = await gpu_client.get_job_status("video/render", gpu_job_id)

            if status.status == "completed":
                # Download rendered clip
                result_url = status.result_url or f"/outputs/{gpu_job_id}.mp4"
                clip_bytes = await gpu_client.download_output(result_url)

                minio_key = f"clips/{source_video_id}/{clip_id}.mp4"
                upload_file(settings.minio_bucket_clips, minio_key, clip_bytes, "video/mp4")

                # Update clip
                async with get_db_session() as session:
                    result = await session.execute(select(Clip).where(Clip.id == clip_id))
                    clip = result.scalar_one()
                    clip.status = ClipStatus.ready
                    clip.minio_key = minio_key
                    clip.file_size_bytes = len(clip_bytes)
                    clip.rendered_at = datetime.now(timezone.utc)

                # Update GPU job
                async with get_db_session() as session:
                    result = await session.execute(select(GpuJob).where(GpuJob.id == db_job_id))
                    job = result.scalar_one()
                    job.status = JobStatus.completed
                    job.completed_at = datetime.now(timezone.utc)

                completed.add(clip_id)
                logger.info("render_complete", clip_id=clip_id, minio_key=minio_key)

            elif status.status == "failed":
                async with get_db_session() as session:
                    result = await session.execute(select(Clip).where(Clip.id == clip_id))
                    clip = result.scalar_one()
                    clip.status = ClipStatus.failed

                completed.add(clip_id)
                logger.error("render_failed", clip_id=clip_id, error=status.error)

    # Mark source video as completed
    async with get_db_session() as session:
        result = await session.execute(select(SourceVideo).where(SourceVideo.id == source_video_id))
        video = result.scalar_one()
        video.status = VideoStatus.completed
        video.completed_at = datetime.now(timezone.utc)

    render_job_ids = [gid for _, gid, _ in render_jobs]
    logger.info(
        "render_all_complete",
        source_video_id=source_video_id,
        total=len(render_jobs),
        completed=len(completed),
    )

    return {
        **state,
        "render_job_ids": render_job_ids,
        "current_step": "done",
    }
