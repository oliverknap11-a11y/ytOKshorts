"""Football-news → Short pipeline.

Fetches headlines from an RSS feed, has Claude write a tight vertical-Short
script, voices it with edge-tts, and composes a 9:16 video with a gradient
background and bold word-by-word captions — reusing the upload/scheduling
machinery from the main package.
"""

from .feeds import NewsItem, fetch_feed, parse_rss

__all__ = ["NewsItem", "fetch_feed", "parse_rss"]
