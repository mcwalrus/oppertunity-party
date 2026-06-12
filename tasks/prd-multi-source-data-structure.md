# PRD: Multi-Source Data Structure

## Introduction

The current `data/` directory is a flat, single-source layout built exclusively
for the Opportunity Party website scraper. As the project expands to ingest
YouTube channels, social media platforms, external text sources (Substack, news),
and media types (audio, video, transcripts), this layout will not scale.

This PRD specifies a restructured `data/` hierarchy that:

- Cleanly separates raw ingested content from normalized consumer-ready content
- Supports text, audio, video, transcripts, and binary media from any source
- Provides a stable contract between ingestors and consumers (MCP, SSG, analysis)
- Makes source attribution, content type, and pipeline stage explicit at the
  folder level rather than in metadata alone

---

## Data Pipeline Overview

```
Ingestors (scraper/, yt-dlp, social APIs, feed readers)
     │
     ▼ write-only
data/sources/{source-id}/          ← raw, ingestor-owned, never read by consumers
     │
     ▼ normalize (transforms/clean_*)
data/clean/{content-type}/         ← canonical, cross-source, read by all consumers
     │
     ├──▶ transforms/ ──▶ site/src/content/    (SSG's own copy)
     ├──▶ mcp/cache/                           (MCP's TTL cache, self-managed)
     └──▶ analysis/                            (TBD — future)
```

**Invariants:**

1. `data/sources/` is write-only from ingestors. Consumers MUST NOT read from it.
2. `data/clean/` is the single source of truth for normalized content.
3. Binary media (video, audio, raw images) lives under `data/sources/` only.
   Clean items reference them by relative path in `meta.json`, never copy them.
4. Every clean item carries mandatory provenance fields (`source_id`,
   `source_type`, `source_url`, `ingested_at`).
5. Consumers own their own copy/cache and are responsible for keeping it current.

---

## Full Directory Structure

```
data/
├── sources/                              # Raw ingestor output — one dir per source
│   ├── opportunity-website/              # Existing scraper (restructured)
│   │   ├── policies/
│   │   │   ├── index.json
│   │   │   ├── tax-reset/
│   │   │   │   ├── tax-reset.md
│   │   │   │   └── pdf-*.md
│   │   │   └── {slug}/
│   │   ├── blog/
│   │   │   ├── index.json
│   │   │   └── {date}-{slug}.md
│   │   ├── events/
│   │   │   ├── index.json
│   │   │   └── {date}-{slug}.md
│   │   ├── team/
│   │   │   ├── index.json
│   │   │   └── {slug}.md
│   │   ├── news/
│   │   │   ├── index.json
│   │   │   └── {slug}.md
│   │   ├── party-information/
│   │   │   ├── index.json
│   │   │   └── {section}.md
│   │   └── pdfs/
│   │       ├── reference.json
│   │       └── *.pdf
│   │
│   ├── youtube/                          # One dir per channel
│   │   └── {channel-slug}/
│   │       ├── channel.json              # Channel metadata
│   │       └── {video-id}/
│   │           ├── meta.json             # Video metadata (title, date, tags, etc.)
│   │           ├── transcript.md         # Auto/manual transcript
│   │           └── media/               # [gitignored] audio/video files
│   │               ├── audio.mp3
│   │               └── video.mp4
│   │
│   ├── social/                           # One dir per platform
│   │   ├── instagram/
│   │   │   └── {account-slug}/
│   │   │       └── {post-id}/
│   │   │           ├── meta.json
│   │   │           └── media/           # [gitignored] images/videos
│   │   ├── facebook/
│   │   │   └── {account-slug}/
│   │   │       └── {post-id}/
│   │   │           └── meta.json
│   │   ├── x/
│   │   │   └── {account-slug}/
│   │   │       └── {post-id}/
│   │   │           └── meta.json
│   │   ├── linkedin/
│   │   │   └── {account-slug}/
│   │   │       └── {post-id}/
│   │   │           └── meta.json
│   │   └── tiktok/
│   │       └── {account-slug}/
│   │           └── {post-id}/
│   │               ├── meta.json
│   │               └── media/           # [gitignored]
│   │
│   └── external/                         # Substack, news sites, other text sources
│       └── {source-slug}/               # e.g. "nz-herald", "gareth-morgan-substack"
│           ├── source.json              # Source metadata (name, URL, feed URL)
│           └── {item-slug}/
│               ├── meta.json
│               └── content.md
│
├── clean/                                # Normalized, consumer-ready — one dir per content type
│   ├── _index.json                       # Cross-source, cross-type index for search/discovery
│   ├── policy/
│   │   └── {slug}/
│   │       ├── {slug}.md                # Clean body with YAML frontmatter
│   │       └── meta.json                # Structured metadata
│   ├── blog-post/
│   │   └── {slug}/
│   │       ├── {slug}.md
│   │       └── meta.json
│   ├── event/
│   │   └── {slug}/
│   │       ├── {slug}.md
│   │       └── meta.json
│   ├── team-member/
│   │   └── {slug}/
│   │       ├── {slug}.md
│   │       └── meta.json
│   ├── party-information/
│   │   └── {slug}/
│   │       ├── {slug}.md
│   │       └── meta.json
│   ├── pdf-document/
│   │   └── {slug}/
│   │       ├── {slug}.md                # Extracted text
│   │       └── meta.json
│   ├── media/                            # Video/audio items (transcript + metadata only)
│   │   └── {slug}/
│   │       ├── transcript.md            # Cleaned transcript body
│   │       ├── summary.md               # [optional] AI-generated summary
│   │       └── meta.json
│   ├── social-post/
│   │   └── {slug}/
│   │       ├── {slug}.md                # Post text content
│   │       └── meta.json
│   └── external-article/
│       └── {slug}/
│           ├── {slug}.md
│           └── meta.json
│
└── .cache/                               # Existing HTTP cache (scraper-internal, unchanged)
    └── ...
```

