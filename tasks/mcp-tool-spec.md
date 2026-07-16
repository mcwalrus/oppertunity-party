# MCP Tool Spec — Opportunity Party Content Server

> **Status:** Draft. All implementation tickets under `oppertunity-party-owp.*`
> reference this file. Update this file before changing tool/resource shapes
> — the LLM-facing contract drifts silently otherwise.

## Server identity

| Field     | Value                                                                |
| --------- | -------------------------------------------------------------------- |
| Name      | `opportunity_mcp` (per `{service}_mcp` convention from mcp-builder)  |
| Transport | stdio (local-only, single-tenant)                                    |
| Source    | `data/clean/` (read-only, refreshed per request)                     |

## Content types

Six types, all items on disk:

```
data/clean/<content_type>/<slug>/<slug>.md     # YAML frontmatter + body
data/clean/<content_type>/<slug>/meta.json     # provenance + type-specific fields
```

| content_type        | count | fields worth noting                                          |
| ------------------- | ----- | ------------------------------------------------------------ |
| `blog-post`         | 27    | `date`, `author`, `excerpt`                                  |
| `event`             | 22    | `date`, `time`, `location`, `venue`, `address`, `registration_url` |
| `party-information` | 5     | `title` only                                                  |
| `pdf-document`      | 8     | `policy_slug` (link back to parent policy)                   |
| `policy`            | 16    | `summary`, `pdf_urls[]`, `tags[]`                            |
| `team-member`       | 44    | `name`, `role`, `electorate`                                 |

Provenance is identical across all types: `slug`, `content_type`, `source_id`,
`source_type`, `source_url`, `ingested_at`, `cleaned_at`, `title`.

## Surface

### Tools (6)

Four **domain find tools** give every content type a discoverable entry point
with structured filters; `opportunity_get_item` is the universal fetcher;
`opportunity_get_status` reports dataset freshness.

| Tool                             | Purpose                                                  |
| -------------------------------- | -------------------------------------------------------- |
| `opportunity_find_events`        | Find events with date, location, venue, query filters    |
| `opportunity_find_members`       | Find team members with role, electorate, query filters   |
| `opportunity_find_policies`      | Find policies with tags, has_pdf, query filters          |
| `opportunity_find_blog_posts`    | Find blog posts with date and query filters              |
| `opportunity_get_item`           | Fetch one item by content_type + slug                    |
| `opportunity_get_status`         | Dataset staleness/versioning summary                     |

### Resources

URI template: `opportunity://{content_type}/{slug}`

Returns the full markdown + meta for the item. Mirrors `opportunity_get_item`
so an LLM browsing the resource tree gets the same shape as a tool call.

### Prompts

None in v1.

## Tool signatures

All four `find_*` tools share the same response envelope (count / offset /
has_more / next_offset) and the same item shape per content type — listed
under each tool below. Pagination is consistent: `limit` default 20, `offset`
default 0.

### `opportunity_find_events`

