#!/usr/bin/env python3
"""Read-only MCP server for Opportunity Party (opportunity.org.nz) information.

Exposes the New Zealand Opportunity Party's public information — policies,
policy documents, candidates/team, news & media releases, and party
governance details — as a set of read-only MCP tools.

Information is collected live from the website where possible (reusing the
project's ``scraper`` package) and falls back to the locally cached
``data/`` directory for fast listing, search, and offline resilience.

Run locally over stdio:

    python mcp/server.py

All tools are strictly read-only; nothing here mutates the website or disk.
"""

# IMPORTANT: import the MCP SDK *before* repository.py adds the project root to
# sys.path. The project's tool folder is named ``mcp/`` and importing the SDK
# first binds the top-level ``mcp`` module to the installed SDK in sys.modules,
# preventing the local folder from shadowing it.
from mcp.server.fastmcp import FastMCP

from enum import Enum
from typing import Optional
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator

import repository as repo

mcp = FastMCP("opportunity_party_mcp")


# --------------------------------------------------------------------------
# Shared input models & helpers
# --------------------------------------------------------------------------
class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


class ContentType(str, Enum):
    """Categories of Opportunity Party content available for search."""

    POLICY = "policy"
    NEWS = "news"
    TEAM = "team"
    PARTY_INFO = "party-info"


class _Base(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )


class EmptyInput(_Base):
    """No parameters; optional output format."""

    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (human-readable) or 'json' (structured).",
    )


class SlugInput(_Base):
    """Look up a single record by its slug/id."""

    slug: str = Field(
        ...,
        description="The slug/id of the record (e.g. 'tax-reset', 'q-needs-you').",
        min_length=1,
        max_length=120,
    )
    prefer_live: bool = Field(
        default=True,
        description="Fetch a fresh copy from the website first, falling back to cache.",
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' or 'json'.",
    )


class SectionInput(_Base):
    """Look up a party-information section by name."""

    section: str = Field(
        ...,
        description="Section name, e.g. 'about' or 'party-information'.",
        min_length=1,
        max_length=80,
    )
    prefer_live: bool = Field(default=True, description="Prefer a live fetch over cache.")
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'."
    )


class SearchInput(_Base):
    """Full-text search across all Opportunity Party content."""

    query: str = Field(
        ...,
        description="Search terms, e.g. 'capital gains tax' or 'fisheries'.",
        min_length=2,
        max_length=200,
    )
    types: Optional[list[ContentType]] = Field(
        default=None,
        description="Restrict to these content types; omit to search everything.",
        max_length=4,
    )
    limit: int = Field(default=20, description="Maximum results to return.", ge=1, le=50)
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN, description="Output format: 'markdown' or 'json'."
    )

    @field_validator("query")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("query cannot be empty")
        return v


_READONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,  # reaches out to the live website
}


