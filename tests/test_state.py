"""Tests for the new-story dedupe state."""

from dataclasses import dataclass

from ytokshorts.news.state import filter_new, load_seen, save_seen, story_key


@dataclass
class _Item:
    title: str
    link: str = ""


def test_story_key_prefers_link():
    assert story_key(_Item("T", "https://x/a")) == "https://x/a"
    assert story_key(_Item("Title only")) == "Title only"


def test_filter_new_removes_seen():
    items = [_Item("A", "l1"), _Item("B", "l2"), _Item("C", "l3")]
    fresh = filter_new(items, {"l2"})
    assert [i.title for i in fresh] == ["A", "C"]


def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / "seen.json"
    save_seen(p, {"l1", "l2"})
    assert load_seen(p) == {"l1", "l2"}


def test_load_seen_missing_is_empty(tmp_path):
    assert load_seen(tmp_path / "nope.json") == set()


def test_load_seen_handles_corrupt(tmp_path):
    p = tmp_path / "seen.json"
    p.write_text("not json {{{")
    assert load_seen(p) == set()
