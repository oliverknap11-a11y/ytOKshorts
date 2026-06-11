"""Tests for the pure logic of the news-to-Short pipeline."""

import pytest

from ytokshorts.config import NewsConfig
from ytokshorts.errors import ConfigError, YtokshortsError
from ytokshorts.news.background import classify, resolve_background
from ytokshorts.news.compose import (
    build_compose_command,
    build_news_ass,
    caption_override,
    emphasize_numbers,
    group_words_into_captions,
    hex_to_ff_color,
)
from ytokshorts.news.feeds import NewsItem, parse_rss, strip_html
from ytokshorts.news.script import (
    build_system_prompt,
    build_user_prompt,
    fallback_script,
    parse_script_response,
)
from ytokshorts.news.tts import WordCue, boundaries_to_cues

# --------------------------------------------------------------------------- #
# feeds
# --------------------------------------------------------------------------- #

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <title>Football</title>
  <item>
    <title>Team A signs star striker</title>
    <description>&lt;p&gt;The deal is worth &lt;b&gt;£50m&lt;/b&gt;.&lt;/p&gt;</description>
    <link>https://example.com/a</link>
    <pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate>
  </item>
  <item>
    <title>Manager sacked after defeat</title>
    <description>Board acts fast.</description>
    <link>https://example.com/b</link>
  </item>
