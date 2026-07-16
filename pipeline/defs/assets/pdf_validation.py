"""Dagster assets for PDF extraction validation + coverage reporting.

Two assets:

- ``validate_pdf_extraction`` (group: validation): runs the two-pass
  validation against every PDF in the source layer and writes a JSON
  report to ``data/clean/_pdf_validation.json``.
- ``write_pdf_pipeline_report`` (group: validation): reads the validation
  JSON + the scraped policy index + the PDF reference registry, then
  emits a human-readable Markdown report at ``docs/pdf-pipeline.md``.

Both are read-only over the source layer; neither mutates any policy
content. Validation output lives alongside the clean layer because it
describes extracted-content quality — same provenance.
"""

# NOTE: do NOT add `from __future__ import annotations` here. Dagster
# inspects the ``context`` parameter's annotation at decoration time to
# validate it against ``AssetExecutionContext``; PEP-563 string
# annotations break that.

import json
import logging

import dagster as dg
from dagster import AssetExecutionContext

from pipeline.paths import CLEAN_DIR, PROJECT_ROOT
from pipeline.transforms.pdf_validation import (
    render_pipeline_report,
    validate_all_pdfs,
    write_validation_json,
)

logger = logging.getLogger(__name__)

# Output paths (resolved relative to project root so Dagster can find them
# regardless of cwd)
VALIDATION_JSON = CLEAN_DIR / "_pdf_validation.json"
REPORT_PATH = PROJECT_ROOT / "docs" / "pdf-pipeline.md"

# Source paths (same shape as ingestors use)
POLICY_INDEX = PROJECT_ROOT / "data" / "sources" / "opportunity-website" / "policies" / "index.json"
PDF_REFERENCE = (
    PROJECT_ROOT / "data" / "sources" / "opportunity-website" / "pdfs" / "reference.json"
)


@dg.asset(group_name="validation", deps=["raw_pdfs"])
def validate_pdf_extraction(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Run validation against every PDF and write data/clean/_pdf_validation.json.

    Two-pass extraction (pymupdf4llm vs pymupdf raw text) computes word
    coverage + structural spot-checks. See ``pdf_validation.py`` for the
    exact metric definitions.
    """
    results = validate_all_pdfs()
    write_validation_json(results, VALIDATION_JSON)

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    context.log.info(
        "PDF validation: %d passed, %d failed (threshold=%.2f)",
        passed,
        failed,
        0.95,
    )
    return dg.MaterializeResult(
        metadata={
            "pdf_count": len(results),
            "passed_count": passed,
            "failed_count": failed,
            "output_path": str(VALIDATION_JSON),
        }
    )


@dg.asset(
    group_name="validation",
    deps=["validate_pdf_extraction", "raw_policies"],
)
def write_pdf_pipeline_report(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Emit docs/pdf-pipeline.md — coverage + quality report.

    Thin wrapper: loads the three inputs and delegates the markdown
    construction to ``render_pipeline_report`` in ``pdf_validation``.
    """
    validation: dict = {}
    if VALIDATION_JSON.exists():
        validation = json.loads(VALIDATION_JSON.read_text(encoding="utf-8"))

    policy_index: list[dict] = []
    if POLICY_INDEX.exists():
        policy_index = json.loads(POLICY_INDEX.read_text(encoding="utf-8"))

    pdf_ref: dict = {}
    if PDF_REFERENCE.exists():
        pdf_ref = json.loads(PDF_REFERENCE.read_text(encoding="utf-8"))

    size = render_pipeline_report(validation, policy_index, pdf_ref, REPORT_PATH)
    results = validation.get("results", [])
    context.log.info("Wrote %s (%d bytes)", REPORT_PATH, size)

    return dg.MaterializeResult(
        metadata={
            "report_path": str(REPORT_PATH),
            "size_bytes": size,
            "pdfs_validated": len(results),
            "policy_pages": len(policy_index),
        }
    )