---

## Clean Layer Schema

Every item in `data/clean/` MUST carry these fields. They are written into both
the YAML frontmatter of the `.md` file and into `meta.json`.

### Mandatory provenance fields (all content types)

| Field | Type | Description |
|---|---|---|
| `slug` | `string` | URL-safe kebab-case identifier, unique within content type |
| `content_type` | `string` | One of: `policy`, `blog-post`, `event`, `team-member`, `party-information`, `pdf-document`, `media`, `social-post`, `external-article` |
| `source_id` | `string` | Ingestor source ID (e.g. `opportunity-website`, `youtube/opportunity-party-nz`) |
| `source_type` | `string` | One of: `website`, `youtube`, `social`, `external` |
| `source_url` | `string` | Canonical URL of the original content |
| `ingested_at` | `ISO-8601` | When the raw data was first ingested |
| `cleaned_at` | `ISO-8601` | When the clean item was last written |

### Content-type specific fields

**`policy`**

```yaml
title: string
summary: string          # 1–2 sentence description
pdf_urls: [string]       # Google Drive / direct PDF links
tags: [string]
```

**`blog-post`**

```yaml
title: string
date: YYYY-MM-DD
author: string
excerpt: string
```

**`event`**

```yaml
title: string
date: YYYY-MM-DD
time: string             # e.g. "6:30 PM"
location: string
description: string
registration_url: string # optional
```

**`team-member`**

```yaml
name: string
role: string             # e.g. "Party Leader", "Candidate"
electorate: string       # optional
```

**`media`**

```yaml
title: string
date: YYYY-MM-DD
duration_seconds: integer
channel: string
platform: string         # youtube, tiktok, etc.
media_path: string       # relative path to binary in data/sources/ (gitignored)
has_transcript: boolean
```

**`social-post`**

