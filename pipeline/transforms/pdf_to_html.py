"""Render cleaned PDF markdown → HTML.

One HTML file per ``data/clean/pdf-document/{slug}/`` is emitted next to
the markdown, so non-SSG consumers (MCP, analysis) can read rendered
HTML directly without running the Astro build first.

HTML is a thin wrapper: ``<html><body>{body}</body></html>`` with no
CSS — the Astro site already owns styling at ``site/dist/``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import markdown as md_lib

from pipeline.paths import CLEAN_DIR, PROJECT_ROOT

# Strip YAML frontmatter at the top of the markdown file (between two
# `---` lines). Markdown body is everything after.
_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)

# Title source: frontmatter `title:` field if present, else first H1 in body,
# else the slug. Keeps the HTML <title> useful when opened standalone.
_TITLE_RE = re.compile(r"^title:\s*[\"']?([^\"'\n]+)[\"']?\s*$", re.MULTILINE)
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


def _strip_frontmatter(md: str) -> str:
    return _FRONTMATTER_RE.sub("", md, count=1)


def _extract_title(md_with_frontmatter: str, slug: str) -> str:
    title = _TITLE_RE.search(md_with_frontmatter)
    if title:
        return title.group(1).strip()
    h1 = _H1_RE.search(md_with_frontmatter)
    if h1:
        return h1.group(1).strip()
    return slug


def render_one(slug_dir: Path) -> tuple[int, str]:
    """Render ``{slug}.md`` → ``{slug}.html`` for one item.

    Returns ``(bytes_written, html_path_relative_to_root)``. Updates the
    item's ``meta.json`` with ``html_path`` so downstream consumers can
    discover the HTML without scanning directories.
    """
    slug = slug_dir.name
    md_path = slug_dir / f"{slug}.md"
    html_path = slug_dir / f"{slug}.html"
    meta_path = slug_dir / "meta.json"

    raw_md = md_path.read_text(encoding="utf-8")
    title = _extract_title(raw_md, slug)
    body_md = _strip_frontmatter(raw_md).strip()

    body_html = md_lib.markdown(body_md, extensions=["extra"])
    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{title}</title>\n"
        "</head>\n"
        "<body>\n"
        f"{body_html}\n"
        "</body>\n"
        "</html>\n"
    )
    html_path.write_text(html, encoding="utf-8")

    # Update meta.json with html_path (relative to project root, matches the
    # convention used by media_path elsewhere in the pipeline).
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    rel_html = html_path.resolve().relative_to(PROJECT_ROOT).as_posix()
    if meta.get("html_path") != rel_html:
        meta["html_path"] = rel_html
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return html_path.stat().st_size, rel_html


def render_pdf_html(clean_root: Path = CLEAN_DIR) -> list[str]:
    """Render every ``pdf-document/{slug}/`` and return list of HTML paths.

    ``clean_root`` defaults to ``CLEAN_DIR`` (``data/clean`` resolved
    relative to the cwd, which Dagster sets to the project root).
    """
    pdf_dir = Path(clean_root) / "pdf-document"
    if not pdf_dir.exists():
        return []
    html_paths: list[str] = []
    for slug_dir in sorted(pdf_dir.iterdir()):
        if not slug_dir.is_dir():
            continue
        if not (slug_dir / f"{slug_dir.name}.md").exists():
            continue
        _, rel = render_one(slug_dir)
        html_paths.append(rel)
    return html_paths
