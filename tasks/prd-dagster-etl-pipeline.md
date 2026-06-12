# PRD: Dagster ETL Pipeline

## Introduction

The project currently runs its scrape → clean → site pipeline as a sequence of plain Python
function calls orchestrated by `just scrape` and `just transform`. Dagster is already a
declared dependency (`dagster>=1.13.9`) but is not wired up. This PRD defines how to
integrate Dagster as the pipeline's orchestration layer — giving every data artefact full
lineage tracking, a visual asset graph, manual and scheduled materialisation, and selective
re-runs per content type.

**Baseline today:** Running `just scrape` executes `main.py --clean` then
`transforms/main.py` as a single untracked Python script. There is no lineage, no
materialisation history, no partial re-run support, and no visibility into what produced
which output file.

---

## Goals

- Model every data artefact (raw scraped files, clean markdown, site content) as a Dagster
  software-defined asset with full lineage
- Enable selective materialisation per content type (e.g. re-run only `clean_blog` without
  re-scraping)
- Replace `just scrape` / `just transform` CLI entry points with Dagster commands; add `dg
  dev` as the development UI command
- Support manual materialisation (UI + CLI) as the primary trigger; add a weekly schedule as
  the automated option
- Keep all existing `scraper/` and `transforms/` module code intact — Dagster wraps it, does
  not replace it
- Pass `just check` (ruff + ty) with no new violations

---

## User Stories

### US-001: Project structure — `pipeline/` module and `definitions.py`
**Description:** As a developer, I need a Dagster code location wired into the project so
that `dg dev` discovers all assets.

**Acceptance Criteria:**
- [ ] New `pipeline/` Python package exists at project root with `__init__.py`
- [ ] `pipeline/defs/` subdirectory contains sub-modules: `assets/`, `resources.py`,
  `jobs.py`, `schedules.py`
- [ ] Root-level `definitions.py` exposes a `defs` symbol of type `dagster.Definitions`
- [ ] `dg dev` starts without errors and the Dagster UI loads at `http://localhost:3000`
- [ ] `just check` passes (ruff + ty)

---

### US-002: Ingestion assets — raw scraper layer
**Description:** As a pipeline operator, I want each scraper to be a Dagster asset so I can
materialise raw data independently per content type.

**Six assets in group `ingestion`:**

| Asset key | Wraps | Output path |
|---|---|---|
| `raw_policies` | `scrape_policies` + `save_policies` | `data/sources/opportunity-website/policies/` |
| `raw_team` | `scrape_team` + `save_team` | `data/sources/opportunity-website/team/` |
| `raw_blog` | `scrape_blog_posts` + `save_blog_posts` | `data/sources/opportunity-website/blog-posts/` |
| `raw_events` | `scrape_events` + `save_events` | `data/sources/opportunity-website/events/` |
| `raw_party_info` | `scrape_party_info` + `save_party_info` | `data/sources/opportunity-website/party-info/` |
| `raw_pdfs` | `download_policy_pdfs` + `convert_all_pdfs` | `data/sources/opportunity-website/pdfs/` |

`raw_pdfs` declares `raw_policies` as an upstream dependency (PDF URLs are derived from
policy pages).

Each asset records `dagster.MaterializeResult` metadata: item count and output directory
path.

**Acceptance Criteria:**
- [ ] All six assets appear in the Dagster UI under group `ingestion`
- [ ] Materialising `raw_policies` writes files to `data/sources/opportunity-website/policies/`
  without touching other content types
- [ ] `raw_pdfs` depends on `raw_policies` in the asset graph (visible in UI lineage view)
- [ ] Asset metadata (item count, path) is recorded in the materialisation event log
- [ ] `just check` passes

---

### US-003: Clean layer assets — normalise to `data/clean/`
**Description:** As a pipeline operator, I want each content type's normalisation step to be
a Dagster asset so I can re-clean a single type without re-scraping.

**Six assets in group `clean`:**

| Asset key | Upstream | Output path |
|---|---|---|
| `clean_policies` | `raw_policies` | `data/clean/policy/` |
| `clean_team` | `raw_team` | `data/clean/team/` |
| `clean_blog` | `raw_blog` | `data/clean/blog/` |
| `clean_events` | `raw_events` | `data/clean/events/` |
| `clean_party_info` | `raw_party_info` | `data/clean/party-information/` |
| `clean_pdfs` | `raw_pdfs` | `data/clean/pdf-document/` |

