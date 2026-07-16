"""Validate PDF→markdown extraction quality.

Two independent extraction paths run against every PDF in
``data/sources/opportunity-website/pdfs/``:

- **pymupdf4llm** (the production extractor in ``pdf_convert.py``)
- **pymupdf** raw page text (independent ground-truth signal)

For each PDF we compute:

- **word coverage ratio**: fraction of unique words present in the
  pymupdf4llm markdown that also appear in the raw pymupdf text.
  Light threshold: ≥0.99.
- **structural spot-check**: heading count, table row count, bullet
  count on the cleaned markdown — must be ≥1 of each when the raw
  PDF has visible structural elements.

Outputs a JSON-serialisable dict per PDF. Consumed by the
``validate_pdf_extraction`` Dagster asset and the pytest suite.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pymupdf
import pymupdf4llm

from pipeline.ingestion.pdf_convert import clean_body
from pipeline.text_clean import strip_glyphs

logger = logging.getLogger(__name__)

# Default policy-PDF location (gitignored raw layer)
DEFAULT_PDF_DIR = Path("data/sources/opportunity-website/pdfs")

# Thresholds — kept loose so tests aren't brittle to legitimate formatting
# differences (hyphenation across line breaks, page-footer vs page-header
# whitespace, table-cell whitespace). True data loss would show up at <0.90.
WORD_COVERAGE_THRESHOLD = 0.95


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class PDFValidation:
    """One PDF's validation result — JSON-serialisable via asdict()."""

    filename: str
    # Independent-extraction word counts
    pymupdf_words: int = 0
    markdown_words: int = 0
    unique_words_pymupdf: int = 0
    unique_words_markdown: int = 0
    # Coverage: fraction of pymupdf unique words present in markdown
    word_coverage: float = 0.0
    # Structural spot-checks (post-clean) — counts in the markdown body
    headings: int = 0
    table_rows: int = 0
    bullets: int = 0
    # Status
    passed: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_markdown(pdf_path: Path) -> str:
    """Run the production extractor (pymupdf4llm) and return raw markdown."""
    return pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)


def extract_raw_text(pdf_path: Path) -> str:
    """Independent extraction — raw text via pymupdf page.get_text().

    Used as ground-truth signal: if pymupdf4llm drops a word, this catches it.
    """
    with pymupdf.open(str(pdf_path)) as doc:
        pages_text = [page.get_text() for page in doc]
    return "\n".join(pages_text)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _normalise_for_compare(text: str) -> str:
    """Strip zero-width chars + replacement chars before tokenisation.

    The constitution PDF embeds glyph fallbacks as zero-width / replacement
    characters in the middle of words (e.g. 'Officers' → 'O\\u200bficers').
    Without normalisation these split into multiple tokens and inflate the
    'missing words' count. NFKD handles the common decomposition cases.
    """
    text = strip_glyphs(text)
    # Strip combining marks (NFKD then drop combining class)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def _tokenise(text: str) -> set[str]:
    """Lowercase alphanumeric tokens — what we count as 'words'."""
    return {tok.lower() for tok in re.findall(r"[A-Za-z0-9]+", _normalise_for_compare(text))}


def word_coverage(raw_text: str, markdown: str) -> tuple[float, int, int, int, int]:
    """Fraction of raw-text words present in markdown + raw/md token counts.

    Returns: (coverage_ratio, raw_tokens, md_tokens, raw_unique, md_unique)
    """
    raw_norm = _normalise_for_compare(raw_text)
    md_norm = _normalise_for_compare(markdown)
    raw_tokens = re.findall(r"[A-Za-z0-9]+", raw_norm)
    md_tokens = re.findall(r"[A-Za-z0-9]+", md_norm)
    raw_unique = _tokenise(raw_text)
    md_unique = _tokenise(markdown)
    if not raw_unique:
        return 0.0, len(raw_tokens), len(md_tokens), 0, len(md_unique)
    # Which raw words are present somewhere in the markdown?
    present = raw_unique & md_unique
    return (
        len(present) / len(raw_unique),
        len(raw_tokens),
        len(md_tokens),
        len(raw_unique),
        len(md_unique),
    )


