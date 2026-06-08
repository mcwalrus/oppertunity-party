"""Scraper for Opportunity Party team / candidate pages."""

from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from markdownify import markdownify

if TYPE_CHECKING:
    from pathlib import Path

    from bs4 import BeautifulSoup, Tag

from .client import DATA_DIR, fetch_page, save_content
from .models import TeamMember

logger = logging.getLogger(__name__)


def scrape_team() -> list[TeamMember]:
    """Scrape the team page and individual candidate profile pages.

    Note: The /meet-q page (party leader) is scraped by party_info.py and
    saved under data/party-information/, not here.
    """
    members: list[TeamMember] = []

    # Scrape the team listing page
    try:
        soup = fetch_page("/team", category="team")
    except Exception as e:
        logger.error("Failed to fetch team page: %s", e)
        return members

    member_links = _extract_member_links(soup)
    logger.info("Found %d team member links", len(member_links))

    for name, path in member_links:
        try:
            member_soup = fetch_page(path, category="team")
            # Use the candidate's own page h1 as the authoritative name
            page_name = _extract_title(member_soup)
            if page_name and page_name not in ("Unknown", ""):
                name = page_name
            content_md = _extract_member_content(member_soup)
            role = _extract_role(member_soup)
            electorate = _extract_electorate(member_soup)
            slug = _path_to_slug(path)

            members.append(
                TeamMember(
                    name=name,
                    slug=slug,
                    role=role,
                    url=f"https://www.opportunity.org.nz{path}",
                    electorate=electorate,
                    content=content_md,
                )
            )
            logger.info(
                "Scraped team member: %s (slug: %s, electorate: %s)", name, slug, electorate
            )
        except Exception as e:
            logger.error("Failed to scrape team member %s: %s", name, e)

    return members


def save_team(members: list[TeamMember]) -> dict[str, Path]:
    """Save team data to markdown files and JSON index.

    Also removes the stale data/team/meet-q.md file if it exists, since
    /meet-q is now managed by party_info.py under data/party-information/.
    """
    output_dir = DATA_DIR / "team"
    saved: dict[str, Path] = {}

    # Remove stale meet-q.md that may have been created by a previous scrape
    stale = output_dir / "meet-q.md"
    if stale.exists():
        stale.unlink()
        logger.info("Removed stale data/team/meet-q.md (now lives in data/party-information/)")
    stale_pdf = output_dir / "meet-q.pdf"
    if stale_pdf.exists():
        stale_pdf.unlink()

    for member in members:
        slug = member.slug or _name_to_slug(member.name)
        md_path = save_content(
            output_dir,
            f"{slug}.md",
            _format_member_md(member),
        )
        saved[slug] = md_path

    json_data = [
        {
            "name": m.name,
            "slug": m.slug or _name_to_slug(m.name),
            "role": m.role,
            "url": m.url,
            "electorate": m.electorate,
            "content": m.content,
            "scraped_at": m.scraped_at,
        }
        for m in members
    ]
    json_path = save_content(
        output_dir, "index.json", json.dumps(json_data, indent=2, ensure_ascii=False)
    )
    saved["_index"] = json_path

    index_md_path = save_content(output_dir, "INDEX.md", _format_team_index(members))
    saved["_index_md"] = index_md_path

    return saved


def _extract_member_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Extract candidate names and profile links from the team page.

    Opportunity Party uses /candidate-{slug} URLs for individual profiles.
    The link text contains the name, role, and electorate concatenated.
    """
    links: list[tuple[str, str]] = []
    seen: set[str] = set()

    for a_tag in soup.select("a[href]"):
        raw_href = a_tag.get("href", "")
        if not isinstance(raw_href, str):
            continue
        href: str = raw_href
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
                name = strong.get_text(strip=True) if strong else slug.replace("-", " ").title()

            links.append((name, href))

    return links


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract the page title / candidate name.

    Prefers the first h1 inside the main content container (to avoid picking
    up site-header or login h1s).  Falls back to the first h1 anywhere, then
    the ``<title>`` element.
    """
    import re as _re

    def _h1_text(el: Tag) -> str:
        # Use separator=" " so adjacent child spans are joined with a space
        return _re.sub(r"\s{2,}", " ", el.get_text(separator=" ", strip=True))

    main = soup.select_one("main, [role='main'], .page-content, article")
    if main:
        h1 = main.find("h1")
        if h1:
            return _h1_text(h1)
    # Fall back: first h1 that isn't a boilerplate (login / nav)
    for h1 in soup.find_all("h1"):
        text = _h1_text(h1)
        if text and "sign in" not in text.lower() and "log in" not in text.lower():
            return text
    title = soup.find("title")
    if title:
        return title.get_text(strip=True).split("|")[0].strip()
    return "Unknown"


