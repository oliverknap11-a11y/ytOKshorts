"""Tests for ffmpeg command/filtergraph construction (pure parts)."""

import pytest

from ytokshorts.clip import build_clip_command, build_filtergraph, escape_filter_path
from ytokshorts.config import ReframeConfig


def test_filtergraph_crop_no_captions():
    graph, label = build_filtergraph(ReframeConfig(mode="crop"), None)
    assert label == "v"
    assert "scale=1080:1920:force_original_aspect_ratio=increase" in graph
    assert "crop=1080:1920" in graph
    assert "split" not in graph


def test_filtergraph_blur_no_captions():
    graph, label = build_filtergraph(ReframeConfig(mode="blur"), None)
    assert label == "v"
    assert "split=2" in graph
    assert "boxblur" in graph
    assert "overlay=(W-w)/2:(H-h)/2" in graph


def test_filtergraph_appends_ass():
    graph, label = build_filtergraph(ReframeConfig(mode="crop"), "/tmp/a.ass")
    assert label == "vout"
    assert graph.endswith("[vout]")
    assert "ass=/tmp/a.ass" in graph


def test_escape_filter_path():
    # POSIX paths pass through untouched.
    assert escape_filter_path("/a/b c.ass") == "/a/b c.ass"
    # Windows paths: backslashes -> forward slashes; drive-letter colon escaped.
    assert escape_filter_path("C:\\work\\news\\x.ass") == "C\\:/work/news/x.ass"
    assert escape_filter_path("work\\news\\x.ass") == "work/news/x.ass"


def test_build_clip_command_structure():
    cmd = build_clip_command(
        "in.mp4", "out.mp4",
        start=12.5, duration=20.0,
        reframe=ReframeConfig(mode="crop"),
        ffmpeg="ffmpeg",
    )
    assert cmd[0] == "ffmpeg"
    # Fast seek: -ss precedes -i.
    assert cmd.index("-ss") < cmd.index("-i")
    assert "-ss" in cmd and cmd[cmd.index("-ss") + 1] == "12.500"
    assert "-t" in cmd and cmd[cmd.index("-t") + 1] == "20.000"
    assert "0:a?" in cmd  # audio included optionally
    assert cmd[-1] == "out.mp4"
    assert "libx264" in cmd


def test_build_clip_command_maps_caption_label():
    cmd = build_clip_command(
        "in.mp4", "out.mp4",
        start=0, duration=10,
        reframe=ReframeConfig(mode="blur"),
        ass_path="cap.ass",
    )
    assert "[vout]" in cmd


def test_build_clip_command_rejects_nonpositive_duration():
    with pytest.raises(ValueError):
        build_clip_command("in.mp4", "out.mp4", start=0, duration=0, reframe=ReframeConfig())
