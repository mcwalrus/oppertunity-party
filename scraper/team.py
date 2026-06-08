"""Scraper for Opportunity Party team / candidate pages."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from markdownify import markdownify

from .client import DATA_DIR, fetch_page, save_content
from .models import TeamMember

logger = logging.getLogger(__name__)


def scrape_team() -> list[TeamMember]:
    """Scrape the team page and individual candidate profile pages."""
    members: list[TeamMember] = []

    # Scrape the leader profile first
    try:
        leader_soup = fetch_page("/meet-q")
        leader_name = _extract_title(leader_soup)
        leader_content = _extract_member_content(leader_soup)
        members.append(
            TeamMember(
                name=leader_name,
                role="Party Leader",
                url="https://www.opportunity.org.nz/meet-q",
                content=leader_content,
            )
        )
        logger.info("Scraped leader: %s", leader_name)
    except Exception as e:
        logger.error("Failed to scrape leader page: %s", e)

    # Scrape the team listing page
    try:
        soup = fetch_page("/team")
    except Exception as e:
        logger.error("Failed to fetch team page: %s", e)
        return members

    member_links = _extract_member_links(soup)
    logger.info("Found %d team member links", len(member_links))

    for name, path in member_links:
        try:
            member_soup = fetch_page(path)
            content_md = _extract_member_content(member_soup)
            role = _extract_role(member_soup)

            members.append(
                TeamMember(
                    name=name,
                    role=role,
                    url=f"https://www.opportunity.org.nz{path}",
                    content=content_md,
                )
            )
            logger.info("Scraped team member: %s", name)
        except Exception as e:
            logger.error("Failed to scrape team member %s: %s", name, e)

    return members


def save_team(members: list[TeamMember]) -> dict[str, Path]:
    """Save team data to markdown files and JSON index."""
    output_dir = DATA_DIR / "team"
    saved: dict[str, Path] = {}

    for member in members:
        slug = _name_to_slug(member.name)
        md_path = save_content(
            output_dir,
            f"{slug}.md",
            _format_member_md(member),
        )
        saved[slug] = md_path

    json_data = [
        {
            "name": m.name,
            "role": m.role,
            "url": m.url,
            "content": m.content,
            "scraped_at": m.scraped_at,
        }
        for m in members
    ]
    json_path = save_content(output_dir, "index.json", json.dumps(json_data, indent=2, ensure_ascii=False))
    saved["_index"] = json_path
    return saved


def _extract_member_links(soup) -> list[tuple[str, str]]:
    """Extract candidate names and profile links from the team page.

    Opportunity Party uses /candidate-{slug} URLs for individual profiles.
    The link text contains the name, role, and electorate concatenated.
    """
    links: list[tuple[str, str]] = []
    seen: set[str] = set()

    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "")
        text = a_tag.get_text(strip=True)

        if href.startswith("/candidate-") and href not in seen and text:
            seen.add(href)
            # Parse the name out of the combined text.
            # Links look like: "Qiulae (Q) WongParty LeaderMt. Albert"
            # or "Daniel EbDeputy LeaderKaipara Ki Mahurangi"
            # or "KaylaKingdon-BebbWELLINGTON BAYS"
            # Strategy: the /candidate- slug usually replaces spaces with hyphens
            # and keeps the name. We'll extract the name from the slug.
            slug = href.replace("/candidate-", "")
            name = slug.replace("-", " ").title()

            # But try to get a better name from the text.
            # The text format is: FirstName LastNameRoleElectorate
            # We can use the slug to help parse, or just use the slug-derived name.
            # Let's also look for nested elements with cleaner text.
            name_el = a_tag.find(["h2", "h3", "h4", ".name", ".candidate-name"])
            if name_el:
                name = name_el.get_text(strip=True)
            else:
                # Try to find the name from the first text node or <strong>
                strong = a_tag.find("strong")
                if strong:
                    name = strong.get_text(strip=True)
                else:
                    # Use slug-derived name as fallback
                    name = slug.replace("-", " ").title()

            links.append((name, href))

    return links


def _extract_title(soup) -> str:
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    title = soup.find("title")
    if title:
        return title.get_text(strip=True).split("|")[0].strip()
    return "Unknown"


def _extract_role(soup) -> str:
    for selector in [".role", ".position", ".title", "h2", ".subtitle"]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(strip=True)
            if text and len(text) < 200:
                return text
    return ""


def _extract_member_content(soup) -> str:
    for selector in ["main", "[role='main']", ".page-content", "article"]:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 50:
            return markdownify(str(el), heading_style="ATX").strip()
    return ""


def _name_to_slug(name: str) -> str:
    slug = name.lower().replace(" ", "-").replace("/", "-")
    keep = "abcdefghijklmnopqrstuvwxyz0123456789-"
    slug = "".join(c if c in keep else "" for c in slug)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:60]


def _format_member_md(member: TeamMember) -> str:
    lines = [f"# {member.name}", ""]
    if member.role:
        lines.append(f"**Role**: {member.role}")
        lines.append("")
    lines.extend(
        [
            f"> **URL**: {member.url}",
            f"> **Scraped**: {member.scraped_at}",
            "",
            member.content,
        ]
    )
    return "\n".join(lines) + "\n"