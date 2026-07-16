# Handoff — PDF Pipeline Hardening Followup

**Session scope:** review of `oppertunity-party-w7q` work (PDF→markdown
validation + coverage report) + applied the root-cause and test-caching
findings from the review. Captures state for the next session to pick
up the remaining improvements.

## What was delivered this session

### Commit pushed to `main`

| SHA | Title |
|---|---|
| `4d20309` | `refactor(pdf-validation): share glyph cleanup, cache test results` |

### New file

| Path | Purpose |
|---|---|
| `pipeline/text_clean.py` | Single source of truth for glyph stripping (zero-width / replacement / PUA-between-letters). Used by both `pdf_convert.clean_body` and `pdf_validation._normalise_for_compare`. The regex can no longer drift between the two. |

### Modified files

| Path | Change |
|---|---|
| `pipeline/ingestion/pdf_convert.py` | `_clean_body` → `clean_body` (now public so the validator can reuse it). Internalises `strip_glyphs()` instead of inlining the regex. |
| `pipeline/transforms/pdf_validation.py` | Imports `clean_body` and `strip_glyphs`. `validate_pdf` runs structural stats against the production-cleaned body — same body production keeps, not a regex hack. `_clean_markdown` removed. `import unicodedata` moved to module top. `extract_raw_text` uses `with pymupdf.open(...)` for exception safety. |
| `tests/test_pdf_extraction.py` | Session-scoped `all_results` fixture validates each PDF once per session; tests parametrise over results. JSON round-trip test uses synthetic `PDFValidation` (no extraction). |
| `data/clean/_pdf_validation.json` | Regenerated — counts updated. |
| `docs/pdf-pipeline.md` | Regenerated — counts updated; "Custom extraction rules" bullet now references `clean_body` (was `_clean_body`). |

### Verification

```bash
just check              # ruff + ruff-format + ty + pytest — must pass
uv run dg launch --job validation_job   # re-materialises both assets
cat docs/pdf-pipeline.md                # human-readable report
```

Validation after refactor (8 PDFs, all pass, threshold 0.95):

| PDF | Words (raw) | Words (md) | Coverage | Δ from before |
|---|---|---|---|---|
| MakingZeroTheHero | 2,159 | 2,554 | 98.2% | bullets 40 → 39 (footer line no longer miscounted) |
| Abundant Energy | 3,338 | 3,515 | 99.2% | coverage 98.9% → 99.2% |
| Citizens Voice | 1,255 | 1,284 | 100.0% | coverage 98.3% → 100.0% |
| Healthy Oceans | 4,154 | 4,247 | 100.0% | coverage 99.4% → 100.0% |
| Tax Reset Overview | 6,078 | 6,186 | 100.0% | coverage 99.7% → 100.0% |
| Tax Reset Transition | 523 | 553 | 99.4% | coverage 98.3% → 99.4% |
| charter | 340 | 346 | 100.0% | unchanged |
| constitution | 10,992 | 11,017 | 96.8% | unchanged |

