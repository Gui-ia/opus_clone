import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from opus_clone.agent.state import PipelineState
from opus_clone.clients.gpu_api import GpuApiClient
from opus_clone.config import get_settings
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import GpuJob, JobStatus, JobType, SourceVideo, VideoStatus
from opus_clone.models.gpu_api import TranscriptionRequest

logger = get_logger("node.transcribe")


async def transcribe_node(state: PipelineState) -> PipelineState:
    """Dispatch transcription and poll until complete."""
    source_video_id = state["source_video_id"]
    gpu_file_id = state["gpu_file_id"]
    settings = get_settings()

    logger.info("transcribe_start", source_video_id=source_video_id)

    # Update status
    async with get_db_session() as session:
        result = await session.execute(select(SourceVideo).where(SourceVideo.id == source_video_id))
        video = result.scalar_one()
        video.status = VideoStatus.transcribing

    gpu_client = GpuApiClient()

    # Create GPU job record
    async with get_db_session() as session:
        job = GpuJob(
            job_type=JobType.transcribe,
            source_video_id=source_video_id,
            status=JobStatus.dispatched,
            dispatched_at=datetime.now(timezone.utc),
        )
        session.add(job)
        await session.flush()
        job_db_id = job.id

    # Dispatch transcription
    request = TranscriptionRequest(
        file_id=gpu_file_id,
        language="pt",
        diarize=True,
        word_timestamps=True,
        webhook_url=f"{settings.app_base_url}/v1/webhooks/asr",
    )
    gpu_job_id = await gpu_client.transcribe(request)

    # Update job with external ID
    async with get_db_session() as session:
        result = await session.execute(select(GpuJob).where(GpuJob.id == job_db_id))
        job = result.scalar_one()
        job.gpu_job_id = gpu_job_id

    # Poll for completion
    transcript_result = None
    for attempt in range(60):  # Max 10 min (60 * 10s)
        await asyncio.sleep(10)
        status = await gpu_client.get_job_status("audio/transcriptions", gpu_job_id)

        if status.status == "completed":
            transcript_result = await gpu_client.get_transcription_result(
                status.result_url or f"{settings.gpu_api_url}/outputs/{gpu_job_id}.json"
            )
            break
        elif status.status == "failed":
            raise RuntimeError(f"Transcription failed: {status.error}")

    if transcript_result is None:
        raise RuntimeError("Transcription timed out")

    # Store transcript in DB
    transcript_dict = transcript_result.model_dump()
    async with get_db_session() as session:
        result = await session.execute(select(SourceVideo).where(SourceVideo.id == source_video_id))
        video = result.scalar_one()
        video.transcript_json = transcript_dict
        video.language_detected = transcript_result.language
        video.speakers_count = len(transcript_result.speakers)

    # Update GPU job
    async with get_db_session() as session:
        result = await session.execute(select(GpuJob).where(GpuJob.id == job_db_id))
        job = result.scalar_one()
        job.status = JobStatus.completed
        job.completed_at = datetime.now(timezone.utc)

    logger.info(
        "transcribe_complete",
        source_video_id=source_video_id,
        segments=len(transcript_result.segments),
        speakers=len(transcript_result.speakers),
    )

    return {
        **state,
        "transcript": transcript_dict,
        "current_step": "analyze",
    }
