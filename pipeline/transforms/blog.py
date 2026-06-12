"""Transform blog posts from data/clean/ to site/src/content/blog/."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pipeline.transforms.clean import normalise_blank_runs

if TYPE_CHECKING:
    from pathlib import Path


def transform_blog(clean_dir: Path, content_dir: Path) -> None:
    """Read data/clean/blog-post/ and write Astro-compatible markdown to site/src/content/blog/."""
    blog_dir = clean_dir / "blog-post"
    out_dir = content_dir / "blog"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not blog_dir.exists():
        return

    for item_dir in sorted(blog_dir.iterdir()):
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
        author = str(meta.get("author") or "")
        url = str(meta.get("source_url") or "")
        scraped = str(meta.get("ingested_at") or "")

        frontmatter_lines = ["---", f'title: "{_esc(title)}"', f"slug: {slug}"]
        if date:
            frontmatter_lines.append(f'date: "{_esc(date)}"')
        if author:
            frontmatter_lines.append(f'author: "{_esc(author)}"')
        if url:
            frontmatter_lines.append(f'url: "{_esc(url)}"')
        if scraped:
            frontmatter_lines.append(f'scrapedAt: "{_esc(scraped)}"')
        frontmatter_lines.append("---")

        output = normalise_blank_runs("\n".join(frontmatter_lines) + "\n" + body)
        (out_dir / f"{slug}.md").write_text(output, encoding="utf-8")
        print(f"  📝 blog/{slug}.md")


def _extract_body(content: str) -> str:
    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            return parts[2]
    return content


def _esc(value: str) -> str:
    return value.replace('"', '\\"')
