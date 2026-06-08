# Opportunity Party Web Scraper
# Run `just` to see all available recipes

default:    # list recipes
    @just --list

# Install Python dependencies via uv
install:
    uv sync

# Scrape everything into data/
scrape: install
    uv run python main.py --clean

# Scrape only policies
scrape-policies: install
    uv run python main.py policies

# Scrape only team profiles
scrape-team: install
    uv run python main.py team

# Scrape only news articles
scrape-news: install
    uv run python main.py news

# Scrape only party information pages
scrape-party-info: install
    uv run python main.py party-info

# Remove all scraped data (keeps policy-assets/)
clean:
    uv run python -c "from scraper.client import clean_data; clean_data()"

# Open the output directory in Finder
open-data:
    open data