def _extract_role(soup: BeautifulSoup) -> str:
    """Extract the candidate's role (Party Leader / Deputy Leader / Candidate).

    Candidate pages carry a media-contact footer that reads e.g.
    "Party Leader & Candidate for Opportunity (Mt. Albert)" or
    "Candidate for Opportunity (Kaipara ki Mahurangi) and Deputy Leader".
    We parse that to produce a clean role label.
    """
    main = soup.select_one("main, [role='main'], .page-content, article") or soup
    # Look for a h5 or h6 containing "Media Contact" and grab the next sibling text
    for heading in main.find_all(["h5", "h6"]):
        if "media contact" in heading.get_text(strip=True).lower():
            # Walk forward siblings for a non-empty text block
            for sibling in heading.next_siblings:
                text = (
                    sibling.get_text(" ", strip=True)
                    if hasattr(sibling, "get_text")
                    else str(sibling).strip()
                )
                if not text:
                    continue
                # Classify role from the description
                lower = text.lower()
                if "party leader" in lower:
                    return "Party Leader"
                if "deputy leader" in lower:
                    return "Deputy Leader"
                if "candidate" in lower:
                    return "Candidate"
            break
    return "Candidate"


def _extract_electorate(soup: BeautifulSoup) -> str:
    """Extract the electorate from a candidate page.

    Candidate pages have an all-uppercase ``<h4>`` element near the top of
    the main content, e.g. ``<h4>KAIPARA KI MAHURANGI</h4>``.  We find the
    first h4 whose text is entirely upper-case and return it in title case.
    """
    main = soup.select_one("main, [role='main'], .page-content, article") or soup
    for h4 in main.find_all("h4"):
        text = h4.get_text(strip=True)
        if not text or len(text) > 80:
            continue
        # Must be uppercase (macron variants like Ō/Ā are already uppercase)
        if text == text.upper() and any(c.isalpha() for c in text):
            # Skip generic headings (e.g. "MEDIA CONTACT" caught via h4 on some pages)
            if text.lower() in ("media contact", "donate"):
                continue
            return text.title()
    return ""


def _extract_member_content(soup: BeautifulSoup) -> str:
    for selector in ["main", "[role='main']", ".page-content", "article"]:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 50:
            _strip_email_links(el)
            md = markdownify(str(el), heading_style="ATX").strip()
            return _clean_markdown(md)
    return ""


def _strip_email_links(el: Tag) -> None:
    """Remove Cloudflare email-protection <a> tags from a BeautifulSoup element."""
    for a in el.find_all("a", href=re.compile(r"/cdn-cgi/l/email-protection")):
        a.decompose()


def _clean_markdown(md: str) -> str:
    """Remove donation sections, email-protection links, and duplicate headings."""
    # Belt-and-suspenders: strip any remaining Cloudflare email-protection links
    # (handles nested brackets in link text, e.g. [Email: [email@protected]](url))
    md = re.sub(
        r"\[(?:[^\[\]]|\[[^\]]*\])*\]\(/cdn-cgi/l/email-protection[^)]*\)",
        "",
        md,
        flags=re.IGNORECASE,
    )
    # Remove donation sections: from a "Donate" heading to end of content
    # (these always appear at the bottom, so strip everything from the first
    # donation heading onwards)
    md = re.sub(
        r"(?m)^#{1,6}\s+Donate\b.*",
        "\x00DONATE_CUT",
        md,
        count=1,
        flags=re.IGNORECASE,
    )
    cut = md.find("\x00DONATE_CUT")
    if cut != -1:
        md = md[:cut]
    # Deduplicate consecutive identical heading blocks.
    # Candidate pages render the electorate + name heading twice (hero + body).
    # e.g. "#### ELECTORATE\n\n# Name\n\n#### ELECTORATE\n\n# Name\n\n" → one copy.
    md = re.sub(
        r"((?:#{1,6} [^\n]+\n\n){1,3})\1",
        r"\1",
        md,
    )
    # Tidy up trailing whitespace and excess blank lines
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.rstrip()


def _path_to_slug(path: str) -> str:
    """Derive a clean slug from a URL path like /candidate-daniel-eb."""
    slug = path.strip("/")
    # Strip the /candidate- prefix used for team member pages
    if slug.startswith("candidate-"):
        slug = slug[len("candidate-") :]
    return slug


def _name_to_slug(name: str) -> str:
    slug = name.lower().replace(" ", "-").replace("/", "-")
    keep = "abcdefghijklmnopqrstuvwxyz0123456789-"
    slug = "".join(c if c in keep else "" for c in slug)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")[:60]


