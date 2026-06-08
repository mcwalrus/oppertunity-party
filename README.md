# Opportunity Party Policy Tracker

Tools for learning about and tracking the New Zealand [Opportunity Party](https://www.opportunity.org.nz) current policies.

## What this does

This repo scrapes content from opportunity.org.nz and stores it locally as searchable markdown.

## Quick start

```bash
brew install poppler just uv  # required tools
just                         # see all commands
just install
just scrape
```

## The data

| Directory | Contents |
|-----------|----------|
| `data/policies/` | Policy pages and PDF-derived documents |
| `data/pdfs/` | Downloaded PDF files |
| `data/team/` | Candidate and team profiles |
| `data/news/` | Media releases and news articles |
| `data/party-information/` | About pages, constitution, rules |

## Why

Makes policy documents easy to find and search. Run `just scrape` anytime to pull the latest content.

## Refreshing content

```bash
just scrape   # scrape everything
just pdfs     # re-convert PDFs without re-scraping
just open     # open data in Finder
```
