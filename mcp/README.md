# Opportunity Party MCP Server

A **read-only** [Model Context Protocol](https://modelcontextprotocol.io) server
that exposes the New Zealand **Opportunity Party** (opportunity.org.nz) public
information — policies, detailed policy documents, candidates/team, news & media
releases, and party governance — as agent-friendly tools.

Information is collected **live from the website where possible** (reusing the
project's `scraper` package) and falls back to the locally cached `data/`
directory for fast listing, full-text search, and offline resilience.

## Tools

| Tool | Purpose |
|------|---------|
| `opportunity_list_policies` | List all policy areas with summaries |
| `opportunity_get_policy` | Full content of one policy (live, cache fallback) |
| `opportunity_list_policy_documents` | List detailed PDF-derived policy papers |
| `opportunity_get_policy_document` | Full text of one detailed policy document |
| `opportunity_list_news` | List news articles / media releases |
| `opportunity_get_news_article` | Full text of one news article |
| `opportunity_list_team` | List team members & election candidates |
| `opportunity_get_team_member` | Full candidate/team profile |
| `opportunity_list_party_info` | List party-information sections |
| `opportunity_get_party_info` | Full party-information section content |
| `opportunity_search` | Full-text search across all content |

Every tool is `readOnlyHint: true` and supports `response_format: "markdown" | "json"`.

## Design

See [`docs/mcp-design.md`](../docs/mcp-design.md) for the full architecture,
data-source strategy, and code-reuse rationale.

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

## Code reuse

This server does **not** duplicate scraping logic. `mcp/repository.py` imports
the existing `scraper` package — its `curl`-based HTTP client, BeautifulSoup
content extractors, and slug helpers — so the MCP server and the scraper share a
single source of truth. The MCP layer adds only read-only data access (live
fetch + cache fallback), search, and response formatting.

## Files

```
mcp/
├── server.py        # FastMCP server: tool definitions, input models, formatting
├── repository.py    # read-only data access; reuses scraper/, live + cache
├── evaluation.xml   # 10 evaluation Q&A pairs
└── README.md
```
