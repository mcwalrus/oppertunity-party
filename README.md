# Opportunity Party Scraper

Scrapes the [Opportunity Party](https://www.opportunity.org.nz) website and converts
policy PDFs to structured markdown. Output is stored under `data/` and exposed via
an MCP server for LLM consumption.

## System requirements

Before running, install the following system tools:

```bash
brew install poppler   # provides pdftotext, used for PDF → text conversion
```

Python 3.12+ is also required.

## Setup

```bash
uv sync
```

## Usage

Run all scrapers:

```bash
uv run python main.py
```

Run specific targets:

```bash
uv run python main.py policies team news party-info pdfs
```

`--clean` wipes `data/` before running (preserves `data/policy-assets/`):

```bash
uv run python main.py --clean
```

## How it works

| Target | What it does |
|--------|-------------|
| `policies` | Scrapes policy pages, downloads PDFs from Google Drive, converts PDFs to markdown via `pdftotext` |
| `team` | Scrapes team / candidate pages |
| `news` | Scrapes news and media releases |
| `party-info` | Scrapes about / party information pages |
| `pdfs` | Re-converts already-downloaded PDFs without re-scraping |

PDF conversion uses `pdftotext -layout` (from poppler) to preserve the layout of
the party's policy documents, then strips running headers/footers and formats the
body as clean markdown under `data/policies/{slug}/`.

## MCP server

```bash
uv run python -m mcp.server
```

See `mcp/README.md` for available tools.
