"""Transform team members from data/ to site/src/content/team/."""

import re
from pathlib import Path

from transforms.clean import (
    clean_body,
    extract_metadata_fields,
    normalise_blank_runs,
)


def transform_team(data_dir: Path, content_dir: Path) -> None:
    """Read data/team/ and write clean markdown to site/src/content/team/."""
    team_dir = data_dir / "team"
    out_dir = content_dir / "team"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not team_dir.exists():
        return

    for md_file in sorted(team_dir.glob("*.md")):
        if md_file.name == "index.json":
            continue

        body = md_file.read_text(encoding="utf-8")
        fields, body = extract_metadata_fields(body)

        # Derive slug from filename
        slug = md_file.stem

        # Team files use markdown headings (# Name) — extract name from first heading
        name = _extract_name(body) or fields.get("Title", slug.replace("-", " ").title())
        role = fields.get("Role", "")
        electorate = fields.get("Electorate", "")
        url = fields.get("URL", "")
        scraped = fields.get("Scraped", "")

        # Clean body — pass name to strip duplicate H1
        body = clean_body(body, title=name, strip_footer=False)

        # Build frontmatter
        fm_lines = [
            "---",
            f'name: "{_esc(name)}"',
            f"slug: {slug}",
        ]
        if role:
            fm_lines.append(f'role: "{_esc(role)}"')
        if electorate:
            fm_lines.append(f'electorate: "{_esc(electorate)}"')
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
        print(f"  📝 team/{slug}.md")


def _extract_name(body: str) -> str:
    """Extract name from the first markdown heading like '# Adam MacRae-Martin'."""
    m = re.match(r"^#\s+(.+)$", body, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
