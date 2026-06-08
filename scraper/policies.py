"""Scraper for Opportunity Party policy pages."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from markdownify import markdownify

if TYPE_CHECKING:
    from pathlib import Path

    from bs4 import BeautifulSoup

from .client import DATA_DIR, fetch_page, save_content
from .models import PolicyPage

logger = logging.getLogger(__name__)

# Known policy slugs from site navigation
POLICY_SLUGS = {
    # Priority policies
    "healthy-oceans": "/healthy-oceans",
    "abundant-energy": "/abundant-energy",
    "productivity-unleashed": "/productivity-unleashed",
    "citizens-voice": "/citizens-voice",
    "tax-reset": "/tax-reset",
    # Other policies
    "clean-up-politics": "/clean_up_politics",
    "honouring-te-tiriti": "/honouring_te_tiriti",
    "future-fit-education": "/future_fit_education",
    "healthy-land": "/healthy_land",
    "healthy-people": "/healthy_people",
    "climate-action": "/climate_action",
    "intergenerational-infrastructure": "/intergenerational_infrastructure",
    "affordable-housing": "/affordable_housing",
    "smart-on-crime": "/smart_on_crime",
}


def scrape_policies() -> list[PolicyPage]:
    """Scrape all known policy pages from the website."""
    policies: list[PolicyPage] = []

    # First get the policy index to discover any new slugs
    try:
        index_soup = fetch_page("/policy", category="policies")
        _discover_policy_links(index_soup)
    except Exception:
        logger.warning("Could not fetch policy index, using known slugs")

    for slug, path in POLICY_SLUGS.items():
        try:
            soup = fetch_page(path, category="policies")
            title = _extract_title(soup)
            pdf_links = _extract_pdf_links(soup)
            content_md = _extract_markdown(soup)
            policy = PolicyPage(
                slug=slug,
                title=title,
                url=f"https://www.opportunity.org.nz{path}",
                content=content_md,
                pdf_downloads=pdf_links,
            )
            policies.append(policy)
            logger.info("Scraped policy: %s (%d PDF links)", title, len(pdf_links))
        except Exception as e:
            logger.error("Failed to scrape policy %s: %s", slug, e)

    return policies


def save_policies(policies: list[PolicyPage]) -> dict[str, Path]:
    """Save each policy into its own directory under data/policies/{slug}/."""
    output_dir = DATA_DIR / "policies"
    saved: dict[str, Path] = {}

    for policy in policies:
        policy_dir = output_dir / policy.slug
        md_path = save_content(
            policy_dir,
            "page.md",
            _format_policy_md(policy),
        )
        saved[policy.slug] = md_path
        logger.debug("Saved %s/page.md", policy.slug)

    json_data = [
        {
            "slug": p.slug,
            "title": p.title,
            "url": p.url,
            "content": p.content,
            "pdf_downloads": p.pdf_downloads,
            "scraped_at": p.scraped_at,
        }
        for p in policies
    ]
    json_path = save_content(
        output_dir, "index.json", json.dumps(json_data, indent=2, ensure_ascii=False)
    )
    saved["_index"] = json_path

    return saved


def _extract_pdf_links(soup: BeautifulSoup) -> list[str]:
    """Extract Google Drive and direct PDF download links from a policy page."""
    links = []
    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "")
        if not isinstance(href, str):
            continue
        if "drive.google.com" in href or href.lower().endswith(".pdf"):
            links.append(href)
    return links


def _discover_policy_links(soup: BeautifulSoup) -> None:
    """Check the policy index page for any new links we don't know about."""
    links = soup.select("a[href]")
    for link in links:
        href = link.get("href", "")
        if not isinstance(href, str):
            continue
        if href.startswith("/policy/"):
            slug = href.replace("/policy/", "").strip("/")
            if slug and slug not in POLICY_SLUGS:
                POLICY_SLUGS[slug] = f"/policy/{slug}"
                logger.info("Discovered new policy slug: %s", slug)


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    title = soup.find("title")
    if title:
        return title.get_text(strip=True).split("|")[0].strip()
    return "Unknown"


def _extract_markdown(soup: BeautifulSoup) -> str:
    for selector in ["main", "[role='main']", ".page-content", "article"]:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 100:
            return markdownify(str(el), heading_style="ATX").strip()
    body = soup.find("body")
    if body:
        for tag in body.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return markdownify(str(body), heading_style="ATX").strip()
    return ""


def _format_policy_md(policy: PolicyPage) -> str:
    lines = [
        f"# {policy.title}",
        "",
        f"> **URL**: {policy.url}",
        f"> **Scraped**: {policy.scraped_at}",
        "",
        policy.content,
    ]
    return "\n".join(lines) + "\n"
