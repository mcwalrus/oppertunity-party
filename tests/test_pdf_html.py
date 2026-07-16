"""Tests for the pdf_html asset — markdown → per-item HTML rendering.

Parametrised over every existing ``data/clean/pdf-document/{slug}/``
directory. Each test asserts:

- ``{slug}.html`` was emitted next to the markdown
- the HTML contains a snippet of the source markdown body
- ``meta.json`` got the ``html_path`` field

Tests skip when the pdf-document clean layer is empty (fresh clone
without running pdf_job).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pipeline.paths import CLEAN_DIR, PROJECT_ROOT

PDF_DOC_DIR = Path(CLEAN_DIR) / "pdf-document"

# Slugs that have an .md file — parametrise tests over those, skip if empty.
pdf_doc_slugs = sorted(
    d.name for d in PDF_DOC_DIR.iterdir() if d.is_dir() and (d / f"{d.name}.md").exists()
)
pytestmark = pytest.mark.skipif(
    not pdf_doc_slugs,
    reason=f"No pdf-document items in {PDF_DOC_DIR} — run pdf_job first",
)


@pytest.fixture(params=pdf_doc_slugs, ids=lambda s: s)
def slug(request):
    return request.param


def test_html_file_exists(slug):
    html = PDF_DOC_DIR / slug / f"{slug}.html"
    assert html.exists(), f"missing {html}"
    assert html.stat().st_size > 0


def test_html_contains_markdown_body(slug):
    """HTML body must include text from the source markdown.

    The first non-empty body line is usually a table row (which the
    HTML renderer restructures), so we pick the first non-empty line
    that isn't a table row or an image-placeholder marker, then strip
    formatting chars and compare against the rendered HTML's plain
    text (via BeautifulSoup — already a direct dep).
    """
    from bs4 import BeautifulSoup

    md_path = PDF_DOC_DIR / slug / f"{slug}.md"
    html_path = PDF_DOC_DIR / slug / f"{slug}.html"
    raw_md = md_path.read_text(encoding="utf-8")
    body = re.sub(r"^---\n.*?\n---\n", "", raw_md, count=1, flags=re.DOTALL)
    snippet = next(
        (
            line.strip()[:80]
            for line in body.splitlines()
            if line.strip() and not line.lstrip().startswith("|") and "picture" not in line.lower()
        ),
        "",
    )
    if not snippet:
        pytest.skip(f"{slug}: no usable body snippet")
    # Strip markdown formatting chars from snippet before searching.
    needle = re.sub(r"[#*`_]", "", snippet).strip()
    # Rendered text strips all tags — robust against <strong>/<p>/<br>
    # insertions between words.
    html_text = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser").get_text(
        " ", strip=True
    )
    # Whitespace-collapse the needle too.
    needle_norm = re.sub(r"\s+", " ", needle)
    html_norm = re.sub(r"\s+", " ", html_text)
    assert needle_norm in html_norm, f"{slug}: snippet {needle_norm!r} not in rendered HTML"


def test_html_wrapper_is_minimal(slug):
    html = (PDF_DOC_DIR / slug / f"{slug}.html").read_text(encoding="utf-8")
    assert "<html" in html
    assert "<body>" in html
    # No CSS — styling lives at site/dist/.
    assert "<style" not in html
    assert '<link rel="stylesheet"' not in html


def test_meta_json_has_html_path(slug):
    meta_path = PDF_DOC_DIR / slug / "meta.json"
    assert meta_path.exists(), f"missing {meta_path}"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    expected_rel = (
        (meta_path.parent / f"{slug}.html").resolve().relative_to(PROJECT_ROOT).as_posix()
    )
    assert meta.get("html_path") == expected_rel, (
        f"{slug}: html_path={meta.get('html_path')!r} expected {expected_rel!r}"
    )


def test_render_one_smoke(tmp_path):
    """Direct render_one() call against a synthetic MD file.

    Catches regressions in strip_frontmatter / title extraction without
    depending on the live clean layer.
    """
    from pipeline.transforms.pdf_to_html import render_one

    slug_dir = tmp_path / "test-slug"
    slug_dir.mkdir()
    (slug_dir / "test-slug.md").write_text(
        '---\ntitle: "Smoke Test"\n---\n# Smoke\n\nhello *world*\n',
        encoding="utf-8",
    )
    (slug_dir / "meta.json").write_text(
        json.dumps({"slug": "test-slug"}, indent=2), encoding="utf-8"
    )
    # Patch PROJECT_ROOT for the duration of the call so html_path is
    # computed relative to tmp_path.
    import pipeline.transforms.pdf_to_html as mod

    orig_root = mod.PROJECT_ROOT
    mod.PROJECT_ROOT = tmp_path
    try:
        bytes_written, rel_path = render_one(slug_dir)
    finally:
        mod.PROJECT_ROOT = orig_root

    html_path = slug_dir / "test-slug.html"
    assert html_path.exists()
    assert bytes_written == html_path.stat().st_size
    assert rel_path.endswith("test-slug/test-slug.html")
    html = html_path.read_text(encoding="utf-8")
    assert "<title>Smoke Test</title>" in html
    assert "hello" in html and "<em>world</em>" in html
    # meta.json updated
    meta = json.loads((slug_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta.get("html_path", "").endswith("test-slug/test-slug.html")
