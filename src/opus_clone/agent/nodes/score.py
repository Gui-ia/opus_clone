import json
from pathlib import Path

from sqlalchemy import select

from opus_clone.agent.state import PipelineState
from opus_clone.clients.gpu_api import GpuApiClient
from opus_clone.db import get_db_session
from opus_clone.logging import get_logger
from opus_clone.models.db import Channel, SourceVideo, VideoStatus
from opus_clone.models.gpu_api import ChatCompletionRequest, ChatMessage

logger = get_logger("node.score")

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


async def score_node(state: PipelineState) -> PipelineState:
    """Use LLM to identify viral moments from transcript + analysis."""
    source_video_id = state["source_video_id"]
    transcript = state.get("transcript", {})
    analysis = state.get("analysis", {})

    logger.info("score_start", source_video_id=source_video_id)

    async with get_db_session() as session:
        result = await session.execute(select(SourceVideo).where(SourceVideo.id == source_video_id))
        video = result.scalar_one()
        video.status = VideoStatus.scoring

        channel_result = await session.execute(select(Channel).where(Channel.id == video.channel_id))
        channel = channel_result.scalar_one()
        max_clips = channel.max_clips_per_video
        min_score = channel.min_viral_score
        clip_durations = channel.preferred_clip_duration_s or [20, 70]

    # Load prompt template
    prompt_path = PROMPTS_DIR / "viral_selection.txt"
    system_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else _default_viral_prompt()

    # Build user message with transcript and analysis context
    segments_text = ""
    for seg in transcript.get("segments", []):
        start = seg.get("start", 0)
        end = seg.get("end", 0)
        speaker = seg.get("speaker", "")
        text = seg.get("text", "")
        segments_text += f"[{start:.1f}s - {end:.1f}s] {speaker}: {text}\n"

    heatmap_info = ""
    async with get_db_session() as session:
        result = await session.execute(select(SourceVideo).where(SourceVideo.id == source_video_id))
        v = result.scalar_one()
        if v.heatmap:
            heatmap_info = f"\n\nHeatmap (most-replayed parts):\n{json.dumps(v.heatmap[:20])}"

    # Build scenes summary from analysis
    scenes_summary = ""
    for scene in analysis.get("scenes", []):
        scenes_summary += f"  Scene {scene.get('scene_idx', 0)}: {scene.get('start_s', 0):.1f}s - {scene.get('end_s', 0):.1f}s ({scene.get('duration_s', 0):.1f}s)\n"

    # Count recurring faces (likely the main speakers)
    identities = analysis.get("identities", [])
    recurring_faces = [i for i in identities if i.get("detections", 0) >= 5]

    user_message = f"""Analyze this video transcript and identify the top {max_clips} most viral clip candidates.

Duration range per clip: {clip_durations[0]}s to {clip_durations[-1]}s
Minimum viral score: {min_score}/100

TRANSCRIPT:
{segments_text[:30000]}
{heatmap_info}

VIDEO ANALYSIS SUMMARY:
- Scenes detected: {len(analysis.get('scenes', []))}
- Recurring faces (main people): {len(recurring_faces)}
- Scene breakdown:
{scenes_summary[:3000]}

Return a JSON array of clip candidates. Each candidate:
{{
  "start_s": <float>,
  "end_s": <float>,
  "hook_text": "<the opening hook>",
  "viral_score": <int 0-100>,
  "confidence": <float 0-1>,
  "hook_type": "<curiosity|shock|contrarian|story|educational>",
  "category": "<string>",
  "rationale": "<why this moment is viral>"
}}

Return ONLY the JSON array, no other text."""

    gpu_client = GpuApiClient()

    # Self-consistency: 3 calls, aggregate results
    all_candidates = []
    for i in range(3):
        request = ChatCompletionRequest(
            messages=[
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_message),
            ],
            max_tokens=4000,
            temperature=0.7,
        )
        response = await gpu_client.chat_completions(request)

        if response.choices:
            content = response.choices[0].message.content
            try:
                # Extract JSON from response
                content = content.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                candidates = json.loads(content)
                if isinstance(candidates, list):
                    all_candidates.extend(candidates)
            except (json.JSONDecodeError, IndexError):
                logger.warning("score_parse_error", attempt=i, content=content[:200])

    # Deduplicate by temporal overlap (NMS with IoU >= 0.5)
    viral_candidates = _nms_temporal(all_candidates, iou_threshold=0.5)

    # Sort by viral_score and take top-K
    viral_candidates.sort(key=lambda c: c.get("viral_score", 0), reverse=True)
    viral_candidates = viral_candidates[:max_clips]

    logger.info(
        "score_complete",
        source_video_id=source_video_id,
        raw_candidates=len(all_candidates),
        final_candidates=len(viral_candidates),
    )

    return {
        **state,
        "viral_candidates": viral_candidates,
        "current_step": "build_edl",
    }


def _nms_temporal(candidates: list[dict], iou_threshold: float = 0.5) -> list[dict]:
    """Non-maximum suppression for temporal segments."""
    if not candidates:
        return []

    # Sort by score descending
    sorted_cands = sorted(candidates, key=lambda c: c.get("viral_score", 0), reverse=True)
    kept = []

    for cand in sorted_cands:
        start = cand.get("start_s", 0)
        end = cand.get("end_s", 0)
        overlap = False

        for existing in kept:
            e_start = existing.get("start_s", 0)
            e_end = existing.get("end_s", 0)
            intersection = max(0, min(end, e_end) - max(start, e_start))
            union = (end - start) + (e_end - e_start) - intersection
            if union > 0 and intersection / union >= iou_threshold:
                overlap = True
                break

        if not overlap:
            kept.append(cand)

    return kept


def _default_viral_prompt() -> str:
    return """You are an expert viral content analyst. Your job is to identify the most engaging, shareable moments from video transcripts.

Focus on:
1. Strong hooks (curiosity gaps, shocking statements, contrarian takes)
2. Emotional peaks (excitement, surprise, humor, controversy)
3. Self-contained stories or insights that work as standalone clips
4. Moments with high rewatch potential

Each clip must:
- Start with a hook that grabs attention in the first 2 seconds
- Be self-contained (makes sense without context)
- End on a satisfying note or cliffhanger
- Be between the specified duration range"""
