"""Transform events from data/ to site/src/content/events/."""

from pathlib import Path

from transforms.clean import (
    clean_body,
    extract_metadata_fields,
    normalise_blank_runs,
)


def transform_events(data_dir: Path, content_dir: Path) -> None:
    """Read data/events/ and write clean markdown to site/src/content/events/."""
    events_dir = data_dir / "events"
    out_dir = content_dir / "events"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not events_dir.exists():
        return

    for md_file in sorted(events_dir.glob("*.md")):
        if md_file.name == "index.json":
            continue

        body = md_file.read_text(encoding="utf-8")
        fields, body = extract_metadata_fields(body)

        title = fields.get("Title", md_file.stem)
        date = fields.get("Date", "")
        location = fields.get("Location", "")
        url = fields.get("URL", "")
        scraped = fields.get("Scraped", "")
        when = fields.get("When", "")
        venue = fields.get("Venue", "")
        address = fields.get("Address", "")

        slug = md_file.stem

        # Clean body
        body = clean_body(body, strip_footer=False, strip_media_contact=False)

        # Build frontmatter
        fm_lines = [
            "---",
            f'title: "{_esc(title)}"',
            f"slug: {slug}",
        ]
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

        frontmatter = "\n".join(fm_lines)
        output = frontmatter + "\n" + body
        output = normalise_blank_runs(output)

        out_file = out_dir / f"{slug}.md"
        out_file.write_text(output, encoding="utf-8")
        print(f"  📝 events/{slug}.md")


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
