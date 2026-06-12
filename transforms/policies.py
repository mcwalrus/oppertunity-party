"""Transform policies from data/clean/ to site/src/content/policies/."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from transforms.clean import normalise_blank_runs

if TYPE_CHECKING:
    from pathlib import Path


def transform_policies(clean_dir: Path, content_dir: Path) -> None:
    """Read data/clean/policy/ and write Astro-compatible markdown to site/src/content/policies/."""
    policies_dir = clean_dir / "policy"
    out_dir = content_dir / "policies"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not policies_dir.exists():
        return

    for item_dir in sorted(policies_dir.iterdir()):
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
        pdf_urls: list[str] = [str(u) for u in (meta.get("pdf_urls") or [])]

        frontmatter = _build_frontmatter(
            slug=slug,
            title=title,
            url=url,
            scraped=scraped,
            pdf_downloads=pdf_urls,
        )
        output = normalise_blank_runs(frontmatter + "\n" + body)
        (out_dir / f"{slug}.md").write_text(output, encoding="utf-8")
        print(f"  📝 policies/{slug}.md")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_body(content: str) -> str:
    """Return the body text after stripping the YAML frontmatter block."""
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            return parts[2]
    return content


def _build_frontmatter(
    *,
    slug: str,
    title: str,
    url: str,
    scraped: str,
    pdf_downloads: list[str],
) -> str:
    lines = ["---", f'title: "{_esc(title)}"', f"slug: {slug}"]
    if url:
        lines.append(f'url: "{_esc(url)}"')
    if scraped:
        lines.append(f'scrapedAt: "{_esc(scraped)}"')
    if pdf_downloads:
        lines.append("pdfDownloads:")
        for dl in pdf_downloads:
            lines.append(f'  - "{_esc(dl)}"')
    lines.append("---")
    return "\n".join(lines)


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
