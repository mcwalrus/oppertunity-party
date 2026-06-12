# Opportunity Party MCP Server — Design

A read-only [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes the New Zealand Opportunity Party's public information to LLM agents.
It lives under [`mcp/`](../mcp).

## Goals & constraints

- **Read-only.** No tool mutates the website or the local cache. Every tool is
  annotated `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`.
- **Live from the website.** All content is fetched from `opportunity.org.nz`.
  There is no stale data layer. A TTL-managed on-disk cache prevents redundant
  fetches while keeping content current.
- **Website-linked results.** Every tool result includes the canonical URL(s) of
  the underlying page(s), so agents and users can follow up on the live site.
- **Interactive tools.** Two tools go beyond information retrieval:
  `opportunity_get_upcoming_events` (live event listing) and
  `opportunity_tax_reset_calculator` (a calculator powered by live policy data).
- **PDF documents via managed cache.** Policy PDFs are binary files on Google
  Drive. The server downloads them, converts with `pymupdf4llm`, and stores the
  markdown output on disk under a long TTL. This is the sole exception to no-cache
  reads — the disk store is managed entirely by the MCP server itself.
- **Agent-friendly.** Clear `opportunity_*` tool names, concise summaries in
  listings, full content in detail views, and canonical URLs in every response.

---

## Architecture

```
                         ┌─────────────────────────────────┐
   MCP client (Claude)   │          mcp/server.py          │
   ───────────────────►  │  FastMCP("opportunity_party_mcp")
                         │  • Pydantic input models         │
                         │  • 12 read-only tools            │
                         │  • markdown / json formatting    │
                         └──────────────┬──────────────────┘
                                        │ imports
                         ┌──────────────▼──────────────────┐
                         │        mcp/repository.py         │
                         │  live-first data access layer    │
                         │  • TTL cache for all fetches     │
                         │  • PDF download + pymupdf4llm    │
                         │  • policy param extraction       │
                         └────────┬─────────────┬──────────┘
                                  │ reuses      │ manages
                   ┌──────────────▼───────┐  ┌──▼─────────────────────┐
                   │   scraper/ package   │  │    mcp/cache/          │
                   │   curl client,       │  │  TTL-keyed JSON files  │
                   │   BS4 extractors,    │  │  + pdf-docs/*.md       │
                   │   markdownify        │  │  (pymupdf4llm output)  │
                   └──────────┬───────────┘  └────────────────────────┘
                              │ curl
                   ┌──────────▼───────────┐
                   │  opportunity.org.nz  │
                   └──────────────────────┘
```

### Two layers

1. **`mcp/repository.py` — data access.** The bridge to the `scraper` package.
   It imports and reuses:
   - `scraper.client`: `BASE_URL`, `fetch_page`, `fetch_html` (the `curl` client).
   - `scraper.policies`: `POLICY_SLUGS`, `_extract_title`, `_extract_pdf_links`,
     `_extract_markdown`, `_discover_policy_links`.
   - `scraper.news`: `_extract_article_links`, `_extract_article_content`, `_title_to_slug`.
   - `scraper.team`: `_extract_member_links`, `_extract_member_content`, `_extract_role`, `_name_to_slug`.
   - `scraper.party_info`: `_extract_content`.
   - `scraper.pdf_convert`: `extract_text`, `parse_header`, `extract_body`, `format_body`.
   - `scraper.pdf_download`: `download_policy_pdfs` helpers.

   It exposes pure read functions (`list_*`, `get_*`, `search`, calculator) returning
   plain dicts, plus a `RepositoryError` for not-found cases with actionable messages.

2. **`mcp/server.py` — MCP surface.** FastMCP tools wrapping the repository,
   with Pydantic input validation, dual `markdown`/`json` output, and shared
   formatting helpers (`_listing_md`, `_detail_md`, `_json`).

---

## TTL cache layer

The repository owns a lightweight TTL cache stored in `mcp/cache/`. Each cached
item is a JSON envelope:

```json
{
  "fetched_at": "2026-06-08T12:00:00Z",
  "ttl_seconds": 86400,
  "data": { ... }
}
```

On every read the repository checks `fetched_at + ttl_seconds > now`. If the
entry is fresh it is returned immediately; if expired (or absent) the live fetch
runs, the result is written back to disk, and the result is returned. The cache
is completely transparent to `server.py`.

PDF document text files (converted via `pymupdf4llm`) live alongside the cache; their TTL is tracked in a sidecar
`mcp/cache/pdf-index.json` file using the same envelope pattern.

### TTL table

| Content | TTL | Rationale |
|---------|-----|-----------|
| Policy listing (`/policy`) | 24 h | New policies added rarely |
| Policy detail (individual page) | 24 h | Policy text stable between campaigns |
| Policy PDF documents | 30 d | PDFs are essentially static once published |
| Tax-reset policy parameters | 24 h | Same as policy detail; refreshed automatically |
| News listing (`/news`) | 1 h | New articles published regularly |
| News article (individual) | 6 h | Published articles rarely change |
| Team listing (`/team`) | 12 h | Candidate list stable in campaign cycle |
| Team member profile | 12 h | Same |
| Events listing (`/events`) | 30 min | Events added/removed frequently |
| Party info (`/about`, `/party-information`) | 7 d | Governance docs very stable |

TTLs are constants in `repository.py` and can be tuned without touching server
logic. A `force_refresh: bool` input field on any tool can bypass the TTL for
a single call.

### Cache directory layout

```
mcp/cache/
├── policies/
│   ├── _index.json            # policy listing cache envelope
│   ├── tax-reset.json         # per-policy detail cache envelope
│   ├── healthy-oceans.json
│   └── ...
├── news/
│   ├── _index.json
│   └── {slug}.json
├── team/
│   ├── _index.json
│   └── {slug}.json
├── party-info/
│   ├── _index.json
│   └── {section}.json
├── events.json                # events listing cache envelope
├── pdf-index.json             # TTL tracker for PDF documents
└── pdf-docs/
    ├── tax-reset_policy-overview.md
    ├── tax-reset_addendum.md
    └── ...
```

---

## Data-source strategy

Every listing and detail fetch goes **live first, cache second** (the inverse of
the old design). The cache exists only to avoid hammering the website on repeated
identical calls within the TTL window.

| Operation | Behaviour |
|-----------|-----------|
| `list_*` | Fetch live page → parse → write cache. Return cache if within TTL. |
| `get_*` detail | Same: live → cache envelope per slug/section. |
| `get_upcoming_events` | Always fetches live; 30-min TTL (short, because events list changes). |
| `get_policy_document` | PDF is downloaded & converted once; re-fetched after 30-day TTL. |
| `tax_reset_calculator` | Loads tax-reset policy parameters from cache (24 h TTL on policy page). |
| `search` | Rebuilds a lightweight in-memory index from all **currently-cached** envelopes; does **not** trigger live fetches. Agents should call `list_*` first to warm the cache. |

Every result always includes:

- `url` — the canonical page URL on opportunity.org.nz.
- `fetched_at` — ISO-8601 timestamp of when the data was last retrieved.
- `cache_hit: bool` — whether the TTL cache was used for this response.

---

## Tool catalogue

| Tool | Input highlights | Live source |
|------|-----------------|-------------|
| `opportunity_list_policies` | `force_refresh` | `/policy` |
| `opportunity_get_policy` | `slug`, `force_refresh` | `/{slug}` |
| `opportunity_list_policy_documents` | `force_refresh` | derived from policy pages (PDF links) |
| `opportunity_get_policy_document` | `id`, `force_refresh` | Google Drive PDF → pymupdf4llm |
| `opportunity_list_news` | `force_refresh` | `/news` |
| `opportunity_get_news_article` | `slug`, `force_refresh` | individual article URL |
| `opportunity_list_team` | `force_refresh` | `/team` + `/meet-q` |
| `opportunity_get_team_member` | `slug`, `force_refresh` | `/candidate-{slug}` |
| `opportunity_list_party_info` | `force_refresh` | `/about`, `/party-information` |
| `opportunity_get_party_info` | `section`, `force_refresh` | individual section URL |
| `opportunity_get_upcoming_events` | `force_refresh` | `/events` |
| `opportunity_tax_reset_calculator` | `income`, `force_refresh` | tax-reset policy page (parameters) |
| `opportunity_search` | `query`, `types`, `limit` | in-memory over cached data |

Workflow pattern: **list/search → get**. Listings and search return slugs/ids and
URLs; the agent passes those to the matching `get_*` tool for full content.

---

## New tools in detail

### `opportunity_get_upcoming_events`

Fetches the live `/events` page and returns all upcoming events. Cached for 30
minutes (shortest TTL in the system — event listings change frequently).

Returns (JSON mode):

```json
{
  "url": "https://www.opportunity.org.nz/events",
  "fetched_at": "...",
  "cache_hit": false,
  "events": [
    {
      "title": "Candidate Meet & Greet — Wellington",
      "date": "2026-07-15",
      "time": "6:30 PM",
      "location": "Civic Square, Wellington",
      "url": "https://www.opportunity.org.nz/events/..."
    }
  ]
}
```

### `opportunity_tax_reset_calculator`

An interactive calculator that uses the Opportunity Party's Tax Reset policy
to show the financial impact on an individual given their income.

The tool:

1. Reads the tax-reset policy page (via TTL cache; 24 h TTL).
2. Extracts key parameters: flat tax rate, UBI/dividend amount, income thresholds,
   and any current figures cited in the policy.
3. Applies those parameters to the user-supplied income to produce a comparison
   of the current NZ tax system vs. the Tax Reset proposal.

Because the parameters come from the live policy page, any update to the policy
automatically flows through on the next cache refresh without touching the tool
code. The `force_refresh` flag forces an immediate re-fetch of the policy page.

Input:

```json
{
  "income": 75000,
  "force_refresh": false
}
```

Returns (JSON mode):

```json
{
  "policy_url": "https://www.opportunity.org.nz/tax-reset",
  "policy_fetched_at": "...",
  "cache_hit": true,
  "parameters": {
    "flat_tax_rate": 0.33,
    "universal_basic_dividend": 14000,
    "description": "33% flat rate on all income above $0; $14,000/year Universal Basic Dividend paid to every adult"
  },
  "income": 75000,
  "current_system": {
    "tax": 17020,
    "net": 57980
  },
  "tax_reset": {
    "tax": 24750,
    "dividend": 14000,
    "net": 64250
  },
  "difference": {
    "net_change": 6270,
    "better_off": true,
    "note": "Net position includes the Universal Basic Dividend"
  }
}
```

Parameters default to values parsed from the policy page. If parsing fails (e.g.
the page changed substantially), the tool returns an error with the policy URL
so the agent can read the page directly.

---

## PDF document management

Policy pages link to PDFs hosted on Google Drive. The server manages these
through `mcp/cache/pdf-index.json`, which tracks each document's:

```json
{
  "id": "tax-reset_policy-overview",
  "policy_slug": "tax-reset",
  "source_url": "https://drive.google.com/...",
  "filename": "tax-reset_policy-overview.md",
  "downloaded_at": "2026-06-01T10:00:00Z",
  "ttl_seconds": 2592000,
  "expires_at": "2026-07-01T10:00:00Z"
}
```

On `get_policy_document`:

1. Check `pdf-index.json`. If the entry exists and `expires_at > now`, read and
   return `mcp/cache/pdf-docs/{filename}`.
2. Otherwise: download the PDF from Google Drive (reusing `pdf_download` helpers),
   convert with `pymupdf4llm`, write markdown to `mcp/cache/pdf-docs/`, update the index, return content.

The listing tool (`list_policy_documents`) derives its list from two sources:

- Policy detail pages (fetched with their normal TTL) which contain Google Drive links.
- The existing `pdf-index.json` entries (for documents already cached).

This means the listing is always live-aware: new PDFs linked from policy pages
appear in the listing on the next policy detail fetch.

---

## Search design

`opportunity_search` operates over whichever data is **currently in the TTL
cache** — it does not trigger any live fetches itself. This is intentional:

- Calling a list tool first warms the cache for that category.
- Agents searching without a prior list call will search only previously warmed
  data (the tool description explains this).
- Results carry `type`, `id`, and `url` so the agent can call the appropriate
  `get_*` tool, which will do a live fetch if the cache is cold or expired.

Scoring: term frequency, title matches weighted 5×, body matches 1×.

---

## Key design decisions

**No stale data.** The old design used `data/*/index.json` (populated by a
separate scrape job) as the primary source for listings. This meant the MCP
server could return content that was days or weeks old without signalling it.
Under the new design, every listing and detail fetch is live unless the TTL
cache has a fresh entry. The cache is owned by and scoped to the MCP server;
the scraper's `data/` directory is no longer used.

**TTL over invalidation.** Content types with different stability get different
TTLs rather than any active invalidation mechanism. This is appropriate for a
read-only server against a site that updates infrequently.

**`force_refresh` on every tool.** Any tool accepts `force_refresh: bool =
false`. When set, the repository skips the cache read, fetches live, and writes
a fresh cache entry. This lets agents or users get immediate freshness without
restarting the server.

**Policy parameters extracted programmatically.** The `tax_reset_calculator` tool
parses the tax-reset policy page rather than hard-coding numbers. This keeps the
calculator in sync with the policy text automatically. The parser should target
well-known phrases in the page (e.g. "33%", "Universal Basic Dividend",
"$14,000") and fall back gracefully when parsing fails.

**Folder named `mcp/` vs. the `mcp` SDK.** `server.py` imports
`from mcp.server.fastmcp import FastMCP` *before* `repository.py` inserts the
project root onto `sys.path`. Importing the SDK first binds the top-level `mcp`
module in `sys.modules`, preventing the local folder from shadowing the SDK.

**Dual output format.** Markdown for human-readable agent reasoning; JSON for
programmatic extraction. Listings stay concise (summaries + URLs only) to
protect context; detail tools return full content.

---

## Response shape (all tools)

Every tool response includes at minimum:

| Field | Type | Description |
|-------|------|-------------|
| `url` | `str` | Canonical page URL on opportunity.org.nz |
| `fetched_at` | `str` | ISO-8601 of last live fetch |
| `cache_hit` | `bool` | `true` if TTL cache was used |

Listing responses also include a `count` field and the relevant array (`policies`,
`news`, `team`, `events`, etc.).

Detail responses include the full `content` (markdown) and `documents` (list of
PDF/Drive URLs when applicable).

---

## Testing

- `uv run python mcp/server.py` — starts the stdio server.
- `npx @modelcontextprotocol/inspector uv run python mcp/server.py` — interactive.
- [`mcp/evaluation.xml`](../mcp/evaluation.xml) — verifiable Q&A pairs covering
  policies, documents, news, events, and the tax calculator.

---

## Future extensions

- Add MCP **resources** (e.g. `policy://{slug}`) alongside tools.
- Pull `sitemap.xml` to auto-discover new pages and policy slugs.
- Expose a `cache_status` tool that reports TTL state per content type.
- Add `/get-involved` scraping (volunteer/join/donate context).
