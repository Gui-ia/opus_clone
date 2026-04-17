from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opus_clone.db import get_db
from opus_clone.logging import get_logger
from opus_clone.models.db import SourceVideo, VideoStatus
from opus_clone.models.domain import ProcessVideosRequest, ProcessVideosResponse, SourceVideoResponse

router = APIRouter(prefix="/api/videos", tags=["videos"])
logger = get_logger("videos")


@router.get("", response_model=list[SourceVideoResponse])
async def list_videos(
    channel_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SourceVideo)
    if channel_id:
        stmt = stmt.where(SourceVideo.channel_id == channel_id)
    if status:
        stmt = stmt.where(SourceVideo.status == status)
    stmt = stmt.order_by(SourceVideo.discovered_at.desc())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    videos = result.scalars().all()
    return [SourceVideoResponse.model_validate(v) for v in videos]


@router.post("/process", response_model=ProcessVideosResponse)
async def process_videos(body: ProcessVideosRequest, db: AsyncSession = Depends(get_db)):
    """Manually trigger processing for selected videos.

    Only videos with status=discovered will be queued for ingestion.
    Videos already processing or completed are skipped.
    """
    from opus_clone.workers.ingest import ingest_video

    queued: list[str] = []
    skipped: list[str] = []

    for vid_id in body.video_ids:
        result = await db.execute(
            select(SourceVideo).where(SourceVideo.id == vid_id)
        )
        video = result.scalar_one_or_none()
        if not video:
            skipped.append(vid_id)
            continue

        if video.status != VideoStatus.discovered.value:
            skipped.append(vid_id)
            continue

        try:
            ingest_video.send(str(video.id))
            queued.append(vid_id)
            logger.info("video_queued_for_processing", video_id=vid_id)
        except Exception as e:
            logger.warning("enqueue_failed", video_id=vid_id, error=str(e))
            skipped.append(vid_id)

    return ProcessVideosResponse(queued=queued, skipped=skipped)


@router.delete("/batch", status_code=200)
async def delete_videos(body: ProcessVideosRequest, db: AsyncSession = Depends(get_db)):
    """Delete multiple videos by ID."""
    deleted: list[str] = []
    not_found: list[str] = []

    for vid_id in body.video_ids:
        result = await db.execute(
            select(SourceVideo).where(SourceVideo.id == vid_id)
        )
        video = result.scalar_one_or_none()
        if not video:
            not_found.append(vid_id)
            continue

        await db.delete(video)
        deleted.append(vid_id)

    if deleted:
        await db.flush()
        logger.info("videos_deleted", count=len(deleted))

    return {"deleted": deleted, "not_found": not_found}


@router.get("/{video_id}", response_model=SourceVideoResponse)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return SourceVideoResponse.model_validate(video)
