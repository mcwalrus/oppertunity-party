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

## Obsidian Graph Naming

<!-- Obsidian graph view labels nodes by filename (without extension). Generic names like
     INDEX or page make every node look identical in the graph. All output markdown files
     MUST use a descriptive, content-specific filename:
     - Section index files: named after the section (e.g. team/team.md, not team/INDEX.md)
     - Per-item files inside a slug directory: named after the slug
       (e.g. policies/tax-reset/tax-reset.md, not policies/tax-reset/page.md)
     When adding new scrapers, follow this pattern — never use generic names like INDEX.md,
     page.md, or index.md for human-readable markdown output. -->

## Quality Gates

```bash
just check   # Must pass before committing
```

Pre-commit hooks (via lefthook) run ruff-lint, ruff-format, ty, and markdown-link-check automatically on staged files.
