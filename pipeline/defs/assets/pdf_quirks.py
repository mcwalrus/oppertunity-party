"""Dagster asset that applies per-PDF quirk patches to source-layer markdown.

Sits between ``raw_pdfs`` (extraction) and ``clean_pdfs`` (source→clean
transform). Each PDF's quirks are defined in
``pipeline/transforms/pdf_quirks.py`` keyed by filename. The patched source
markdown is what ``clean_pdfs`` reads.

Source layer is gitignored; unpatched raw extraction is reproducible from
the PDF binary. Patches are deterministic and idempotent — re-running this
asset is safe.
"""

# NOTE: do NOT add `from __future__ import annotations` here. Dagster
# inspects the ``context`` parameter's annotation at decoration time to
# validate it against ``AssetExecutionContext``; PEP-563 string
# annotations break that.

import dagster as dg
from dagster import AssetExecutionContext

from pipeline.defs.partitions import policy_slug_partitions
from pipeline.ingestion.client import DATA_DIR
from pipeline.transforms.pdf_quirks import QUIRKS_BY_FILENAME, apply_quirks


@dg.asset(
    group_name="clean",
    deps=["raw_pdfs"],
    partitions_def=policy_slug_partitions,
)
def apply_pdf_quirks(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Apply per-PDF quirk patches to source-layer PDF markdown for this partition."""
    policy_slug = context.partition_key
    policy_dir = DATA_DIR / "policies" / policy_slug

    if not policy_dir.exists():
        return dg.MaterializeResult(metadata={"policy_slug": policy_slug, "patched_files": []})

    patched: list[str] = []
    for md_file in sorted(policy_dir.glob("pdf-*.md")):
        quirks = QUIRKS_BY_FILENAME.get(md_file.name, [])
        if not quirks:
            continue

        original = md_file.read_text(encoding="utf-8")
        patched_text = apply_quirks(md_file.name, original)
        if patched_text != original:
            md_file.write_text(patched_text, encoding="utf-8")
            patched.append(md_file.name)
            context.log.info("Patched %s with %d quirk(s)", md_file.name, len(quirks))

    return dg.MaterializeResult(
        metadata={
            "policy_slug": policy_slug,
            "patched_files": patched,
            "patch_count": len(patched),
        }
    )
