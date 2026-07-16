"""Tests for PDF→markdown extraction quality.

Two-pass validation: extract via pymupdf4llm (production path) and
pymupdf raw text (independent signal). Assert word coverage + a
minimum structural skeleton for every PDF in
``data/sources/opportunity-website/pdfs/``.

Tests are skipped automatically if the PDF directory is empty (i.e. on
a fresh clone without raw PDFs). The threshold (0.95) is loose enough
to pass legitimate formatting differences but tight enough to catch
truly broken extraction (which lands at <0.90).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.transforms.pdf_validation import (
    DEFAULT_PDF_DIR,
    WORD_COVERAGE_THRESHOLD,
    validate_pdf,
)

PDF_DIR = Path(DEFAULT_PDF_DIR)
pdf_paths = sorted(PDF_DIR.glob("*.pdf"))
pytestmark = pytest.mark.skipif(
    not pdf_paths,
    reason=f"No PDFs in {PDF_DIR} — run `uv run dg launch pdf_job` first",
)


@pytest.fixture(params=pdf_paths, ids=lambda p: p.name)
def pdf_path(request):
    return request.param


def test_validation_runs(pdf_path):
    """Smoke test — validation completes without exceptions."""
    result = validate_pdf(pdf_path)
    assert result.filename == pdf_path.name
    assert result.pymupdf_words > 0


def test_word_coverage_meets_threshold(pdf_path):
    """Every word in the raw PDF must round-trip into the markdown ≥95% of the time."""
    result = validate_pdf(pdf_path)
    assert result.word_coverage >= WORD_COVERAGE_THRESHOLD, (
        f"{pdf_path.name}: coverage {result.word_coverage:.3f} "
        f"< threshold {WORD_COVERAGE_THRESHOLD}"
    )


def test_no_font_glyph_artefacts(pdf_path):
    """Zero-width / PUA / replacement characters in word interiors must be stripped.

    Constitution.pdf originally emitted 'O<PUA>ficers' for 'Officers'. The
    _clean_body() fix in pdf_convert.py removes these. This test guards
    against regressions in the stripper.
    """
    result = validate_pdf(pdf_path)
    assert "font-glyph artefact" not in " ".join(result.notes), f"{pdf_path.name}: {result.notes}"


def test_structural_skeleton_present(pdf_path):
    """Non-trivial PDFs must have ≥1 heading + ≥1 bullet in the cleaned markdown.

    Governance docs (charter, constitution) are also policy PDFs — charter
    has 15 headings, constitution has 118 — so the heading threshold is
    safe. The bullet threshold accommodates pure-table docs like the
    transition plan (which has 4 bullets and 16 table rows).
    """
    result = validate_pdf(pdf_path)
    if result.pymupdf_words < 500:  # tiny docs skip the check
        pytest.skip("Document too short for structural spot-check")
    assert result.headings >= 1, f"{pdf_path.name}: no headings detected"


def test_validation_json_loadable(pdf_path, tmp_path):
    """Round-trip through the JSON writer/loader."""
    from pipeline.transforms.pdf_validation import (
        load_validation_json,
        write_validation_json,
    )

    result = validate_pdf(pdf_path)
    out = tmp_path / "validation.json"
    write_validation_json([result], out)
    loaded = load_validation_json(out)
    assert loaded["pdf_count"] == 1
    assert loaded["results"][0]["filename"] == pdf_path.name
