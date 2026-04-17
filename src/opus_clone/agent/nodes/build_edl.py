import json
from pathlib import Path

from sqlalchemy import select

from opus_clone.agent.state import PipelineState
from opus_clone.clients.gpu_api import GpuApiClient
from opus_clone.clients.image_search import search_image
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import Clip, ClipStatus, SourceVideo, VideoStatus
from opus_clone.models.gpu_api import ChatCompletionRequest, ChatMessage
from opus_clone.services.edl_builder import build_edl

logger = get_logger("node.build_edl")

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


async def build_edl_node(state: PipelineState) -> PipelineState:
    """Build EDL for each viral candidate and insert clips into DB."""
    source_video_id = state["source_video_id"]
    viral_candidates = state.get("viral_candidates", [])
    transcript = state.get("transcript", {})
    analysis = state.get("analysis", {})

    logger.info("build_edl_start", source_video_id=source_video_id, candidates=len(viral_candidates))

    async with get_db_session() as session:
        result = await session.execute(select(SourceVideo).where(SourceVideo.id == source_video_id))
        video = result.scalar_one()
        video.status = VideoStatus.clipping

    gpu_client = GpuApiClient()
    edls = []
    clip_ids = []

    for i, candidate in enumerate(viral_candidates):
        # Build EDL from candidate
        edl = build_edl(candidate, transcript, analysis)
        edl_dict = edl.model_dump()

        # Process B-roll mentions: search images and upload to GPU API
        for mention in candidate.get("broll_mentions", []):
            query = mention.get("query", "")
            if not query:
                continue
            try:
                image_bytes = await search_image(query)
                if image_bytes:
                    upload_resp = await gpu_client.upload_file(image_bytes, f"broll_{query[:30]}.jpg")
                    edl_dict["broll_overlays"].append({
                        "start_ms": int(mention.get("time_s", 0) * 1000),
                        "end_ms": int((mention.get("time_s", 0) + mention.get("duration_s", 3)) * 1000),
                        "source_file_id": upload_resp.file_id,
                        "mode": "fullscreen",
                        "audio_duck_db": -6,
                    })
                    logger.info("broll_added", query=query, file_id=upload_resp.file_id)
            except Exception as e:
                logger.warning("broll_search_failed", query=query, error=str(e))

        # Generate title and hashtags via LLM
        title, hashtags = await _generate_metadata(gpu_client, candidate, transcript)

        # Insert clip into DB
        async with get_db_session() as session:
            clip = Clip(
                source_video_id=source_video_id,
                start_ms=edl.clip_start_ms,
                end_ms=edl.clip_end_ms,
                hook_text=candidate.get("hook_text"),
                viral_score=candidate.get("viral_score"),
                confidence=candidate.get("confidence"),
                hook_type=candidate.get("hook_type"),
                category=candidate.get("category"),
                rationale=candidate.get("rationale"),
                title_suggestion=title,
                hashtags=hashtags,
                edl=edl_dict,
                status=ClipStatus.planned,
            )

            # Build transcript slice for this clip
            clip.transcript_slice = _extract_transcript_slice(
                transcript, edl.clip_start_ms, edl.clip_end_ms
            )

            session.add(clip)
            await session.flush()
            clip_ids.append(str(clip.id))

        edls.append(edl_dict)
        logger.info(
            "clip_planned",
            clip_index=i,
            clip_id=clip_ids[-1],
            start_ms=edl.clip_start_ms,
            end_ms=edl.clip_end_ms,
            viral_score=candidate.get("viral_score"),
        )

    logger.info("build_edl_complete", source_video_id=source_video_id, clips_created=len(clip_ids))

    return {
        **state,
        "edls": edls,
        "clips": [{"id": cid} for cid in clip_ids],
        "current_step": "render",
    }


async def _generate_metadata(
    gpu_client: GpuApiClient,
    candidate: dict,
    transcript: dict,
) -> tuple[str, list[str]]:
    """Generate title and hashtags via LLM."""
    prompt_path = PROMPTS_DIR / "title_hashtags.txt"
    system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else (
        "Generate a catchy, viral title and 5-8 relevant hashtags for a short video clip. "
        "Return JSON: {\"title\": \"...\", \"hashtags\": [\"#...\", ...]}"
    )

    hook = candidate.get("hook_text", "")
    category = candidate.get("category", "")

    request = ChatCompletionRequest(
        messages=[
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(
                role="user",
                content=f"Hook: {hook}\nCategory: {category}\nRationale: {candidate.get('rationale', '')}",
            ),
        ],
        max_tokens=500,
        temperature=0.7,
    )

    try:
        response = await gpu_client.chat_completions(request)
        if response.choices:
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            data = json.loads(content)
            return data.get("title", hook), data.get("hashtags", [])
    except Exception:
        pass

    return hook or "Viral Clip", ["#viral", "#shorts", "#clips"]


def _extract_transcript_slice(transcript: dict, start_ms: int, end_ms: int) -> dict:
    """Extract transcript segments within clip range."""
    sliced_segments = []
    for seg in transcript.get("segments", []):
        seg_start_ms = int(seg.get("start", 0) * 1000)
        seg_end_ms = int(seg.get("end", 0) * 1000)
        if seg_end_ms <= start_ms or seg_start_ms >= end_ms:
            continue
        sliced_segments.append(seg)
    return {"segments": sliced_segments}
