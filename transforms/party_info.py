"""Transform party information from data/ to site/src/content/party-info/."""

from pathlib import Path

from transforms.clean import (
    clean_body,
    extract_metadata_fields,
    normalise_blank_runs,
)


def transform_party_info(data_dir: Path, content_dir: Path) -> None:
    """Read data/party-information/ and write clean markdown to site/src/content/party-info/."""
    pi_dir = data_dir / "party-information"
    out_dir = content_dir / "party-info"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not pi_dir.exists():
        return

    for md_file in sorted(pi_dir.glob("*.md")):
        if md_file.name == "index.json":
            continue

        body = md_file.read_text(encoding="utf-8")
        fields, body = extract_metadata_fields(body)

        # Use filename stem as slug and section title
        slug = md_file.stem
        title = fields.get("Title", slug.replace("-", " ").title())
        url = fields.get("URL", "")
        scraped = fields.get("Scraped", "")

        # Clean body — pass title to strip duplicate H1
        body = clean_body(body, title=title, strip_footer=True, strip_media_contact=False)

        # Build frontmatter
        fm_lines = [
            "---",
            f'title: "{_esc(title)}"',
            f"slug: {slug}",
        ]
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
        print(f"  📝 party-info/{slug}.md")


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
