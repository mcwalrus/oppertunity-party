"""Dagster asset — extract PDF images and reference them in clean markdown.

Runs after ``clean_pdfs`` (downstream in the clean layer) for one
policy-slug partition. For every pdf-document item belonging to
the partition, this asset:

1. Extracts embedded images from the source PDF into
   ``data/clean/pdf-document/{slug}/images/``.
2. Replaces ``----- Start/End of picture text -----`` blocks in the
   item's clean markdown with ``![alt](images/file.jpg)`` links.
3. Records ``image_paths`` + ``images_extracted_at`` in the item's
   ``meta.json``.

The asset is idempotent — re-running skips already-extracted images
(see ``extract_pdf_images``) and only rewrites ``meta.json`` when
the recorded ``image_paths`` actually changed.
"""

# NOTE: do NOT add `from __future__ import annotations` here. Dagster
# inspects the ``context`` parameter's annotation at decoration time to
# validate it against ``AssetExecutionContext``; PEP-563 string
# annotations break that.

import logging
from pathlib import Path

import dagster as dg
from dagster import AssetExecutionContext

from pipeline.defs.partitions import policy_slug_partitions
from pipeline.paths import CLEAN_DIR, DATA_DIR, POLICY_ASSETS_DIR
from pipeline.transforms.pdf_images import (
    extract_pdf_images,
    find_pages_with_picture_text,
    find_pdf_for_slug,
    replace_picture_text_with_images,
    update_meta_with_images,
)

logger = logging.getLogger(__name__)

# Source markdown filename produced by pdf_convert per policy slug.
# Each policy-slug partition has one (or more) pdf-{type}.md files
# that map to a corresponding pdf-document/{slug} clean item.
_PDF_INDEX = DATA_DIR / "policies" / "pdf-index.json"


@dg.asset(
    group_name="clean",
    deps=["clean_pdfs"],
    partitions_def=policy_slug_partitions,
)
def pdf_images(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Extract PDF images and reference them in clean markdown for this partition."""
    policy_slug = context.partition_key

    pdf_entries = find_pdf_for_slug(_PDF_INDEX, policy_slug)
    if not pdf_entries:
        return dg.MaterializeResult(metadata={"policy_slug": policy_slug, "items_processed": 0})

    items_processed: list[str] = []
    images_extracted: list[str] = []
    total_replacements = 0

    for entry in pdf_entries:
        source_md_relpath = entry.get("output_file", "")
        # The pdf-index output_file is absolute; derive the clean slug
        # from the source filename's stem (e.g. "pdf-default.md" -> "default").
        source_md_name = Path(source_md_relpath).name
        doc_type = source_md_name[len("pdf-") : -len(".md")]  # strip "pdf-" + ".md"
        doc_slug = f"{policy_slug}-{doc_type}"
        item_dir = CLEAN_DIR / "pdf-document" / doc_slug
        if not item_dir.exists():
            context.log.warning("No clean item for %s — skipping", doc_slug)
            continue

        # Resolve the source PDF
        source_pdf_name = entry.get("source_file", "")
        pdf_path = POLICY_ASSETS_DIR / source_pdf_name
        if not pdf_path.exists():
            context.log.warning("Source PDF missing: %s — skipping", pdf_path)
            continue

        # Extract images — only from pages that pymupdf4llm flagged with
        # a picture-text block, so decorative page backgrounds are dropped.
        page_filter = find_pages_with_picture_text(pdf_path)
        images_dir = item_dir / "images"
        image_meta = extract_pdf_images(pdf_path, images_dir, page_filter=page_filter)
        if not image_meta:
            context.log.info("No images extracted from %s", source_pdf_name)
            continue

        # Rewrite the clean markdown: replace picture-text blocks with
        # image references in document order.
        md_path = item_dir / f"{doc_slug}.md"
        md_text = md_path.read_text(encoding="utf-8")
        image_filenames = [m["filename"] for m in sorted(image_meta, key=lambda m: m["page"])]
        new_md, replacements = replace_picture_text_with_images(
            md_text, image_filenames, image_rel_dir="images"
        )
        if replacements:
            md_path.write_text(new_md, encoding="utf-8")
            total_replacements += replacements

        # Record in meta.json
        meta_path = item_dir / "meta.json"
        update_meta_with_images(meta_path, image_meta)

        items_processed.append(doc_slug)
        images_extracted.extend(m["filename"] for m in image_meta)

    context.log.info(
        "pdf_images: %d items, %d images, %d markdown replacements",
        len(items_processed),
        len(images_extracted),
        total_replacements,
    )
    return dg.MaterializeResult(
        metadata={
            "policy_slug": policy_slug,
            "items_processed": items_processed,
            "image_count": len(images_extracted),
            "image_filenames": images_extracted,
            "picture_text_replacements": total_replacements,
        }
    )
