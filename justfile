# Opportunity Party Scraper
# Run `just` to see available recipes.
#
# All data-pipeline operations (scrape, transform, PDFs, site build, sitemap,
# deploy) are managed as Dagster assets — run `just dev` to open the UI, or
# launch them headless with `dg launch`. Linting and one-shot tooling stay in
# this justfile so they're trivial to run outside the pipeline.

# Install Python dependencies
install:
    uv sync

# Launch the Dagster UI dev server
dev:
    uv run dg dev

# Open scraped data in Finder
open:
    open data

# Verify code quality: lint + format-check + type-check + tests (read-only, safe for CI)
# Excludes .agents/ — that's vendored third-party skill code, not ours.
check: install
    uv run ruff check .
    uv run ruff format --check .
    uv run ty check --error-on-warning --exclude '.agents/**' .
    uv run pytest tests/ -q

# Auto-fix lint issues and reformat (ty has no autofix — run `just check` after)
fix: install
    uv run ruff check --fix .
    uv run ruff format .

# Validate normalized clean-layer markdown files with markdown-link-check
# Checks that every link in data/clean/**/*.md resolves (external URLs + relative
# paths resolved against https://www.opportunity.org.nz via .markdown-link-check.json).
validate:
    @echo "Running markdown-link-check on clean layer..."
    @find data/clean -name '*.md' | sort | xargs -I{} npx --yes markdown-link-check --config .markdown-link-check.json {}

# Run pytest suite (PDF extraction validation, etc.). Skips automatically when
# data/sources/opportunity-website/pdfs/ is empty (fresh clone without raw PDFs).
test: install
    uv run pytest tests/ -q

# Wire lefthook into .git/hooks (run once after cloning)
hooks-install:
    lefthook install
    @echo "Git hooks installed via lefthook."