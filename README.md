# Opportunity Party Policy Tracker

A tool for exploring and understanding the New Zealand [Opportunity Party](https://www.opportunity.org.nz) (TOP) through a variety of their public data sources — policies, policy documents, news, blog posts, team profiles, events, and party governance — all presented as readable markdown files.

## What this does

This repo scrapes content from opportunity.org.nz and stores it locally as searchable markdown. The goal is to make it easy to browse, read, and understand what TOP stands for across a variety of their media sources — without having to navigate the website directly.

## The data

All scraped content lives under `data/`:

```
data/
├── policies/
│   └── <policy-area>/
│       └── <document>.md
├── team/
│   └── <name>.md
├── blog/
│   └── <date>-<slug>.md
├── events/
│   └── <date>-<slug>.md
├── news/
│   └── <slug>.md
├── party-information/
│   └── <section>.md
└── pdfs/
    └── <document>.pdf
```

Each file is plain markdown — readable in any editor, terminal, or markdown viewer.

## Downloading fresh data

The `data/` directory is included in the repo. If you want to pull the latest content directly from opportunity.org.nz, you'll need the following tools installed:

```bash
brew install poppler just uv  # required tools
just install
just scrape                   # fetch everything fresh from the website
just pdfs                     # re-convert PDFs to markdown without re-scraping
just open                     # open data/ in Finder
```

## Contributing

Contributions are welcome. If you notice broken scrapers, missing content, or want to improve the output format, open a pull request or file an issue.

```bash
just check    # run linting and type checks before submitting
```
