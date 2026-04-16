import xml.etree.ElementTree as ET

from fastapi import APIRouter, Request, Response
from sqlalchemy import select

from opus_clone.config import get_settings
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import GpuJob, SourceVideo, VideoStatus
from opus_clone.models.gpu_api import RenderWebhook, TranscriptionWebhook, VideoAnalyzeWebhook
from opus_clone.services.hmac_webhook import verify_signature

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])
logger = get_logger("webhooks")

ATOM_NS = "http://www.w3.org/2005/Atom"
YT_NS = "http://www.youtube.com/xml/schemas/2015"


# ========== YouTube PubSubHubbub ==========

@router.get("/youtube-pubsub")
async def pubsub_verify(request: Request):
    """Hub verification — respond with hub.challenge."""
    params = request.query_params
    mode = params.get("hub.mode")
    challenge = params.get("hub.challenge", "")
    topic = params.get("hub.topic", "")
    logger.info("pubsub_verify", mode=mode, topic=topic)
    if mode == "subscribe":
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=404)


@router.post("/youtube-pubsub")
async def pubsub_notification(request: Request):
    """Receive YouTube PubSubHubbub Atom notification."""
    body = await request.body()
    logger.info("pubsub_notification_received", size=len(body))

    try:
        root = ET.fromstring(body)
        entries = root.findall(f"{{{ATOM_NS}}}entry")

        for entry in entries:
            video_id_el = entry.find(f"{{{YT_NS}}}videoId")
            channel_id_el = entry.find(f"{{{YT_NS}}}channelId")
            title_el = entry.find(f"{{{ATOM_NS}}}title")
            published_el = entry.find(f"{{{ATOM_NS}}}published")

            if video_id_el is None or channel_id_el is None:
                continue

            video_id = video_id_el.text
            channel_ext_id = channel_id_el.text
            title = title_el.text if title_el is not None else None
            published = published_el.text if published_el is not None else None

            logger.info(
                "pubsub_new_video",
                video_id=video_id,
                channel_id=channel_ext_id,
                title=title,
            )

            async with get_db_session() as session:
                # Find channel
                from opus_clone.models.db import Channel, PlatformType

                stmt = select(Channel).where(
                    Channel.platform == PlatformType.youtube,
                    Channel.external_id == channel_ext_id,
                    Channel.is_active.is_(True),
                )
                result = await session.execute(stmt)
                channel = result.scalar_one_or_none()

                if not channel:
                    logger.warning("pubsub_unknown_channel", channel_id=channel_ext_id)
                    continue

                # Dedup check
                existing = await session.execute(
                    select(SourceVideo).where(
                        SourceVideo.channel_id == channel.id,
                        SourceVideo.external_id == video_id,
                    )
                )
                if existing.scalar_one_or_none():
                    logger.info("pubsub_duplicate", video_id=video_id)
                    continue

                # Insert new source video
                from opus_clone.models.db import SourceType

                video = SourceVideo(
                    channel_id=channel.id,
                    external_id=video_id,
                    source_type=SourceType.video,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    title=title,
                    status=VideoStatus.discovered,
                )
                session.add(video)
                await session.flush()

                logger.info("pubsub_video_created", video_id=video.id, external_id=video_id)

                # Enqueue ingest job
                try:
                    from opus_clone.workers.ingest import ingest_video
                    ingest_video.send(str(video.id))
                except Exception:
                    logger.warning("pubsub_enqueue_failed", video_id=video.id)

    except ET.ParseError:
        logger.error("pubsub_xml_parse_error")

    return Response(status_code=200)


# ========== GPU Webhooks ==========

async def _verify_gpu_webhook(request: Request) -> bytes | None:
    settings = get_settings()
    body = await request.body()
    signature = request.headers.get("X-Signature", "")
    if settings.webhook_shared_secret and not verify_signature(body, signature, settings.webhook_shared_secret):
        logger.warning("webhook_signature_invalid")
        return None
    return body


@router.post("/asr")
async def webhook_asr(request: Request):
    """Receive transcription completion from GPU."""
    body = await _verify_gpu_webhook(request)
    if body is None:
        return Response(status_code=401)

    payload = TranscriptionWebhook.model_validate_json(body)
    logger.info("webhook_asr", job_id=payload.job_id, status=payload.status)

    async with get_db_session() as session:
        result = await session.execute(
            select(GpuJob).where(GpuJob.gpu_job_id == payload.job_id)
        )
        job = result.scalar_one_or_none()
        if job:
            from opus_clone.models.db import JobStatus
            job.status = JobStatus.completed if payload.status == "completed" else JobStatus.failed
            job.response_payload = payload.model_dump()
            if payload.error:
                job.error_message = payload.error

    return Response(status_code=200)


@router.post("/analyze")
async def webhook_analyze(request: Request):
    """Receive video analysis completion from GPU."""
    body = await _verify_gpu_webhook(request)
    if body is None:
        return Response(status_code=401)

    payload = VideoAnalyzeWebhook.model_validate_json(body)
    logger.info("webhook_analyze", job_id=payload.job_id, status=payload.status)

    async with get_db_session() as session:
        result = await session.execute(
            select(GpuJob).where(GpuJob.gpu_job_id == payload.job_id)
        )
        job = result.scalar_one_or_none()
        if job:
            from opus_clone.models.db import JobStatus
            job.status = JobStatus.completed if payload.status == "completed" else JobStatus.failed
            job.response_payload = payload.model_dump()

    return Response(status_code=200)


@router.post("/render")
async def webhook_render(request: Request):
    """Receive render completion from GPU."""
    body = await _verify_gpu_webhook(request)
    if body is None:
        return Response(status_code=401)

    payload = RenderWebhook.model_validate_json(body)
    logger.info("webhook_render", job_id=payload.job_id, status=payload.status)

    async with get_db_session() as session:
        result = await session.execute(
            select(GpuJob).where(GpuJob.gpu_job_id == payload.job_id)
        )
        job = result.scalar_one_or_none()
        if job:
            from opus_clone.models.db import JobStatus
            job.status = JobStatus.completed if payload.status == "completed" else JobStatus.failed
            job.response_payload = payload.model_dump()

    return Response(status_code=200)
