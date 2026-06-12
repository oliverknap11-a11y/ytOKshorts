"""Tests for the AI-presenter pieces: country detection, kit selection,
HeyGen request shaping, and presenter compositing (all pure)."""

import pytest

from ytokshorts.config import AvatarConfig
from ytokshorts.errors import ConfigError, YtokshortsError
from ytokshorts.news.avatar import (
    avatar_id_for_country,
    build_generate_payload,
    build_local_command,
    build_talking_photo_payload,
    newest_video,
    parse_status,
    resolve_photo,
    resolve_presenter_clip,
)
from ytokshorts.news.portrait import composite_on_color, crop_upper_body, subject_bbox
from ytokshorts.news.compose import build_news_ass, build_presenter_compose_command
from ytokshorts.news.country import detect_country

# --------------------------------------------------------------------------- #
# country detection
# --------------------------------------------------------------------------- #

def test_detect_country_by_nation_and_demonym():
    assert detect_country("England squad named for the friendly") == "england"
    assert detect_country("French stars shine in Paris") == "france"
    assert detect_country("Brazilian wonderkid signs deal") == "brazil"


def test_detect_country_multiword_priority():
    # "south korea" must win over a bare "korea" match.
    assert detect_country("South Korea face Japan in qualifier") == "south-korea"


def test_detect_country_none_for_neutral():
    assert detect_country("Club transfer rumour heats up") is None
    assert detect_country("") is None


def test_detect_country_word_boundary():
    # "usa" should not match inside another word like "usage".
    assert detect_country("Heavy usage of the bench") is None


# --------------------------------------------------------------------------- #
# kit / avatar selection
# --------------------------------------------------------------------------- #

def test_avatar_id_for_country_map_then_neutral():
    cfg = AvatarConfig(avatar_map={"england": "av_eng"}, neutral_avatar="av_logo")
    assert avatar_id_for_country("england", cfg) == "av_eng"
    assert avatar_id_for_country("france", cfg) == "av_logo"   # falls back to neutral
    assert avatar_id_for_country(None, cfg) == "av_logo"


def test_avatar_id_for_country_requires_some_avatar():
    with pytest.raises(YtokshortsError):
        avatar_id_for_country("england", AvatarConfig())


def test_resolve_presenter_clip(tmp_path):
    (tmp_path / "england.mp4").write_bytes(b"x")
    (tmp_path / "neutral.mp4").write_bytes(b"x")
    cfg = AvatarConfig(clips_dir=str(tmp_path))
    assert resolve_presenter_clip("england", cfg).name == "england.mp4"
    assert resolve_presenter_clip("france", cfg).name == "neutral.mp4"   # fallback
    assert resolve_presenter_clip(None, cfg).name == "neutral.mp4"


def test_resolve_presenter_clip_missing(tmp_path):
    assert resolve_presenter_clip("england", AvatarConfig(clips_dir=str(tmp_path))) is None


# --------------------------------------------------------------------------- #
# HeyGen request/response shaping
# --------------------------------------------------------------------------- #

def test_build_generate_payload_audio_and_green_bg():
    p = build_generate_payload("av_1", "https://x/a.mp3", width=1080, height=1920,
                               chroma_color="#00FF00")
    vi = p["video_inputs"][0]
    assert vi["character"]["avatar_id"] == "av_1"
    assert vi["voice"] == {"type": "audio", "audio_url": "https://x/a.mp3"}
    assert vi["background"] == {"type": "color", "value": "#00FF00"}
    assert p["dimension"] == {"width": 1080, "height": 1920}


def test_build_generate_payload_transparent_when_no_chroma():
    p = build_generate_payload("av_1", "u", width=1080, height=1920, chroma_color="")
    assert p["video_inputs"][0]["background"] == {"type": "transparent"}


def test_parse_status():
    done = {"data": {"status": "completed", "video_url": "https://x/v.mp4"}}
    assert parse_status(done) == ("completed", "https://x/v.mp4")
    assert parse_status({"data": {"status": "processing"}}) == ("processing", None)


def test_build_talking_photo_payload():
    p = build_talking_photo_payload("tp_1", "https://x/a.mp3", width=1080, height=1920,
                                    chroma_color="#00FF00", use_avatar_iv=True)
    char = p["video_inputs"][0]["character"]
    assert char["type"] == "talking_photo"
    assert char["talking_photo_id"] == "tp_1"
    assert char["use_avatar_iv_model"] is True
    assert p["video_inputs"][0]["voice"] == {"type": "audio", "audio_url": "https://x/a.mp3"}
    assert p["video_inputs"][0]["background"] == {"type": "color", "value": "#00FF00"}


def test_resolve_photo(tmp_path):
    (tmp_path / "portugal.png").write_bytes(b"x")
    (tmp_path / "neutral.jpg").write_bytes(b"x")
    cfg = AvatarConfig(photo_dir=str(tmp_path))
    assert resolve_photo("portugal", cfg).name == "portugal.png"
    assert resolve_photo("spain", cfg).name == "neutral.jpg"   # neutral fallback
    assert resolve_photo(None, cfg).name == "neutral.jpg"


