# Opportunity Party Scraper
# Run `just` to see available recipes

# Install dependencies
install:
    uv sync

# Scrape everything and run the full transform pipeline
scrape: install
    uv run python main.py --clean
    uv run python -m transforms.main

# Run transforms only (no re-scraping)
transform: install
    uv run python -m transforms.main

# Re-convert PDFs to markdown (no re-scrape)
pdfs: install
    uv run python main.py pdfs

# Open scraped data in Finder
open:
    open data

# Lint with ruff
lint: install
    uv run ruff check .

# Lint and auto-fix with ruff
lint-fix: install
    uv run ruff check . --fix

# Format with ruff
fmt: install
    uv run ruff format .

# Type-check with ty
typecheck: install
    uv run ty check --error-on-warning .

# Run all quality checks (lint + typecheck)
check: install
    uv run ruff check .
    uv run ty check --error-on-warning .

# Validate normalized clean-layer markdown files with markdown-link-check
# Checks that every link in data/clean/**/*.md resolves (external URLs + relative
# paths resolved against https://www.opportunity.org.nz via .markdown-link-check.json).
validate:
    @echo "Running markdown-link-check on clean layer..."
    @find data/clean -name '*.md' | sort | xargs -I{} npx --yes markdown-link-check --config .markdown-link-check.json {}

# YouTube: show year-grouped summary
media-list: install
    uv run python main.py media youtube --mode=list

# YouTube: interactive pick + download
media-download: install
    uv run python main.py media youtube --mode=download

# YouTube: force re-enumerate and refresh cache
media-refresh: install
    uv run python main.py media youtube --refresh

# Install site dependencies
site-install:
    cd site && pnpm install

# Type-check the Astro site
site-check: site-install
    cd site && pnpm check

# Build the static site
site-build: transform site-install
    cd site && pnpm build

# Preview the built site locally
site-preview: site-build
    cd site && pnpm preview

# Dev server for the site
site-dev: site-install
    cd site && pnpm dev

# Resolve docs_site_map.md with absolute URLs.
# Reads site/dist/docs_site_map.md and rewrites relative links using SITE_URL.
# Requires: SITE_URL env var (or set in site/.env.local), and a prior site-build run.
# Example: SITE_URL=https://opportunity.org.nz just site-generate-sitemap
site-generate-sitemap: site-install
    cd site && pnpm generate:sitemap

# Wire lefthook into .git/hooks (run once after cloning)
hooks-install:
    lefthook install
    @echo "Git hooks installed via lefthook."
