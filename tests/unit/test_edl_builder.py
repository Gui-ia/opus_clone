import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_build_edl_basic():
    """EDL builder creates valid EDL from candidate + transcript + analysis."""
    from opus_clone.services.edl_builder import build_edl

    transcript = json.loads((FIXTURES / "sample_transcript.json").read_text())
    analysis = json.loads((FIXTURES / "sample_analyze.json").read_text())

    candidate = {
        "start_s": 0.0,
        "end_s": 22.5,
        "hook_text": "Hoje a gente vai falar sobre algo que mudou minha vida",
        "viral_score": 85,
        "confidence": 0.9,
        "hook_type": "curiosity",
        "category": "business",
        "rationale": "Strong hook with personal transformation",
    }

    edl = build_edl(candidate, transcript, analysis)

    assert edl.clip_start_ms == 0
    assert edl.clip_end_ms == 22500
    assert edl.output_spec.width == 1080
    assert edl.output_spec.height == 1920
    assert edl.output_spec.codec == "h264_nvenc"
    assert len(edl.reframe.tracks) > 0
    assert len(edl.captions.words) > 0
    assert len(edl.zooms) > 0


def test_build_edl_reframe_tracks():
    """Reframe tracks are correctly derived from active speaker timeline."""
    from opus_clone.services.edl_builder import build_edl

    transcript = json.loads((FIXTURES / "sample_transcript.json").read_text())
    analysis = json.loads((FIXTURES / "sample_analyze.json").read_text())

    candidate = {"start_s": 0.0, "end_s": 12.5}
    edl = build_edl(candidate, transcript, analysis)

    for track in edl.reframe.tracks:
        assert track.start_ms >= 0
        assert track.end_ms <= 12500
        assert 0 <= track.cx_ratio <= 1
        assert 0 <= track.cy_ratio <= 1


def test_build_edl_caption_words():
    """Caption words are extracted from transcript within clip range."""
    from opus_clone.services.edl_builder import build_edl

    transcript = json.loads((FIXTURES / "sample_transcript.json").read_text())
    analysis = json.loads((FIXTURES / "sample_analyze.json").read_text())

    candidate = {"start_s": 0.0, "end_s": 5.0}
    edl = build_edl(candidate, transcript, analysis)

    assert len(edl.captions.words) > 0
    for word in edl.captions.words:
        assert word.start_ms >= 0
        assert word.end_ms <= 5000
        assert word.word  # Not empty


def test_build_edl_empty_analysis():
    """EDL builder handles empty analysis gracefully."""
    from opus_clone.services.edl_builder import build_edl

    transcript = json.loads((FIXTURES / "sample_transcript.json").read_text())

    candidate = {"start_s": 0.0, "end_s": 10.0}
    edl = build_edl(candidate, transcript, {})

    # Should have fallback center reframe
    assert len(edl.reframe.tracks) == 1
    assert edl.reframe.tracks[0].cx_ratio == 0.5


def test_edl_model_serialization():
    """EDL model serializes to JSON matching GPU render contract."""
    from opus_clone.services.edl_builder import build_edl

    transcript = json.loads((FIXTURES / "sample_transcript.json").read_text())
    analysis = json.loads((FIXTURES / "sample_analyze.json").read_text())

    candidate = {"start_s": 0.0, "end_s": 22.5}
    edl = build_edl(candidate, transcript, analysis)

    edl_dict = edl.model_dump()

    # Required top-level keys
    assert "clip_start_ms" in edl_dict
    assert "clip_end_ms" in edl_dict
    assert "output_spec" in edl_dict
    assert "reframe" in edl_dict
    assert "captions" in edl_dict

    # Output spec
    assert edl_dict["output_spec"]["width"] == 1080
    assert edl_dict["output_spec"]["height"] == 1920
    assert edl_dict["output_spec"]["loudnorm"]["I"] == -14

    # Serializes to valid JSON
    json_str = json.dumps(edl_dict)
    assert json.loads(json_str) == edl_dict
