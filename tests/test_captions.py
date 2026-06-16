"""Tests for caption rendering (pure parts)."""

from ytokshorts.captions import (
    Caption,
    clip_captions,
    format_ass_timestamp,
    format_srt_timestamp,
    to_ass,
    to_srt,
)
from ytokshorts.config import CaptionConfig


def test_format_srt_timestamp():
    assert format_srt_timestamp(0) == "00:00:00,000"
    assert format_srt_timestamp(3661.5) == "01:01:01,500"
    assert format_srt_timestamp(-1) == "00:00:00,000"


def test_format_ass_timestamp():
    assert format_ass_timestamp(0) == "0:00:00.00"
    assert format_ass_timestamp(3661.25) == "1:01:01.25"


def test_to_srt_structure():
    caps = [Caption(0.0, 1.5, "hello"), Caption(1.5, 3.0, "world")]
    srt = to_srt(caps)
    assert "1\n00:00:00,000 --> 00:00:01,500\nhello" in srt
    assert "2\n00:00:01,500 --> 00:00:03,000\nworld" in srt


def test_to_ass_alignment_and_resolution():
    caps = [Caption(0.0, 1.0, "hi")]
    ass = to_ass(caps, CaptionConfig(position="top"), width=1080, height=1920)
    assert "PlayResX: 1080" in ass
    assert "PlayResY: 1920" in ass
    # Top alignment is \an8; it appears as the Alignment field in the style line.
    style_line = next(l for l in ass.splitlines() if l.startswith("Style:"))
    assert ",8," in style_line
    assert "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,hi" in ass


def test_to_ass_escapes_braces_and_newlines():
    caps = [Caption(0.0, 1.0, "a{b}\nc")]
    ass = to_ass(caps, CaptionConfig(), width=1080, height=1920)
    assert "a\\{b\\}\\Nc" in ass


def test_clip_captions_slices_and_retimes():
    caps = [
        Caption(0.0, 2.0, "before"),
        Caption(10.0, 12.0, "inside"),
        Caption(19.0, 21.0, "straddle-end"),
        Caption(30.0, 31.0, "after"),
    ]
    out = clip_captions(caps, start=8.0, end=20.0)
    texts = [c.text for c in out]
    assert texts == ["inside", "straddle-end"]
    # 'inside' shifted by -8s.
    assert out[0].start == 2.0 and out[0].end == 4.0
    # 'straddle-end' clipped to the window end (20) then shifted.
    assert out[1].start == 11.0 and out[1].end == 12.0


def test_clip_captions_empty_when_no_overlap():
    caps = [Caption(0.0, 1.0, "x")]
    assert clip_captions(caps, 5.0, 10.0) == []
