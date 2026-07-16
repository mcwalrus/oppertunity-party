# Agent Instructions

## Project Overview

Scrapes the New Zealand [Opportunity Party](https://www.opportunity.org.nz) website and converts content into local markdown files. Sources include policies (with linked PDFs), blog posts, news, team profiles, events, and party governance documents.

## Key Paths

| Path                                        | Description                                                        | Git     |
| ------------------------------------------- | ------------------------------------------------------------------ | ------- |
| `data/sources/opportunity-website/`         | Raw scraper output — written by ingestors, never read by consumers | Ignored |
| `data/clean/`                               | Normalized content — canonical source for all consumers            | Tracked |
| `data/clean/_index.json`                    | Cross-type search index (regenerated each transform run)           | Tracked |
| `pipeline/`                                 | Dagster code location — wraps ingestion + transforms as assets     | —       |
| `docs/data-architecture.md`                 | Pipeline design, layer invariants, how to add source/consumer      | Tracked |
| `docs/dependencies.md`                      | Why each dependency exists (grouped by purpose)                    | Tracked |
| `docs/reference/`                           | Reference materials used while building (Dagster course, …)        | Tracked |
| `tasks/`                                    | PRDs and planning notes (`prd-*.md`, `campaign-website-issues/`)   | Tracked |

TODO: add docs/data-schema.md

## Data Pipeline

https://dagster.io/ is the library we use to manage ETL (Extract, Transform, Load) processes. This will include web-scraping, data cleansing, transformations, site build, sitemap resolution, and deployment. We expect agents to apply the appropriate Asset management.

### Operations go through Dagster

**Most operations should be expressed as Dagster assets** — not as standalone scripts or justfile recipes. The justfile is reserved for:

- **Local development tooling** that doesn't fit the asset model (interactive dev servers, manual lint runs, lefthook setup).
- **Quality gates** (lint, type-check, link validation) that run pre-commit or in CI.

If you want to add a new data-pipeline operation (a new source, transform, build step, deploy step), model it as a Dagster asset under `pipeline/defs/assets/` and wire it into the relevant job in `pipeline/defs/jobs.py`. The `full_pipeline` job should remain the canonical "run everything end-to-end" entry point.

**Exceptions to "always use Dagster":**

- **Linters and type-checkers** stay in the justfile (`just check`, `just fix`, `just validate`). They're local, stateless, and trivial to run outside the pipeline — modeling them as Dagster assets would add ceremony without benefit.
- **One-off local developer tools** (e.g. `just dev` for the Dagster UI, `just open` for Finder) stay in the justfile.

### Adding new Dagster assets

When you add a new asset:

1. **Pick the right group** (`ingestion`, `clean`, `site`) — this drives job selection.
2. **Declare upstream deps** via the `deps=[...]` argument on `@dg.asset`. Don't rely on file-path inference.
3. **Register the asset** in `pipeline/definitions.py` and add it to the appropriate job in `pipeline/defs/jobs.py` if it needs to run as part of `full_pipeline`.
4. **Production-affecting assets** (anything that publishes, deploys, or pushes) must be excluded from `full_pipeline` and exposed via their own explicit job. Example: `site_deploy` is a separate `site_deploy_job`.

### Raw data policy

Raw data should only be managed locally if it is useful for comparison or analysis with the of transformation of data, or if data is of significant storage requirements. This would be to avoid refetching during development, or heavy processing. If an ETL pipeline is managed, we should say that it is okay to avoid storing raw data unnecessarily.

### Type-annotation note for Dagster assets

Do **not** add `from __future__ import annotations` to files that define Dagster assets. PEP-563 string annotations break Dagster's runtime validation of `context: AssetExecutionContext`. The existing `pipeline/defs/assets/ingestion.py` and `clean.py` are correct reference patterns; `site.py` deliberately omits the future import for this reason.

## Setup

Run the onboarding script once on a fresh machine (macOS/Linux only):

```bash
./scripts/setup.sh
```

This installs all system dependencies via Homebrew (`scripts/Brewfile`), installs [pi](https://pi.dev), configures shell hooks for `fnm` and `direnv`, installs Node + Python + site deps, and wires up git hooks. Keep track of all tools or major dependencies going forward.

## CLI Tools

| Tool       | Purpose                                                            |
| ---------- | ------------------------------------------------------------------ |
| `uv`       | Dependency management and script runner (`uv sync`, `uv run`)      |
| `just`     | Task runner — see `justfile` for recipes (lint, dev, open)         |
| `ruff`     | Linter and formatter for Python                                    |
| `ty`       | Static type checker for Python                                     |
| `lefthook` | Git hook manager (pre-commit runs ruff + ty + markdown-link-check) |
| `fnm`      | Node.js version manager (reads `.node-version`)                    |
| `pnpm`     | Node package manager (used by `site/`)                             |
| `direnv`   | Per-directory env vars — run `direnv allow` after cloning          |
| `pi`       | AI coding agent — install via `scripts/setup.sh`                   |
| `dg`       | CLI for managing Dagster projects                                  |
| `dagster`  | CLI tools for working with Dagster                                 |

## Python Libraries

| Library       | Purpose                                     |
| ------------- | ------------------------------------------- |
| `yt-dlp`      | Download videos                             |
| `pymupdf4llm` | PDF to markdown converter (strongly vetted) |
| `dagster`     | ETL pipeline orchestration (asset-based)    |

## Node Libraries

| Library         | Purpose      |
| --------------- | ------------ |
| `astro`         | SSG          |
| `@astrojs/check`| Type check   |
| `typescript`    | TS compiler  |

## Common Commands

### Dagster — data pipeline (primary)

```bash
just dev            # Open the Dagster UI (dg dev) — pick jobs to launch from there
uv run dg launch    # Run a job headless (see `uv run dg launch --help` for options)
```

Inside the Dagster UI, the canonical jobs are:

- **`full_pipeline`** — scrape → transform → site build → sitemap resolution (everything except deploy).
- **`site_deploy_job`** — explicit deploy to Cloudflare Workers via wrangler. Production-affecting.
- **`ingestion_job`** / **`transforms_job`** / **`pdf_job`** — narrower jobs for targeted runs.

### Justfile — local tooling

```bash
just install        # uv sync
just check          # ruff check + ruff format --check + ty check (read-only, CI-safe)
just fix            # ruff check --fix + ruff format
just validate       # markdown-link-check on all data/clean/**/*.md
just open           # Open scraped data in Finder
just hooks-install  # Wire lefthook into .git/hooks (once after cloning)
```

## Quality Gates

```bash
just check   # Must pass before committing
```

Pre-commit hooks (via lefthook) run ruff-lint, ruff-format, ty, and markdown-link-check automatically on staged files.