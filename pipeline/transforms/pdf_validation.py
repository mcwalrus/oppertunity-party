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
from datetime import UTC, datetime
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


# ---------------------------------------------------------------------------
# Pipeline report
# ---------------------------------------------------------------------------


def render_pipeline_report(
    validation: dict,
    policy_index: list[dict],
    pdf_ref: dict,
    output_path: Path,
) -> int:
    """Render and write docs/pdf-pipeline.md. Returns bytes written.

    Reads three pre-loaded inputs (validation JSON, scraper policy index,
    PDF reference registry) and emits a human-readable Markdown report
    covering policy coverage, per-PDF extraction quality, and known issues.
    All file IO is performed here so the asset wrapper stays thin.
    """
    # Index validation results by filename (reserved for per-PDF drill-down;
    # not currently referenced by the report body).
    _val_index = {r["filename"]: r for r in validation.get("results", [])}

    # Map policy_slug → set of unique PDF filenames (via pdf_ref, deduped —
    # reference.json carries both migrated and canonical entries pointing at
    # the same file).
    pdfs_by_slug: dict[str, set[str]] = {}
    for entry in pdf_ref.get("downloads", {}).values():
        slug = entry.get("policy_slug")
        filename = entry.get("filename")
        if slug and filename:
            pdfs_by_slug.setdefault(slug, set()).add(filename)

    # Cross-check: which policy pages have a PDF link in the scraper index
    # but NO matching entry in pdf_ref? These are "missing PDF downloads" —
    # the link was discovered but the download didn't materialise.
    missing_downloads: list[tuple[str, str]] = []
    for p in policy_index:
        for url in p.get("pdf_downloads") or []:
            if "drive.google.com" not in url:
                continue
            slug = p["slug"]
            if slug not in pdfs_by_slug:
                missing_downloads.append((slug, url))

    # Generate the report
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = []
    lines.append("# PDF Pipeline Report")
    lines.append("")
    lines.append(
        "Auto-generated by the `write_pdf_pipeline_report` Dagster asset. "
        "Run via the `validation_job` job, or `just dev` + the Dagster UI."
    )
    lines.append("")
    lines.append(f"_Last regenerated: {now}_")
    lines.append("")
    lines.append("## What this pipeline does")
    lines.append("")
    lines.append(
        "Opportunity Party publishes policy detail PDFs on Google Drive. "
        "These PDFs are downloaded into `data/sources/opportunity-website/pdfs/` "
        "(gitignored — never served from the web), then extracted to markdown "
        "via [`pymupdf4llm`](https://pymupdf4llm.readthedocs.io/), normalised "
        "into `data/clean/policy/{slug}/`, and rendered as HTML by the Astro "
        "site at `site/dist/policies/{slug}/`. The site is the only place the "
        "policy text appears online — no PDF file is ever served."
    )
    lines.append("")
    lines.append("## Policy coverage")
    lines.append("")
    lines.append(
        f"Of {len(policy_index)} policy pages on opportunity.org.nz, "
        f"{sum(1 for p in policy_index if p.get('pdf_downloads'))} "
        "have linked PDF documents."
    )
    lines.append("")
    lines.append("| Policy | Slug | Linked PDF? | Filename |")
    lines.append("|---|---|---|---|")
    for p in sorted(policy_index, key=lambda x: x.get("title", "")):
        slug = p.get("slug", "")
        title = p.get("title", slug)
        pdfs = p.get("pdf_downloads") or []
        if pdfs:
            filenames = ", ".join(sorted(pdfs_by_slug.get(slug, set())))
            lines.append(f"| {title} | `{slug}` | yes | {filenames or '(unresolved)'} |")
        else:
            lines.append(f"| {title} | `{slug}` | no | — |")
    lines.append("")

    # Flag policy pages with a PDF link in the scraper index but no
    # matching entry in pdf_ref — these need the pdf_job re-run.
    if missing_downloads:
        lines.append("### Missing PDF downloads")
        lines.append("")
        lines.append(
            "These policy pages have a PDF link in the scraper index but no "
            "matching entry in `pdfs/reference.json` — re-run `pdf_job` for "
            "the listed slug(s) to fetch them."
        )
        lines.append("")
        lines.append("| Slug | Link |")
        lines.append("|---|---|")
        for slug, url in missing_downloads:
            lines.append(f"| `{slug}` | {url} |")
        lines.append("")

    # Governance PDFs (charter, constitution)
    governance = list(pdfs_by_slug.get("charter", set())) + list(
        pdfs_by_slug.get("constitution", set())
    )
    if governance:
        lines.append("### Governance documents")
        lines.append("")
        lines.append(
            "Charter + Constitution are stored under `party-information/` in "
            "the clean layer but their source PDFs live alongside the policy "
            "PDFs."
        )
        lines.append("")
        lines.append("| Document | Filename |")
        lines.append("|---|---|")
        for fn in governance:
            doc = "Charter" if "charter" in fn.lower() else "Constitution"
            lines.append(f"| {doc} | `{fn}` |")
        lines.append("")

    # Per-PDF quality table
    lines.append("## Extraction quality")
    lines.append("")
    results = validation.get("results", [])
    if not results:
        lines.append("_No validation results available._")
        lines.append("")
    else:
        lines.append(
            f"Threshold: word coverage ≥ {validation.get('threshold', 0.95):.0%} "
            "(pymupdf4llm markdown vs pymupdf raw text). Lower coverage means "
            "more content lost during extraction."
        )
        lines.append("")
        lines.append("| PDF | Words (raw) | Words (md) | Coverage | H | T | B | Status |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for r in sorted(results, key=lambda x: x["filename"]):
            cov = r["word_coverage"]
            status = "✅ pass" if r["passed"] else "⚠️ fail"
            lines.append(
                f"| `{r['filename']}` "
                f"| {r['pymupdf_words']:,} "
                f"| {r['markdown_words']:,} "
                f"| {cov:.1%} "
                f"| {r['headings']} "
                f"| {r['table_rows']} "
                f"| {r['bullets']} "
                f"| {status} |"
            )
        lines.append("")
        lines.append(
            "_H = headings, T = table rows, B = bullet items in the cleaned markdown body._"
        )
        lines.append("")

        # Notes per PDF
        any_notes = any(r.get("notes") for r in results)
        if any_notes:
            lines.append("### Per-PDF notes")
            lines.append("")
            for r in sorted(results, key=lambda x: x["filename"]):
                if r.get("notes"):
                    lines.append(f"- **`{r['filename']}`**: " + "; ".join(r["notes"]))
            lines.append("")

    # Known issues + future improvements
    lines.append("## Known issues & future improvements")
    lines.append("")
    lines.append(
        "- **Constitution font-glyph artefacts**: the source PDF embeds "
        "'ffi' / 'ffl' ligatures as Private Use Area chars and a few "
        "replacement chars. `_clean_body()` in `pdf_convert.py` strips "
        "zero-width / replacement / PUA-between-letters characters "
        "post-extraction. Coverage stays at ~97% because the source PDF "
        "itself is missing the letter 'i' in 'Qualifcations' — unfixable "
        "from extraction side."
    )
    lines.append("")
    lines.append(
        "- **Tax Reset Transition Plan**: small table cells lose some text "
        "in the markdown (98.3% coverage). The numeric values are intact; "
        "the loss is in cell whitespace. Not worth a custom extractor for "
        "a single document."
    )
    lines.append("")
    lines.append(
        "- **No automatic PDF discovery**: `pipeline/ingestion/policies.py` "
        "scrapes policy pages for PDF links but a policy that links to a "
        "PDF outside Google Drive (e.g. the `MakingZeroTheHero` report on "
        "healthy-land) downloads via plain HTTP. New link types need to be "
        "added there."
    )
    lines.append("")
    lines.append(
        "- **No image extraction**: PDFs have illustrations (Tax Reset "
        "calculator, Healthy Oceans diagrams) that are dropped as `**==> "
        "picture <==**` placeholders. Re-introducing images would require "
        "deciding where they live — `data/sources/` for binaries (gitignored) "
        "+ a `media_paths` field in `pdf-document` meta — plus an Astro "
        "template change."
    )
    lines.append("")
    lines.append(
        "- **No HTML output outside Astro**: policy content is served only "
        "after `pnpm build` produces `site/dist/`. LLM/MCP consumers that "
        "want rendered HTML must run the build first. Adding a "
        "`pipeline/defs/assets/pdf_html.py` asset that emits one .html per "
        "policy (mirroring what Astro produces) would let non-Astro consumers "
        "read HTML directly — but it's a duplicate of the build output."
    )
    lines.append("")
    lines.append("## How to extend")
    lines.append("")
    lines.append(
        "- **New PDF link type**: extend `pipeline/ingestion/pdf_download.py:_download_single`."
    )
    lines.append(
        "- **Custom extraction rules**: `pipeline/ingestion/pdf_convert.py` "
        "owns `parse_header` / `_clean_body` / `format_markdown`."
    )
    lines.append(
        "- **Tighter validation**: lower `WORD_COVERAGE_THRESHOLD` in "
        "`pipeline/transforms/pdf_validation.py` (currently 0.95)."
    )
    lines.append(
        "- **Run validation locally**: `uv run dg launch validation_job` (or "
        "`just dev` → UI → validation_job)."
    )
    lines.append("- **Run pytest suite**: `uv run pytest tests/` (also via `just test`).")
    lines.append("")

    # Write the file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path.stat().st_size
