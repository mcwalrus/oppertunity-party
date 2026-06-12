# Data Architecture

This document describes the full data pipeline for the Opportunity Party
tracker: from raw ingestors through the normalized clean layer and into
downstream consumers (SSG, MCP, analysis).

---

## Pipeline Overview

```
Ingestors (scraper/, yt-dlp, social APIs, feed readers)
     │
     ▼ write-only
data/sources/{source-id}/          ← raw, ingestor-owned, never read by consumers
     │
     ▼ transforms/sources/          (one module per source)
data/clean/{content-type}/         ← canonical, cross-source, read by all consumers
     │
     ├──▶ transforms/               ──▶ site/src/content/     (Astro SSG)
     ├──▶ mcp/cache/                                          (MCP TTL cache)
     └──▶ data/derived/                                       (future analysis)
```

Run the full pipeline with:

```bash
just transform       # sources → clean → site/src/content/
just scrape          # scrape fresh + transform
```

---

## Layer Invariants

### `data/sources/`

- **Owner:** ingestors (scraper modules, yt-dlp, social API clients).
- **Contract:** Ingestors write here; consumers MUST NOT read from this path.
- **Gitignore:** Entirely gitignored. Raw output is ephemeral — regenerate it
  with `just scrape`.
- **Format:** One directory per source (`{source-id}/`), then content-type
  subdirectories as defined in [data-schema.md](data-schema.md).
- **Binary media:** Audio/video files live under `{source-id}/**/media/` and
  are gitignored. Clean items reference them by relative path; they are never
  copied into `data/clean/`.

### `data/clean/`

- **Owner:** transform pipeline (`transforms/sources/{source}.py`).
- **Contract:** All consumers read from here. Never modified by ingestors.
- **Gitignore:** Tracked by git. This is the durable, version-controlled record
  of normalized content.
- **Format:** `data/clean/{content-type}/{slug}/{slug}.md` + `meta.json`.
  See [data-schema.md](data-schema.md) for full schema per content type.
- **Index:** `data/clean/_index.json` is regenerated on every clean transform
  run. It is a flat array of `{slug, content_type, source_id, source_url,
  title, date}` entries — suitable for search/discovery without reading
  individual files.
- **Binary media:** NEVER copied here. Only text and metadata.

### `site/src/content/`

- **Owner:** site transforms (`transforms/blog.py`, etc.).
- **Contract:** Rebuilt on every `just transform` run. Not hand-edited.
- **Format:** Astro-compatible YAML frontmatter + markdown body. Field names
  match the Astro `content.config.ts` collection schemas.
- **Source:** Reads from `data/clean/`, never from `data/sources/` directly.

### `mcp/cache/`

- **Owner:** MCP server (`mcp/server.py`).
- **Contract:** Self-managed TTL cache. Not part of the transform pipeline.

### `data/.cache/`

- **Owner:** HTTP scraper (`scraper/cache.py`).
- **Contract:** Disk cache for raw HTTP responses. Gitignored. Separate from
  `data/sources/` so it survives `--clean` scraper runs.

---

## Directory Reference

```
data/
├── sources/                        # [gitignored] raw ingestor output
│   ├── opportunity-website/        # Website scraper output
│   │   ├── policies/               # Policy pages + extracted PDFs
│   │   ├── blog/                   # Blog posts (flat files)
│   │   ├── events/                 # Events (flat files)
│   │   ├── team/                   # Team/candidate profiles (flat files)
│   │   ├── party-information/      # Party info pages
│   │   ├── news/                   # News articles
│   │   └── pdfs/                   # Raw PDF files + reference.json
│   ├── youtube/                    # YouTube channel enumeration cache
│   │   └── {channel-slug}/
│   │       ├── channel.json
│   │       └── {video-id}/
│   │           ├── meta.json
│   │           ├── transcript.md
│   │           └── media/          # [gitignored] audio/video
│   ├── social/                     # Social media platforms
│   │   └── {platform}/{account}/{post-id}/
│   │       ├── meta.json
│   │       └── media/              # [gitignored] images/video
│   └── external/                   # Substack, news sites, RSS
│       └── {source-slug}/
│           ├── source.json
│           └── {item-slug}/
│               ├── meta.json
│               └── content.md
│
├── clean/                          # [git-tracked] normalized consumer-ready content
│   ├── _index.json                 # Cross-type search index (regenerated each run)
│   ├── policy/{slug}/
│   ├── blog-post/{slug}/
│   ├── event/{slug}/
│   ├── team-member/{slug}/
│   ├── party-information/{slug}/
│   ├── pdf-document/{slug}/
│   ├── media/{slug}/
│   ├── social-post/{slug}/
│   └── external-article/{slug}/
│
├── derived/                        # [future] analysis outputs applied back to content
│
└── .cache/                         # [gitignored] HTTP response cache (scraper-internal)
```

