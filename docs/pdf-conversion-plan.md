# Plan: Replace `pdftotext` with `pymupdf4llm` for PDF → Markdown

**Status:** Proposed (2026-06-08)
**Owner:** Max
**Scope:** `scraper/pdf_convert.py`, `scraper/party_info.py`, `pyproject.toml`

## Problem

The current pipeline shells out to `pdftotext -layout` (poppler) and then
hand-parses the text in `scraper/pdf_convert.py`. The output has three
recurring quality problems:

- **No headings.** Section titles ("The problems we're solving", "Our reforms
  will:") come out as plain paragraphs, so the markdown has no structure.
- **Broken paragraph reflow.** Wrapped lines are not re-joined — ~228 lines per
  document end mid-sentence, which hurts downstream chunking/search in the MCP
  layer.
- **Mangled tables.** The Tax Reset costings tables are destroyed by
  `-layout` text extraction.

It also carries a **system dependency** (`brew install poppler`) that must be
present on every machine and in CI.

## Evaluation

Benchmarked four converters on all six PDFs in `data/pdfs/`. Harness and the
recommended extraction code are committed under
[`docs/reference/`](./reference/) so the comparison is reproducible.

| Converter | Headings | Paragraph reflow | Tables | Offline | Cost |
|-----------|:--------:|:----------------:|:------:|:-------:|------|
| `pdftotext -layout` (current) | ❌ 0 | ❌ ~228 breaks | ❌ broken | ✅ | system dep (poppler) |
| markitdown (Microsoft) | ❌ 0 | ❌ ~225 breaks | ❌ | ✅ | raw text dump, not md-aware |
| docling (IBM) | — | — | — | ❌ | needs model download (HF/modelscope) + torch + minutes/CPU; **could not run offline** |
| **pymupdf4llm** ⭐ | ✅ 3–55/doc | ✅ **0 breaks** | ✅ real md tables | ✅ | pure-Python (PyMuPDF), fast |

Per-document signals for pymupdf4llm (headings / reflow_breaks):

```
MakingZeroTheHero-Summary-Report.pdf      14 / 0
Opportunity_Policy_Abundant Energy.pdf    28 / 0
Opportunity_Policy_Citizens Voice.pdf      9 / 0
Opportunity_Policy_Healthy Oceans.pdf     40 / 0
Opportunity_Tax Reset_Policy Overview.pdf 55 / 0
Opportunity_Tax Reset_Transition Plan.pdf  3 / 0
```

### Decision

Adopt **pymupdf4llm**. It is the only candidate that produces structured
markdown (headings + reflowed prose + tables), runs fully offline with no
model downloads, and removes the poppler system dependency. docling's stronger
layout model is not worth its network/torch/CPU cost for this small set of
clean, text-layer PDFs.

## Implementation steps

1. **Dependency swap**
   - `uv add pymupdf4llm`
   - Remove the `brew install poppler` note from `pyproject.toml`.
   - Keep poppler only if `scraper/party_info.py` still needs it (see step 3).

2. **Rewrite `scraper/pdf_convert.py`**
   - Replace `extract_text()` (subprocess `pdftotext`) with
     `pymupdf4llm.to_markdown()`. See
     [`docs/reference/pymupdf4llm_extract.py`](./reference/pymupdf4llm_extract.py)
     for the drop-in `extract_markdown()` + `parse_header()`.
   - Delete most of `format_body()` — pymupdf4llm already emits bullets,
     headings, and tables. The only post-processing kept is the `_clean()`
     pass that strips:
     1. `**==> picture ... <==**` placeholders,
     2. bold page footers (`**Opportunity Party Energy**`, `**Page 1**`) — the
        existing `PAGE_FOOTER_RE` still applies after de-bolding,
     3. the one-line header block (already captured into the front-matter table).
   - `parse_header()` now reads the bold values from the single header line
     (`Date **February 2026** Policy **Abundant Energy** ...`) instead of the
     multi-space key/value format.

3. **`scraper/party_info.py`** also calls `pdftotext -layout` (line ~209).
   Either migrate it to the same helper or leave it; if migrated, poppler can
   be dropped entirely.

4. **Verify**
   - Re-run conversion over `data/pdfs/*.pdf`, diff the new
     `data/policies/**/pdf-*.md` against the committed versions.
   - Confirm: headings present, no mid-sentence line breaks, Tax Reset tables
     render as markdown tables.
   - `just` lint/type checks pass (ruff + ty).

## Risks / notes

- **Source typos pass through.** e.g. "do better.We" has no space in the PDF
  text layer; no converter fixes this. Out of scope.
- **Output churn.** The committed `pdf-*.md` files will change substantially
  (this is the point). Review the first regeneration diff carefully.
- **`pymupdf4llm` version** pinned during eval: `1.27.2.3` (bundles PyMuPDF).
- **Licensing:** PyMuPDF is AGPL — fine for this internal scraper, worth noting
  if any of this is ever distributed.

## Reference files

- [`docs/reference/benchmark_converters.py`](./reference/benchmark_converters.py)
  — the comparison harness (re-run to reproduce the table above).
- [`docs/reference/pymupdf4llm_extract.py`](./reference/pymupdf4llm_extract.py)
  — drop-in extraction + cleanup helper for `pdf_convert.py`.
