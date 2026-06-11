"""Tests for pure transforms in media + pipeline (no ffmpeg required)."""

import pytest

from ytokshorts.config import HighlightConfig
from ytokshorts.media import _media_info_from_probe
from ytokshorts.pipeline import even_segments


def test_media_info_from_probe_picks_video_and_audio():
    data = {
        "format": {"duration": "123.45"},
        "streams": [
            {"codec_type": "audio"},
            {"codec_type": "video", "width": 1920, "height": 1080},
        ],
    }
    info = _media_info_from_probe(data)
    assert info.duration == pytest.approx(123.45)
    assert info.width == 1920 and info.height == 1080
    assert info.has_audio is True
    assert info.aspect == pytest.approx(1920 / 1080)


def test_media_info_no_audio_and_stream_duration_fallback():
    data = {
        "format": {},
        "streams": [
            {"codec_type": "video", "width": 640, "height": 480, "duration": "10.0"},
        ],
    }
    info = _media_info_from_probe(data)
    assert info.has_audio is False
    assert info.duration == pytest.approx(10.0)


def test_even_segments_spreads_across_timeline():
    cfg = HighlightConfig(min_duration=10, max_duration=20, target_count=3, spacing=5)
    segs = even_segments(120.0, cfg)
    assert len(segs) == 3
    assert segs[0].start == 0.0
    assert segs[-1].end == pytest.approx(120.0)
    # Non-decreasing starts.
    assert segs == sorted(segs, key=lambda s: s.start)


def test_even_segments_single_when_short():
    cfg = HighlightConfig(min_duration=10, max_duration=58, target_count=5, spacing=5)
    segs = even_segments(30.0, cfg)
    assert len(segs) == 1
    assert segs[0].start == 0.0 and segs[0].end == pytest.approx(30.0)


def test_even_segments_too_short_is_empty():
    cfg = HighlightConfig(min_duration=15, max_duration=58, target_count=5, spacing=5)
    assert even_segments(5.0, cfg) == []