```yaml
platform: string
account: string
date: YYYY-MM-DD
text: string             # raw post text (also body of .md)
media_paths: [string]    # relative paths to media in data/sources/ (gitignored)
engagement: {}           # platform-specific (likes, shares, etc.) — optional
```

**`external-article`**

```yaml
title: string
date: YYYY-MM-DD
author: string
publication: string      # e.g. "NZ Herald", "Gareth Morgan Substack"
excerpt: string
```

---

## Goals

- Support ingestion of text, audio, video, and transcripts from any source type
  without restructuring `data/` again
- Maintain a clean contract between ingestors (write `sources/`) and consumers
  (read `clean/`)
- Allow consumers to filter by `content_type`, `source_id`, or `source_type`
  without parsing content
- Ensure the SSG only receives content approved for public presentation (from
  the clean layer, not raw)
- Make binary media discoverable by path reference without duplicating large
  files across layers

---

## User Stories

### US-001: Restructure opportunity-website source path

**Description:** As a developer, I need the existing scraper output moved into
`data/sources/opportunity-website/` so the new layout is established and the
scraper writes to the canonical source path.

**Acceptance Criteria:**

- [ ] All content currently under `data/{type}/` is moved to
  `data/sources/opportunity-website/{type}/`
- [ ] `scraper/` write paths updated throughout to use new location
- [ ] `transforms/` read paths updated to use new source location
- [ ] `data/.cache/` remains at `data/.cache/` (unchanged)
- [ ] `.gitignore` updated: `data/sources/` added with explanatory comment;
  old media-only patterns removed
- [ ] `git status` shows `data/sources/` as untracked (not staged)
- [ ] `git status` shows `data/clean/` as tracked once first clean transform runs
- [ ] `just scrape` completes without errors
- [ ] `just check` (ruff + ty) passes

### US-002: Define and document the clean layer schema

**Description:** As a developer, I need a documented, versioned schema for
`data/clean/` items so any ingestor or consumer can produce or read clean data
correctly.

**Acceptance Criteria:**

- [ ] `docs/data-schema.md` written, covering all content types
- [ ] Mandatory provenance fields documented (`slug`, `content_type`,
  `source_id`, `source_type`, `source_url`, `ingested_at`, `cleaned_at`)
- [ ] Each content-type's specific fields documented with types and whether optional
- [ ] `meta.json` schema matches YAML frontmatter schema exactly (no divergence)
- [ ] `just check` passes

### US-003: Implement clean layer transform for opportunity-website

**Description:** As a developer, I need a transform step that reads from
`data/sources/opportunity-website/` and writes normalized items to `data/clean/`
so downstream consumers have a stable, source-agnostic input.

**Acceptance Criteria:**

- [ ] New module `transforms/sources/opportunity_website.py` reads each content
  type from `data/sources/opportunity-website/` and writes to the correct
  `data/clean/{content-type}/{slug}/` directory
- [ ] Each output directory contains `{slug}.md` (with YAML frontmatter) and
  `meta.json` matching the schema from US-002
- [ ] Existing `transforms/main.py` updated to run this step before the
  `data/clean/ → site/src/content/` step
- [ ] `transforms/` reads from `data/clean/` (not `data/sources/`) when
  building `site/src/content/`
- [ ] `just scrape` produces correct output end-to-end
- [ ] `just check` passes

### US-004: Define YouTube source schema and layout

**Description:** As a developer, I need a documented schema for YouTube source
data so a future ingestor knows exactly where and how to write channel/video data.

**Acceptance Criteria:**

- [ ] `docs/data-schema.md` extended with YouTube source schema:
  - `data/sources/youtube/{channel-slug}/channel.json` fields documented
  - `data/sources/youtube/{channel-slug}/{video-id}/meta.json` fields documented
  - `data/sources/youtube/{channel-slug}/{video-id}/transcript.md` format documented
  - `data/sources/youtube/{channel-slug}/{video-id}/media/` noted as gitignored
