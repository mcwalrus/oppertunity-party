"""Scraper for Opportunity Party blog posts via RSS feed."""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import TYPE_CHECKING

from markdownify import markdownify

if TYPE_CHECKING:
    from pathlib import Path

    from bs4 import BeautifulSoup

from .client import DATA_DIR, fetch_html, fetch_page, save_content
from .models import BlogPost

logger = logging.getLogger(__name__)

RSS_URL_PATH = "/news.rss"


def scrape_blog_posts(max_posts: int = 50) -> list[BlogPost]:
    """Scrape blog posts from the RSS feed and individual article pages."""
    items: list[BlogPost] = []

    try:
        rss_xml = fetch_html(RSS_URL_PATH)
    except Exception as e:
        logger.error("Failed to fetch blog RSS: %s", e)
        return items

    feed_items = _parse_rss(rss_xml)
    logger.info("Found %d blog posts in RSS feed", len(feed_items))

    for title, url_path, pub_date, author in feed_items[:max_posts]:
        try:
            article_soup = fetch_page(url_path)
            content_md = _extract_article_content(article_soup)

            items.append(
                BlogPost(
                    title=title,
                    url=f"https://www.opportunity.org.nz{url_path}",
                    date=pub_date,
                    excerpt="",
                    content=content_md,
                    author=author,
                )
            )
            logger.info("Scraped blog post: %s (%s)", title, pub_date)
        except Exception as e:
            logger.error("Failed to scrape blog post '%s': %s", title, e)

    return items


def _parse_rss(xml: str) -> list[tuple[str, str, str, str]]:
    """Parse RSS XML and return list of (title, url_path, date, author)."""
    items: list[tuple[str, str, str, str]] = []
    root = ET.fromstring(xml)
    channel = root.find("channel")
    if channel is None:
        return items
    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_date_el = item.find("pubDate")
        author_el = item.find("author")

        title = title_el.text.strip() if title_el is not None and title_el.text else ""
        link = link_el.text.strip() if link_el is not None and link_el.text else ""
        pub_date_raw = (
            pub_date_el.text.strip() if pub_date_el is not None and pub_date_el.text else ""
        )
        author = author_el.text.strip() if author_el is not None and author_el.text else ""

        if not link:
            continue

        # Convert pubDate to YYYY-MM-DD
        date_fmt = _parse_rfc822_date(pub_date_raw)

        # Extract path from full URL
        url_path = link.replace("http://www.opportunity.org.nz", "").replace(
            "https://www.opportunity.org.nz", ""
        )
        if not url_path.startswith("/"):
            url_path = "/" + url_path

        items.append((title, url_path, date_fmt, author))
    return items


def _parse_rfc822_date(raw: str) -> str:
    """Convert RFC 822 date string to YYYY-MM-DD."""
    try:
        dt = datetime.strptime(raw, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return ""


def _extract_article_content(soup: BeautifulSoup) -> str:
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


def save_blog_posts(items: list[BlogPost]) -> dict[str, Path]:
    """Save blog posts to markdown files and JSON index."""
    output_dir = DATA_DIR / "blog"
    saved: dict[str, Path] = {}

    for item in items:
        slug = _title_to_slug(item.title)
        date_prefix = item.date + "-" if item.date else ""
        md_path = save_content(
            output_dir,
            f"{date_prefix}{slug}.md",
            _format_blog_md(item),
        )
        saved[f"{date_prefix}{slug}"] = md_path

    json_data = [
        {
            "title": i.title,
            "url": i.url,
            "date": i.date,
            "excerpt": i.excerpt,
            "content": i.content,
            "author": i.author,
            "scraped_at": i.scraped_at,
        }
        for i in items
    ]
    json_path = save_content(
        output_dir, "index.json", json.dumps(json_data, indent=2, ensure_ascii=False)
    )
    saved["_index"] = json_path
    return saved


def _format_blog_md(item: BlogPost) -> str:
    meta = [f"**Title**: {item.title}"]
    if item.date:
        meta.append(f"**Date**: {item.date}")
    if item.author:
        meta.append(f"**Author**: {item.author}")
    meta.append(f"**URL**: {item.url}")
    meta.append(f"**Scraped**: {item.scraped_at}")

    return "\n".join(meta) + "\n\n" + item.content + "\n"
