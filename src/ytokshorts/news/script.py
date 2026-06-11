"""Turn a news item into a tight, punchy vertical-Short script with Claude.

Uses the official Anthropic SDK with structured outputs so the model returns a
clean ``{title, script}`` object — no preamble to strip. A dependency-free
fallback (headline + summary) keeps the pipeline runnable without an API key.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from ..config import NewsConfig
from ..errors import MissingDependencyError, YtokshortsError
from .feeds import NewsItem

log = logging.getLogger("ytokshorts")


@dataclass(frozen=True)
class ScriptResult:
    """A generated Short: an on-screen ``title`` and the spoken ``script``."""

    title: str
    script: str


def build_system_prompt(words_target: int) -> str:
    """The scriptwriter system prompt (pure — unit-tested)."""
    return (
        "You are a scriptwriter for a faceless football-news YouTube Shorts "
        "channel. Given a news story, write a single voiceover script for a "
        f"vertical Short of about {words_target} words (~25 seconds spoken).\n"
        "Structure it as three beats so the middle stays gripping:\n"
        "1. HOOK (3-6 words): a bold, curiosity-piquing opener.\n"
        "2. MIDDLE (the bulk): build the stakes — why this matters, the "
        "tension or stakes, a surprising angle or the key number/detail. Keep "
        "it moving; vary sentence length; no filler.\n"
        "3. PAYOFF: a punchy closing line that invites a reaction or opinion.\n"
        "Rules:\n"
        "- Conversational, energetic, present tense. Plain spoken English.\n"
        "- Only use facts present in the story; never invent transfers, "
        "scores, quotes, or numbers. If details are thin, keep it short.\n"
        "- Surface concrete numbers (scores, fees, ages) when present — they "
        "land well on screen.\n"
        "- No emojis, no hashtags, no stage directions, no markdown, no beat "
        "labels — just the words to be read aloud.\n"
        "Also provide a short punchy on-screen title (max 60 characters)."
    )


def build_user_prompt(item: NewsItem) -> str:
    """Render a news item into the user turn (pure — unit-tested)."""
    parts = [f"Headline: {item.title}"]
    if item.summary:
        parts.append(f"Summary: {item.summary}")
    return "\n".join(parts)


# JSON Schema for structured output — guarantees a parseable {title, script}.
SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "script": {"type": "string"},
    },
    "required": ["title", "script"],
    "additionalProperties": False,
}


def fallback_script(item: NewsItem, words_target: int) -> ScriptResult:
    """Build a serviceable script from the headline + summary, no LLM needed."""
    title = item.title.strip()
    body = item.summary.strip()
    spoken = f"{title}." if not title.endswith((".", "!", "?")) else title
    if body:
        spoken += f" {body}"
    # Trim to roughly the word budget so the voiceover stays Short-length.
    words = spoken.split()
    if len(words) > words_target:
        spoken = " ".join(words[:words_target]).rstrip(",;:") + "..."
    return ScriptResult(title=_trim_title(title), script=spoken)


def generate_script(item: NewsItem, config: NewsConfig, *, use_llm: bool = True) -> ScriptResult:
    """Generate a script via Claude, falling back to the headline if unavailable."""
    if not use_llm:
        return fallback_script(item, config.words_target)
    try:
        return _draft_with_claude(item, config)
    except MissingDependencyError:
        raise
    except YtokshortsError as exc:
        log.warning("Claude scripting failed (%s); using headline fallback.", exc)
        return fallback_script(item, config.words_target)


def _draft_with_claude(item: NewsItem, config: NewsConfig) -> ScriptResult:
    """Call the Anthropic Messages API with structured output."""
    try:
        import anthropic  # type: ignore
    except ImportError as exc:
        raise MissingDependencyError(
            "anthropic", extra="news", purpose="write scripts with Claude"
        ) from exc

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    try:
        response = client.messages.create(
            model=config.model,
            max_tokens=1024,
            system=build_system_prompt(config.words_target),
            output_config={
                "format": {"type": "json_schema", "schema": SCRIPT_SCHEMA},
                "effort": config.effort,
            },
            messages=[{"role": "user", "content": build_user_prompt(item)}],
        )
    except anthropic.AuthenticationError as exc:
        raise YtokshortsError(
            "Anthropic API key missing or invalid. Set ANTHROPIC_API_KEY, or run "
            "with --no-llm to script straight from the headline."
        ) from exc
    except anthropic.APIError as exc:  # rate limits, server errors, etc.
        raise YtokshortsError(f"Anthropic API error: {exc}") from exc

    if response.stop_reason == "refusal":
        raise YtokshortsError("Claude declined to write this script.")

    text = next((b.text for b in response.content if b.type == "text"), "")
    return parse_script_response(text, fallback=item.title)


def parse_script_response(text: str, *, fallback: str) -> ScriptResult:
    """Parse the model's JSON response into a :class:`ScriptResult` (pure)."""
    try:
        data = json.loads(text)
        title = str(data.get("title") or fallback).strip()
        script = str(data.get("script") or "").strip()
    except (json.JSONDecodeError, AttributeError):
        # Structured outputs make this unlikely, but degrade gracefully.
        title, script = fallback, text.strip()
    if not script:
        raise YtokshortsError("Claude returned an empty script.")
    return ScriptResult(title=_trim_title(title), script=script)


def _trim_title(title: str) -> str:
    """Clamp a title to 60 chars on a word boundary."""
    title = re.sub(r"\s+", " ", title).strip().strip('"')
    if len(title) <= 60:
        return title
    return title[:57].rsplit(" ", 1)[0] + "..."
