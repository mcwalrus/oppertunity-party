# Opportunity Party MCP Server

A **read-only** [Model Context Protocol](https://modelcontextprotocol.io) server
that exposes the New Zealand **Opportunity Party** (opportunity.org.nz) public
information — policies, detailed policy documents, candidates/team, news & media
releases, upcoming events, party governance, and an interactive tax calculator —
as agent-friendly tools.

All content is **fetched live from the website**. A TTL-managed on-disk cache
under `mcp/cache/` avoids redundant requests while keeping data current. Every
tool result includes the canonical website URL so agents and users can follow up
directly on the live site.

## Tools

| Tool | Purpose | TTL |
|------|---------|-----|
| `opportunity_list_policies` | List all policy areas with summaries + URLs | 24 h |
| `opportunity_get_policy` | Full content of one policy (live, TTL cached) | 24 h |
| `opportunity_list_policy_documents` | List detailed PDF-derived policy papers | derived |
| `opportunity_get_policy_document` | Full text of one policy PDF (pdftotext) | 30 d |
| `opportunity_list_news` | List news articles / media releases | 1 h |
| `opportunity_get_news_article` | Full text of one news article | 6 h |
| `opportunity_list_team` | List team members & election candidates | 12 h |
| `opportunity_get_team_member` | Full candidate/team profile | 12 h |
| `opportunity_list_party_info` | List party-information sections | 7 d |
| `opportunity_get_party_info` | Full party-information section content | 7 d |
| `opportunity_get_upcoming_events` | Live upcoming events listing | 30 min |
| `opportunity_tax_reset_calculator` | Tax impact calculator using live policy parameters | 24 h (params) |
| `opportunity_search` | Full-text search across cached content | — |

Every tool is `readOnlyHint: true`, supports `response_format: "markdown" | "json"`,
and accepts `force_refresh: bool` to bypass the TTL for a single call.

## Design

See [`docs/mcp-design.md`](../docs/mcp-design.md) for the full architecture,
TTL strategy, PDF management, and interactive tool design.

## Running

```bash
# from the project root
uv run python mcp/server.py
```

The server communicates over **stdio**.

### Register with Claude Code

```bash
claude mcp add opportunity-party -- uv run python mcp/server.py
```

Or add to your MCP client config:

```json
{
  "mcpServers": {
    "opportunity-party": {
      "command": "uv",
      "args": ["run", "python", "mcp/server.py"],
      "cwd": "/Users/max.collier/Projects/Max/vault/oppertunity-party"
    }
  }
}
```

### Inspect

```bash
npx @modelcontextprotocol/inspector uv run python mcp/server.py
```

## Cache

The server manages its own cache at `mcp/cache/`. It is safe to delete this
directory at any time — the server will re-fetch everything live on the next
request. The scraper's `data/` directory is **not** used by the MCP server.

```
mcp/cache/
├── policies/          # per-policy JSON envelopes (24 h TTL)
├── news/              # per-article JSON envelopes (6 h TTL)
├── team/              # per-member JSON envelopes (12 h TTL)
├── party-info/        # per-section JSON envelopes (7 d TTL)
├── events.json        # events listing (30 min TTL)
├── pdf-index.json     # PDF document TTL tracker
└── pdf-docs/          # pdftotext output (30 d TTL)
```

## Files

```
mcp/
├── server.py        # FastMCP server: tool definitions, input models, formatting
├── repository.py    # live-first data access; TTL cache; PDF management
├── evaluation.xml   # evaluation Q&A pairs
└── README.md
```
