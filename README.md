# Opportunity Party Policy Tracker

A tool for exploring and understanding the New Zealand [Opportunity Party](https://www.opportunity.org.nz) (TOP) through a variety of their public data sources — policies, policy documents, news, blog posts, team profiles, events, and party governance — all presented as readable markdown files.

## What this does

This repo scrapes content from opportunity.org.nz and stores it locally as searchable markdown. The goal is to make it easy to browse, read, and understand what TOP stands for across a variety of their media sources — without having to navigate the website directly.

## The data pipeline

Content flows through three stages:

```
Ingestors (scraper/, yt-dlp, ...)
     ↓
data/sources/{source}/          ← raw ingestor output (gitignored)
     ↓ transforms/sources/
data/clean/{content-type}/      ← normalized, committed, read by consumers
     ↓ transforms/
site/src/content/               ← Astro SSG input (rebuilt on each transform)
```

See [docs/data-architecture.md](docs/data-architecture.md) for the full pipeline design and [docs/data-schema.md](docs/data-schema.md) for the schema reference.

## The data

All normalized content lives in `data/clean/` (committed to git):

```
data/
└── clean/
    ├── _index.json               ← cross-type search index
    ├── policy/{slug}/            ← policy pages + full PDF text
    ├── blog-post/{slug}/         ← blog posts and news articles
    ├── event/{slug}/             ← upcoming events
    ├── team-member/{slug}/       ← team and candidate profiles
    ├── party-information/{slug}/ ← party info, about, governance
    └── pdf-document/{slug}/      ← extracted policy PDF documents
```

Each item contains `{slug}.md` (YAML frontmatter + cleaned body) and `meta.json` (identical provenance fields as machine-readable JSON).

## Downloading fresh data

Raw ingestor output goes to `data/sources/` (gitignored — regenerated on demand). You'll need these tools:

```bash
brew install just uv             # required tools
just install                     # install Python dependencies
just scrape                      # scrape website + run full transform pipeline
just transform                   # re-run transforms only (no re-scraping)
just pdfs                        # re-convert PDFs to markdown without re-scraping
```

## Contributing

Contributions are welcome. If you notice broken scrapers, missing content, or want to improve the output format, open a pull request or file an issue.

```bash
just check    # run linting and type checks before submitting
```

For architecture and schema documentation, see:

- [docs/data-architecture.md](docs/data-architecture.md) — pipeline design, layer invariants, how to add new sources/consumers
- [docs/data-schema.md](docs/data-schema.md) — full schema reference for clean and source layers