---

## How to Add a New Source

1. **Choose a source ID** — kebab-case, unique under `data/sources/`.
   Examples: `gareth-morgan-substack`, `youtube/opportunity-party-nz`.

2. **Create the ingestor** — write a module (or script) that writes raw output
   to `data/sources/{source-id}/`. Follow the schemas in
   [data-schema.md](data-schema.md) for the correct directory layout.

3. **Write the clean transform** — create
   `transforms/sources/{source_module}.py`. It must:
   - Read from `data/sources/{source-id}/`
   - Write clean items to `data/clean/{content-type}/{slug}/`
     (one `{slug}.md` + one `meta.json` per item)
   - Include all mandatory provenance fields (see [data-schema.md](data-schema.md))
   - Regenerate `data/clean/_index.json` by calling `_write_index(entries)`

4. **Register the transform** — import and call the new transform from
   `transforms/main.py` in Stage 1.

5. **Update `.gitignore`** — if the source produces large binary media, add a
   pattern like `data/sources/{source-id}/**/media/`. The top-level
   `data/sources/` rule already gitignores all raw ingestor output; the
   specific pattern is only needed for documentation clarity.

6. **Test** — run `just scrape` (or `just transform`) and confirm:
   - `data/clean/` contains the expected items
   - `data/clean/_index.json` is updated
   - `just check` passes

---

## How to Add a New Consumer

Consumers read from `data/clean/`. They MUST NOT read from `data/sources/`.

1. **Read `data/clean/_index.json`** for a quick overview of all items
   (slug, content_type, source_id, title, date) without reading individual files.

2. **Read individual items** from `data/clean/{content-type}/{slug}/`:
   - `meta.json` for structured, machine-readable metadata (no YAML parsing)
   - `{slug}.md` for the human-readable body with YAML frontmatter

3. **Own your output directory** — consumers write to their own path
   (e.g. `site/src/content/`, `mcp/cache/`) and rebuild it from `data/clean/`
   on each run. Do not write back into `data/clean/` directly.
   Write-back from analysis goes to `data/derived/`.

4. **Handle missing items gracefully** — `data/clean/` is rebuilt by the
   transform pipeline. If a source is offline, some content types may be
   absent. Consumers should handle this without crashing.

---

## Binary/Media Asset Strategy

Large binary files (audio, video, raw images) follow these rules:

- **Live in** `data/sources/{source-id}/**/media/` — always gitignored.
- **Referenced by** relative path in `meta.json` (`media_path` or
  `media_paths` field) — the path is relative to the project root.
- **Never copied** into `data/clean/`. Clean items only contain text,
  transcripts, and metadata.
- **Downloading** is triggered by the relevant ingestor (e.g. `just
  media-download` for YouTube). Content can exist in `data/clean/` (with
  `has_transcript: false`, `media_path: null`) before the binary is
  downloaded.

---

## Transform Modules Reference

| Module | Reads from | Writes to |
|---|---|---|
| `transforms/sources/opportunity_website.py` | `data/sources/opportunity-website/` | `data/clean/` |
| `transforms/policies.py` | `data/clean/policy/` | `site/src/content/policies/` |
| `transforms/blog.py` | `data/clean/blog-post/` | `site/src/content/blog/` |
| `transforms/events.py` | `data/clean/event/` | `site/src/content/events/` |
| `transforms/team.py` | `data/clean/team-member/` | `site/src/content/team/` |
| `transforms/party_info.py` | `data/clean/party-information/` | `site/src/content/party-info/` |
