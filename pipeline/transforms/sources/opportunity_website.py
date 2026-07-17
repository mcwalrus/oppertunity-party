"""Normalize data/sources/opportunity-website/ into the data/clean/ layer.

Reads the raw scraper output (old-style ``**Key**: Value`` metadata blocks)
for every content type and writes normalized items to::

    data/clean/{content-type}/{slug}/{slug}.md   — YAML frontmatter + body
    data/clean/{content-type}/{slug}/meta.json   — machine-readable metadata
    data/clean/_index.json                       — flat cross-type search index

Provenance fields written to every item
---------------------------------------
slug, content_type, source_id, source_type, source_url, ingested_at, cleaned_at
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pipeline.paths import CLEAN_DIR
from pipeline.paths import DATA_DIR as SOURCE_DIR
from pipeline.transforms.clean import (
    clean_body,
    extract_metadata_fields,
    normalise_blank_runs,
    strip_contents_section,
    strip_footer_sections,
)

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SOURCE_ID = "opportunity-website"
SOURCE_TYPE = "website"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def transform_opportunity_website(
    content_type: str | None = None,
    policy_slug: str | None = None,
) -> list[dict[str, str]]:
    """Read content types from sources and write normalized items to data/clean/.

    Args:
        content_type: When provided, only the matching content type is processed
            and written to ``data/clean/{type}/`` — other directories are not
            touched.  Accepted values: ``'policy'``, ``'team'``, ``'blog'``,
            ``'events'``, ``'party-information'``, ``'pdf-document'``.
            When ``None`` (default) all types are processed and
            ``data/clean/_index.json`` is regenerated — preserving the
            existing behaviour.
        policy_slug: When provided alongside ``content_type='pdf-document'``,
            only PDFs belonging to that policy slug are processed.  Ignored
            for all other content types.

    Returns a list of index entries suitable for ``data/clean/_index.json``.
    """
    cleaned_at = datetime.now(UTC).isoformat()
    index_entries: list[dict[str, str]] = []

    if content_type is None or content_type == "policy":
        index_entries += _transform_policies(cleaned_at)
    if content_type is None or content_type == "blog":
        index_entries += _transform_blog(cleaned_at)
        index_entries += _transform_news(cleaned_at)
    if content_type is None or content_type == "events":
        index_entries += _transform_events(cleaned_at)
    if content_type is None or content_type == "team":
        index_entries += _transform_team(cleaned_at)
    if content_type is None or content_type == "party-information":
        index_entries += _transform_party_info(cleaned_at)
    if content_type is None or content_type == "pdf-document":
        index_entries += _transform_pdf_documents(cleaned_at, policy_slug=policy_slug)

    if content_type is None:
        _write_index(index_entries)
        print(f"  📋 clean/_index.json  ({len(index_entries)} items)")

    return index_entries


# ---------------------------------------------------------------------------
# Per-type transforms
# ---------------------------------------------------------------------------


def _transform_policies(cleaned_at: str) -> list[dict[str, str]]:
    """Write data/clean/policy/{slug}/ for each scraped policy."""
    policies_dir = SOURCE_DIR / "policies"
    if not policies_dir.exists():
        return []

    # Load index.json for structured metadata (pdf_downloads, scraped_at)
    index_data: dict[str, dict[str, object]] = {}
    index_file = policies_dir / "index.json"
    if index_file.exists():
        with open(index_file) as f:
            for entry in json.load(f):
                index_data[entry["slug"]] = entry

    entries: list[dict[str, str]] = []
    for slug_dir in sorted(policies_dir.iterdir()):
        if not slug_dir.is_dir():
            continue
        slug = slug_dir.name

        main_file = slug_dir / f"{slug}.md"
        if not main_file.exists():
            # Some dirs have only pdf-*.md files (e.g. charter, constitution).
            # Create a minimal policy clean item from their PDF content.
            pdf_files = sorted(slug_dir.glob("pdf-*.md"))
            if pdf_files:
                idx = index_data.get(slug, {})
                title = str(idx.get("title") or slug.replace("-", " ").title())
                src_url = str(idx.get("url") or "")
                ing_at = str(idx.get("scraped_at") or "")
                pdf_content = _load_pdf_content(pdf_files)
                meta: dict[str, object] = {
                    "slug": slug,
                    "content_type": "policy",
                    "source_id": SOURCE_ID,
                    "source_type": SOURCE_TYPE,
                    "source_url": src_url,
                    "ingested_at": ing_at,
                    "cleaned_at": cleaned_at,
                    "title": title,
                    "summary": "",
                    "pdf_urls": [],
                    "tags": [],
                }
                _write_clean_item("policy", slug, meta, pdf_content)
                print(f"  📝 clean/policy/{slug}/{slug}.md  (PDF-only)")
                entries.append(
                    {
                        "slug": slug,
                        "content_type": "policy",
                        "source_id": SOURCE_ID,
                        "source_url": src_url,
                        "title": title,
                        "date": "",
                    }
                )
            continue

        raw = main_file.read_text(encoding="utf-8")
        bq_meta = _extract_blockquote_meta(raw)
        title = _extract_h1_title(raw) or slug.replace("-", " ").title()

        idx = index_data.get(slug, {})
        source_url: str = str(bq_meta.get("URL") or idx.get("url") or "")
        ingested_at: str = str(bq_meta.get("Scraped") or idx.get("scraped_at") or "")
        raw_pdfs = idx.get("pdf_downloads")
        pdf_urls: list[str] = [str(u) for u in raw_pdfs] if isinstance(raw_pdfs, list) else []

        # Clean body — strip images, footer CTA, nav, duplicate H1
        body = clean_body(raw, title=title, strip_footer=True, strip_media_contact=True)

        # Append PDF markdown content
        pdf_files = sorted(slug_dir.glob("pdf-*.md"))
        pdf_content = _load_pdf_content(pdf_files)
        if pdf_content:
            body = body.rstrip() + "\n\n## Full Policy Detail\n\n" + pdf_content

        body = normalise_blank_runs(body)

        meta: dict[str, object] = {
            "slug": slug,
            "content_type": "policy",
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "source_url": source_url,
            "ingested_at": ingested_at,
            "cleaned_at": cleaned_at,
            "title": title,
            "summary": "",
            "pdf_urls": pdf_urls,
            "tags": [],
        }
        _write_clean_item("policy", slug, meta, body)
        print(f"  📝 clean/policy/{slug}/{slug}.md")

        entries.append(
            {
                "slug": slug,
                "content_type": "policy",
                "source_id": SOURCE_ID,
                "source_url": source_url,
                "title": title,
                "date": "",
            }
        )

    return entries


def _transform_blog(cleaned_at: str) -> list[dict[str, str]]:
    """Write data/clean/blog-post/{slug}/ for each scraped blog post."""
    blog_dir = SOURCE_DIR / "blog"
    if not blog_dir.exists():
        return []

    entries: list[dict[str, str]] = []
    for md_file in sorted(blog_dir.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        # extract_metadata_fields returns stripped body; use it to avoid duplicate metadata
        fields, stripped = extract_metadata_fields(raw)

        slug = md_file.stem
        title = fields.get("Title", slug)
        date = fields.get("Date", "")
        author = fields.get("Author", "")
        source_url = fields.get("URL", "")
        ingested_at = fields.get("Scraped", "")

        body = clean_body(stripped, title=title, strip_footer=False, strip_media_contact=True)
        body = normalise_blank_runs(body)

        meta: dict[str, object] = {
            "slug": slug,
            "content_type": "blog-post",
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "source_url": source_url,
            "ingested_at": ingested_at,
            "cleaned_at": cleaned_at,
            "title": title,
            "date": date,
            "author": author,
            "excerpt": "",
        }
        _write_clean_item("blog-post", slug, meta, body)
        print(f"  📝 clean/blog-post/{slug}/{slug}.md")

        entries.append(
            {
                "slug": slug,
                "content_type": "blog-post",
                "source_id": SOURCE_ID,
                "source_url": source_url,
                "title": title,
                "date": date,
            }
        )

    return entries


def _transform_events(cleaned_at: str) -> list[dict[str, str]]:
    """Write data/clean/event/{slug}/ for each scraped event."""
    events_dir = SOURCE_DIR / "events"
    if not events_dir.exists():
        return []

    entries: list[dict[str, str]] = []
    for md_file in sorted(events_dir.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        fields, stripped = extract_metadata_fields(raw)

        slug = md_file.stem
        title = fields.get("Title", slug)
        date = fields.get("Date", "")
        time_str = fields.get("When", fields.get("Time", ""))
        location = fields.get("Location", "")
        venue = fields.get("Venue", "")
        address = fields.get("Address", "")
        source_url = fields.get("URL", "")
        ingested_at = fields.get("Scraped", "")

        body = clean_body(stripped, title=title, strip_footer=False, strip_media_contact=False)
        body = normalise_blank_runs(body)

        meta: dict[str, object] = {
            "slug": slug,
            "content_type": "event",
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "source_url": source_url,
            "ingested_at": ingested_at,
            "cleaned_at": cleaned_at,
            "title": title,
            "date": date,
            "time": time_str,
            "location": location,
            "venue": venue,
            "address": address,
            "description": "",
            "registration_url": "",
        }
        _write_clean_item("event", slug, meta, body)
        print(f"  📝 clean/event/{slug}/{slug}.md")

        entries.append(
            {
                "slug": slug,
                "content_type": "event",
                "source_id": SOURCE_ID,
                "source_url": source_url,
                "title": title,
                "date": date,
            }
        )

    return entries


def _transform_team(cleaned_at: str) -> list[dict[str, str]]:
    """Write data/clean/team-member/{slug}/ for each scraped team member."""
    team_dir = SOURCE_DIR / "team"
    if not team_dir.exists():
        return []

    entries: list[dict[str, str]] = []
    for md_file in sorted(team_dir.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        # Strip **Role**: / **Electorate**: lines first; also grab blockquote URL
        fields, stripped = extract_metadata_fields(raw)

        slug = md_file.stem
        # Name comes from the H1 heading; fall back to slug
        name = _extract_h1_title(raw) or fields.get("Title", slug.replace("-", " ").title())
        role = fields.get("Role", "")
        electorate = fields.get("Electorate", "")
        bq_meta = _extract_blockquote_meta(raw)
        source_url = fields.get("URL") or bq_meta.get("URL", "")
        ingested_at = fields.get("Scraped") or bq_meta.get("Scraped", "")

        body = clean_body(stripped, title=name, strip_footer=False, strip_media_contact=True)
        body = normalise_blank_runs(body)

        meta: dict[str, object] = {
            "slug": slug,
            "content_type": "team-member",
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "source_url": source_url,
            "ingested_at": ingested_at,
            "cleaned_at": cleaned_at,
            "name": name,
            "role": role,
            "electorate": electorate,
        }
        _write_clean_item("team-member", slug, meta, body)
        print(f"  📝 clean/team-member/{slug}/{slug}.md")

        entries.append(
            {
                "slug": slug,
                "content_type": "team-member",
                "source_id": SOURCE_ID,
                "source_url": source_url,
                "title": name,
                "date": "",
            }
        )

    return entries


def _transform_party_info(cleaned_at: str) -> list[dict[str, str]]:
    """Write data/clean/party-information/{slug}/ for each party-info page."""
    pi_dir = SOURCE_DIR / "party-information"
    if not pi_dir.exists():
        return []

    entries: list[dict[str, str]] = []
    for md_file in sorted(pi_dir.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")

        slug = md_file.stem
        title = _extract_h1_title(raw) or slug.replace("-", " ").title()
        bq_meta = _extract_blockquote_meta(raw)
        source_url = bq_meta.get("URL", "")
        ingested_at = bq_meta.get("Scraped", "")

        body = clean_body(raw, title=title, strip_footer=True, strip_media_contact=False)
        body = normalise_blank_runs(body)

        meta: dict[str, object] = {
            "slug": slug,
            "content_type": "party-information",
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "source_url": source_url,
            "ingested_at": ingested_at,
            "cleaned_at": cleaned_at,
            "title": title,
        }
        _write_clean_item("party-information", slug, meta, body)
        print(f"  📝 clean/party-information/{slug}/{slug}.md")

        entries.append(
            {
                "slug": slug,
                "content_type": "party-information",
                "source_id": SOURCE_ID,
                "source_url": source_url,
                "title": title,
                "date": "",
            }
        )

    return entries


def _transform_news(cleaned_at: str) -> list[dict[str, str]]:
    """Write data/clean/blog-post/{slug}/ for each scraped news item.

    News items are normalized as ``blog-post`` content type since they are
    the same kind of article.  Slugs do not collide with blog post slugs
    because blog filenames have a ``{date}-`` prefix.
    """
    news_dir = SOURCE_DIR / "news"
    if not news_dir.exists():
        return []

    entries: list[dict[str, str]] = []
    for md_file in sorted(news_dir.glob("*.md")):
        raw = md_file.read_text(encoding="utf-8")
        bq_meta = _extract_blockquote_meta(raw)

        slug = md_file.stem
        title = _extract_h1_title(raw) or slug.replace("-", " ").title()
        source_url = bq_meta.get("URL", "")
        ingested_at = bq_meta.get("Scraped", "")

        body = clean_body(raw, title=title, strip_footer=False, strip_media_contact=True)
        body = normalise_blank_runs(body)

        meta: dict[str, object] = {
            "slug": slug,
            "content_type": "blog-post",
            "source_id": SOURCE_ID,
            "source_type": SOURCE_TYPE,
            "source_url": source_url,
            "ingested_at": ingested_at,
            "cleaned_at": cleaned_at,
            "title": title,
            "date": "",
            "author": "",
            "excerpt": "",
        }
        _write_clean_item("blog-post", slug, meta, body)
        print(f"  📝 clean/blog-post/{slug}/{slug}.md  (from news)")

        entries.append(
            {
                "slug": slug,
                "content_type": "blog-post",
                "source_id": SOURCE_ID,
                "source_url": source_url,
                "title": title,
                "date": "",
            }
        )

    return entries


def _transform_pdf_documents(
    cleaned_at: str,
    policy_slug: str | None = None,
) -> list[dict[str, str]]:
    """Write data/clean/pdf-document/{slug}/ for each extracted PDF markdown file.

    PDF markdown files live inside ``policies/{policy-slug}/pdf-*.md`` in the
    source layer.  Each becomes its own ``pdf-document`` clean item whose slug
    is ``{policy-slug}-{pdf-type}`` (e.g. ``tax-reset-policy-overview``).

    Args:
        cleaned_at: ISO timestamp recorded as ``cleaned_at`` in each item.
        policy_slug: When provided, only the matching policy slug is processed.
            Omit (or pass ``None``) to process all slugs.
    """
    policies_dir = SOURCE_DIR / "policies"
    if not policies_dir.exists():
        return []

    entries: list[dict[str, str]] = []
    for slug_dir in sorted(policies_dir.iterdir()):
        if not slug_dir.is_dir():
            continue
        # Skip slugs that don't match the requested partition.
        if policy_slug is not None and slug_dir.name != policy_slug:
            continue
        policy_slug_val = slug_dir.name

        for pdf_file in sorted(slug_dir.glob("pdf-*.md")):
            raw = pdf_file.read_text(encoding="utf-8")

            # Extract metadata table from PDF markdown
            pdf_meta = _extract_pdf_table_meta(raw)
            doc_type = pdf_meta.get("Document Type", pdf_file.stem.replace("pdf-", ""))
            title_base = pdf_meta.get("Policy", policy_slug_val.replace("-", " ").title())
            title = f"{title_base} — {doc_type}" if doc_type else title_base
            ingested_at = pdf_meta.get("Downloaded", cleaned_at)

            # Slug: "{policy-slug}-{pdf-stem-without-pdf-prefix}"
            pdf_type = pdf_file.stem[len("pdf-") :]  # e.g. "policy-overview"
            doc_slug = f"{policy_slug_val}-{pdf_type}"

            body = _strip_pdf_metadata_table(raw)

            meta: dict[str, object] = {
                "slug": doc_slug,
                "content_type": "pdf-document",
                "source_id": SOURCE_ID,
                "source_type": SOURCE_TYPE,
                "source_url": "",
                "ingested_at": ingested_at,
                "cleaned_at": cleaned_at,
                "title": title,
                "policy_slug": policy_slug_val,
            }
            _write_clean_item("pdf-document", doc_slug, meta, body)
            print(f"  📝 clean/pdf-document/{doc_slug}/{doc_slug}.md")

            entries.append(
                {
                    "slug": doc_slug,
                    "content_type": "pdf-document",
                    "source_id": SOURCE_ID,
                    "source_url": "",
                    "title": title,
                    "date": "",
                }
            )

    return entries


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _write_clean_item(
    content_type: str,
    slug: str,
    meta: dict[str, object],
    body: str,
) -> None:
    """Write ``{slug}.md`` and ``meta.json`` into ``data/clean/{content_type}/{slug}/``.

    ``meta.json`` is written as a merge of the existing on-disk fields
    and the new ``meta`` dict (new fields win). This preserves
    out-of-band fields added by downstream consumers (e.g. ``html_path``
    written by the ``pdf_html`` asset) when the transform pipeline
    re-materialises the item.
    """
    item_dir = CLEAN_DIR / content_type / slug
    item_dir.mkdir(parents=True, exist_ok=True)

    # Write .md with YAML frontmatter
    frontmatter = _build_frontmatter(meta)
    md_content = frontmatter + "\n" + body.lstrip("\n")
    (item_dir / f"{slug}.md").write_text(md_content, encoding="utf-8")

    # Preserve existing meta.json fields the transform didn't compute
    # (e.g. html_path added by pdf_html after the clean layer was written).
    meta_path = item_dir / "meta.json"
    if meta_path.exists():
        try:
            existing = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
        # New meta wins, but unknown existing fields are kept.
        merged = {**existing, **meta}
    else:
        merged = meta

    meta_path.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _write_index(entries: list[dict[str, str]]) -> None:
    """Write the flat cross-type search index to data/clean/_index.json."""
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    index_path = CLEAN_DIR / "_index.json"
    index_path.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def regenerate_clean_index() -> int:
    """Regenerate data/clean/_index.json from the existing clean data.

    Scans every ``meta.json`` under CLEAN_DIR without re-running the full
    transform pipeline, then writes a fresh cross-type search index.

    Returns the number of index entries written.
    """
    entries: list[dict[str, str]] = []
    if CLEAN_DIR.exists():
        for type_dir in sorted(CLEAN_DIR.iterdir()):
            # Skip special files/dirs (e.g. _index.json lives at this level)
            if not type_dir.is_dir() or type_dir.name.startswith("_"):
                continue
            for item_dir in sorted(type_dir.iterdir()):
                if not item_dir.is_dir():
                    continue
                meta_file = item_dir / "meta.json"
                if not meta_file.exists():
                    continue
                with open(meta_file) as fh:
                    meta: dict[str, object] = json.load(fh)
                entries.append(
                    {
                        "slug": str(meta.get("slug", "")),
                        "content_type": str(meta.get("content_type", "")),
                        "source_id": str(meta.get("source_id", "")),
                        "source_url": str(meta.get("source_url", "")),
                        "title": str(meta.get("title", "")),
                        "date": str(meta.get("date", "")),
                    }
                )
    _write_index(entries)
    return len(entries)


# ---------------------------------------------------------------------------
# YAML frontmatter builder
# ---------------------------------------------------------------------------


def _build_frontmatter(fields: dict[str, object]) -> str:
    """Build a minimal YAML frontmatter block from a dict.

    Rules:
    - ``None``, ``""``, and ``[]`` values are omitted.
    - String values are double-quoted with internal quotes escaped.
    - Lists become flow sequences of double-quoted strings.
    """
    lines = ["---"]
    for key, value in fields.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, list):
            items_str = ", ".join(f'"{_esc(str(v))}"' for v in value)
            lines.append(f"{key}: [{items_str}]")
        else:
            lines.append(f'{key}: "{_esc(str(value))}"')
    lines.append("---")
    return "\n".join(lines)


def _esc(s: str) -> str:
    """Escape a string for use inside YAML double-quoted scalars."""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


# ---------------------------------------------------------------------------
# Source-format parsing helpers
# ---------------------------------------------------------------------------


def _extract_blockquote_meta(body: str) -> dict[str, str]:
    """Extract ``> **Key**: Value`` blockquote metadata lines."""
    fields: dict[str, str] = {}
    for line in body.split("\n"):
        m = re.match(r"^>\s*\*\*(URL|Scraped)\*\*:\s*(.+)$", line.strip())
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


def _extract_h1_title(body: str) -> str:
    """Return the text of the first ``# Heading`` in the body, or ``""``."""
    for line in body.split("\n"):
        m = re.match(r"^#\s+(.+)$", line)
        if m:
            return m.group(1).strip()
    return ""


