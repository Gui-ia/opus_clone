from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opus_clone.db import get_db
from opus_clone.models.db import SourceVideo
from opus_clone.models.domain import SourceVideoResponse

router = APIRouter(prefix="/api/videos", tags=["videos"])


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


@router.get("/{video_id}", response_model=SourceVideoResponse)
async def get_video(video_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SourceVideo).where(SourceVideo.id == video_id))
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
    return SourceVideoResponse.model_validate(video)
