# Data Schema Reference

This document is the authoritative schema reference for all layers of the
data pipeline: `data/sources/` (raw ingestor output) and `data/clean/`
(normalized consumer-ready content).

See [data-architecture.md](data-architecture.md) for the pipeline overview.

---

## Table of Contents

1. [Clean Layer Schema](#clean-layer-schema)
   - [Mandatory Provenance Fields](#mandatory-provenance-fields)
   - [policy](#policy)
   - [blog-post](#blog-post)
   - [event](#event)
   - [team-member](#team-member)
   - [party-information](#party-information)
   - [pdf-document](#pdf-document)
   - [media](#media)
   - [social-post](#social-post)
   - [external-article](#external-article)
2. [Source Layer Schemas](#source-layer-schemas)
   - [opportunity-website](#opportunity-website-source)
   - [youtube](#youtube-source)
   - [social](#social-source)
   - [external](#external-source)

---

## Clean Layer Schema

Every item in `data/clean/` lives in its own directory:

```
data/clean/{content-type}/{slug}/
    {slug}.md      ← YAML frontmatter + cleaned body (human-readable)
    meta.json      ← identical fields as machine-readable JSON (no divergence)
```

**Rule:** If `meta.json` and the YAML frontmatter ever diverge, `meta.json`
wins in code. The YAML frontmatter is for human readability and Astro content
collections; `meta.json` is for programmatic consumers (MCP, index builder,
analysis).

### Mandatory Provenance Fields

These fields MUST appear in every clean item's YAML frontmatter and `meta.json`.

| Field | Type | Description |
|---|---|---|
| `slug` | `string` | URL-safe kebab-case identifier, unique within `content_type` |
| `content_type` | `string` | One of the content types listed below |
| `source_id` | `string` | Ingestor source ID, e.g. `opportunity-website`, `youtube/opportunity-party-nz` |
| `source_type` | `string` | One of: `website`, `youtube`, `social`, `external` |
| `source_url` | `string` | Canonical URL of the original content |
| `ingested_at` | ISO-8601 string | When the raw data was first scraped/ingested |
| `cleaned_at` | ISO-8601 string | When the clean item was last written |

---

### `policy`

**Path:** `data/clean/policy/{slug}/`

Additional fields (beyond mandatory provenance):

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | ✅ | Policy display name |
| `summary` | `string` | ✅ (may be empty) | 1–2 sentence description |
| `pdf_urls` | `[string]` | ✅ (may be `[]`) | Google Drive / direct PDF download links |
| `tags` | `[string]` | ✅ (may be `[]`) | Topic tags |

**Example frontmatter:**

```yaml
---
slug: "tax-reset"
content_type: "policy"
source_id: "opportunity-website"
source_type: "website"
source_url: "https://www.opportunity.org.nz/tax-reset"
ingested_at: "2026-06-08T13:25:46.158309"
cleaned_at: "2026-06-12T00:00:00+00:00"
title: "Tax Reset"
summary: ""
pdf_urls: ["https://drive.google.com/file/d/..."]
tags: []
---
```

---

### `blog-post`

**Path:** `data/clean/blog-post/{slug}/`

Used for both blog posts and news articles from the opportunity website
(and future external sources such as Substack).

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | ✅ | Article title |
| `date` | `YYYY-MM-DD` | ✅ (may be empty) | Publication date |
| `author` | `string` | ✅ (may be empty) | Author name |
| `excerpt` | `string` | ✅ (may be empty) | Short summary / teaser |

---

### `event`

**Path:** `data/clean/event/{slug}/`

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | ✅ | Event name |
| `date` | `YYYY-MM-DD` | ✅ (may be empty) | Event date |
| `time` | `string` | ✅ (may be empty) | Human-readable time, e.g. `"6:30 PM"` |
| `location` | `string` | ✅ (may be empty) | Location name or city |
| `venue` | `string` | ✅ (may be empty) | Venue name |
| `address` | `string` | ✅ (may be empty) | Full street address |
| `description` | `string` | ✅ (may be empty) | Short description |
| `registration_url` | `string` | optional | Ticketing / RSVP URL |

---

### `team-member`

**Path:** `data/clean/team-member/{slug}/`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | `string` | ✅ | Full display name |
| `role` | `string` | ✅ (may be empty) | Role title, e.g. `"Party Leader"`, `"Candidate"` |
| `electorate` | `string` | optional | NZ electorate contested, e.g. `"Mt Albert"` |

---

### `party-information`

**Path:** `data/clean/party-information/{slug}/`

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | ✅ | Section/page title |

---

### `pdf-document`

**Path:** `data/clean/pdf-document/{slug}/`

Slug format: `{policy-slug}-{document-type}`, e.g. `tax-reset-policy-overview`.

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | ✅ | Document title, e.g. `"Tax Reset — Policy Overview"` |
| `policy_slug` | `string` | ✅ (may be empty) | Parent policy slug for cross-referencing |
| `image_paths` | `[string]` | ✅ (may be `[]`) | Relative paths to extracted images under `data/clean/pdf-document/{slug}/images/`. Only images from pages with embedded graphics (signalled by `pymupdf4llm` picture-text blocks) are included — decorative page backgrounds are dropped. See [PDF image extraction](#pdf-image-extraction). |
| `images_extracted_at` | ISO-8601 string | optional | When the image extraction last ran (set by the `pdf_images` Dagster asset). |

The `.md` body contains the extracted text from the PDF. Picture-text
blocks emitted by `pymupdf4llm` (for content it couldn't OCR) are
replaced with `![alt](images/filename.jpg)` references at transform
time — see [PDF image extraction](#pdf-image-extraction) below.

#### PDF image extraction

PDFs may contain embedded charts, diagrams, and other content graphics
that `pymupdf4llm` cannot extract as text. The `pdf_images` Dagster
asset extracts these as JPEG files and references them in the clean
markdown.

- **Source:** the PDF at `data/sources/opportunity-website/pdfs/*.pdf`
- **Output:** `data/clean/pdf-document/{slug}/images/img-NNN-NNN.jpg`
  (named by page number, 1-indexed, then 0-indexed within page)
- **Markdown:** each `**----- Start of picture text -----**` block in
  the body is replaced with `![alt](images/img-NNN-NNN.jpg)` in
  document order
- **Filter:** only pages flagged by `pymupdf4llm` with a picture-text
  block are extracted from, so decorative page backgrounds (which
  `pymupdf4llm` doesn't flag) are dropped automatically

This is a deliberate exception to the
[Binary/Media Asset Strategy](data-architecture.md#binarymedia-asset-strategy)
rule that media stays in `data/sources/` — PDF images are small, useful
content illustrations (charts, diagrams) that belong with the markdown
they describe. They are tracked in git alongside the clean text.

---

### `media`

**Path:** `data/clean/media/{slug}/`

Used for YouTube videos, podcast episodes, and other audio/video items.
Binary media is never copied to `data/clean/`; it is referenced by path.

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | ✅ | Video/episode title |
| `date` | `YYYY-MM-DD` | ✅ (may be empty) | Publication date |
| `duration_seconds` | `integer` | optional | Runtime in seconds |
| `channel` | `string` | optional | Channel/show name |
| `platform` | `string` | optional | `youtube`, `tiktok`, etc. |
| `media_path` | `string` | optional | Relative path to binary in `data/sources/` (gitignored) |
| `has_transcript` | `boolean` | ✅ | Whether `transcript.md` exists in this item directory |

Additional files (optional):

| File | Description |
|---|---|
| `transcript.md` | Cleaned transcript body |
| `summary.md` | AI-generated summary (optional) |

---

### `social-post`

**Path:** `data/clean/social-post/{slug}/`

| Field | Type | Required | Description |
|---|---|---|---|
| `platform` | `string` | ✅ | `instagram`, `facebook`, `x`, `linkedin`, `tiktok` |
| `account` | `string` | ✅ | Account handle/slug |
| `date` | `YYYY-MM-DD` | ✅ (may be empty) | Post date |
| `text` | `string` | ✅ (may be empty) | Raw post text (also used as `.md` body) |
| `media_paths` | `[string]` | ✅ (may be `[]`) | Relative paths to images/video in `data/sources/` (gitignored) |
| `engagement` | `object` | optional | Platform-specific engagement metrics (see below) |

**Platform-specific `engagement` sub-fields:**

| Platform | Fields |
|---|---|
| Instagram | `likes`, `comments`, `saves`, `reach` |
| Facebook | `likes`, `comments`, `shares`, `reach` |
| X (Twitter) | `likes`, `retweets`, `replies`, `views` |
| LinkedIn | `likes`, `comments`, `shares`, `impressions` |
| TikTok | `likes`, `comments`, `shares`, `views`, `saves` |

---

### `external-article`

**Path:** `data/clean/external-article/{slug}/`

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | `string` | ✅ | Article title |
| `date` | `YYYY-MM-DD` | ✅ (may be empty) | Publication date |
| `author` | `string` | optional | Author name |
| `publication` | `string` | optional | Publication name, e.g. `"NZ Herald"` |
| `excerpt` | `string` | optional | Short summary / teaser |

---

## Source Layer Schemas

Raw ingestor output lives under `data/sources/{source-id}/`.  These schemas
document what each ingestor writes so future ingestors have a clear target.
Consumers MUST NOT read from `data/sources/` — use `data/clean/` instead.

---

### opportunity-website Source

**Path:** `data/sources/opportunity-website/`

The website scraper writes one sub-directory per content type.

#### Policies

```
data/sources/opportunity-website/policies/
    index.json                     ← array of policy metadata objects
    {slug}/
        {slug}.md                  ← scraped website page (markdown with metadata blocks)
        pdf-{type}.md              ← extracted PDF text (one file per PDF)
```

`index.json` entry fields: `slug`, `title`, `url`, `content`, `pdf_downloads[]`, `scraped_at`.

#### Blog posts

```
data/sources/opportunity-website/blog/
    index.json                     ← array of blog post metadata
    {date}-{slug}.md               ← scraped article with **Key**: Value metadata header
```

#### Events

```
data/sources/opportunity-website/events/
    index.json
    {date}-{slug}.md
```

#### Team members

```
data/sources/opportunity-website/team/
    index.json
    {slug}.md                      ← H1 name heading + **Role**: / **Electorate**: metadata
```

#### Party information

```
data/sources/opportunity-website/party-information/
    index.json
    {section}.md                   ← H1 title + > **URL**: blockquote metadata
```

#### News

```
data/sources/opportunity-website/news/
    {slug}.md
```

#### PDFs

```
data/sources/opportunity-website/pdfs/
    reference.json                 ← download tracking (md5, filename, policy_slug, etc.)
    *.pdf                          ← raw downloaded PDFs (gitignored via data/sources/)
```

---

### youtube Source

**Path:** `data/sources/youtube/{channel-slug}/`

```
data/sources/youtube/{channel-slug}/
    channel.json                   ← channel metadata
    {video-id}/
        meta.json                  ← video metadata
        transcript.md              ← auto/manual transcript
        media/                     ← [gitignored] audio/video binaries
            audio.mp3
            video.mp4
```

#### `channel.json` fields

| Field | Type | Description |
|---|---|---|
| `channel_id` | `string` | YouTube channel ID |
| `channel_slug` | `string` | Filesystem slug, e.g. `opportunity-party-nz` |
| `display_name` | `string` | Human-readable channel name |
| `url` | `string` | Channel URL |
| `description` | `string` | Channel description |
| `fetched_at` | ISO-8601 | When metadata was fetched |

#### `{video-id}/meta.json` fields

| Field | Type | Description |
|---|---|---|
| `video_id` | `string` | YouTube video ID |
| `title` | `string` | Video title |
| `date` | `YYYY-MM-DD` | Upload date |
| `duration_seconds` | `integer` | Video duration |
| `description` | `string` | Video description |
| `tags` | `[string]` | Video tags |
| `channel_slug` | `string` | Parent channel slug |
| `thumbnail_url` | `string` | Thumbnail URL |
| `view_count` | `integer` | View count at ingestion time |
| `fetched_at` | ISO-8601 | When metadata was fetched |

#### `{video-id}/transcript.md`

Plain markdown. Auto-generated or manually corrected. The first line may be
a `# Title` heading. No YAML frontmatter (provenance is in `meta.json`).

#### `media/` directory (gitignored)

Binary audio/video files downloaded by yt-dlp. Gitignored via the
`data/sources/` rule in `.gitignore`. Clean items reference these by relative
path in their `meta.json` (`media_path` field).

---

### social Source

**Path:** `data/sources/social/{platform}/{account-slug}/{post-id}/`

Supported platforms: `instagram`, `facebook`, `x`, `linkedin`, `tiktok`.

```
data/sources/social/{platform}/{account-slug}/
    {post-id}/
        meta.json
        media/        ← [gitignored] images and video files (instagram, tiktok only)
```

#### `meta.json` fields (all platforms)

| Field | Type | Description |
|---|---|---|
| `post_id` | `string` | Platform post identifier |
| `platform` | `string` | Platform name |
| `account` | `string` | Account handle/slug |
| `url` | `string` | Canonical post URL |
| `date` | `YYYY-MM-DD` | Post date |
| `text` | `string` | Post text content |
| `fetched_at` | ISO-8601 | When metadata was fetched |
| `engagement` | `object` | Platform-specific engagement metrics (see [social-post](#social-post)) |

**`media/` directories** exist for platforms that include images or video
(Instagram, TikTok). They are gitignored via `data/sources/`.

---

### external Source

**Path:** `data/sources/external/{source-slug}/`

For Substack newsletters, news sites, RSS-scraped articles.

```
data/sources/external/{source-slug}/
    source.json                    ← source metadata
    {item-slug}/
        meta.json                  ← article metadata
        content.md                 ← raw article body (may contain HTML artefacts)
```

#### `source.json` fields

| Field | Type | Description |
|---|---|---|
| `name` | `string` | Human-readable source name, e.g. `"NZ Herald"` |
| `url` | `string` | Source homepage URL |
| `feed_url` | `string` | RSS/Atom feed URL (if applicable) |
| `source_type` | `string` | `"rss"`, `"substack"`, `"scrape"` |
| `description` | `string` | Brief description of the source |

#### `{item-slug}/meta.json` fields

| Field | Type | Description |
|---|---|---|
| `item_id` | `string` | Source-specific item identifier |
| `title` | `string` | Article title |
| `url` | `string` | Canonical article URL |
| `date` | `YYYY-MM-DD` | Publication date |
| `author` | `string` | Author name |
| `excerpt` | `string` | Short excerpt / teaser |
| `fetched_at` | ISO-8601 | When the article was fetched |

#### `{item-slug}/content.md`

Raw article body in markdown (may contain scraper artefacts — normalize via
the clean transform before consuming).