Each asset wraps the relevant content-type path of `transform_opportunity_website()`. If that
function is currently monolithic, the agent must refactor it to accept a `content_type`
parameter (or equivalent) so it can be called per type. The `_index.json` is regenerated
after all clean assets run (see US-005).

**Acceptance Criteria:**
- [ ] All six assets appear under group `clean` with correct upstream edges to `ingestion`
  assets
- [ ] Materialising `clean_blog` writes only `data/clean/blog/` and does not touch other
  clean directories
- [ ] `just check` passes

---

### US-004: Site layer assets — generate `site/src/content/`
**Description:** As a pipeline operator, I want each site-content collection to be a Dagster
asset so the Astro site can be rebuilt per content type.

**Five assets in group `site`:**

| Asset key | Upstream | Output path |
|---|---|---|
| `site_policies` | `clean_policies` | `site/src/content/policies/` |
| `site_team` | `clean_team` | `site/src/content/team/` |
| `site_blog` | `clean_blog` | `site/src/content/blog/` |
| `site_events` | `clean_events` | `site/src/content/events/` |
| `site_party_info` | `clean_party_info` | `site/src/content/party-info/` |

Each wraps the corresponding `transform_<type>(CLEAN_DIR, CONTENT_DIR)` call from
`transforms/main.py`. The existing behaviour of wiping `site/src/content/` before writing is
preserved — but scoped to the specific collection subdirectory only (not the whole tree).

**Acceptance Criteria:**
- [ ] All five assets appear under group `site` with correct upstream edges to `clean` assets
- [ ] Materialising `site_blog` writes only `site/src/content/blog/` without clearing other
  collections
- [ ] Full three-layer graph (`ingestion` → `clean` → `site`) is visible in the Dagster UI
  lineage view
- [ ] `just check` passes

---

### US-005: Search index asset — `_index.json`
**Description:** As a downstream consumer, I need `data/clean/_index.json` to stay current
whenever any clean asset is materialised.

**One asset in group `clean`:**
- `clean_index` — depends on all six `clean_*` assets; calls `_write_index()` (or equivalent
  from `transforms/sources/opportunity_website.py`) to regenerate `data/clean/_index.json`

**Acceptance Criteria:**
- [ ] `clean_index` appears downstream of all six clean assets in the graph
- [ ] Materialising all clean assets triggers `clean_index` when selected together
- [ ] `just check` passes

---

### US-006: Jobs — named selectable pipelines
**Description:** As an operator, I want named jobs so I can run the full pipeline or a
specific layer without specifying individual asset keys.

**Three jobs:**

| Job name | Asset selection |
|---|---|
| `full_pipeline` | All assets (`*`) |
| `ingestion_job` | `group:ingestion` |
| `transforms_job` | `group:clean + group:site` |

**Acceptance Criteria:**
- [ ] All three jobs are visible in the Dagster UI under Jobs
- [ ] `dagster job execute -j full_pipeline` runs end-to-end without errors on a machine with
  cached data
- [ ] `just check` passes

---

### US-007: Weekly schedule
**Description:** As an operator, I want the full pipeline to run automatically each week so
content stays current without manual intervention.

**One schedule:**
- `weekly_full_pipeline` — cron `0 6 * * 1` (Monday 06:00 UTC), targets `full_pipeline` job
- Schedule is **OFF by default** (Dagster default); operator must enable in UI

**Acceptance Criteria:**
- [ ] `weekly_full_pipeline` appears in UI under Automation → Schedules
- [ ] Schedule is off by default
- [ ] `just check` passes

---

### US-008: Replace `just` pipeline commands
**Description:** As a developer, I want the `just` task runner to invoke Dagster commands so
all pipeline execution goes through one system.

**Replacements:**

| Old command | New command |
|---|---|
| `just scrape` | `dagster asset materialize --select "group:ingestion"` |
| `just transform` | `dagster asset materialize --select "group:clean group:site"` |

**New command added:**

| Command | Runs |
|---|---|
| `just dev` | `dg dev` (starts Dagster UI at localhost:3000) |

