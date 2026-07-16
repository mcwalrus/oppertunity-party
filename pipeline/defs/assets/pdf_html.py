"""Dagster asset — render cleaned PDF markdown to per-item HTML.

Writes ``data/clean/pdf-document/{slug}/{slug}.html`` for every
existing item, and updates each item's ``meta.json`` with
``html_path`` (project-root-relative path).
"""

# NOTE: do NOT add `from __future__ import annotations` here. Dagster
# inspects the ``context`` parameter's annotation at decoration time to
# validate it against ``AssetExecutionContext``; PEP-563 string
# annotations break that.

import dagster as dg
from dagster import AssetExecutionContext

from pipeline.transforms.pdf_to_html import render_pdf_html


@dg.asset(group_name="clean", deps=["clean_pdfs"])
def pdf_html(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Render every pdf-document/{slug}/{slug}.md → {slug}.html.

    Idempotent — re-runs overwrite existing HTML files with identical
    output (deterministic rendering). Updates ``meta.json`` with
    ``html_path`` only when the value differs.
    """
    html_paths = render_pdf_html()
    context.log.info("Rendered %d PDF HTML files", len(html_paths))
    return dg.MaterializeResult(
        metadata={
            "html_count": len(html_paths),
            "html_paths": html_paths[:20],  # truncate for UI
        }
    )