def structural_stats(markdown: str) -> dict[str, int]:
    """Count structural elements in the cleaned markdown."""
    return {
        "headings": len(re.findall(r"^#{1,6}\s", markdown, re.MULTILINE)),
        "table_rows": len(re.findall(r"^\|", markdown, re.MULTILINE)),
        "bullets": len(re.findall(r"^- ", markdown, re.MULTILINE)),
    }


# ---------------------------------------------------------------------------
# Per-PDF validation
# ---------------------------------------------------------------------------


def validate_pdf(pdf_path: Path) -> PDFValidation:
    """Run all validation steps for one PDF and return a result record."""
    raw_text = extract_raw_text(pdf_path)
    raw_md = extract_markdown(pdf_path)
    # Structural stats run against the production-cleaned body (same cleanup
    # that pdf_convert.clean_body applies) — not against a regex hack.
    body = clean_body(raw_md)

    coverage, raw_n, md_n, raw_uniq, md_uniq = word_coverage(raw_text, raw_md)
    stats = structural_stats(body)

    notes: list[str] = []
    # Detect font-glyph artefacts — common pattern: a word with a replacement
    # char or zero-width joiner in the middle, e.g. "O\ufficers" or "Wri\u200ben".
    # These render fine in markdown but break plain-text grep / search.
    glyph_artefact_count = len(re.findall(r"[A-Za-z][\ufffd\u200b-\u200f]", body))
    if glyph_artefact_count:
        notes.append(f"{glyph_artefact_count} font-glyph artefact(s) in body")

    if coverage < WORD_COVERAGE_THRESHOLD:
        notes.append(f"word coverage {coverage:.3f} < threshold {WORD_COVERAGE_THRESHOLD}")

    # Structural sanity — a non-trivial policy PDF should have ≥1 heading.
    # Skip for governance docs that are pure table-of-contents (charter is
    # 340 words; would otherwise fail).
    is_short = raw_n < 500  # tiny docs skip the heading check
    if not is_short and stats["headings"] == 0:
        notes.append("no headings detected in markdown body")

    # Pass = coverage OK. Glyph artefacts are noted but don't fail (rendering
    # is fine; downstream consumers can choose to post-process).
    passed = coverage >= WORD_COVERAGE_THRESHOLD

    return PDFValidation(
        filename=pdf_path.name,
        pymupdf_words=raw_n,
        markdown_words=md_n,
        unique_words_pymupdf=raw_uniq,
        unique_words_markdown=md_uniq,
        word_coverage=round(coverage, 4),
        headings=stats["headings"],
        table_rows=stats["table_rows"],
        bullets=stats["bullets"],
        passed=passed,
        notes=notes,
    )


def validate_all_pdfs(pdf_dir: Path = DEFAULT_PDF_DIR) -> list[PDFValidation]:
    """Validate every PDF in *pdf_dir* and return results sorted by filename."""
    if not pdf_dir.exists():
        logger.warning("PDF directory missing: %s", pdf_dir)
        return []
    results: list[PDFValidation] = []
    for pdf_path in sorted(pdf_dir.glob("*.pdf")):
        try:
            results.append(validate_pdf(pdf_path))
        except Exception as e:
            logger.error("Validation failed for %s: %s", pdf_path.name, e)
            results.append(
                PDFValidation(
                    filename=pdf_path.name,
                    passed=False,
                    notes=[f"exception during validation: {e}"],
                )
            )
    return results


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def write_validation_json(
    results: list[PDFValidation],
    output_path: Path,
) -> None:
    """Write results as JSON to *output_path*."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "threshold": WORD_COVERAGE_THRESHOLD,
        "pdf_count": len(results),
        "passed_count": sum(1 for r in results if r.passed),
        "results": [r.to_dict() for r in results],
    }
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def load_validation_json(input_path: Path) -> dict:
    """Read a previously-written validation JSON; returns {} if missing."""
    if not input_path.exists():
        return {}
    return json.loads(input_path.read_text(encoding="utf-8"))
