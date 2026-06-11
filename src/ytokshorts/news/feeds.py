"""Fetch and parse RSS news feeds (stdlib only — no feedparser dependency)."""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from ..errors import YtokshortsError

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SPACE_BEFORE_PUNCT_RE = re.compile(r"\s+([.,!?;:])")


@dataclass(frozen=True)
class NewsItem:
    """One story from a feed."""

    title: str
    summary: str
    link: str = ""
    published: str = ""


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace from a feed snippet."""
    if not text:
        return ""
    # Tags become spaces (so words don't fuse), then tidy the spacing — including
    # the stray space a closing tag leaves in front of punctuation.
    collapsed = _WS_RE.sub(" ", _TAG_RE.sub(" ", text)).strip()
    return _SPACE_BEFORE_PUNCT_RE.sub(r"\1", collapsed)


def parse_rss(xml_text: str) -> list[NewsItem]:
    """Parse an RSS 2.0 (or Atom) document into :class:`NewsItem` objects.

    Pure and dependency-free so it can be unit-tested against fixture XML.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise YtokshortsError(f"Could not parse feed XML: {exc}") from exc

    items: list[NewsItem] = []

    # RSS 2.0: <rss><channel><item>...
    for item in root.iter("item"):
        title = _text(item, "title")
        summary = strip_html(_text(item, "description"))
        link = _text(item, "link")
        published = _text(item, "pubDate")
        if title:
            items.append(NewsItem(title=title, summary=summary, link=link, published=published))

    if items:
        return items

    # Atom fallback: <feed><entry>... with namespaced tags.
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title = _text(entry, "{http://www.w3.org/2005/Atom}title")
        summary = strip_html(
            _text(entry, "{http://www.w3.org/2005/Atom}summary")
            or _text(entry, "{http://www.w3.org/2005/Atom}content")
        )
        link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.get("href", "") if link_el is not None else ""
        published = _text(entry, "{http://www.w3.org/2005/Atom}updated")
        if title:
            items.append(NewsItem(title=title, summary=summary, link=link, published=published))

    return items


def _text(parent: ET.Element, tag: str) -> str:
    el = parent.find(tag)
    return (el.text or "").strip() if el is not None and el.text else ""


def fetch_feed(url: str, *, timeout: float = 20.0) -> list[NewsItem]:
    """Download ``url`` and parse it into news items."""
    req = urllib.request.Request(url, headers={"User-Agent": "ytokshorts/0.1 (+https://github.com)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - user-provided feed
            raw = resp.read()
    except Exception as exc:  # urllib raises a zoo of error types
        raise YtokshortsError(f"Could not fetch feed {url}: {exc}") from exc
    return parse_rss(raw.decode("utf-8", "replace"))
