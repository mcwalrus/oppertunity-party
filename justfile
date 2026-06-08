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