**Acceptance Criteria:**
- [ ] `just scrape` invokes Dagster ingestion materialisation
- [ ] `just transform` invokes Dagster clean+site materialisation
- [ ] `just dev` starts the Dagster webserver
- [ ] Old `uv run python main.py` / `uv run python -m transforms.main` invocations are
  removed from the justfile
- [ ] `just check` passes

---

## Functional Requirements

- **FR-1:** A `pipeline/` Python package exists at project root with a `defs/` subdirectory
  containing `assets/ingestion.py`, `assets/clean.py`, `assets/site.py`, `jobs.py`,
  `schedules.py`
- **FR-2:** A root-level `definitions.py` exports `defs: dagster.Definitions` — this is the
  entry point for `dg dev`
- **FR-3:** All 18 assets (6 ingestion + 7 clean including index + 5 site) are registered in
  `defs`
- **FR-4:** All assets in the `ingestion` group wrap existing `scraper/` functions without
  duplicating their logic
- **FR-5:** All assets in the `clean` group wrap existing `transforms/` functions; if
  `transform_opportunity_website()` is monolithic it must be refactored to support per-type
  invocation
- **FR-6:** Each asset emits `MaterializeResult` with at minimum an `item_count` metadata
  entry
- **FR-7:** `raw_pdfs` declares `non_argument_deps={"raw_policies"}` (or equivalent) so the
  dependency is visible in the graph without passing data in memory
- **FR-8:** Site assets scope their output wipe to their own collection subdirectory, not the
  entire `site/src/content/` tree
- **FR-9:** Three named jobs are registered: `full_pipeline`, `ingestion_job`,
  `transforms_job`
- **FR-10:** One schedule `weekly_full_pipeline` targeting `full_pipeline` at cron
  `0 6 * * 1`, default OFF
- **FR-11:** `justfile` recipes `scrape`, `transform`, and new `dev` invoke Dagster CLI
  commands

---

## Non-Goals

- No `ConfigurableResource` abstraction for the HTTP client (scraper clients configure
  themselves via `scraper/client.py` — leave that unchanged)
- No partitions or backfills (content types are not time-sliced)
- No `@asset_check` data quality rules
- No Dagster Cloud / production deployment configuration
- No changes to the MCP server (`mcp/`)
- No changes to the Astro site (`site/`)
- No sensor-driven automation (file-system sensors deferred to a future cycle)
- Do not move `scraper/` or `transforms/` into a `src/` layout
- Do not add pytest test suite for assets in this cycle

---

## Technical Considerations

- **Entry point:** `dg dev` discovers the code location via `definitions.py` at project root.
  The `[tool.dagster]` section in `pyproject.toml` may need `python_file = "definitions.py"`
  if `dg` does not auto-detect it.
- **Existing function signatures:** `scraper/*` functions return typed lists; asset wrappers
  call them and discard the return value (side-effect: files written to disk). This is
  consistent with how Dagster handles IO-manager-less assets.
- **`transform_opportunity_website()` monolith:** Currently normalises all content types in
  one call. The agent must split or parameterise it to support per-type materialisation
  without processing all types every run. Existing callers of the function (if any outside
  `transforms/main.py`) must be updated.
- **`site/src/content/` wipe scope:** The current `transforms/main.py` wipes the entire
  `CONTENT_DIR` before writing. Site assets must change this to wipe only their own
  subdirectory (e.g. `site/src/content/blog/`) for selective materialisation to be safe.
- **Type checking:** All new code in `pipeline/` must pass `ty` with no errors. Use `from
  __future__ import annotations` for forward references.

---

## Success Metrics

- `dg dev` starts and all 18 assets render in the Dagster UI asset graph
- `dagster asset materialize --select raw_blog` completes without touching any other content
  type's output directory
- `dagster job execute -j full_pipeline` produces the same output as the old `just scrape &&
  just transform` sequence
- `just check` passes with zero new violations

---

## Open Questions

- Does `pyproject.toml` need a `[tool.dagster]` entry pointing to `definitions.py`, or does
  `dg dev` auto-discover it from the project root? (Agent to verify on first run of `dg dev`
  and add config if needed.)
- Should `raw_pdfs` be a non-argument dep of `raw_policies` or a separate ingestion step
  that the operator triggers independently? Investigate seperately.
