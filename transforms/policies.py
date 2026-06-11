"""Transform policies from data/ to site/src/content/policies/."""

import json
import re
from pathlib import Path

from transforms.clean import (
    clean_body,
    extract_metadata_fields,
    normalise_blank_runs,
)


def transform_policies(data_dir: Path, content_dir: Path) -> None:
    """Read data/policies/ and write clean markdown to site/src/content/policies/."""
    policies_dir = data_dir / "policies"
    out_dir = content_dir / "policies"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load index.json for metadata
    index_data: dict[str, dict] = {}
    index_file = policies_dir / "index.json"
    if index_file.exists():
        with open(index_file) as f:
            entries = json.load(f)
            for entry in entries:
                index_data[entry["slug"]] = entry

    # Process each policy slug directory
    for slug_dir in sorted(policies_dir.iterdir()):
        if not slug_dir.is_dir():
            continue
        slug = slug_dir.name

        # Find the main markdown file (the one named after the slug)
        main_file = slug_dir / f"{slug}.md"
        if not main_file.exists():
            # Some dirs only have pdf-*.md files (e.g. charter, constitution)
            # Use those as the main content
            pdf_files = sorted(slug_dir.glob("pdf-*.md"))
            if pdf_files:
                _write_policy_from_pdf_only(slug, pdf_files, index_data, out_dir)
            continue

        # Read and process main file
        body = main_file.read_text(encoding="utf-8")
        fields, body = extract_metadata_fields(body)

        # Build frontmatter from index.json + extracted fields
        index_entry = index_data.get(slug, {})
        title = fields.get("Title") or index_entry.get("title", slug.replace("-", " ").title())
        url = fields.get("URL") or index_entry.get("url", "")
        scraped = fields.get("Scraped") or index_entry.get("scraped_at", "")
        pdf_downloads = index_entry.get("pdf_downloads", [])

        # Clean body — pass title to strip duplicate H1
        body = clean_body(body, title=title)

        # Find and append PDF content
        pdf_files = sorted(slug_dir.glob("pdf-*.md"))
        pdf_content = _load_pdf_content(pdf_files)

        # Build output file
        frontmatter = _build_frontmatter(
            slug=slug,
            title=title,
            url=url,
            scraped=scraped,
            pdf_downloads=pdf_downloads,
        )

        output = frontmatter + "\n" + body
        if pdf_content:
            output += "\n\n## Full Policy Detail\n\n" + pdf_content

        output = normalise_blank_runs(output)

        out_file = out_dir / f"{slug}.md"
        out_file.write_text(output, encoding="utf-8")
        print(f"  📝 policies/{slug}.md")


def _write_policy_from_pdf_only(
    slug: str, pdf_files: list[Path], index_data: dict[str, dict], out_dir: Path
) -> None:
    """Handle slug dirs that only have pdf-*.md files (e.g. charter, constitution)."""
    index_entry = index_data.get(slug, {})
    title = index_entry.get("title", slug.replace("-", " ").title())
    url = index_entry.get("url", "")
    scraped = index_entry.get("scraped_at", "")

    pdf_content = _load_pdf_content(pdf_files)

    frontmatter = _build_frontmatter(
        slug=slug,
        title=title,
        url=url,
        scraped=scraped,
        pdf_downloads=index_entry.get("pdf_downloads", []),
    )

    output = frontmatter + "\n" + pdf_content
    output = normalise_blank_runs(output)

    out_file = out_dir / f"{slug}.md"
    out_file.write_text(output, encoding="utf-8")
    print(f"  📝 policies/{slug}.md (PDF-only)")


def _load_pdf_content(pdf_files: list[Path]) -> str:
    """Load and concatenate PDF markdown files, stripping their metadata tables."""
    sections: list[str] = []
    for pdf_file in pdf_files:
        content = pdf_file.read_text(encoding="utf-8")
        # Strip the metadata table at the top of PDF markdown
        content = re.sub(r"^# .+?\n(\|.*?\|.*?\n)+\n*", "", content, count=1)
        # Strip standalone "**Tax**" noise lines from PDF content
        content = re.sub(r"^\*\*Tax\*\*\s*$", "", content, flags=re.MULTILINE)
        # Strip all H1 headings — they duplicate the page template's H1
        content = re.sub(r"^#[^#].+$", "", content, flags=re.MULTILINE)
        # Also strip any leading blank lines
        content = content.lstrip("\n")
        if content.strip():
            sections.append(content.strip())

    return "\n\n".join(sections)


def _build_frontmatter(
    *, slug: str, title: str, url: str, scraped: str, pdf_downloads: list[str]
) -> str:
    """Build YAML frontmatter string."""
    lines = ["---", f'title: "{_escape_yaml(title)}"', f"slug: {slug}"]
    if url:
        lines.append(f'url: "{_escape_yaml(url)}"')
    if scraped:
        lines.append(f'scrapedAt: "{_escape_yaml(scraped)}"')
    if pdf_downloads:
        lines.append("pdfDownloads:")
        for dl in pdf_downloads:
            lines.append(f'  - "{_escape_yaml(dl)}"')
    lines.append("---")
    return "\n".join(lines)


def _escape_yaml(value: str) -> str:
    """Escape double quotes in a YAML value."""
    return value.replace('"', '\\"')