def test_composite_on_color_replaces_transparency():
    from PIL import Image
    # A 2x2 image: fully transparent -> should become solid green.
    img = Image.new("RGBA", (2, 2), (123, 50, 200, 0))
    out = composite_on_color(img, "#00FF00")
    assert out.mode == "RGB"
    assert out.getpixel((0, 0)) == (0, 255, 0)


def test_crop_upper_body_keeps_head_region():
    from PIL import Image
    # Transparent 100x400 canvas with an opaque "subject" from y=40..360 (tall).
    img = Image.new("RGBA", (100, 400), (0, 0, 0, 0))
    for y in range(40, 360):
        for x in range(30, 70):
            img.putpixel((x, y), (200, 30, 40, 255))
    assert subject_bbox(img) == (30, 40, 70, 360)
    cropped = crop_upper_body(img, keep=0.55)
    # Subject height 320 -> keep 176 -> cropped height ~176 (well under 400).
    assert cropped.height < img.height
    assert 150 < cropped.height < 220


def test_build_local_command_substitutes(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x")
    (tmp_path / "v.mp3").write_bytes(b"x")
    cmd = build_local_command(
        'python inf.py --source_image "{image}" --driven_audio "{audio}" --result_dir "{result_dir}"',
        tmp_path / "a.png", tmp_path / "v.mp3", tmp_path / "out",
    )
    assert "a.png" in cmd and "v.mp3" in cmd and "out" in cmd
    assert "{image}" not in cmd


def test_newest_video_picks_latest(tmp_path):
    import os, time
    old = tmp_path / "old.mp4"; old.write_bytes(b"x")
    time.sleep(0.01)
    new = tmp_path / "sub" / "new.mp4"; new.parent.mkdir(); new.write_bytes(b"x")
    os.utime(new, (time.time() + 5, time.time() + 5))
    assert newest_video(tmp_path) == new


def test_newest_video_none(tmp_path):
    with pytest.raises(YtokshortsError):
        newest_video(tmp_path)


# --------------------------------------------------------------------------- #
# presenter compositing command
# --------------------------------------------------------------------------- #

def test_presenter_compose_heygen_uses_clip_audio():
    cmd = build_presenter_compose_command(
        "caps.ass", "pres.mp4", "out.mp4",
        width=1080, height=1920, duration=20.0,
        bg_top="#1B6B34", bg_bottom="#0A2A14",
        background=("image", "pitch.png"),
        presenter_has_audio=True,
    )
    joined = " ".join(cmd)
    assert "chromakey=0x00FF00" in joined
    assert "[bgf][pres]overlay=" in joined
    assert "ass=caps.ass" in joined
    # presenter is input 1; its audio is mapped (no separate audio input).
    assert "-map" in cmd and "1:a" in cmd
    assert cmd[-1] == "out.mp4"


def test_presenter_compose_clips_loops_and_uses_voiceover():
    cmd = build_presenter_compose_command(
        "caps.ass", "loop.mp4", "out.mp4",
        width=1080, height=1920, duration=20.0,
        bg_top="#000000", bg_bottom="#111111",
        presenter_has_audio=False, audio_path="voice.mp3",
    )
    assert "-stream_loop" in cmd
    assert "voice.mp3" in " ".join(cmd)
    assert "2:a" in cmd          # audio is the 3rd input


def test_presenter_compose_requires_audio_when_no_clip_audio():
    with pytest.raises(ValueError):
        build_presenter_compose_command(
            "c.ass", "p.mp4", "o.mp4",
            width=1080, height=1920, duration=20.0,
            bg_top="#000000", bg_bottom="#111111",
            presenter_has_audio=False, audio_path=None,
        )


# --------------------------------------------------------------------------- #
# subtitle band (above the presenter's head)
# --------------------------------------------------------------------------- #

def test_top_band_keeps_subtitles_in_upper_frame():
    from ytokshorts.news.compose import group_words_into_captions
    from ytokshorts.news.tts import WordCue

    caps = group_words_into_captions([WordCue(f"w{i}", float(i), float(i) + 0.4) for i in range(4)], 1)
    ass = build_news_ass("T", caps, width=1080, height=1920, duration=10.0, band="top")
    ys = [int(line.split("\\pos(540,")[1].split(")")[0])
          for line in ass.splitlines() if "\\pos(540," in line]
    assert ys and max(ys) < round(1920 * 0.46)   # all subtitles in the top band


# --------------------------------------------------------------------------- #
# config validation
# --------------------------------------------------------------------------- #

def test_avatar_config_validation():
    with pytest.raises(ConfigError, match="avatar.mode"):
        AvatarConfig(mode="hologram")
    with pytest.raises(ConfigError, match="avatar.position"):
        AvatarConfig(position="left")
    with pytest.raises(ConfigError, match="avatar.scale"):
        AvatarConfig(scale=0)


def test_avatar_config_defaults_disabled():
    assert AvatarConfig().enabled is False
    assert AvatarConfig().mode == "clips"
