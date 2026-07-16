![Opportunity Party — Expect Better](assets/opportunity-party-expect-better.webp)

# Opportunity Party

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org)
[![Dagster pipeline](https://img.shields.io/badge/orchestration-Dagster-5e30a8)](https://dagster.io)
[![Built with Astro](https://img.shields.io/badge/site-Astro-FF5D01)](https://astro.build)

A scraping and analysis pipeline for [opportunity.org.nz](https://www.opportunity.org.nz). Web content is scraped, cleaned into canonical markdown, and built into a static site — ready for future analysis or introspection of downstream tooling on the party's people, policies, or manfiest. See [LICENSE](LICENSE) for terms.

## Quickstart

Requires macOS or Linux, [Homebrew](https://brew.sh), and Python 3.12+.

```bash
brew bundle --file=scripts/Brewfile   # direnv, fnm, uv, just, lefthook, …
direnv allow                          # load .envrc (DAGSTER_HOME + venv PATH)
just install                          # uv sync — Python deps
just dev                              # open the Dagster UI
```

This project is shaped for AI-assisted development: every workflow is observable, every command is reproducible, every tool choice is deliberate. The selection of building blocks of which tools + dependencies are used are more significant. Anything that breaks I can verify through [dagster.io](https://dagster.io/), with manual validation of transformations via [obsidian.md](https://obsidian.md/).

## Pipeline

```mermaid
flowchart LR
    raw[data/sources/<br/>raw ingestor output] --> scrape[scrape]
    scrape --> transform[transform]
    transform --> clean[data/clean/<br/>canonical markdown]
    clean --> build[site build]
    build --> site[static site]
```

## Key tools

Three things to understand before you touch anything:

**[Dagster](https://dagster.io)** — the Python orchestrator. Every scrape, transform, and build step is an *asset* under `pipeline/defs/assets/`. New sources, transforms, and consumers are added by writing new assets and wiring them into a job. The UI (`just dev`) shows the full lineage of any output back to its raw source — useful for visualisation. AI agents can use the `dg` utility enabled by `direnv`.

**[direnv](https://direnv.net)** — auto-loads `.envrc` when you `cd` into the project. Combined with `uv`, every shell session gets the exact pinned toolchain (and a stable `DAGSTER_HOME`) without global installs. Run `direnv allow` once after cloning.

**[pi.dev](https://pi.dev)** — the AI coding harness this project is shaped for. Skills, agent context, and the Dagster observability surface are designed so an agent can pick up any task without re-explaining the codebase. Additionally I have used `npx skills@latest` for downloading useful skills for project development.

## Working with the data

```
data/
├── sources/    # gitignored, raw ingestor output — write-only
└── clean/      # tracked, canonical markdown + meta.json — read by all consumers
```

Ingestors write to `data/sources/`; everyone else reads from `data/clean/`. Adding a new source or consumer, schema details, and the layer invariants all live in [`docs/data-architecture.md`](docs/data-architecture.md).

## Commands

| Recipe | What it does |
| --- | --- |
| `just install` | `uv sync` — install Python deps |
| `just dev` | Launch the Dagster UI |
| `just check` | `ruff check` + `ruff format --check` + `ty check` (read-only, CI-safe) |
| `just fix` | Auto-fix lint and reformat |
| `just validate` | Verify links in `data/clean/**/*.md` |
| `just hooks-install` | Wire lefthook into `.git/hooks` (once after cloning) |

## Contributing

Only valiadation is running `just check` before opening a PR — it must pass. The same checks run automatically on git pre-commit. To glance over the project structure, start with [`docs/data-architecture.md`](docs/data-architecture.md) for architecture and [`docs/data-schema.md`](docs/data-schema.md) for schema questions.

### Future Roadmap

The Opportunity Party is one voice among many. The most useful analysis often comes from combining this corpus with other sources rather than reading it in isolation. **Candidate sources worth adding if possible**:

- News coverage that mentions the party or its policies
- YouTube/podcast transcripts (`youtube` ingestor is already in place)
- Social feeds (X, Facebook, SubStack) via API clients
- Parliamentary records, select-committee submissions
- External newsletters and policy commentary

A browsable static site that mirrors the party's public-facing pages as plain markdown would be useful for archive and research access — particularly when the live marketing site changes and a snapshot is needed for citation. I'd host this if there's interest. For anything else, feel free to fork or open an issue with the source URL and what you want to extract — the pattern is small and well-defined.