def _extract_pdf_table_meta(body: str) -> dict[str, str]:
    """Extract the metadata table at the top of a PDF-extracted markdown file.

    The table looks like::

        | Field | Value |
        |-------|-------|
        | Date  | May 2026 |
        ...
    """
    fields: dict[str, str] = {}
    for line in body.split("\n"):
        m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$", line)
        if m and m.group(1) not in ("Field", "------", "-----"):
            fields[m.group(1)] = m.group(2).strip("`").strip()
    return fields


def _strip_pdf_metadata_table(body: str) -> str:
    """Remove the leading H1 title, metadata table, and Contents section from a PDF markdown file.

    If a ``## **Contents**`` section (pymupdf4llm's extraction of the PDF's own
    TOC page) is stripped, an HTML comment is prepended to the body documenting
    the removal so the change is visible in the clean output file.
    """
    # Strip "# Title\n| Field | Value |\n|------|\n| ... |\n..."
    body = re.sub(r"^# .+?\n(\|.*?\|.*?\n)+\n*", "", body, count=1)
    # Strip standalone bold noise lines (e.g. "**Tax**")
    body = re.sub(r"^\*\*.+?\*\*\s*$", "", body, flags=re.MULTILINE)
    # Strip H1 headings (they duplicate the clean item's title)
    body = re.sub(r"^#[^#].+$", "", body, flags=re.MULTILINE)
    body = body.lstrip("\n")

    # Strip the Contents (TOC) section if present and document the removal.
    body, had_contents = strip_contents_section(body)
    if had_contents:
        body = (
            "<!-- The Contents (TOC) table has been removed during transformation; "
            "the rendered document provides its own navigation. -->\n\n" + body
        )
    return body


def _load_pdf_content(pdf_files: list[Path]) -> str:
    """Load and concatenate PDF markdown files, stripping their metadata tables."""
    sections: list[str] = []
    for pdf_file in pdf_files:
        content = _strip_pdf_metadata_table(pdf_file.read_text(encoding="utf-8"))
        if content.strip():
            sections.append(content.strip())
    return "\n\n".join(sections)


def _esc_yaml_value(s: str) -> str:  # alias kept for readability in callers
    return _esc(s)


def _strip_policy_footer(body: str) -> str:
    """Remove trailing 'Check out more policies' / 'Get Involved' sections."""
    return strip_footer_sections(body)
