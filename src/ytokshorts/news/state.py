"""Track which stories have already been turned into Shorts.

So a scheduled/repeated run only processes *new* news (``--new-only``) instead
of re-rendering the same headlines every time. State is a small JSON file of
story keys; everything here is pure and unit-tested.
"""

from __future__ import annotations

import json
from pathlib import Path


def story_key(item) -> str:
    """A stable identifier for a news item (prefer the link, fall back to title)."""
    return (getattr(item, "link", "") or getattr(item, "title", "")).strip()


def load_seen(path: str | Path) -> set[str]:
    """Load the set of already-processed story keys (empty if no/invalid file)."""
    p = Path(path)
    if not p.exists():
        return set()
    try:
        data = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return set()
    if isinstance(data, dict):
        return set(data.get("seen", []))
    if isinstance(data, list):
        return set(data)
    return set()


def save_seen(path: str | Path, seen: set[str]) -> None:
    """Persist the set of processed story keys."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"seen": sorted(seen)}, indent=2))


def filter_new(items: list, seen: set[str]) -> list:
    """Return only the items whose key is not already in ``seen`` (order kept)."""
    return [it for it in items if story_key(it) not in seen]
