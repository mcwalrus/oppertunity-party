"""Transform team members from data/clean/ to site/src/content/team/."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pipeline.transforms.clean import normalise_blank_runs

if TYPE_CHECKING:
    from pathlib import Path


def transform_team(clean_dir: Path, content_dir: Path) -> None:
    """Read data/clean/team-member/ and write Astro-compatible markdown to site/src/content/team/."""
    team_dir = clean_dir / "team-member"
    out_dir = content_dir / "team"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not team_dir.exists():
        return

    for item_dir in sorted(team_dir.iterdir()):
        if not item_dir.is_dir():
            continue
        slug = item_dir.name

        meta_file = item_dir / "meta.json"
        md_file = item_dir / f"{slug}.md"
        if not md_file.exists():
            continue

        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
        body = _extract_body(md_file.read_text(encoding="utf-8"))

        name = str(meta.get("name") or slug.replace("-", " ").title())
        role = str(meta.get("role") or "")
        electorate = str(meta.get("electorate") or "")
        url = str(meta.get("source_url") or "")
        scraped = str(meta.get("ingested_at") or "")

        fm_lines = ["---", f'name: "{_esc(name)}"', f"slug: {slug}"]
        if role:
            fm_lines.append(f'role: "{_esc(role)}"')
        if electorate:
            fm_lines.append(f'electorate: "{_esc(electorate)}"')
        if url:
            fm_lines.append(f'url: "{_esc(url)}"')
        if scraped:
            fm_lines.append(f'scrapedAt: "{_esc(scraped)}"')
        fm_lines.append("---")

        output = normalise_blank_runs("\n".join(fm_lines) + "\n" + body)
        (out_dir / f"{slug}.md").write_text(output, encoding="utf-8")
        print(f"  📝 team/{slug}.md")


def _extract_body(content: str) -> str:
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            return parts[2]
    return content


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