```python
class FindEventsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: Optional[str] = Field(
        default=None, min_length=1, max_length=200,
        description="Optional substring match (case-insensitive) on title + body.",
    )
    date_from: Optional[str] = Field(
        default=None,
        description="ISO 8601 date (e.g. '2026-03-15'). Inclusive lower bound on event.date.",
    )
    date_to: Optional[str] = Field(
        default=None,
        description="ISO 8601 date (e.g. '2026-04-15'). Inclusive upper bound on event.date.",
    )
    location: Optional[str] = Field(
        default=None, min_length=1, max_length=200,
        description="Substring match (case-insensitive) on event.location AND event.address.",
    )
    venue: Optional[str] = Field(
        default=None, min_length=1, max_length=200,
        description="Substring match (case-insensitive) on event.venue.",
    )
    include_past: bool = Field(
        default=False,
        description="Include events with date < now. Default false (upcoming only).",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

Response (JSON string):

```json
{
  "total": 8,
  "count": 8,
  "offset": 0,
  "items": [
    {
      "slug": "town-hall-auckland",
      "content_type": "event",
      "title": "Town Hall — Auckland",
      "date": "2026-03-15",
      "time": "19:00",
      "location": "Auckland",
      "venue": "Auckland Town Hall",
      "address": "Queen Street, Auckland CBD",
      "registration_url": "https://...",
      "source_url": "https://www.opportunity.org.nz/events/town-hall-auckland"
    }
  ],
  "has_more": false,
  "next_offset": null
}
```

Sort: `date` asc (soonest upcoming first). Events with a null/unparseable
`date` are excluded unless `include_past=true` AND a date filter is supplied.

### `opportunity_find_members`

```python
class FindMembersInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: Optional[str] = Field(
        default=None, min_length=1, max_length=200,
        description="Optional substring match (case-insensitive) on title + body (typically matches name).",
    )
    role: Optional[str] = Field(
        default=None, min_length=1, max_length=200,
        description="Exact match (case-insensitive) on member.role (e.g. 'Board', 'Candidate').",
    )
    electorate: Optional[str] = Field(
        default=None, min_length=1, max_length=200,
        description="Exact match (case-insensitive) on member.electorate (e.g. 'Auckland Central').",
    )
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

Response (JSON string):

```json
{
  "total": 44,
  "count": 44,
  "offset": 0,
  "items": [
    {
      "slug": "jane-doe",
      "content_type": "team-member",
      "title": "Jane Doe",
      "name": "Jane Doe",
      "role": "Board",
      "electorate": "Auckland Central",
      "source_url": "https://www.opportunity.org.nz/team/jane-doe"
    }
  ],
  "has_more": false,
  "next_offset": null
}
```

Sort: `role` asc, then `name` asc. `role` and `electorate` are exact-match
because the values are short, controlled vocabularies (electorates overlap:
"Auckland" vs "Auckland Central" vs "Auckland East") — substring match would
return noise.

### `opportunity_find_policies`

```python
class FindPoliciesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: Optional[str] = Field(
        default=None, min_length=1, max_length=200,
        description="Optional substring match (case-insensitive) on title + body.",
    )
    tags: Optional[list[str]] = Field(
        default=None,
        description="Match policies whose tags[] contains ALL of these values (AND, case-insensitive exact match per tag).",
    )
    has_pdf: Optional[bool] = Field(
        default=None,
        description="If true, only policies with at least one linked pdf-document. If false, only policies without. Default: no filter.",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

Response (JSON string):

```json
{
  "total": 3,
  "count": 3,
  "offset": 0,
  "items": [
    {
      "slug": "abundant-energy",
      "content_type": "policy",
      "title": "Abundant Energy",
      "summary": "...",
      "tags": ["energy", "environment"],
      "pdf_slugs": ["abundant-energy-pdf"],
      "source_url": "https://www.opportunity.org.nz/abundant-energy"
    }
  ],
  "has_more": false,
  "next_offset": null
}
```

Sort: `title` asc. `pdf_slugs` is always populated (empty list when no PDFs)
so callers can render the linked-PDFs UI without a second round trip to
`opportunity_get_item`.

### `opportunity_find_blog_posts`

```python
class FindBlogPostsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: Optional[str] = Field(
        default=None, min_length=1, max_length=200,
        description="Optional substring match (case-insensitive) on title + body.",
    )
    date_from: Optional[str] = Field(
        default=None,
        description="ISO 8601 date (e.g. '2026-01-15'). Inclusive lower bound on post.date.",
    )
    date_to: Optional[str] = Field(
        default=None,
        description="ISO 8601 date (e.g. '2026-04-15'). Inclusive upper bound on post.date.",
    )
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

Response (JSON string):

```json
{
  "total": 27,
  "count": 20,
  "offset": 0,
  "items": [
    {
      "slug": "why-we-stand-for-housing",
      "content_type": "blog-post",
      "title": "Why we stand for housing",
      "date": "2026-03-10",
      "author": "Jane Doe",
      "excerpt": "...",
      "source_url": "https://www.opportunity.org.nz/blog/why-we-stand-for-housing"
    }
  ],
  "has_more": true,
  "next_offset": 20
}
```