def _json(payload) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _listing_md(title: str, items: list[dict], fields: list[tuple[str, str]]) -> str:
    """Render a list of records as a compact markdown document."""
    lines = [f"# {title}", "", f"{len(items)} result(s).", ""]
    for it in items:
        head = it.get("title") or it.get("name") or it.get("section") or it.get("id")
        lines.append(f"## {head}")
        for key, label in fields:
            val = it.get(key)
            if val:
                lines.append(f"- **{label}**: {val}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _detail_md(record: dict, header_fields: list[tuple[str, str]]) -> str:
    """Render a single detail record (with markdown ``content``) as markdown."""
    head = (
        record.get("title")
        or record.get("name")
        or record.get("section", "").replace("-", " ").title()
    )
    lines = [f"# {head}", ""]
    for key, label in header_fields:
        val = record.get(key)
        if val:
            lines.append(f"> **{label}**: {val}")
    lines.append("")
    lines.append(record.get("content", "").strip())
    return "\n".join(lines).strip() + "\n"


# --------------------------------------------------------------------------
# Policies
# --------------------------------------------------------------------------
@mcp.tool(name="opportunity_list_policies", annotations={"title": "List Policy Areas", **_READONLY})
async def opportunity_list_policies(params: EmptyInput) -> str:
    """List every Opportunity Party policy area with a short summary.

    Use this first to discover policy slugs before calling
    ``opportunity_get_policy``.

    Returns (JSON mode) a list of objects:
        {
          "slug": str,           # e.g. "tax-reset"
          "title": str,          # e.g. "Tax Reset"
          "url": str,            # canonical page URL
          "has_documents": bool, # whether downloadable PDF documents exist
          "summary": str         # ~280-char plain-text preview
        }
    """
    items = repo.load_policies()
    if params.response_format == ResponseFormat.JSON:
        return _json({"count": len(items), "policies": items})
    return _listing_md(
        "Opportunity Party Policies",
        items,
        [("slug", "Slug"), ("url", "URL"), ("has_documents", "Has documents"), ("summary", "Summary")],
    )


@mcp.tool(name="opportunity_get_policy", annotations={"title": "Get Policy", **_READONLY})
async def opportunity_get_policy(params: SlugInput) -> str:
    """Get the full content of a single policy by slug.

    Fetches the live policy page where possible (reusing the scraper's
    extraction logic) and falls back to the local cache. Discover valid slugs
    with ``opportunity_list_policies``.

    Returns (JSON mode):
        {
          "slug": str, "title": str, "url": str,
          "content": str,            # full policy text as markdown
          "documents": [str],        # PDF / Google Drive download links
          "source": "live" | "cache"
        }
    """
    try:
        record = repo.get_policy(params.slug, prefer_live=params.prefer_live)
    except repo.RepositoryError as e:
        return f"Error: {e}"
    if params.response_format == ResponseFormat.JSON:
        return _json(record)
    docs = record.get("documents", [])
    md = _detail_md(record, [("url", "URL"), ("source", "Source")])
    if docs:
        md += "\n## Downloadable documents\n" + "".join(f"- {d}\n" for d in docs)
    return md


@mcp.tool(
    name="opportunity_list_policy_documents",
    annotations={"title": "List Policy Documents", **_READONLY},
)
async def opportunity_list_policy_documents(params: EmptyInput) -> str:
    """List detailed policy documents (official PDFs converted to markdown).

    These are the richer, primary-source policy papers (overviews, addenda,
    transition plans) behind the summary policy pages.

    Returns (JSON mode) a list of:
        {
          "id": str,             # e.g. "tax-reset_policy-overview"
          "title": str, "policy": str,
          "date": str,           # e.g. "February 2026"
          "document_type": str,  # e.g. "Policy Overview"
          "source_file": str
        }
    """
    items = repo.load_policy_documents()
    if params.response_format == ResponseFormat.JSON:
        return _json({"count": len(items), "documents": items})
    return _listing_md(
        "Opportunity Party Policy Documents",
        [{**d, "title": d["title"]} for d in items],
        [("id", "ID"), ("document_type", "Type"), ("date", "Date"), ("source_file", "Source PDF")],
    )


@mcp.tool(
    name="opportunity_get_policy_document",
    annotations={"title": "Get Policy Document", **_READONLY},
)
async def opportunity_get_policy_document(params: SlugInput) -> str:
    """Get the full text of a detailed policy document by id.

    Discover ids with ``opportunity_list_policy_documents``. These documents
    are converted from the party's official PDFs and contain the most detailed
    policy content available.

    Returns (JSON mode):
        {
          "id": str, "title": str, "policy": str, "date": str,
          "document_type": str, "source_file": str,
          "content": str,   # full document as markdown
          "source": "cache"
        }
    """
    try:
        record = repo.get_policy_document(params.slug)
    except repo.RepositoryError as e:
        return f"Error: {e}"
    if params.response_format == ResponseFormat.JSON:
        return _json(record)
    return _detail_md(
        record, [("policy", "Policy"), ("document_type", "Type"), ("date", "Date")]
    )


# --------------------------------------------------------------------------
# News
# --------------------------------------------------------------------------
@mcp.tool(name="opportunity_list_news", annotations={"title": "List News", **_READONLY})
async def opportunity_list_news(params: EmptyInput) -> str:
    """List Opportunity Party news articles and media releases.

    Returns (JSON mode) a list of:
        {"slug": str, "title": str, "url": str, "date": str, "summary": str}
    """
    items = repo.load_news()
    if params.response_format == ResponseFormat.JSON:
        return _json({"count": len(items), "news": items})
    return _listing_md(
        "Opportunity Party News & Media Releases",
        items,
        [("slug", "Slug"), ("date", "Date"), ("url", "URL"), ("summary", "Summary")],
    )


@mcp.tool(name="opportunity_get_news_article", annotations={"title": "Get News Article", **_READONLY})
async def opportunity_get_news_article(params: SlugInput) -> str:
    """Get the full text of a news article / media release by slug.

    Discover slugs with ``opportunity_list_news``.

    Returns (JSON mode):
        {"slug": str, "title": str, "url": str, "date": str,
         "content": str, "source": "live" | "cache"}
    """
    try:
        record = repo.get_news_article(params.slug, prefer_live=params.prefer_live)
    except repo.RepositoryError as e:
        return f"Error: {e}"
    if params.response_format == ResponseFormat.JSON:
        return _json(record)
    return _detail_md(record, [("date", "Date"), ("url", "URL"), ("source", "Source")])


# --------------------------------------------------------------------------
# Team / candidates
# --------------------------------------------------------------------------
@mcp.tool(name="opportunity_list_team", annotations={"title": "List Team & Candidates", **_READONLY})
async def opportunity_list_team(params: EmptyInput) -> str:
    """List Opportunity Party team members and election candidates.

    Returns (JSON mode) a list of:
        {"slug": str, "name": str, "role": str, "url": str}
    """
    items = repo.load_team()
    if params.response_format == ResponseFormat.JSON:
        return _json({"count": len(items), "team": items})
    return _listing_md(
        "Opportunity Party Team & Candidates",
        items,
        [("slug", "Slug"), ("role", "Role"), ("url", "URL")],
    )


@mcp.tool(name="opportunity_get_team_member", annotations={"title": "Get Team Member", **_READONLY})
async def opportunity_get_team_member(params: SlugInput) -> str:
    """Get a full team-member / candidate profile by slug.

    Discover slugs with ``opportunity_list_team``.

    Returns (JSON mode):
        {"slug": str, "name": str, "role": str, "url": str,
         "content": str, "source": "live" | "cache"}
    """
    try:
        record = repo.get_team_member(params.slug, prefer_live=params.prefer_live)
    except repo.RepositoryError as e:
        return f"Error: {e}"
    if params.response_format == ResponseFormat.JSON:
        return _json(record)
    return _detail_md(record, [("role", "Role"), ("url", "URL"), ("source", "Source")])


# --------------------------------------------------------------------------
# Party information
# --------------------------------------------------------------------------
@mcp.tool(name="opportunity_list_party_info", annotations={"title": "List Party Info", **_READONLY})
async def opportunity_list_party_info(params: EmptyInput) -> str:
    """List available party-information sections (about, governance, etc.).

    Returns (JSON mode) a list of: {"section": str, "url": str, "summary": str}
    """
    items = repo.load_party_info()
    if params.response_format == ResponseFormat.JSON:
        return _json({"count": len(items), "sections": items})
    return _listing_md(
        "Opportunity Party Information Sections",
        items,
        [("section", "Section"), ("url", "URL"), ("summary", "Summary")],
    )


@mcp.tool(name="opportunity_get_party_info", annotations={"title": "Get Party Info Section", **_READONLY})
async def opportunity_get_party_info(params: SectionInput) -> str:
    """Get the full content of a party-information section by name.

    Discover section names with ``opportunity_list_party_info``. Sections
    cover party background ('about') and governance/constitution details.

    Returns (JSON mode):
        {"section": str, "url": str, "content": str, "source": "live" | "cache"}
    """
    try:
        record = repo.get_party_info_section(params.section, prefer_live=params.prefer_live)
    except repo.RepositoryError as e:
        return f"Error: {e}"
    if params.response_format == ResponseFormat.JSON:
        return _json(record)
    return _detail_md(record, [("url", "URL"), ("source", "Source")])


# --------------------------------------------------------------------------
# Search
# --------------------------------------------------------------------------
@mcp.tool(name="opportunity_search", annotations={"title": "Search All Content", **_READONLY})
async def opportunity_search(params: SearchInput) -> str:
    """Full-text search across all Opportunity Party content.

    Searches policies, news, team profiles, and party information at once,
    ranking by relevance (title matches weighted higher). Use this to locate
    the right record, then fetch it with the relevant ``opportunity_get_*``
    tool using the returned ``type`` and ``id``.

    Returns (JSON mode) a list of:
        {
          "type": "policy" | "news" | "team" | "party-info",
          "id": str,        # slug/id to pass to the matching get_* tool
          "title": str, "url": str,
          "score": int,     # relevance score
          "snippet": str    # context around the match
        }
    """
    type_values = [t.value for t in params.types] if params.types else None
    results = repo.search(params.query, types=type_values, limit=params.limit)
    if params.response_format == ResponseFormat.JSON:
        return _json({"query": params.query, "count": len(results), "results": results})
    if not results:
        return f"No results found for '{params.query}'."
    lines = [f"# Search results for '{params.query}'", "", f"{len(results)} match(es).", ""]
    for r in results:
        lines.append(f"## [{r['type']}] {r['title']} (id: `{r['id']}`)")
        if r.get("url"):
            lines.append(f"- **URL**: {r['url']}")
        lines.append(f"- **Relevance**: {r['score']}")
        lines.append(f"- {r['snippet']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


if __name__ == "__main__":
    mcp.run()
