import json
from pathlib import Path

import pytest
from pydantic import ValidationError

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_channel_create_validation():
    from opus_clone.models.domain import ChannelCreate

    channel = ChannelCreate(
        platform="youtube",
        external_id="UCxxx123",
        username="testchannel",
    )
    assert channel.platform == "youtube"
    assert channel.min_viral_score == 65
    assert channel.max_clips_per_video == 8


def test_channel_create_invalid_platform():
    from opus_clone.models.domain import ChannelCreate

    with pytest.raises(ValidationError):
        ChannelCreate(
            platform="twitch",  # invalid
            external_id="xxx",
            username="test",
        )


def test_edl_model():
    from opus_clone.models.edl import EDL

    fixture = json.loads((FIXTURES / "sample_edl.json").read_text())
    edl = EDL(**fixture)

    assert edl.clip_start_ms == 0
    assert edl.clip_end_ms == 56000
    assert edl.output_spec.width == 1080
    assert edl.output_spec.height == 1920
    assert len(edl.reframe.tracks) == 5
    assert len(edl.captions.words) == 7
    assert len(edl.zooms) == 2


def test_transcription_result():
    from opus_clone.models.gpu_api import TranscriptionResult

    fixture = json.loads((FIXTURES / "sample_transcript.json").read_text())
    result = TranscriptionResult(**fixture)

    assert result.language == "pt"
    assert result.duration == 180.5
    assert len(result.segments) == 3
    assert result.segments[0].words[0].word == "Hoje"


def test_analysis_result():
    from opus_clone.models.gpu_api import AnalysisResult

    fixture = json.loads((FIXTURES / "sample_analyze.json").read_text())
    result = AnalysisResult(**fixture)

    assert result.duration == 180.5
    assert len(result.scenes) == 4
    assert len(result.active_speaker_timeline) == 7
    assert len(result.keyframes) == 5


def test_nms_temporal():
    from opus_clone.agent.nodes.score import _nms_temporal

    candidates = [
        {"start_s": 0, "end_s": 30, "viral_score": 90},
        {"start_s": 5, "end_s": 35, "viral_score": 85},  # overlaps heavily with first
        {"start_s": 60, "end_s": 90, "viral_score": 80},  # no overlap
        {"start_s": 62, "end_s": 88, "viral_score": 75},  # overlaps with third
    ]

    result = _nms_temporal(candidates, iou_threshold=0.5)

    assert len(result) == 2
    assert result[0]["viral_score"] == 90
    assert result[1]["viral_score"] == 80
