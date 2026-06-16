"""Detect which national team a football story is about, from its text.

A small curated keyword map (nations + demonyms) — dependency-free and
unit-tested. Returns a canonical lowercase country key (e.g. ``"england"``)
used to pick the presenter's kit; ``None`` means the story is neutral.
"""

from __future__ import annotations

import re

# country_key -> list of lowercase keywords (nation names + demonyms/adjectives).
_COUNTRY_KEYWORDS: dict[str, list[str]] = {
    "england": ["england", "english", "three lions", "wembley"],
    "scotland": ["scotland", "scottish"],
    "wales": ["wales", "welsh"],
    "ireland": ["ireland", "irish"],
    "france": ["france", "french", "les bleus"],
    "spain": ["spain", "spanish", "la roja"],
    "germany": ["germany", "german", "die mannschaft"],
    "italy": ["italy", "italian", "azzurri"],
    "portugal": ["portugal", "portuguese"],
    "netherlands": ["netherlands", "holland", "dutch", "oranje"],
    "belgium": ["belgium", "belgian"],
    "croatia": ["croatia", "croatian"],
    "brazil": ["brazil", "brazilian", "selecao", "seleção"],
    "argentina": ["argentina", "argentine", "argentinian", "albiceleste"],
    "uruguay": ["uruguay", "uruguayan"],
    "colombia": ["colombia", "colombian"],
    "mexico": ["mexico", "mexican"],
    "usa": ["usa", "united states", "usmnt", "uswnt", "american"],
    "morocco": ["morocco", "moroccan"],
    "senegal": ["senegal", "senegalese"],
    "nigeria": ["nigeria", "nigerian"],
    "egypt": ["egypt", "egyptian"],
    "ghana": ["ghana", "ghanaian"],
    "japan": ["japan", "japanese"],
    "south-korea": ["south korea", "korea", "korean"],
    "australia": ["australia", "australian", "socceroos"],
    "saudi-arabia": ["saudi arabia", "saudi"],
    "poland": ["poland", "polish"],
    "switzerland": ["switzerland", "swiss"],
    "denmark": ["denmark", "danish"],
    "sweden": ["sweden", "swedish"],
    "norway": ["norway", "norwegian"],
    "turkey": ["turkey", "turkish", "türkiye"],
    "greece": ["greece", "greek"],
}

# Pre-build (keyword, country) pairs sorted longest-first so "south korea" wins
# over "korea" and multi-word names match before single words.
_PAIRS: list[tuple[str, str]] = sorted(
    ((kw, country) for country, kws in _COUNTRY_KEYWORDS.items() for kw in kws),
    key=lambda p: len(p[0]),
    reverse=True,
)


def detect_country(text: str) -> str | None:
    """Return the canonical country key mentioned in ``text``, or None.

    Matches on whole words (case-insensitive). The first (longest) keyword hit
    wins, so a story naming a specific nation maps to it; stories that name none
    (transfers between clubs, general news) return None → neutral.
    """
    if not text:
        return None
    haystack = f" {text.lower()} "
    for keyword, country in _PAIRS:
        if re.search(rf"(?<![\w]){re.escape(keyword)}(?![\w])", haystack):
            return country
    return None
