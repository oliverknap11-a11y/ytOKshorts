"""Tests for schedule math and request-body construction (pure parts)."""

import pytest

from ytokshorts.config import UploadConfig
from ytokshorts.errors import YtokshortsError
from ytokshorts.upload import (
    _apply_title_suffix,
    build_video_resource,
    compute_schedule_times,
)


def test_schedule_none_start_is_all_none():
    assert compute_schedule_times(None, 24, 3) == [None, None, None]
    assert compute_schedule_times("", 24, 2) == [None, None]


def test_schedule_spacing_and_z_parsing():
    times = compute_schedule_times("2026-06-12T09:00:00Z", 12, 3)
    assert times == [
        "2026-06-12T09:00:00Z",
        "2026-06-12T21:00:00Z",
        "2026-06-13T09:00:00Z",
    ]


def test_schedule_naive_time_treated_as_utc():
    assert compute_schedule_times("2026-06-12T09:00:00", 24, 1) == ["2026-06-12T09:00:00Z"]


def test_schedule_invalid_time_raises():
    with pytest.raises(YtokshortsError, match="Invalid schedule time"):
        compute_schedule_times("not-a-time", 24, 1)


def test_schedule_zero_count():
    assert compute_schedule_times("2026-06-12T09:00:00Z", 24, 0) == []


def test_apply_title_suffix():
    assert _apply_title_suffix("Funny clip", "#shorts") == "Funny clip #shorts"
    # Idempotent / case-insensitive.
    assert _apply_title_suffix("Already #Shorts", "#shorts") == "Already #Shorts"
    assert _apply_title_suffix("x", "") == "x"


def test_build_video_resource_basic():
    cfg = UploadConfig(tags=["a", "b"], category_id="24", title_suffix="#shorts")
    res = build_video_resource("My clip", "desc", cfg)
    assert res["snippet"]["title"] == "My clip #shorts"
    assert res["snippet"]["tags"] == ["a", "b"]
    assert res["snippet"]["categoryId"] == "24"
    assert res["status"]["privacyStatus"] == "private"
    assert "publishAt" not in res["status"]


def test_build_video_resource_scheduled():
    cfg = UploadConfig(privacy="private")
    res = build_video_resource("t", "d", cfg, publish_at="2026-06-12T09:00:00Z")
    assert res["status"]["publishAt"] == "2026-06-12T09:00:00Z"


def test_build_video_resource_scheduled_requires_private():
    cfg = UploadConfig(privacy="unlisted")
    with pytest.raises(YtokshortsError, match="requires privacy 'private'"):
        build_video_resource("t", "d", cfg, publish_at="2026-06-12T09:00:00Z")


def test_build_video_resource_title_capped_at_100():
    cfg = UploadConfig(title_suffix="")
    res = build_video_resource("x" * 250, "", cfg)
    assert len(res["snippet"]["title"]) == 100
