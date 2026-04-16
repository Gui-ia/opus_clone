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
            source_file_id=gpu_file_id,
            edl=edl,
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
                # Download rendered clip and upload to MinIO
                result_url = status.result_url or f"{settings.gpu_api_url}/outputs/{gpu_job_id}.mp4"
                clip_bytes = await gpu_client.download_output(f"{gpu_job_id}.mp4")

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
                    clip.error_message = status.error

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
