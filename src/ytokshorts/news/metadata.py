"""Build copy-paste YouTube metadata (title, description, hashtags) per Short.

So manual posting in YouTube Studio is paste-and-go. All pure + unit-tested.
"""

from __future__ import annotations

_GENERIC_TAGS = ["Shorts", "Football", "FootballNews", "Soccer"]


def build_hashtags(country: str | None) -> list[str]:
    """Hashtags for a clip: the country (if any) first, then football generics."""
    tags: list[str] = []
    if country:
        tags.append(country.replace("-", " ").title().replace(" ", ""))
    tags += _GENERIC_TAGS
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def build_youtube_title(title: str) -> str:
    """A YouTube title: ensure ``#Shorts`` is present, capped at 100 chars."""
    t = " ".join(title.split()).strip()
    if "#shorts" not in t.lower():
        suffix = " #Shorts"
        t = t[: 100 - len(suffix)] + suffix if len(t) + len(suffix) > 100 else t + suffix
    return t[:100]


def build_description(script: str, source_link: str, hashtags: list[str]) -> str:
    """A description: the spoken script, the source link, then hashtags."""
    parts = [script.strip()]
    if source_link:
        parts.append(f"Source: {source_link}")
    if hashtags:
        parts.append(" ".join(f"#{h}" for h in hashtags))
    return "\n\n".join(parts)


def build_upload_txt(youtube_title: str, description: str) -> str:
    """A human-friendly sidecar file: title + description, ready to paste."""
    return f"TITLE:\n{youtube_title}\n\nDESCRIPTION:\n{description}\n"
