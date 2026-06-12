# Agent Instructions

## Project Overview

Scrapes the New Zealand [Opportunity Party](https://www.opportunity.org.nz) website and converts content into local markdown files. Sources include policies (with linked PDFs), blog posts, news, team profiles, events, and party governance documents.

## Key Paths

| Path                                        | Description                                                        | Git     |
| ------------------------------------------- | ------------------------------------------------------------------ | ------- |
| `data/sources/opportunity-website/`         | Raw scraper output — written by ingestors, never read by consumers | Ignored |
| `data/clean/`                               | Normalized content — canonical source for all consumers            | Tracked |
| `data/clean/_index.json`                    | Cross-type search index (regenerated each transform run)           | Tracked |
| `data/.cache/`                              | HTTP response cache (scraper-internal, ephemeral)                  | Ignored |
| `site/src/content/`                         | Astro SSG input — rebuilt from `data/clean/` each run              | Ignored |
| `transforms/sources/opportunity_website.py` | Source → clean transform                                           | —       |
| `transforms/main.py`                        | Full pipeline entry point                                          | —       |

## Data Pipeline

https://dagster.io/ is the library we use to manage ETL (Extract, Transform, Load) processes. This will include, web-scraping, data cleansing, transformations and writing to target directories. We expect agents to apply the appropriate Asset management.

Dagster.io has it's own approach to ETL pipelines, and we expect decisions to represent assets in particular means have been signed off during the design / planning phase, and apply the right `@dg` decorators to define workflows. 

Raw data should only be managed locally if it is useful for comparison or analysis with the of transformation of data, or if data is of significant storage requirements. This would be to avoid refetching during development, or heavy processing. If an ETL pipeline is managed, we should say that it is okay to avoid storing raw data unnecessarily.

## Setup

Run the onboarding script once on a fresh machine (macOS/Linux only):

```bash
./scripts/setup.sh
```

This installs all system dependencies via Homebrew (`scripts/Brewfile`), installs [pi](https://pi.dev), configures shell hooks for `fnm` and `direnv`, installs Node + Python + site deps, and wires up git hooks.

## Tools

| Tool       | Purpose                                                            |
| ---------- | ------------------------------------------------------------------ |
| `uv`       | Dependency management and script runner (`uv sync`, `uv run`)      |
| `just`     | Task runner — see `justfile` for all recipes                       |
| `ruff`     | Linter and formatter for Python                                    |
| `ty`       | Static type checker for Python                                     |
| `lefthook` | Git hook manager (pre-commit runs ruff + ty + markdown-link-check) |
| `fnm`      | Node.js version manager (reads `.node-version`)                    |
| `pnpm`     | Node package manager (used by `site/`)                             |
| `direnv`   | Per-directory env vars — run `direnv allow` after cloning          |
| `pi`       | AI coding agent — install via `scripts/setup.sh`                   |
| `dg`       | CLI for managing Dagster projects.                                 |
| `dagster`  | CLI tools for working with Dagster.                                |


**Python Libraries**

yt-dlp: download videos
pymupdf4llm: pdf to markdown converter


## Common Commands

```bash
just install      # uv sync
just scrape       # Scrape website + run full transform pipeline
just transform    # Re-run transforms only (no re-scraping)
just pdfs         # Re-convert PDFs to markdown without re-scraping
just check        # ruff check + ty check
just lint-fix     # ruff check --fix
just fmt          # ruff format
just validate     # markdown-link-check on all data/clean/**/*.md
```

## Quality Gates

```bash
just check   # Must pass before committing
```

Pre-commit hooks (via lefthook) run ruff-lint, ruff-format, ty, and markdown-link-check automatically on staged files.
