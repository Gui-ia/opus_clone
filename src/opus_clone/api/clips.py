from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opus_clone.config import get_settings
from opus_clone.db import get_db
from opus_clone.logging import get_logger
from opus_clone.models.db import Clip, ClipStatus
from opus_clone.models.domain import ClipApproval, ClipResponse

router = APIRouter(prefix="/api/clips", tags=["clips"])
logger = get_logger("clips")


@router.get("", response_model=list[ClipResponse])
async def list_clips(
    source_video_id: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Clip)
    if source_video_id:
        stmt = stmt.where(Clip.source_video_id == source_video_id)
    if status:
        stmt = stmt.where(Clip.status == status)
    stmt = stmt.order_by(Clip.viral_score.desc().nulls_last())
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    clips = result.scalars().all()
    return [ClipResponse.model_validate(c) for c in clips]


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(clip_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = result.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return ClipResponse.model_validate(clip)


@router.patch("/{clip_id}/approve", response_model=ClipResponse)
async def approve_clip(clip_id: str, data: ClipApproval | None = None, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = result.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    if clip.status not in (ClipStatus.ready, ClipStatus.rejected):
        raise HTTPException(status_code=400, detail=f"Cannot approve clip with status '{clip.status}'")

    clip.status = ClipStatus.approved
    clip.approved_at = datetime.now(timezone.utc)
    if data:
        if data.title:
            clip.title_suggestion = data.title
        if data.description:
            clip.description = data.description
        if data.hashtags:
            clip.hashtags = data.hashtags

    logger.info("clip_approved", clip_id=clip_id)
    return ClipResponse.model_validate(clip)


@router.get("/{clip_id}/stream")
async def stream_clip(clip_id: str, db: AsyncSession = Depends(get_db)):
    """Get a presigned URL to stream/download the rendered clip."""
    from fastapi.responses import RedirectResponse
    from opus_clone.services.minio import generate_presigned_get

    result = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = result.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    if not clip.minio_key:
        raise HTTPException(status_code=404, detail="Clip not rendered yet")

    config = get_settings()
    url = generate_presigned_get(config.minio_bucket_clips, clip.minio_key, expires=3600)
    return RedirectResponse(url=url)


@router.patch("/{clip_id}/reject", response_model=ClipResponse)
async def reject_clip(clip_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Clip).where(Clip.id == clip_id))
    clip = result.scalar_one_or_none()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    clip.status = ClipStatus.rejected
    logger.info("clip_rejected", clip_id=clip_id)
    return ClipResponse.model_validate(clip)
