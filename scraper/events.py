"""Scraper for Opportunity Party events from /events calendar page."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING

from bs4 import Tag
from markdownify import markdownify

if TYPE_CHECKING:
    from pathlib import Path

from .client import DATA_DIR, fetch_page, save_content
from .models import EventItem

logger = logging.getLogger(__name__)

EVENTS_URL_PATH = "/events"

_MONTHS_RE = re.compile(
    r"^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)",
    flags=re.IGNORECASE,
)


# ---------------------------------------------------------------
#  PUBLIC API
# ---------------------------------------------------------------


def scrape_events() -> list[EventItem]:
    """Scrape upcoming events from the /events calendar page."""
    items: list[EventItem] = []

    try:
        soup = fetch_page(EVENTS_URL_PATH, category="events")
    except Exception as exc:
        logger.error("Failed to fetch events page: %s", exc)
        return items

    event_cards = soup.find_all(class_="event-card")
    logger.info("Found %d event cards", len(event_cards))

    for card in event_cards:
        try:
            item = _parse_event_card(card)
            if item:
                items.append(item)
                logger.info(
                    "Scraped event: %s (%s, %s)",
                    item.title,
                    item.date,
                    item.location,
                )
        except Exception as exc:
            text = card.get_text(strip=True)[:80]
            logger.error("Failed to parse event card '%s...': %s", text, exc)

    return items


def save_events(items: list[EventItem]) -> dict[str, Path]:
    """Save events to markdown files and a JSON index."""
    output_dir = DATA_DIR / "events"
    saved: dict[str, Path] = {}

    for item in items:
        slug = _title_to_slug(item.title)
        date_prefix = item.date + "-" if item.date else ""
        md_path = save_content(
            output_dir,
            f"{date_prefix}{slug}.md",
            _format_event_md(item),
        )
        saved[f"{date_prefix}{slug}"] = md_path

    json_data = [
        {
            "title": i.title,
            "url": i.url,
            "date": i.date,
            "time": i.time,
            "location": i.location,
            "description": i.description,
            "scraped_at": i.scraped_at,
        }
        for i in items
    ]
    json_path = save_content(
        output_dir, "index.json", json.dumps(json_data, indent=2, ensure_ascii=False)
    )
    saved["_index"] = json_path
    return saved


# ---------------------------------------------------------------
#  PARSING
# ---------------------------------------------------------------


def _parse_event_card(card: Tag) -> EventItem | None:
    """Extract event details from an event-card DOM element."""
    link_el = card.find("a", href=True)
    if not link_el:
        return None

    url_path = str(link_el["href"])  # type: ignore[arg-type]
    if not url_path.startswith("/"):
        url_path = "/" + url_path

    title = _extract_title(card)
    event_date, event_time = _extract_when(card)
    location = _extract_location(card)

    description = ""
    if event_date and event_date >= datetime.now().strftime("%Y-%m-%d"):
        try:
            event_soup = fetch_page(url_path, category="events")
            description = _extract_event_description(event_soup)
        except Exception as exc:
            logger.warning("Could not fetch event detail %s: %s", url_path, exc)

    return EventItem(
        title=title,
        url=f"https://www.opportunity.org.nz{url_path}",
        date=event_date,
        time=event_time,
        location=location,
        description=description,
    )


def _extract_title(card: Tag) -> str:
    """Extract event title from card."""
    for sel in (".event__name", "h3", "h4", ".title"):
        el = card.select_one(sel)
        if el:
            return el.get_text(strip=True)

    parts = card.get_text(separator="\n", strip=True).splitlines()
    for part in parts:
        if _looks_like_date(part):
            continue
        if _looks_like_location(part):
            continue
        if part and len(part) > 3:
            return part
    return "Untitled Event"


def _extract_when(card: Tag) -> tuple[str, str]:
    """Extract (date, time) from event card."""
    text = card.get_text(separator="|", strip=True)
    head, *_ = text.split("|")
    head = head.strip()

    date_fmt = ""
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            dt = datetime.strptime(head, fmt)
            date_fmt = dt.strftime("%Y-%m-%d")
            break
        except ValueError:
            continue

    return date_fmt, ""


def _extract_location(card: Tag) -> str:
    """Extract event location from card."""
    text = card.get_text(separator="|", strip=True)
    parts = [p.strip() for p in text.split("|")]

    if len(parts) >= 3:
        return parts[2]
    if len(parts) >= 2 and not _looks_like_date(
        parts[1].split()[0] if " " in parts[1] else parts[1]
    ):
        return parts[1]
    return ""


def _looks_like_date(text: str) -> bool:
    return bool(_MONTHS_RE.match(text.strip()))


def _looks_like_location(text: str) -> bool:
    return "," in text and len(text) > 10


def _extract_event_description(soup: Tag) -> str:
    """Parse the event detail page into clean structured text."""
    main = soup.select_one("main, [role='main'], .page-content")
    if not main:
        return ""

    parts: list[str] = []

    # --- When / Where header block ---
    header = main.select_one(".event-header, section[aria-label='Event info']")
    if header:
        when_col = _header_col(header, "When")
        where_col = _header_col(header, "Where")

        if when_col:
            # e.g. "June 09, 2026 at 7:00pm" and "2 hrs"
            time_line = _col_text(when_col, "fa-calendar", "i ~ span, span:has(+ span)")
            duration = _col_text(when_col, "fa-clock", None)
            when_parts = [t for t in (time_line, duration) if t]
            if when_parts:
                parts.append("**When**: " + " · ".join(when_parts))

        if where_col:
            venue = (where_col.select_one(".h4, h4") or Tag()).get_text(strip=True)
            addr_el = where_col.select_one("a[href*='maps.google']")
            addr = addr_el.get_text(strip=True) if addr_el else ""
            if venue:
                parts.append(f"**Venue**: {venue}")
            if addr:
                parts.append(f"**Address**: {addr}")

        if parts:
            parts.append("")

    # --- Body / intro ---
    intro = main.select_one("#intro, .intro, .event-description, .page-body")
    if intro:
        body = markdownify(str(intro), heading_style="ATX").strip()
        # drop any residual RSVP noise
        lines = [ln for ln in body.splitlines() if "RSVP" not in ln or len(ln) > 20]
        parts.append("\n".join(lines))

    return "\n".join(parts).strip()


def _header_col(header: Tag, label: str) -> Tag | None:
    """Find the When or Where column by its headline label."""
    for span in header.select(".event-header-column-headline"):
        if span.get_text(strip=True).lower() == label.lower():
            return span.find_parent("div", recursive=False) or span.parent
    return None


def _col_text(col: Tag, icon_class: str, _unused: str | None) -> str:
    """Extract visible text from a column span that sits next to a FA icon."""
    for icon in col.select(f"i.{icon_class}"):
        sibling = icon.find_next_sibling(string=True)
        if not sibling:
            parent = icon.parent
            if parent:
                text = parent.get_text(separator=" ", strip=True)
                # strip the icon's own text if any
                return text
        else:
            return sibling.strip()
    # Fallback: grab any <span> that's not the countdown
    for span in col.select("span"):
        cls = " ".join(span.get("class") or [])  # type: ignore[arg-type]
        if "headline" in cls or "h4" in cls:
            continue
        text = span.get_text(strip=True)
        if text and icon_class.replace("fa-", "") in ("clock", "calendar"):
            return text
    return ""


def _title_to_slug(title: str) -> str:
    slug = title.lower()
    keep = "abcdefghijklmnopqrstuvwxyz0123456789- "
    slug = "".join(c if c in keep else "" for c in slug)
    slug = slug.strip().replace(" ", "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:80]


def _format_event_md(item: EventItem) -> str:
    meta = [f"**Title**: {item.title}"]
    if item.date:
        meta.append(f"**Date**: {item.date}")
    if item.time:
        meta.append(f"**Time**: {item.time}")
    if item.location:
        meta.append(f"**Location**: {item.location}")
    meta.append(f"**URL**: {item.url}")
    meta.append(f"**Scraped**: {item.scraped_at}")

    return "\n".join(meta) + "\n\n" + item.description + "\n"
