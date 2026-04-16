from sqlalchemy import select

from opus_clone.agent.state import PipelineState
from opus_clone.clients.gpu_api import GpuApiClient
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import SourceVideo, VideoStatus
from opus_clone.services.minio import download_file

logger = get_logger("node.prepare")


async def prepare_node(state: PipelineState) -> PipelineState:
    """Upload source video to GPU API, get file_id."""
    source_video_id = state["source_video_id"]
    logger.info("prepare_start", source_video_id=source_video_id)

    async with get_db_session() as session:
        result = await session.execute(
            select(SourceVideo).where(SourceVideo.id == source_video_id)
        )
        video = result.scalar_one()
        minio_key = video.minio_key
        minio_bucket = video.minio_bucket
        channel_id = video.channel_id

    # Download from MinIO
    gpu_client = GpuApiClient()
    if gpu_client.mock:
        file_id = "mock-file-id-001"
    else:
        video_bytes = download_file(minio_bucket, minio_key)
        filename = minio_key.split("/")[-1]
        upload_result = await gpu_client.upload_file(video_bytes, filename)
        file_id = upload_result.file_id

    logger.info("prepare_uploaded", source_video_id=source_video_id, gpu_file_id=file_id)

    return {
        **state,
        "gpu_file_id": file_id,
        "channel_id": channel_id,
        "minio_key": minio_key,
        "current_step": "transcribe",
    }
