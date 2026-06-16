"""Smoke tests for CLI argument wiring (no external tools invoked)."""

import pytest

from ytokshorts.cli import _build_parser, main


def test_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "ytokshorts" in capsys.readouterr().out


def test_no_command_returns_one():
    assert main([]) == 1


def test_run_parses_overrides():
    args = _build_parser().parse_args(
        ["run", "https://example.com/v", "--count", "3", "--reframe-mode", "crop", "--no-captions"]
    )
    assert args.command == "run"
    assert args.source == "https://example.com/v"
    assert args.count == 3
    assert args.reframe_mode == "crop"
    assert args.no_captions is True


def test_clip_requires_start_end_out():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["clip", "in.mp4"])  # missing required args


def test_upload_mutually_exclusive_flags():
    parser = _build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "x", "--upload", "--no-upload"])
