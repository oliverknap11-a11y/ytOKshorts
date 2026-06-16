"""Tests for YouTube upload metadata generation (pure)."""

from ytokshorts.news.metadata import (
    build_description,
    build_hashtags,
    build_upload_txt,
    build_youtube_title,
)


def test_build_hashtags_country_first():
    tags = build_hashtags("portugal")
    assert tags[0] == "Portugal"
    assert "Shorts" in tags and "FootballNews" in tags


def test_build_hashtags_multiword_country():
    assert build_hashtags("south-korea")[0] == "SouthKorea"


def test_build_hashtags_neutral_no_country():
    tags = build_hashtags(None)
    assert "Shorts" in tags
    assert all(t in ("Shorts", "Football", "FootballNews", "Soccer") for t in tags)


def test_build_hashtags_dedupes():
    # "Football" generic shouldn't duplicate if a country happened to collide.
    tags = build_hashtags("football")
    assert len(tags) == len({t.lower() for t in tags})


def test_build_youtube_title_adds_shorts():
    assert build_youtube_title("England squad named").endswith("#Shorts")


def test_build_youtube_title_keeps_existing_shorts():
    t = build_youtube_title("Big news #Shorts")
    assert t.lower().count("#shorts") == 1


def test_build_youtube_title_caps_100():
    assert len(build_youtube_title("x" * 200)) <= 100


def test_build_description_has_script_source_tags():
    d = build_description("Read this out.", "https://x/a", ["Portugal", "Shorts"])
    assert "Read this out." in d
    assert "Source: https://x/a" in d
    assert "#Portugal" in d and "#Shorts" in d


def test_build_upload_txt_format():
    txt = build_upload_txt("T #Shorts", "desc here")
    assert "TITLE:\nT #Shorts" in txt
    assert "DESCRIPTION:\ndesc here" in txt