Several coverages moved up because `clean_body` now strips page-footer
tokens that were inflating the markdown-side token set (they aren't in
pymupdf's raw text, so they previously lowered the overlap).

Test suite: 32 passed, 1 skipped, ~10s (was 40 invocations
re-extracting per test).

## Findings from the review

### Applied during this session (5 of 13)

| # | Finding | Where | Applied via |
|---|---|---|---|
| 1 | Glyph-stripping regex duplicated in two files | `pdf_convert.py` + `pdf_validation.py` | Created `text_clean.py:strip_glyphs()`; both call it |
| 2 | `import unicodedata` inside function body | `pdf_validation.py:_normalise_for_compare` | Moved to module top while editing the file |
| 4 | Tests re-extract per test (5 × 8 PDFs = 40 extractions) | `tests/test_pdf_extraction.py` | Session-scoped `all_results` fixture; tests parametrise over results |
| 5 | `test_validation_json_loadable` did a full extraction just to test the JSON serializer | `tests/test_pdf_extraction.py` | Synthetic `PDFValidation` for the round-trip test |
| 10 | `pymupdf.open` without `with` — exception path leaks the document handle | `pdf_validation.py:extract_raw_text` | `with pymupdf.open(...) as doc:` |

### Remaining (8 of 13) — for the next session

| # | Severity | Where | Issue | Fix |
|---|---|---|---|---|
| 3 | Medium | `pipeline/transforms/pdf_validation.py:word_coverage` | Re-runs `_normalise_for_compare` 4× per call (twice in `word_coverage`, then twice again via `_tokenise`). | Have `_tokenise` accept pre-normalised text; or skip the recompute when caller already normalised. |
| 6 | Medium | `pipeline/defs/assets/pdf_validation.py` (333 lines) | Asset `write_pdf_pipeline_report` is 333 lines; ~130 are the markdown report builder. | Move report builder to `pipeline/transforms/pdf_validation.py:render_pipeline_report(...)`. Asset becomes ~30 lines. |
| 7 | Low | `pipeline/defs/assets/pdf_validation.py:103` | `_val_index = {...}` is built and never read. Comment says "reserved for per-PDF drill-down; not currently referenced". | Delete. Add back when drill-down is implemented. |
| 8 | Low | `pipeline/defs/assets/pdf_validation.py:79` | Log hard-codes `0.95` instead of importing `WORD_COVERAGE_THRESHOLD`. | `from pipeline.transforms.pdf_validation import WORD_COVERAGE_THRESHOLD`. |
| 9 | Low | `tests/test_pdf_extraction.py:46` | Test docstring says "≥1 heading" but the original `validate_pdf` docstring mentioned "≥1 heading and ≥1 bullet" — only headings are actually checked. | Pick one: drop the bullet mention from both docstrings, or add the bullet assertion. (Validator's bullet count is already collected.) |
| 11 | Trivial | `pipeline/defs/assets/pdf_validation.py:asset top` | "do NOT add `from __future__`" comment is redundant — `AGENTS.md` documents this globally. | Remove the comment. |
| 12 | Trivial | `pipeline/transforms/pdf_validation.py:extract_markdown`, `extract_raw_text` | `str(pdf_path)` casts are unnecessary; pymupdf accepts Path. | Drop the casts. |
| 13 | Trivial | `tests/conftest.py` | 5-line `sys.path.insert` could be `[tool.pytest.ini_options] pythonpath = ["."]` in pyproject.toml. | Either works; the pyproject form is shorter. |

### Why these were deferred

- **#3 + #6** are the only medium-severity items left. #3 is a perf
  cleanup (no behaviour change); #6 is structural (extracts the report
  builder out of the asset file). Both are reasonable for a follow-up
  commit but didn't block the main refactor.
- **#7, #8, #9, #11, #12, #13** are quality cleanups. Ponytail: ship
  the lazy version first, polish later.

## Suggested next move

Apply **#6** (extract report builder to `render_pipeline_report()`) —
it's the highest-impact remaining item and unblocks future iteration on
report formatting without touching the asset file. Then **#3 + #8 +
#12** in a single follow-up commit if the session has time.

## Reproducibility checklist

```bash
cd /Users/max.collier/Projects/Max/vault/sms/projects/oppertunity-party
just check              # ruff + ruff-format + ty + pytest — must pass
uv run dg launch --job validation_job   # re-materialises both assets
cat docs/pdf-pipeline.md                # human-readable report
```

A clean clone will have an empty `data/sources/opportunity-website/pdfs/`
and the pytest suite will skip with "No PDFs in ... — run
`uv run dg launch pdf_job` first". This is intentional — the tests
don't depend on the PDFs being present at install time.

## Things to NOT touch without re-reading context

- `pipeline/text_clean.py:strip_glyphs` — the regex is tuned for the
  constitution font. Touching it without re-running the validation may
  silently reintroduce artefacts.
- `pipeline/ingestion/pdf_convert.py:clean_body` — now public. Its
  private helpers (regex patterns, header / footer matchers) may be
  relied on by downstream callers; rename carefully.
- `data/sources/opportunity-website/pdfs/reference.json` — has both
  `_migrated_*` and canonical entries pointing at the same files. The
  validation report dedupes these by filename set but the underlying
  JSON still has both. Don't "clean up" the duplicates without checking
  whether the canonical/migrated split encodes something useful (it
  does: provenance of how each file arrived).

## Known issues surfaced by the validation report (not fixed)

These were also documented in the original w7q handoff; reproduced
here so the next session doesn't have to re-discover them.

1. **Productivity-unleashed has an unscraped PDF link.** The scraper
   index has a Google Drive URL for this policy but
   `pdfs/reference.json` doesn't list it (it's misclassified as
   `abundant-energy`). Re-running `pdf_job` for the
   `productivity-unleashed` partition should fix it.
2. **Constitution "Qualifcations" missing letter 'i'.** Real PDF source
   issue, not an extraction problem. Coverage stays at 96.8% because of it.
3. **Tax Reset Transition Plan whitespace loss** in table cells.
   98.3% → 99.4% coverage after the refactor (improved because footer
   tokens are no longer counted). Values intact.
4. **No image extraction.** Illustrations in policy PDFs are dropped as
   `**==> picture <==**` placeholders. Re-introducing them needs a
   decision on where binaries live (`data/sources/` for gitignored
   storage) + a `media_paths` field in `pdf-document` meta + an Astro
   template change.
5. **No HTML output outside Astro.** Policy content is served only
   after `pnpm build` produces `site/dist/`. Non-Astro consumers
   (LLM/MCP) that want rendered HTML must run the build first.

## Suggested skills for next session

- **`/skill:diagnosing-bugs`** — if you see extraction regressions in
  CI, this skill's loop fits well for the word-coverage metric.
- **`/skill:tdd`** — if extending `tests/test_pdf_extraction.py` with
  new assertions, red-green-refactor discipline applies cleanly.
- **`/skill:prototype`** — if exploring the "No HTML output outside
  Astro" idea, build a throwaway prototype to validate state model
  before adding an asset.
- **`/skill:prd`** — if turning "Add image extraction" into a real
  feature, shape it as a PRD before code.
- **`/skill:handoff`** — again, when handing off this handoff doc.