def _strip_redundant_name_headings(md: str, name: str, electorate: str) -> str:
    """Strip repeated name/electorate headings already captured in file metadata.

    Candidate profile pages embed the electorate (as ``#### ELECTORATE``) and
    the candidate name (as ``# Name`` and ``## **Name**``) inside the page body.
    Since these are already rendered as structured metadata at the top of the
    file, this function removes the redundant occurrences:

    - Removes the ``#### ELECTORATE`` heading.
    - Removes the repeated ``# Name`` heading (keeps the first/file-title one).
    - Replaces ``## **Name**`` / ``## Name`` / ``## **Name (suffix)**`` bio
      section headers with ``## About``.
    """
    # Strip the #### ELECTORATE heading (already in **Electorate** metadata)
    if electorate:
        md = re.sub(
            rf"(?m)^####\s+{re.escape(electorate.upper())}\s*\n+",
            "",
            md,
        )

    # Strip repeated # Name headings — keep only the first (file title)
    if name:
        first_seen = False

        def _drop_after_first(m: re.Match) -> str:  # type: ignore[type-arg]
            nonlocal first_seen
            if not first_seen:
                first_seen = True
                return m.group(0)
            return ""

        md = re.sub(
            rf"(?m)^#\s+\*{{0,2}}{re.escape(name)}\*{{0,2}}\s*\n+",
            _drop_after_first,
            md,
        )

    # Replace ## **Name** / ## Name / ## **Name (suffix)** with ## About
    # but leave headings already starting with "About" untouched.
    if name:
        md = re.sub(
            rf"(?m)^##\s+\*{{0,2}}{re.escape(name)}(?:\s+\([^)]*\))?\*{{0,2}}\s*$",
            "## About",
            md,
        )

    # Tidy up any excess blank lines introduced by the removals
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip()


def _format_member_md(member: TeamMember) -> str:
    lines = [f"# {member.name}", ""]
    if member.role:
        lines.append(f"**Role**: {member.role}")
    if member.electorate:
        lines.append(f"**Electorate**: {member.electorate}")
    if member.role or member.electorate:
        lines.append("")
    content = _strip_redundant_name_headings(member.content, member.name, member.electorate or "")
    lines.extend(
        [
            f"> **URL**: {member.url}",
            f"> **Scraped**: {member.scraped_at}",
            "",
            content,
        ]
    )
    return "\n".join(lines) + "\n"


def _format_team_index(members: list[TeamMember]) -> str:
    """Generate a human-readable index of all team members / candidates."""
    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d")
    leadership_roles = {"Party Leader", "Deputy Leader"}

    leadership = [m for m in members if m.role in leadership_roles]
    candidates = [m for m in members if m.role not in leadership_roles]
    candidates.sort(key=lambda m: m.name.lower())

    lines = [
        "# Opportunity Party — Team & Candidates Index",
        "",
        "**Source**: [opportunity.org.nz/team](https://www.opportunity.org.nz/team)  ",
        f"**Generated**: {now}",
        "",
        "---",
        "",
    ]

    # Key facts — prefer the entry that has an electorate (i.e. the candidate
    # page, not the generic /meet-q redirect which has no electorate)
    leaders = [m for m in leadership if m.role == "Party Leader"]
    leader = next((m for m in leaders if m.electorate), None) or (leaders[0] if leaders else None)
    deputy = next((m for m in leadership if m.role == "Deputy Leader"), None)
    lines += [
        "## Key Facts",
        "",
    ]
    if leader:
        elec = f" — standing in **{leader.electorate}**" if leader.electorate else ""
        lines.append(f"- **Party Leader**: {leader.name}{elec}")
    if deputy:
        elec = f" — standing in **{deputy.electorate}**" if deputy.electorate else ""
        lines.append(f"- **Deputy Leader**: {deputy.name}{elec}")
    lines.append(f"- **Total candidates**: {len(members)}")
    electorates = [m.electorate for m in members if m.electorate]
    lines.append(f"- **Electorates contested**: {len(set(electorates))}")
    lines.append("")

    # Leadership table
    if leadership:
        lines += [
            "## Leadership",
            "",
            "| Name | Role | Electorate | Profile |",
            "|------|------|------------|---------|",
        ]
        for m in leadership:
            slug = m.slug or _name_to_slug(m.name)
            lines.append(
                f"| [{m.name}]({slug}.md) | {m.role} | {m.electorate or '—'} | [opportunity.org.nz]({m.url}) |"
            )
        lines.append("")

    # Full candidates table
    lines += [
        "## All Candidates (A-Z)",
        "",
        "| Name | Role | Electorate | Profile |",
        "|------|------|------------|---------|",
    ]
    for m in sorted(members, key=lambda m: m.name.lower()):
        slug = m.slug or _name_to_slug(m.name)
        role_label = m.role or "Candidate"
        lines.append(
            f"| [{m.name}]({slug}.md) | {role_label} | {m.electorate or '—'} | [opportunity.org.nz]({m.url}) |"
        )
    lines.append("")

    return "\n".join(lines)
