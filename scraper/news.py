"""Scraper for Opportunity Party news / media releases."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from markdownify import markdownify

from .client import DATA_DIR, fetch_page, save_content
from .models import NewsItem

logger = logging.getLogger(__name__)


def scrape_news(max_articles: int = 30) -> list[NewsItem]:
    """Scrape the news index and individual article pages."""
    items: list[NewsItem] = []

    try:
        soup = fetch_page("/news")
    except Exception as e:
        logger.error("Failed to fetch news page: %s", e)
        return items

    article_links = _extract_article_links(soup)
    logger.info("Found %d news article links", len(article_links))

    for title, url_path, date in article_links[:max_articles]:
        try:
            article_soup = fetch_page(url_path)
            content_md = _extract_article_content(article_soup)

            items.append(
                NewsItem(
                    title=title,
                    url=f"https://www.opportunity.org.nz{url_path}",
                    date=date,
                    content=content_md,
                )
            )
            logger.info("Scraped news: %s", title)
        except Exception as e:
            logger.error("Failed to scrape news article '%s': %s", title, e)

    return items


def save_news(items: list[NewsItem]) -> dict[str, Path]:
    """Save news articles to markdown files and JSON index."""
    output_dir = DATA_DIR / "news"
    saved: dict[str, Path] = {}

    for item in items:
        slug = _title_to_slug(item.title)
        md_path = save_content(
            output_dir,
            f"{slug}.md",
            _format_news_md(item),
        )
        saved[slug] = md_path

    json_data = [
        {
            "title": i.title,
            "url": i.url,
            "date": i.date,
            "content": i.content,
            "scraped_at": i.scraped_at,
        }
        for i in items
    ]
    json_path = save_content(output_dir, "index.json", json.dumps(json_data, indent=2, ensure_ascii=False))
    saved["_index"] = json_path
    return saved


def _extract_article_links(soup) -> list[tuple[str, str, str]]:
    """Extract article titles, URLs, and dates from the news listing page.

    Opportunity Party news articles live at root-level URLs with
    underscore-separated slugs (e.g. /the_pray_and_delay_budget).
    They're not under /news/ sub-paths.
    """
    articles: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    # Known non-article root-level paths to skip
    SKIP_PREFIXES = (
        "/policy", "/team", "/about", "/events", "/news", "/get-involved",
        "/volunteer", "/join", "/donate", "/contact", "/party-information",
        "/login", "/subscribe", "/meet-q", "/candidate-", "/cdn-cgi",
    )

    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "")
        title = a_tag.get_text(strip=True)

        # Must be a root-level path with underscores or hyphens (news slug pattern)
        # Must not be in the skip list, must have meaningful title length
        is_article = (
            href.startswith("/")
            and not any(href.startswith(prefix) for prefix in SKIP_PREFIXES)
            and href != "/"
            and title
            and len(title) > 10
            and href not in seen
            # News slugs contain underscores or are known patterns
            and ("_" in href or len(href) > 5)
        )

        if is_article and href not in seen:
            seen.add(href)
            date = _find_nearby_date(a_tag)
            articles.append((title, href, date))

    return articles


def _find_nearby_date(a_tag) -> str:
    """Look for a date near an article link."""
    parent = a_tag.parent
    for _ in range(3):
        if parent is None:
            break
        for selector in ["time", ".date", ".posted-at", ".post-date", "[datetime]"]:
            date_el = parent.select_one(selector)
            if date_el:
                dt = date_el.get("datetime", "") or date_el.get_text(strip=True)
                if dt:
                    return dt
        parent = parent.parent
    return ""


def _extract_article_content(soup) -> str:
    for selector in ["main", "[role='main']", ".page-content", "article"]:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 50:
            return markdownify(str(el), heading_style="ATX").strip()
    return ""


def _title_to_slug(title: str) -> str:
    slug = title.lower()
    keep = "abcdefghijklmnopqrstuvwxyz0123456789- "
    slug = "".join(c if c in keep else "" for c in slug)
    slug = slug.strip().replace(" ", "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:80]


def _format_news_md(item: NewsItem) -> str:
    lines = [f"# {item.title}", ""]
    if item.date:
        lines.append(f"**Date**: {item.date}")
        lines.append("")
    lines.extend(
        [
            f"> **URL**: {item.url}",
            f"> **Scraped**: {item.scraped_at}",
            "",
            item.content,
        ]
    )
    return "\n".join(lines) + "\n"