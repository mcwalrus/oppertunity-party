"""Transform party information from data/clean/ to site/src/content/party-info/."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pipeline.transforms.clean import normalise_blank_runs

if TYPE_CHECKING:
    from pathlib import Path


def transform_party_info(clean_dir: Path, content_dir: Path) -> None:
    """Read data/clean/party-information/ and write to site/src/content/party-info/."""
    pi_dir = clean_dir / "party-information"
    out_dir = content_dir / "party-info"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not pi_dir.exists():
        return

    for item_dir in sorted(pi_dir.iterdir()):
        if not item_dir.is_dir():
            continue
        slug = item_dir.name

        meta_file = item_dir / "meta.json"
        md_file = item_dir / f"{slug}.md"
        if not md_file.exists():
            continue

        meta = json.loads(meta_file.read_text(encoding="utf-8")) if meta_file.exists() else {}
        body = _extract_body(md_file.read_text(encoding="utf-8"))

        title = str(meta.get("title") or slug.replace("-", " ").title())
        url = str(meta.get("source_url") or "")
        scraped = str(meta.get("ingested_at") or "")

        fm_lines = ["---", f'title: "{_esc(title)}"', f"slug: {slug}"]
        if url:
            fm_lines.append(f'url: "{_esc(url)}"')
        if scraped:
            fm_lines.append(f'scrapedAt: "{_esc(scraped)}"')
        fm_lines.append("---")

        output = normalise_blank_runs("\n".join(fm_lines) + "\n" + body)
        (out_dir / f"{slug}.md").write_text(output, encoding="utf-8")
        print(f"  📝 party-info/{slug}.md")


def _extract_body(content: str) -> str:
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            return parts[2]
    return content


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
