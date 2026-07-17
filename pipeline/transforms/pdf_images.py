"""Extract images from PDFs and reference them in clean markdown.

Runs as part of the clean pipeline (downstream of ``clean_pdfs``).
For every pdf-document item, this module:

1. Extracts embedded images from the source PDF with ``pdfimages -j -p``
   (poppler-utils), writing them to ``{slug}/images/`` next to the
   clean markdown.  ``pdfimages`` is a CLI, not a Python lib — it
   handles JPEG/PNG/JP2/JBIG2/JPEG2000 with no extra deps.
2. Replaces ``----- Start of picture text -----`` blocks in the
   clean markdown with ``![alt](images/file.jpg)`` references.
   pymupdf4llm emits these blocks when it sees an embedded image
   but cannot OCR it; the markdown-side replacement turns them
   into proper image links.
3. Records image metadata in the item's ``meta.json`` so downstream
   consumers (HTML renderer, site build) can discover the assets.

The first N picture-text blocks are replaced with images in document
order (N = number of images extracted). Any extra picture-text blocks
are dropped — they were text styled as graphics (e.g. pull-quotes),
not actual images, so the markdown-side OCR garbage is removed.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path  # noqa: TC003 — used at runtime in function bodies, not annotations only

logger = logging.getLogger(__name__)

# `pdfimages` filename template used for the CLI invocation. The ``-p``
# flag prefixes each extracted file with its 1-indexed page number, so
# ``img-003-001.jpg`` means page 3, image 1 (zero-indexed within page).
_PDFIMAGES_PREFIX = "img"

# pymupdf4llm's picture-text block pattern. Each block is exactly two lines
# in the extracted markdown:
#
#     **----- Start of picture text -----**<br>
#     <content>... **----- End of picture text -----**<br>
#
# The content line contains inline ``<br>`` separators (e.g. ``4% Not
# intending to<br>4% Not at all<br>...``), so it's not multi-line — the
# whole picture sits on one line between the start and end markers.
# Anchored on the full line pair so it doesn't match prose that happens
# to mention picture text.
_PICTURE_TEXT_RE = re.compile(
    r"^\*\*----- Start of picture text -----\*\*<br>\n"
    r"[^\n]*\*\*----- End of picture text -----\*\*<br>\n",
    re.MULTILINE,
)


def extract_pdf_images(
    pdf_path: Path,
    output_dir: Path,
    page_filter: set[int] | None = None,
) -> list[dict]:
    """Extract images from *pdf_path* into *output_dir* and return metadata.

    When *page_filter* is provided (a set of 1-indexed page numbers),
    only images from those pages are kept — files from other pages are
    extracted by ``pdfimages`` then deleted. This drops decorative
    page-background images: pymupdf4llm emits a ``----- Start of picture
    text -----`` block only when it sees embedded content it couldn't OCR
    as text, so pages with picture-text are the ones with actual data viz.

    Skips extraction when *output_dir* already contains extracted images
    (idempotent re-run). Returns a list of ``{"filename", "page",
    "size_bytes"}`` dicts, sorted by filename so the order is stable.

    Raises ``RuntimeError`` if pdfimages exits with a non-zero status
    (e.g. corrupted PDF, unsupported encryption).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Idempotency: if any images already exist for this output_dir, treat
    # the extraction as done and just list what's there. Caller is
    # responsible for clearing the directory to force a re-extract.
    existing = _list_extracted_images(output_dir)
    if existing:
        return existing

    # ponytail: pdfimages is the stdlib of image extraction. -j = JPEG
    # when possible, -p = prefix filenames with page number. No Python
    # library needed; pypdf/PyMuPDF are heavier and we'd reinvent the
    # CLI to handle JPEG2000/JBIG2. Switch to PyMuPDF if pdfimages ever
    # misses something it catches.
    result = subprocess.run(
        ["pdfimages", "-j", "-p", str(pdf_path), str(output_dir / _PDFIMAGES_PREFIX)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pdfimages failed for {pdf_path.name} (exit {result.returncode}): {result.stderr}"
        )

    # Drop images from pages without picture-text blocks — these are
    # decorative/background graphics pymupdf4llm didn't flag as content.
    if page_filter is not None:
        for img_path in list(output_dir.iterdir()):
            if not img_path.is_file():
                continue
            parts = img_path.stem.split("-")
            try:
                page = int(parts[1]) if len(parts) >= 3 else 0
            except ValueError:
                page = 0
            if page not in page_filter:
                img_path.unlink()

    extracted = _list_extracted_images(output_dir)
    logger.info(
        "Extracted %d images from %s (page filter: %s)",
        len(extracted),
        pdf_path.name,
        sorted(page_filter) if page_filter else "none",
    )
    return extracted


def find_pages_with_picture_text(pdf_path: Path) -> set[int]:
    """Return the set of 1-indexed page numbers containing picture-text blocks.

    Uses ``pymupdf4llm``'s ``page_chunks=True, page_separators=True``
    mode to get per-page text — pymupdf4llm emits
    ``----- Start of picture text -----`` only when it sees embedded
    graphics it can't OCR, so this set is a reliable proxy for "pages
    with real content graphics." With ``page_separators=True`` the
    metadata dict per chunk includes ``page_number`` (1-indexed).
    """
    import pymupdf4llm

    chunks = pymupdf4llm.to_markdown(
        str(pdf_path),
        page_chunks=True,
        page_separators=True,
        show_progress=False,
    )
    pages: set[int] = set()
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        page_num = metadata.get("page_number")
        if page_num is None:
            continue
        text = chunk.get("text", "")
        if "Start of picture text" in text:
            pages.add(page_num)
    return pages


def _list_extracted_images(output_dir: Path) -> list[dict]:
    """Return metadata for every image file in *output_dir*, sorted by name."""
    images: list[dict] = []
    for img_path in sorted(output_dir.iterdir()):
        if not img_path.is_file():
            continue
        # Filename format: img-{page}-{index}.{ext}
        # e.g. img-003-001.jpg -> page 3, image 1
        parts = img_path.stem.split("-")
        try:
            page = int(parts[1]) if len(parts) >= 3 else 0
        except ValueError:
            page = 0
        images.append(
            {
                "filename": img_path.name,
                "page": page,
                "size_bytes": img_path.stat().st_size,
            }
        )
    return images


def replace_picture_text_with_images(
    md: str,
    image_filenames: list[str],
    image_rel_dir: str,
) -> tuple[str, int]:
    """Replace ``----- Start/End of picture text -----`` blocks with image refs.

    Walks the markdown in order, swapping each picture-text block for
    a markdown image link using the next filename from *image_filenames*.
    Any picture-text blocks past the last image are dropped (they were
    text styled as graphics, not actual embedded images).

    Returns ``(new_md, replacements_made)``.
    """
    image_iter = iter(image_filenames)

    def _swap(match: re.Match[str]) -> str:
        filename = next(image_iter, None)
        if filename is None:
            # No more images — drop the block entirely. pymupdf4llm
            # emitted this for a styled text box, not a real image.
            return ""
        alt = filename.rsplit(".", 1)[0]  # e.g. "img-003-001"
        return f"![{alt}]({image_rel_dir}/{filename})\n\n"

    new_md, count = _PICTURE_TEXT_RE.subn(_swap, md)
    return new_md, count


def update_meta_with_images(meta_path: Path, image_meta: list[dict]) -> bool:
    """Write *image_meta* into *meta_path* under ``image_paths`` / ``images_extracted_at``.

    Returns True if the file was modified (caller can use this to decide
    whether to log / skip downstream work). Merges with existing fields
    rather than overwriting — same convention as the rest of the pipeline.
    """
    if not image_meta and not meta_path.exists():
        return False

    meta: dict[str, object] = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}

    # Stable, sorted-by-page ordering for the recorded paths so the JSON
    # diff in version control doesn't churn on filename ordering.
    sorted_meta = sorted(image_meta, key=lambda m: (m["page"], m["filename"]))
    rel_paths = [
        f"data/clean/pdf-document/{meta.get('slug', 'unknown')}/images/{m['filename']}"
        for m in sorted_meta
    ]

    changed = meta.get("image_paths") != rel_paths
    if changed:
        meta["image_paths"] = rel_paths
        meta["images_extracted_at"] = _now_iso()
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return changed


def _now_iso() -> str:
    """Return current UTC time as an ISO-8601 string."""
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


def find_pdf_for_slug(pdf_index_path: Path, policy_slug: str) -> list[dict]:
    """Return pdf-index entries whose ``policy_slug`` matches *policy_slug*.

    Reads ``pdf-index.json`` (written by ``pdf_convert.convert_all_pdfs``).
    Returns an empty list if the index is missing or empty.
    """
    if not pdf_index_path.exists():
        return []
    try:
        entries = json.loads(pdf_index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return [e for e in entries if e.get("policy_slug") == policy_slug]
