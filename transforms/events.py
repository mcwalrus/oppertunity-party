"""Transform events from data/clean/ to site/src/content/events/."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from transforms.clean import normalise_blank_runs

if TYPE_CHECKING:
    from pathlib import Path


def transform_events(clean_dir: Path, content_dir: Path) -> None:
    """Read data/clean/event/ and write Astro-compatible markdown to site/src/content/events/."""
    events_dir = clean_dir / "event"
    out_dir = content_dir / "events"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not events_dir.exists():
        return

    for item_dir in sorted(events_dir.iterdir()):
        if not item_dir.is_dir():
            continue
        slug = item_dir.name

        meta_file = item_dir / "meta.json"
        md_file = item_dir / f"{slug}.md"
        if not md_file.exists():
            continue

        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
        body = _extract_body(md_file.read_text(encoding="utf-8"))

        title = str(meta.get("title") or slug)
        date = str(meta.get("date") or "")
        when = str(meta.get("time") or "")  # clean layer stores as "time"; Astro schema: "when"
        venue = str(meta.get("venue") or "")
        address = str(meta.get("address") or "")
        location = str(meta.get("location") or "")
        url = str(meta.get("source_url") or "")
        scraped = str(meta.get("ingested_at") or "")

        fm_lines = ["---", f'title: "{_esc(title)}"', f"slug: {slug}"]
        if date:
            fm_lines.append(f'date: "{_esc(date)}"')
        if when:
            fm_lines.append(f'when: "{_esc(when)}"')
        if venue:
            fm_lines.append(f'venue: "{_esc(venue)}"')
        if address:
            fm_lines.append(f'address: "{_esc(address)}"')
        if location:
            fm_lines.append(f'location: "{_esc(location)}"')
        if url:
            fm_lines.append(f'url: "{_esc(url)}"')
        if scraped:
            fm_lines.append(f'scrapedAt: "{_esc(scraped)}"')
        fm_lines.append("---")

        output = normalise_blank_runs("\n".join(fm_lines) + "\n" + body)
        (out_dir / f"{slug}.md").write_text(output, encoding="utf-8")
        print(f"  📝 events/{slug}.md")


def _extract_body(content: str) -> str:
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            return parts[2]
    return content


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
