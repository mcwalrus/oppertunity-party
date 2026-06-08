# Opportunity Party MCP Server — Design

A read-only [Model Context Protocol](https://modelcontextprotocol.io) server that
exposes the New Zealand Opportunity Party's public information to LLM agents.
It lives under [`mcp/`](../mcp) and **reuses the existing `scraper` package**
rather than duplicating any HTTP or extraction logic.

## Goals & constraints

- **Read-only.** No tool mutates the website or the local cache. Every tool is
  annotated `readOnlyHint: true`, `destructiveHint: false`, `idempotentHint: true`.
- **Collect from the website where possible.** Detail lookups fetch the live
  page first (current content), and gracefully fall back to cache on any failure.
- **Reuse, don't duplicate.** The MCP layer imports the scraper's `curl` client,
  BeautifulSoup extractors, and slug helpers — one source of truth.
- **Agent-friendly.** Clear `opportunity_*` tool names, concise summaries in
  listings, full content in detail views, and a cross-content search to locate
  records before fetching them.

## Architecture

```
                         ┌──────────────────────────────┐
   MCP client (Claude)   │        mcp/server.py         │
   ───────────────────►  │  FastMCP("opportunity_party_mcp")
                         │  • Pydantic input models      │
                         │  • 11 read-only tools         │
                         │  • markdown / json formatting │
                         └──────────────┬───────────────┘
                                        │ imports
                         ┌──────────────▼───────────────┐
                         │       mcp/repository.py       │
                         │  read-only data access layer  │
                         │  • live fetch + cache fallback │
                         │  • cross-content search        │
                         └───────┬───────────────┬───────┘
                                 │ reuses        │ reads
                   ┌─────────────▼──────┐  ┌─────▼─────────────┐
                   │  scraper/ package  │  │   data/ cache     │
                   │  client, policies, │  │  index.json per   │
                   │  news, team, …     │  │  category + PDFs  │
                   └─────────┬──────────┘  └───────────────────┘
                             │ curl
                   ┌─────────▼──────────┐
                   │ opportunity.org.nz │
                   └────────────────────┘
```

### Two layers

1. **`mcp/repository.py` — data access.** The bridge to the `scraper` package.
   It imports and reuses:
   - `scraper.client`: `BASE_URL`, `DATA_DIR`, `fetch_page` (the `curl` client).
   - `scraper.policies`: `POLICY_SLUGS`, `_extract_title`, `_extract_pdf_links`,
     `_extract_markdown`.
   - `scraper.news` / `scraper.team` / `scraper.party_info`: content extractors
     and the `_title_to_slug` / `_name_to_slug` slug helpers.

   It exposes pure read functions (`load_*`, `get_*`, `search`) returning plain
   dicts, plus a `RepositoryError` for not-found cases with actionable messages
   (the error lists valid slugs).

2. **`mcp/server.py` — MCP surface.** FastMCP tools wrapping the repository,
   with Pydantic input validation, dual `markdown`/`json` output, and shared
   formatting helpers (`_listing_md`, `_detail_md`, `_json`).

## Data-source strategy

Each lookup has two backing sources and a clear policy for which to use:

| Operation | Primary source | Fallback | Rationale |
|-----------|----------------|----------|-----------|
| `list_*` / `search` | local cache (`data/*/index.json`) | known slugs | Fast, stable, no N live fetches |
| `get_policy` | **live website** | cache | Policies change; freshness matters |
| `get_news_article` | cache, then live refresh | cache | News URLs are idiosyncratic; cache is reliable |
| `get_team_member` | cache, then live refresh | cache | Same |
| `get_party_info` | cache, then live refresh | cache | Same |
| `get_policy_document` | cache (PDF-derived markdown) | — | Documents only exist as converted PDFs |

Every detail record reports its `source: "live" | "cache"` so the agent knows
how fresh the answer is. `prefer_live` is a per-call flag (default `true`) that
can force cache-only reads for speed or offline use.

## Tool catalogue

| Tool | Kind | Source behaviour |
|------|------|------------------|
| `opportunity_list_policies` | list | cache → known slugs |
| `opportunity_get_policy` | detail | live → cache |
| `opportunity_list_policy_documents` | list | cache (PDF index) |
| `opportunity_get_policy_document` | detail | cache |
| `opportunity_list_news` | list | cache |
| `opportunity_get_news_article` | detail | cache → live refresh |
| `opportunity_list_team` | list | cache |
| `opportunity_get_team_member` | detail | cache → live refresh |
| `opportunity_list_party_info` | list | cache |
| `opportunity_get_party_info` | detail | cache → live refresh |
| `opportunity_search` | search | cache (all categories) |

Workflow pattern: **list/search → get**. Listings and search return slugs/ids;
the agent passes those to the matching `get_*` tool for full content.

## Search design

`opportunity_search` flattens all cached records (policies, news, team, party
info) into a uniform shape and scores by term frequency — title matches weighted
5×, body matches 1×. Results carry `type` + `id` so the agent can fetch the full
record, plus a context `snippet` around the first match. Optional `types` filter
restricts the scope.

## Key design decisions

- **Folder named `mcp/` vs. the `mcp` SDK.** `server.py` imports
  `from mcp.server.fastmcp import FastMCP` *before* `repository.py` inserts the
  project root onto `sys.path`. Importing the SDK first binds the top-level
  `mcp` module in `sys.modules`, so the local folder never shadows the SDK.
- **Defensive PDF-document handling.** The on-disk `pdf-index.json` can contain
  messy directory names and absolute paths. The repository keys documents by a
  stable id derived from the clean `policy` + `document_type` fields, resolves
  each markdown path defensively (absolute or relative), de-duplicates, and skips
  placeholder/`unknown` rows.
- **Dual output format.** Markdown for human-readable agent reasoning; JSON for
  programmatic extraction. Listings stay concise (summaries only) to protect
  context; detail tools return full content.

## Testing

- `uv run python mcp/server.py` — starts the stdio server.
- `npx @modelcontextprotocol/inspector uv run python mcp/server.py` — interactive.
- [`mcp/evaluation.xml`](../mcp/evaluation.xml) — 10 verifiable Q&A pairs covering
  policies, documents, news, and search.

## Future extensions

- Add a `refresh`/re-scrape tool (would make it read-write — out of current scope).
- Expose MCP **resources** (e.g. `policy://{slug}`) alongside tools.
- Pull `sitemap.xml` / `robots.txt` to auto-discover new pages.
- Add events (`/events`) once the scraper covers them.
```
