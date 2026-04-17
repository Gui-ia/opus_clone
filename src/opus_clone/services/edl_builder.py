from opus_clone.logging import get_logger
from opus_clone.models.edl import (
    CaptionConfig,
    CaptionWord,
    EDL,
    OutputSpec,
    ReframeConfig,
    ReframeTrack,
    ZoomConfig,
)

logger = get_logger("edl_builder")


def build_edl(
    candidate: dict,
    transcript: dict,
    analysis: dict,
    style_preset: str = "default",
) -> EDL:
    """Build a complete EDL from a viral candidate, transcript, and analysis data."""
    start_s = candidate.get("start_s", 0)
    end_s = candidate.get("end_s", 60)
    start_ms = int(start_s * 1000)
    end_ms = int(end_s * 1000)

    # Build reframe tracks from face detections (dominant identity in clip range)
    reframe_tracks = _build_reframe_tracks(analysis, start_ms, end_ms)

    # Build caption words from transcript
    caption_words = _build_caption_words(transcript, start_ms, end_ms)

    # Detect zoom points at emotional peaks
    zooms = _detect_zoom_points(candidate, start_ms, end_ms)

    edl = EDL(
        clip_start_ms=start_ms,
        clip_end_ms=end_ms,
        output_spec=OutputSpec(),
        reframe=ReframeConfig(tracks=reframe_tracks),
        captions=CaptionConfig(words=caption_words),
        zooms=zooms,
    )

    return edl


def _build_reframe_tracks(analysis: dict, start_ms: int, end_ms: int) -> list[ReframeTrack]:
    """Build reframe tracks from face detections within the clip range.

    Strategy: find the dominant identity (most detections) in the clip's time range,
    then use their face bounding boxes to build reframe keyframes.
    Falls back to center frame if no face data.
    """
    start_s = start_ms / 1000.0
    end_s = end_ms / 1000.0

    # First try active_speaker if available
    active_speaker = analysis.get("active_speaker", [])
    if active_speaker:
        tracks = []
        for entry in active_speaker:
            entry_time = entry.get("time_s", 0)
            if entry_time < start_s or entry_time > end_s:
                continue
            bbox = entry.get("bbox", [0, 0, 0, 0])
            source_w = analysis.get("width", 1920)
            source_h = analysis.get("height", 1080)
            cx = ((bbox[0] + bbox[2]) / 2) / source_w if source_w else 0.5
            cy = ((bbox[1] + bbox[3]) / 2) / source_h if source_h else 0.4
            tracks.append(ReframeTrack(
                start_ms=int(entry_time * 1000),
                end_ms=int(entry_time * 1000) + 1000,
                cx_ratio=max(0.1, min(0.9, cx)),
                cy_ratio=max(0.1, min(0.9, cy)),
                scale=1.0,
            ))
        if tracks:
            return tracks

    # Fallback: use face detections to find dominant identity in clip range
    faces_in_range = [
        f for f in analysis.get("faces", [])
        if start_s <= f.get("time_s", 0) <= end_s
    ]

    if not faces_in_range:
        # No face data — center frame
        return [ReframeTrack(
            start_ms=start_ms, end_ms=end_ms,
            cx_ratio=0.5, cy_ratio=0.4, scale=1.0,
        )]

    # Find the most frequent identity in this clip range
    identity_counts: dict[int, int] = {}
    for f in faces_in_range:
        iid = f.get("identity_id", -1)
        identity_counts[iid] = identity_counts.get(iid, 0) + 1

    dominant_id = max(identity_counts, key=identity_counts.get)

    # Build reframe tracks from dominant identity's face positions
    source_w = analysis.get("width", 1920)
    source_h = analysis.get("height", 1080)
    tracks = []

    dominant_faces = [f for f in faces_in_range if f.get("identity_id") == dominant_id]
    for f in dominant_faces:
        bbox = f.get("bbox", [0, 0, 0, 0])
        time_s = f.get("time_s", 0)
        # bbox is [x1, y1, x2, y2] in pixel coords
        cx = ((bbox[0] + bbox[2]) / 2) / source_w if source_w else 0.5
        cy = ((bbox[1] + bbox[3]) / 2) / source_h if source_h else 0.4

        tracks.append(ReframeTrack(
            start_ms=int(time_s * 1000),
            end_ms=int(time_s * 1000) + 2000,  # Hold for 2s per keyframe
            cx_ratio=max(0.1, min(0.9, cx)),
            cy_ratio=max(0.1, min(0.9, cy)),
            scale=1.0,
        ))

    if not tracks:
        tracks.append(ReframeTrack(
            start_ms=start_ms, end_ms=end_ms,
            cx_ratio=0.5, cy_ratio=0.4, scale=1.0,
        ))

    return tracks


def _build_caption_words(transcript: dict, start_ms: int, end_ms: int) -> list[CaptionWord]:
    """Extract word-level captions within the clip range."""
    words = []
    for segment in transcript.get("segments", []):
        for word_data in segment.get("words", []):
            w_start = word_data.get("start")
            w_end = word_data.get("end")
            if w_start is None or w_end is None:
                continue

            word_start_ms = int(w_start * 1000)
            word_end_ms = int(w_end * 1000)

            if word_end_ms <= start_ms or word_start_ms >= end_ms:
                continue

            word_text = word_data.get("word", "").upper().strip()
            if not word_text:
                continue

            # Simple emphasis detection (keywords that tend to be viral)
            emphasis = _is_emphasis_word(word_text)

            words.append(CaptionWord(
                word=word_text,
                start_ms=word_start_ms,
                end_ms=word_end_ms,
                emphasis=emphasis,
                color="#FFD700" if emphasis else None,
            ))

    return words


def _detect_zoom_points(candidate: dict, start_ms: int, end_ms: int) -> list[ZoomConfig]:
    """Detect zoom points based on hook location and emotional peaks."""
    zooms = []

    # Zoom at the hook (first 3 seconds)
    hook_end = min(start_ms + 3000, end_ms)
    zooms.append(ZoomConfig(
        start_ms=start_ms,
        end_ms=hook_end,
        scale=1.12,
        ease="ease_in_out",
    ))

    # Zoom at midpoint (emotional peak estimate)
    mid = (start_ms + end_ms) // 2
    zooms.append(ZoomConfig(
        start_ms=mid - 1000,
        end_ms=mid + 1000,
        scale=1.10,
        ease="ease_in_out",
    ))

    return zooms


_EMPHASIS_WORDS = {
    "DINHEIRO", "MILHÃO", "MILHÕES", "RICO", "POBRE", "GRÁTIS", "GRATUITO",
    "SEGREDO", "NUNCA", "SEMPRE", "INCRÍVEL", "ABSURDO", "CHOCANTE",
    "PROIBIDO", "DESCOBRI", "VERDADE", "MENTIRA", "ERRO", "PERIGO",
    "URGENTE", "ATENÇÃO", "CUIDADO", "MUDOU", "TRIPLICOU", "DOBROU",
    "IMPOSSÍVEL", "FATURAMENTO", "LUCRO", "RESULTADO",
}


def _is_emphasis_word(word: str) -> bool:
    return word.strip(".,!?") in _EMPHASIS_WORDS
