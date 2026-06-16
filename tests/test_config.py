"""Tests for configuration loading and validation."""

import pytest

from ytokshorts.config import Config
from ytokshorts.errors import ConfigError


def test_defaults():
    cfg = Config()
    assert cfg.work_dir == "work"
    assert cfg.highlights.target_count == 5
    assert cfg.reframe.mode == "blur"
    assert cfg.upload.enabled is False
    assert cfg.reframe.aspect == pytest.approx(1080 / 1920)


def test_from_dict_nested():
    cfg = Config.from_dict(
        {
            "work_dir": "out",
            "highlights": {"target_count": 3, "max_duration": 30},
            "reframe": {"mode": "crop"},
        }
    )
    assert cfg.work_dir == "out"
    assert cfg.highlights.target_count == 3
    assert cfg.highlights.max_duration == 30
    assert cfg.reframe.mode == "crop"
    # Untouched fields keep defaults.
    assert cfg.highlights.min_duration == 15.0


def test_unknown_top_level_key_raises():
    with pytest.raises(ConfigError, match="Unknown config option 'nope'"):
        Config.from_dict({"nope": 1})


def test_unknown_nested_key_raises():
    with pytest.raises(ConfigError, match="highlights.bogus"):
        Config.from_dict({"highlights": {"bogus": 1}})


def test_validation_max_over_60():
    with pytest.raises(ConfigError, match="max_duration must be <= 60"):
        Config.from_dict({"highlights": {"max_duration": 90}})


def test_validation_min_greater_than_max():
    with pytest.raises(ConfigError, match="max_duration must be >= min_duration"):
        Config.from_dict({"highlights": {"min_duration": 50, "max_duration": 30}})


def test_validation_bad_reframe_mode():
    with pytest.raises(ConfigError, match="reframe.mode"):
        Config.from_dict({"reframe": {"mode": "squish"}})


def test_validation_schedule_requires_private():
    with pytest.raises(ConfigError, match="requires upload.privacy"):
        Config.from_dict({"upload": {"privacy": "public", "schedule_start": "2026-01-01T00:00:00Z"}})


def test_load_missing_path_raises():
    with pytest.raises(ConfigError, match="not found"):
        Config.load("/nonexistent/ytokshorts.toml")


def test_load_none_returns_defaults():
    assert Config.load(None).work_dir == "work"


def test_load_from_toml_file(tmp_path):
    p = tmp_path / "cfg.toml"
    p.write_text('work_dir = "x"\n[highlights]\ntarget_count = 2\n')
    cfg = Config.load(p)
    assert cfg.work_dir == "x"
    assert cfg.highlights.target_count == 2
