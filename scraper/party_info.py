"""Scraper for Opportunity Party information pages."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from markdownify import markdownify

from .client import DATA_DIR, fetch_page, save_content
from .models import PartyInfo

logger = logging.getLogger(__name__)


def scrape_party_info() -> list[PartyInfo]:
    """Scrape party information and about pages."""
    pages: list[PartyInfo] = []

    # Scrape the main party-information page
    try:
        soup = fetch_page("/party-information")
        content_md = _extract_content(soup)

        pages.append(
            PartyInfo(
                section="party-information",
                url="https://www.opportunity.org.nz/party-information",
                content=content_md,
            )
        )
        logger.info("Scraped party-information page")

        # Look for sub-links on the party-information page
        sub_links = _discover_sub_links(soup)
        for section_name, path in sub_links.items():
            try:
                sub_soup = fetch_page(path)
                sub_content = _extract_content(sub_soup)
                pages.append(
                    PartyInfo(
                        section=section_name,
                        url=f"https://www.opportunity.org.nz{path}",
                        content=sub_content,
                    )
                )
                logger.info("Scraped party info sub-page: %s", section_name)
            except Exception as e:
                logger.error("Failed to scrape sub-page %s: %s", section_name, e)

    except Exception as e:
        logger.error("Failed to scrape party-information: %s", e)

    # Scrape the about page
    try:
        about_soup = fetch_page("/about")
        about_content = _extract_content(about_soup)
        pages.append(
            PartyInfo(
                section="about",
                url="https://www.opportunity.org.nz/about",
                content=about_content,
            )
        )
        logger.info("Scraped about page")
    except Exception as e:
        logger.error("Failed to scrape about page: %s", e)

    return pages


def save_party_info(pages: list[PartyInfo]) -> dict[str, Path]:
    """Save party information to markdown files and JSON index."""
    output_dir = DATA_DIR / "party-information"
    saved: dict[str, Path] = {}

    for page in pages:
        slug = page.section.replace(" ", "-").lower()
        md_path = save_content(
            output_dir,
            f"{slug}.md",
            _format_info_md(page),
        )
        saved[slug] = md_path

    json_data = [
        {
            "section": p.section,
            "url": p.url,
            "content": p.content,
            "scraped_at": p.scraped_at,
        }
        for p in pages
    ]
    json_path = save_content(
        output_dir,
        "index.json",
        json.dumps(json_data, indent=2, ensure_ascii=False),
    )
    saved["_index"] = json_path
    return saved


def _discover_sub_links(soup) -> dict[str, str]:
    """Find sub-page links on the party-information page."""
    sub_links: dict[str, str] = {}
    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "")
        text = a_tag.get_text(strip=True)
        if any(
            keyword in href.lower()
            for keyword in ["constitution", "governance", "registration", "rules"]
        ):
            name = text if text else href.strip("/").split("/")[-1].replace("-", " ")
            sub_links[name] = href
    return sub_links


def _extract_content(soup) -> str:
    for selector in ["main", "[role='main']", ".page-content", "article"]:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 50:
            return markdownify(str(el), heading_style="ATX").strip()
    return ""


def _format_info_md(page: PartyInfo) -> str:
    lines = [
        f"# {page.section.replace('-', ' ').title()}",
        "",
        f"> **URL**: {page.url}",
        f"> **Scraped**: {page.scraped_at}",
        "",
        page.content,
    ]
    return "\n".join(lines) + "\n"