</channel></rss>"""


def test_parse_rss_extracts_items():
    items = parse_rss(RSS_SAMPLE)
    assert len(items) == 2
    assert items[0].title == "Team A signs star striker"
    assert items[0].summary == "The deal is worth £50m."  # HTML stripped
    assert items[0].link == "https://example.com/a"
    assert items[1].title == "Manager sacked after defeat"


def test_parse_atom_fallback():
    atom = """<?xml version="1.0"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry>
        <title>Atom headline</title>
        <summary>Some summary</summary>
        <link href="https://example.com/x"/>
      </entry>
    </feed>"""
    items = parse_rss(atom)
    assert len(items) == 1
    assert items[0].title == "Atom headline"
    assert items[0].link == "https://example.com/x"


def test_parse_rss_invalid_raises():
    with pytest.raises(YtokshortsError):
        parse_rss("not xml <<<")


def test_strip_html():
    assert strip_html("<p>Hi   <b>there</b></p>") == "Hi there"
    assert strip_html("") == ""


# --------------------------------------------------------------------------- #
# script
# --------------------------------------------------------------------------- #

def test_build_prompts_include_story():
    item = NewsItem(title="Big transfer", summary="Details here")
    sys = build_system_prompt(60)
    assert "60 words" in sys
    user = build_user_prompt(item)
    assert "Big transfer" in user and "Details here" in user


def test_fallback_script_trims_to_budget():
    item = NewsItem(title="Headline", summary=" ".join(f"word{i}" for i in range(100)))
    res = fallback_script(item, words_target=20)
    assert res.title == "Headline"
    assert len(res.script.split()) <= 21  # budget + ellipsis token
    assert res.script.endswith("...")


def test_parse_script_response_valid_json():
    res = parse_script_response('{"title": "T", "script": "Read this out."}', fallback="fb")
    assert res.title == "T"
    assert res.script == "Read this out."


def test_parse_script_response_empty_raises():
    with pytest.raises(YtokshortsError):
        parse_script_response('{"title": "T", "script": ""}', fallback="fb")


def test_parse_script_response_non_json_degrades():
    res = parse_script_response("just some text", fallback="Fallback Title")
    assert res.title == "Fallback Title"
    assert res.script == "just some text"


def test_trim_title_clamps_length():
    long = "x" * 100
    res = parse_script_response(f'{{"title": "{long}", "script": "hi"}}', fallback="fb")
    assert len(res.title) <= 60


# --------------------------------------------------------------------------- #
# tts
# --------------------------------------------------------------------------- #

def test_boundaries_to_cues_converts_ticks():
    # 1 second == 10,000,000 ticks.
    boundaries = [
        {"offset": 0, "duration": 5_000_000, "text": "Hello"},
        {"offset": 5_000_000, "duration": 5_000_000, "text": "world"},
        {"offset": 10_000_000, "duration": 0, "text": "  "},  # blank dropped
    ]
    cues = boundaries_to_cues(boundaries)
    assert len(cues) == 2
    assert cues[0] == WordCue("Hello", 0.0, 0.5)
    assert cues[1] == WordCue("world", 0.5, 1.0)


# --------------------------------------------------------------------------- #
# compose
# --------------------------------------------------------------------------- #

def test_group_words_into_captions():
    cues = [WordCue(f"w{i}", float(i), float(i) + 0.5) for i in range(5)]
    caps = group_words_into_captions(cues, max_words=2)
    assert len(caps) == 3  # 2 + 2 + 1
    assert caps[0].text == "w0 w1"
    assert caps[0].start == 0.0
    assert caps[0].end == 1.5
    assert caps[2].text == "w4"


def test_group_words_empty():
    assert group_words_into_captions([], 3) == []


def test_hex_to_ff_color():
    assert hex_to_ff_color("#0E2A1B") == "0x0E2A1B"
    assert hex_to_ff_color("07140d") == "0x07140D"
    with pytest.raises(ValueError):
        hex_to_ff_color("#nothex")


def test_build_news_ass_has_both_styles():
    caps = [WordCue("hi", 0.0, 0.5)]
    ass = build_news_ass(
        "My Title",
        group_words_into_captions(caps, 3),
        width=1080, height=1920, duration=10.0,
    )
    assert "Style: Title," in ass
    assert "Style: Caption," in ass
    assert "PlayResX: 1080" in ass
    assert "My Title" in ass
    assert "Dialogue: 0," in ass


def test_build_compose_command_gradient_default():
    cmd = build_compose_command(
        "voice.mp3", "caps.ass", "out.mp4",
        width=1080, height=1920, duration=20.0,
        bg_top="#0E2A1B", bg_bottom="#07140D",
    )
    assert cmd[0] == "ffmpeg"
    assert "lavfi" in cmd
    joined = " ".join(cmd)
    assert "gradients=s=1080x1920" in joined
    assert "0x0E2A1B" in joined
    assert "ass=caps.ass" in joined
    assert cmd[-1] == "out.mp4"
    assert "-t" in cmd and cmd[cmd.index("-t") + 1] == "20.000"


def test_build_compose_command_image_background_has_loop_and_scrim():
    cmd = build_compose_command(
        "voice.mp3", "caps.ass", "out.mp4",
        width=1080, height=1920, duration=20.0,
        bg_top="#000000", bg_bottom="#111111",
        background=("image", "pitch.png"), scrim=0.4,
    )
    joined = " ".join(cmd)
    assert "-loop" in cmd and "pitch.png" in joined
    assert "drawbox" in joined and "black@0.40" in joined
    assert "gradients" not in joined  # not the fallback


def test_build_compose_command_video_background_stream_loops():
    cmd = build_compose_command(
        "voice.mp3", "caps.ass", "out.mp4",
        width=1080, height=1920, duration=20.0,
        bg_top="#000000", bg_bottom="#111111",
        background=("video", "broll.mp4"),
    )
    assert "-stream_loop" in cmd
    assert "broll.mp4" in " ".join(cmd)


def test_build_compose_command_rejects_zero_duration():
    with pytest.raises(ValueError):
        build_compose_command(
            "a.mp3", "c.ass", "o.mp4",
            width=1080, height=1920, duration=0,
            bg_top="#000000", bg_bottom="#111111",
        )


# --------------------------------------------------------------------------- #
# captions: animation + emphasis
# --------------------------------------------------------------------------- #

def test_caption_override_animates_or_not():
    assert caption_override(False) == ""
    anim = caption_override(True)
    assert "\\fad" in anim and "\\t(" in anim


def test_emphasize_numbers_wraps_scores_and_money():
    out = emphasize_numbers("won 2-1 for £50m")
    assert "2-1" in out and "£50m" in out
    assert out.count("\\c&H28C8FF&") == 2   # two numeric tokens highlighted
    assert "\\c&HFFFFFF&" in out            # reset back to white


def test_emphasize_numbers_leaves_plain_text():
    assert emphasize_numbers("no digits here") == "no digits here"


def test_build_news_ass_animation_in_dialogue():
    caps = [WordCue("Bellingham", 0.0, 0.5)]
    grouped = group_words_into_captions(caps, 3)
    ass = build_news_ass("T", grouped, width=1080, height=1920, duration=5.0, animate=True)
    assert "\\fad(90,70)" in ass        # caption pop
    plain = build_news_ass("T", grouped, width=1080, height=1920, duration=5.0, animate=False)
    assert "\\fad(90,70)" not in plain


# --------------------------------------------------------------------------- #
# background resolution
# --------------------------------------------------------------------------- #

def test_classify_by_extension():
    assert classify("a.png") == "image"
    assert classify("b.MP4") == "video"
    assert classify("c.txt") is None


def test_resolve_background_file(tmp_path):
    f = tmp_path / "bg.jpg"
    f.write_bytes(b"x")
    assert resolve_background(str(f), 0) == ("image", str(f))


def test_resolve_background_folder_cycles(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "b.mp4").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")  # ignored
    k0, p0 = resolve_background(str(tmp_path), 0)
    k1, p1 = resolve_background(str(tmp_path), 1)
    k2, p2 = resolve_background(str(tmp_path), 2)  # wraps back to index 0
    assert {p0, p1} == {str(tmp_path / "a.png"), str(tmp_path / "b.mp4")}
    assert p2 == p0


def test_resolve_background_missing_raises():
    from ytokshorts.errors import YtokshortsError
    with pytest.raises(YtokshortsError):
        resolve_background("/nope/missing.png", 0)


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #

def test_news_config_defaults():
    n = NewsConfig()
    assert n.model == "claude-opus-4-8"
    assert n.count == 3
    assert "rss" in n.feed.lower() or "feed" in n.feed.lower()


def test_news_config_validation():
    with pytest.raises(ConfigError, match="news.effort"):
        NewsConfig(effort="turbo")
    with pytest.raises(ConfigError, match="news.count"):
        NewsConfig(count=0)
