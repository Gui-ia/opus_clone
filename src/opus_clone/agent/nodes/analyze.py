import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from opus_clone.agent.state import PipelineState
from opus_clone.clients.gpu_api import GpuApiClient
from opus_clone.config import get_settings
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import GpuJob, JobStatus, JobType, SourceVideo, VideoStatus
from opus_clone.models.gpu_api import VideoAnalyzeRequest

logger = get_logger("node.analyze")


async def analyze_node(state: PipelineState) -> PipelineState:
    """Dispatch video analysis and poll until complete."""
    source_video_id = state["source_video_id"]
    gpu_file_id = state["gpu_file_id"]
    settings = get_settings()

    logger.info("analyze_start", source_video_id=source_video_id)

    async with get_db_session() as session:
        result = await session.execute(select(SourceVideo).where(SourceVideo.id == source_video_id))
        video = result.scalar_one()
        video.status = VideoStatus.analyzing

    gpu_client = GpuApiClient()

    # Create GPU job record
    async with get_db_session() as session:
        job = GpuJob(
            job_type=JobType.analyze_video,
            source_video_id=source_video_id,
            status=JobStatus.dispatched,
            dispatched_at=datetime.now(timezone.utc),
        )
        session.add(job)
        await session.flush()
        job_db_id = job.id

    # Dispatch analysis
    request = VideoAnalyzeRequest(
        file_id=gpu_file_id,
        webhook_url=f"{settings.app_base_url}/v1/webhooks/analyze",
    )
    gpu_job_id = await gpu_client.analyze_video(request)

    async with get_db_session() as session:
        result = await session.execute(select(GpuJob).where(GpuJob.id == job_db_id))
        job = result.scalar_one()
        job.gpu_job_id = gpu_job_id

    # Poll for completion
    analysis_result = None
    for attempt in range(60):
        await asyncio.sleep(10)
        status = await gpu_client.get_job_status("video/analyze", gpu_job_id)

        if status.status == "completed":
            analysis_result = await gpu_client.get_analysis_result(
                status.result_url or f"{settings.gpu_api_url}/outputs/{gpu_job_id}.json"
            )
            break
        elif status.status == "failed":
            raise RuntimeError(f"Analysis failed: {status.error}")

    if analysis_result is None:
        raise RuntimeError("Analysis timed out")

    analysis_dict = analysis_result.model_dump()
    async with get_db_session() as session:
        result = await session.execute(select(SourceVideo).where(SourceVideo.id == source_video_id))
        video = result.scalar_one()
        video.scene_analysis = analysis_dict

    async with get_db_session() as session:
        result = await session.execute(select(GpuJob).where(GpuJob.id == job_db_id))
        job = result.scalar_one()
        job.status = JobStatus.completed
        job.completed_at = datetime.now(timezone.utc)

    logger.info(
        "analyze_complete",
        source_video_id=source_video_id,
        scenes=len(analysis_result.scenes),
        faces=len(analysis_result.faces),
    )

    return {
        **state,
        "analysis": analysis_dict,
        "current_step": "score",
    }
