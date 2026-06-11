# Opportunity Party Scraper
# Run `just` to see available recipes

# Install dependencies
install:
    uv sync

# Scrape everything
scrape: install
    uv run python main.py --clean

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

# Validate all scraped markdown files with markdown-link-check
# Checks that every link in data/**/*.md resolves (external URLs + relative paths
# resolved against https://www.opportunity.org.nz via .markdown-link-check.json).
validate:
    @echo "Running markdown-link-check on scraped data..."
    @find data -name '*.md' | sort | xargs -I{} npx --yes markdown-link-check --config .markdown-link-check.json {}

# Transform scraped data into site content
transform: install
    uv run python -m transforms.main

# Install site dependencies
site-install:
    cd site && pnpm install

# Build the static site
site-build: transform site-install
    cd site && pnpm build

# Preview the built site locally
site-preview: site-build
    cd site && pnpm preview

# Dev server for the site
site-dev: site-install
    cd site && pnpm dev

# Wire lefthook into .git/hooks (run once after cloning)
hooks-install:
    lefthook install
    @echo "Git hooks installed via lefthook."
