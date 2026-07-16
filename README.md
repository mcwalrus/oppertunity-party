# Opportunity Party

A toolkit and for exploring and understanding the New Zealand [Opportunity Party](https://www.opportunity.org.nz) (formerly TOP) through a variety of their public data sources — policies, policy documents, news, blog posts, team profiles, events, and party governance —  formatted as plaintext, markdown files. This library pulls data from a variety of other public sources across the internet. The aim is to produce a dataset supportive for AI analysis.

TODO sections:

* Getting Started
* Why Dagster? (visual flow)
* Architecture - dagster -> site -> MCP (eventually)
* Data sources - use external doc
* Helpful resources - weblinks + docs/reference guides
* Contributing - Borrow general policy from elsewhere

Note, specification documents are likely out of sync. Don't bother updating them.



## The data pipeline





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


## Contributing

Contributions are welcome. If you notice broken scrapers, missing content, or want to improve the output format, open a pull request or file an issue.

```bash
just check    # run linting and type checks before submitting
```

For architecture and schema documentation, see:

- [docs/data-architecture.md](docs/data-architecture.md) — pipeline design, layer invariants, how to add new sources/consumers