- [ ] `.gitignore` updated to exclude `data/sources/youtube/**/media/`
- [ ] `data/clean/media/` item schema documented (what a normalized YouTube item looks like)
- [ ] `just check` passes

### US-005: Define social media source schema and layout

**Description:** As a developer, I need a documented schema for each social
media platform's source data so ingestors have a clear target layout.

**Acceptance Criteria:**

- [ ] `docs/data-schema.md` extended with social source schema:
  - `data/sources/social/{platform}/{account-slug}/{post-id}/meta.json` fields
    documented for Instagram, Facebook, X, LinkedIn, TikTok
  - Platform-specific `engagement` sub-fields documented per platform
  - `media/` subdirectory noted as gitignored for platforms that include it
- [ ] `.gitignore` updated to exclude `data/sources/social/**/media/`
- [ ] `data/clean/social-post/` item schema documented
- [ ] `just check` passes

### US-006: Define external text source schema and layout

**Description:** As a developer, I need a documented schema for external text
sources (Substack, news sites) so ingestors know where and how to write articles.

**Acceptance Criteria:**

- [ ] `docs/data-schema.md` extended with external source schema:
  - `data/sources/external/{source-slug}/source.json` fields documented
    (`name`, `url`, `feed_url`, `source_type`)
  - `data/sources/external/{source-slug}/{item-slug}/meta.json` and
    `content.md` fields documented
- [ ] `data/clean/external-article/` item schema documented
- [ ] `just check` passes

### US-007: Write data architecture documentation and update project docs

**Description:** As a developer, I need a single reference document explaining
the full data pipeline — from ingestors through `sources/`, `clean/`, and into
each consumer — so any contributor can understand how data flows.

**Acceptance Criteria:**

- [ ] `docs/data-architecture.md` written covering:
  - Pipeline diagram (sources → clean → consumers)
  - Invariants (what each layer owns and what it must not do)
  - How to add a new source (checklist)
  - How to add a new consumer (checklist)
  - Binary/media asset strategy (path references, gitignore)
- [ ] `README.md` updated to reference `docs/data-architecture.md`
- [ ] `AGENTS.md` updated with the new key paths under `data/`
- [ ] `just check` passes

---

## Functional Requirements

- **FR-1:** `data/sources/{source-id}/` is the write target for all ingestors.
  No consumer reads from this path directly.
- **FR-2:** `data/clean/{content-type}/{slug}/` is the read source for all
  consumers. The clean layer is always derived from one or more source items.
- **FR-3:** Every clean item MUST contain both a `{slug}.md` (with YAML
  frontmatter) and a `meta.json` file with identical provenance fields.
- **FR-4:** `content_type` and `source_id` MUST be present in every clean
  item's frontmatter and `meta.json`.
- **FR-5:** Binary media files (video, audio, raw images) MUST NOT be copied
  into `data/clean/`. They live under `data/sources/` only and are referenced
  by relative path in `meta.json`.
- **FR-6:** `data/clean/_index.json` MUST be regenerated on every clean
  transform run. It contains a flat array of `{slug, content_type, source_id,
  source_url, title, date}` entries for all items — usable for search and
  discovery without reading individual item files.
- **FR-7:** `transforms/` reads from `data/clean/` when building
  `site/src/content/`. It MUST NOT read from `data/sources/` directly.
- **FR-8:** The `site/src/content/` directory is owned by the transforms
  pipeline — it is rebuilt from `data/clean/` on each run and is not
  hand-edited.
- **FR-9:** Large binary files under `data/sources/**/media/` MUST be
  gitignored. The `.gitignore` must be updated before any ingestor for a
  media-bearing source is implemented.
- **FR-10:** `data/sources/` MUST be gitignored in its entirety. Raw ingestor
  output is ephemeral — it is regenerated by running `just scrape` and must
  not be committed. A comment in `.gitignore` must explain this explicitly.
- **FR-11:** `data/clean/` MUST be committed to the repository. The clean
  layer is the durable, version-controlled record of normalized content.
  It is the only layer that git tracks under `data/`.

