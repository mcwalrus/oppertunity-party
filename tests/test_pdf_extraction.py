"""Tests for PDF→markdown extraction quality.

Two-pass validation: extract via pymupdf4llm (production path) and
pymupdf raw text (independent signal). Assert word coverage + a
minimum structural skeleton for every PDF in
``data/sources/opportunity-website/pdfs/``.

Tests are skipped automatically if the PDF directory is empty (i.e. on
a fresh clone without raw PDFs). The threshold (0.95) is loose enough
to pass legitimate formatting differences but tight enough to catch
truly broken extraction (which lands at <0.90).

Per-PDF validation runs once as a session-scoped fixture and is shared
across tests, so the suite pays the extraction cost once per PDF
instead of once per (test x PDF).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pipeline.transforms.pdf_validation import (
    DEFAULT_PDF_DIR,
    WORD_COVERAGE_THRESHOLD,
    PDFValidation,
    load_validation_json,
    validate_pdf,
    write_validation_json,
)

PDF_DIR = Path(DEFAULT_PDF_DIR)
pdf_paths = sorted(PDF_DIR.glob("*.pdf"))
pytestmark = pytest.mark.skipif(
    not pdf_paths,
    reason=f"No PDFs in {PDF_DIR} — run `uv run dg launch pdf_job` first",
)


@pytest.fixture(scope="session")
def all_results():
    """Validate every PDF once; share the results across all tests."""
    return {p.name: validate_pdf(p) for p in pdf_paths}


@pytest.fixture(params=[p.name for p in pdf_paths], ids=lambda n: n)
def validation_result(request, all_results):
    """Pre-computed validation result for one PDF — no per-test extraction."""
    return all_results[request.param]


def test_validation_runs(validation_result):
    """Smoke test — validation completes and produces a non-empty result."""
    assert validation_result.pymupdf_words > 0


def test_word_coverage_meets_threshold(validation_result):
    """Every word in the raw PDF must round-trip into the markdown ≥95% of the time."""
    assert validation_result.word_coverage >= WORD_COVERAGE_THRESHOLD, (
        f"{validation_result.filename}: coverage {validation_result.word_coverage:.3f} "
        f"< threshold {WORD_COVERAGE_THRESHOLD}"
    )


def test_no_font_glyph_artefacts(validation_result):
    """Zero-width / PUA / replacement characters in word interiors must be stripped.

    Constitution.pdf originally emitted 'O<PUA>ficers' for 'Officers'. The
    clean_body() fix in pdf_convert.py removes these. This test guards
    against regressions in strip_glyphs().
    """
    assert "font-glyph artefact" not in " ".join(validation_result.notes), (
        f"{validation_result.filename}: {validation_result.notes}"
    )


def test_structural_skeleton_present(validation_result):
    """Non-trivial PDFs must have ≥1 heading in the cleaned markdown body."""
    if validation_result.pymupdf_words < 500:  # tiny docs skip the check
        pytest.skip("Document too short for structural spot-check")
    assert validation_result.headings >= 1, f"{validation_result.filename}: no headings detected"


def test_validation_json_loadable(tmp_path):
    """Round-trip through the JSON writer/loader — no PDF extraction.

    The serialiser is a pure function; no need to pay the extraction cost
    to test it. Synthetic PDFValidation exercises the same code path.
    """
    result = PDFValidation(filename="synthetic.pdf", word_coverage=0.95, passed=True)
    out = tmp_path / "validation.json"
    write_validation_json([result], out)
    loaded = load_validation_json(out)
    assert loaded["pdf_count"] == 1
    assert loaded["results"][0]["filename"] == "synthetic.pdf"
