"""Compatibility shim - re-exports from blog_posts and events.

The public scraper API has moved:
  - blog posts  → scraper.blog_posts
  - events      → scraper.events

This module re-exports the helpers that mcp/repository.py relies on so that
existing callers continue to work without changes.
"""

from .blog_posts import (  # noqa: F401
    _extract_article_content,
    _title_to_slug,
)
