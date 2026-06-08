# Agent Instructions — Opportunity Party Policy Tracker

## Project Overview

Scrapes the New Zealand [Opportunity Party](https://www.opportunity.org.nz) website and converts content into local markdown files under `data/`. Sources include policies (with linked PDFs), blog posts, news, team profiles, events, and party governance documents.

The scraper lives in `scraper/` as a set of modules (one per content type). `main.py` is the CLI entry point. All scraped output goes to `data/`.

## Tools

| Tool | Purpose |
|------|---------|
| `uv` | Dependency management and script runner (`uv sync`, `uv run`) |
| `just` | Task runner — see `justfile` for all recipes |
| `ruff` | Linter and formatter for Python |
| `ty` | Static type checker for Python |
| `lefthook` | Git hook manager (pre-commit runs ruff + ty + markdown-link-check) |
| `poppler` | PDF utilities (required for PDF-to-markdown conversion) |
| `npx markdown-link-check` | Validates links in scraped markdown output |

## Common Commands

```bash
just install      # uv sync
just scrape       # Scrape everything (--clean)
just pdfs         # Re-convert PDFs to markdown without re-scraping
just check        # ruff check + ty check
just lint-fix     # ruff check --fix
just fmt          # ruff format
just validate     # markdown-link-check on all data/**/*.md
```

## Quality Gates

```bash
just check   # Must pass before committing
```

Pre-commit hooks (via lefthook) run ruff-lint, ruff-format, ty, and markdown-link-check automatically on staged files.
