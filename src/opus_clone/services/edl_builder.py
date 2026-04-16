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

    # Build reframe tracks from active speaker timeline
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
    """Build reframe tracks from active speaker timeline."""
    timeline = analysis.get("active_speaker_timeline", [])
    tracks = []

    for entry in timeline:
        entry_start = entry.get("start_ms", 0)
        entry_end = entry.get("end_ms", 0)

        # Only include entries that overlap with our clip
        if entry_end <= start_ms or entry_start >= end_ms:
            continue

        bbox = entry.get("bbox_normalized", [0.5, 0.3, 0.2, 0.4])
        cx = bbox[0] + bbox[2] / 2 if len(bbox) >= 4 else 0.5
        cy = bbox[1] + bbox[3] / 2 if len(bbox) >= 4 else 0.4

        tracks.append(ReframeTrack(
            start_ms=max(entry_start, start_ms),
            end_ms=min(entry_end, end_ms),
            cx_ratio=cx,
            cy_ratio=cy,
            scale=1.0,
        ))

    # Fallback: center frame if no speaker data
    if not tracks:
        tracks.append(ReframeTrack(
            start_ms=start_ms,
            end_ms=end_ms,
            cx_ratio=0.5,
            cy_ratio=0.4,
            scale=1.0,
        ))

    return tracks


def _build_caption_words(transcript: dict, start_ms: int, end_ms: int) -> list[CaptionWord]:
    """Extract word-level captions within the clip range."""
    words = []
    for segment in transcript.get("segments", []):
        for word_data in segment.get("words", []):
            word_start_ms = int(word_data.get("start", 0) * 1000)
            word_end_ms = int(word_data.get("end", 0) * 1000)

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