Sort: `date` desc (most recent first).

### `opportunity_get_item`

```python
class GetItemInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    content_type: Literal[
        "blog-post", "event", "party-information",
        "pdf-document", "policy", "team-member",
    ] = Field(..., description="Content type of the item to fetch.")
    slug: str = Field(
        ..., min_length=1, max_length=200,
        description="Item slug (e.g. 'abundant-energy').",
    )
```

Response (JSON string):

```json
{
  "meta": { "slug": "...", "content_type": "...", "title": "...", "...": "..." },
  "body": "... markdown body with YAML frontmatter stripped ..."
}
```

### `opportunity_get_status`

```python
class GetStatusInput(BaseModel):
    pass
```

Response (JSON string):

```json
{
  "total_items": 122,
  "last_cleaned_at": "2026-07-16T02:06:13.010616+00:00",
  "per_content_type": {
    "blog-post": 27,
    "event": 22,
    "party-information": 5,
    "pdf-document": 8,
    "policy": 16,
    "team-member": 44
  },
  "freshness": "fresh"
}
```

`freshness` heuristic: `fresh` if `last_cleaned_at` is within the last 7 days,
`stale` otherwise. Surfaced as a hint, not enforced — the server never refuses
a request based on staleness.

## Annotations

| Tool                          | readOnly | destructive | idempotent | openWorld |
| ----------------------------- | -------- | ----------- | ---------- | --------- |
| `opportunity_find_events`     | true     | false       | true       | false     |
| `opportunity_find_members`    | true     | false       | true       | false     |
| `opportunity_find_policies`   | true     | false       | true       | false     |
| `opportunity_find_blog_posts` | true     | false       | true       | false     |
| `opportunity_get_item`        | true     | false       | true       | false     |
| `opportunity_get_status`      | true     | false       | true       | false     |

All tools are read-only over a gitignored dataset; nothing leaves the host.

## Errors

Errors are JSON-shaped strings (LLMs parse them), never raised exceptions
across the MCP boundary.

| Condition                | Shape                                                                |
| ------------------------ | -------------------------------------------------------------------- |
| Slug not found           | `{"error": "not_found", "content_type": "...", "slug": "..."}`       |
| Invalid content_type     | `{"error": "invalid_content_type", "value": "..."}`                   |
| `data/clean/` missing    | `{"error": "data_unavailable", "path": "..."}`                       |
| Internal error           | `{"error": "internal", "type": "...", "message": "..."}`             |

Pydantic `extra="forbid"` plus min/max length constraints on inputs catches
malformed input before any disk I/O.

## Resource templates

```python
@mcp.resource("opportunity://{content_type}/{slug}")
async def opportunity_item(content_type: str, slug: str) -> str:
    # Same payload as opportunity_get_item, JSON string
    ...
```

One resource template covers all six content types. The server does not list
individual items as resources (122 static URIs would flood the LLM context) —
LLMs discover items via the four `opportunity_find_*` tools, then fetch a
specific item by URI or via `opportunity_get_item`.

## Out of scope (this surface)

- Prompts (deferred — see epic)
- Write/mutation tools
- HTTP/SSE transport
- Authentication / multi-tenant
- Reading from `site/dist/` (server reads `data/clean/` only)
- Cross-content free-text search (e.g. "everything about housing" returning
  policies + blog posts + events in one call) — the four `find_*` tools cover
  the structured case; a free-text cross-type search is a v2 problem if the
  voter use case actually needs it
- Member → policy authorship inference — `team-member` data doesn't carry
  authored policies; inferring it is out of scope
- Geo-distance filtering on events — text match on `location`/`address` covers
  the voter case; lat/lon isn't in the data
- BM25 / field-boost ranking — 122 items doesn't need it; the `query` parameter
  is substring match only