---

## Non-Goals

- This PRD does **not** specify ingestor implementation for YouTube, social,
  or external sources — only their target schemas and layout.
- This PRD does **not** redesign the MCP server — the MCP continues to use
  `mcp/cache/` as its own cache and may eventually read from `site/src/content/`.
- This PRD does **not** define analysis outputs — `analysis/` is a placeholder
  for a future PRD.
- This PRD does **not** introduce a database layer (SQLite, etc.). Files remain
  the canonical store.
- This PRD does **not** add new content scrapers. It only restructures what
  exists and defines schemas for what will come.

---

## Technical Considerations

- **Slug uniqueness:** Slugs must be unique within a `content_type` directory.
  For items from multiple sources of the same type (e.g. blog posts from both
  the website and Substack), prefix the slug with the `source_id` short code
  if a collision is possible: `{source-prefix}-{original-slug}`.
- **`meta.json` is the machine-readable truth.** The YAML frontmatter in `.md`
  is for human readability and tooling (Obsidian, Astro). If they diverge,
  `meta.json` wins in code.
- **Existing `mcp/cache/`** is unaffected by this restructure. The MCP server
  continues to manage its own TTL cache independently.
- **Existing `data/.cache/`** (HTTP scraper cache) is unaffected.
- **The `transforms/` module** currently reads `data/{type}/` directly. After
  US-001 and US-003, it will read `data/clean/{content-type}/` instead. The
  intermediate step (sources → clean) is new work.
- **Gitignore strategy:**

  ```
  # Raw ingestor output — ephemeral, regenerated by `just scrape`
  data/sources/
  ```

  The existing media-only patterns (`data/sources/**/media/`) are superseded
  by the top-level `data/sources/` ignore. They are no longer needed.

- **Migration note:** The content currently committed under `data/{type}/`
  (policies, blog, events, team, etc.) will be moved to
  `data/sources/opportunity-website/{type}/` and will therefore become
  gitignored. After US-001 and US-003 are complete, `data/clean/` will hold
  the committed normalized equivalents. The git history of the old paths is
  preserved; no `git filter-branch` is needed.

---

## Design Considerations

### Why directory-per-item in `data/clean/`?

Some items (media, PDF documents) require multiple files (transcript + meta,
or extracted text + meta). Using a directory-per-item in `data/clean/` is
consistent across all content types and avoids special-casing single-file vs
multi-file items.

### Why both `{slug}.md` and `meta.json`?

- `.md` with YAML frontmatter: human-readable in Obsidian, directly usable by
  Astro content collections, diffable in git.
- `meta.json`: machine-readable without YAML parsing, usable for index building
  and search, consumed by the MCP and analysis layers without markdown parsing.

### Why keep `data/sources/` read-only for consumers?

Raw ingestor output is messy — it contains scraper artefacts, CDN image tags,
navigation cruft, and varying formats. If consumers read from `sources/` they
couple to ingestor internals. The clean layer is the stable API.

---

## Success Metrics

- `just scrape && just check` runs end-to-end without errors after restructure
- Any new source can be added by: (a) writing to `data/sources/{new-source}/`,
  (b) implementing a clean transform, and (c) requiring zero changes to existing
  consumers
- A developer unfamiliar with the project can determine the correct write path
  for a new ingestor in under 5 minutes by reading `docs/data-architecture.md`
- The clean layer index (`data/clean/_index.json`) covers all content types and
  is regenerated without manual steps

---

## Open Questions

- Should `data/clean/_index.json` be committed to git, or generated at build
  time only? Commit to git.
- Should campaign-specific content (currently under `data/campaign/`) be
  absorbed into a `campaign` content type in `data/clean/`, or kept as a
  separate first-class source? Absorbe please
- Should the analysis layer eventually write *back* into `data/clean/` (e.g.
  adding a `summary.md` to existing items), or maintain its own separate
  output directory? Analysis should applied back to `data/derived`
