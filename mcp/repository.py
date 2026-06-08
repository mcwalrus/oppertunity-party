"""Read-only data access layer for Opportunity Party information.

This module is the bridge between the MCP server and the existing
``scraper`` package. It deliberately *reuses* the scraper's HTTP client,
content-extraction helpers, and slug logic rather than duplicating them,
so the MCP server and the scraper stay in lock-step.

Two sources back every lookup:

  1. **Live website** (``https://www.opportunity.org.nz``) via the scraper's
     ``curl``-based client — used for the always-fresh ``get_*`` detail views.
  2. **Local cache** (the scraper's ``data/`` directory) — used for fast,
     stable listing and full-text search, and as a fallback when the live
     site is unreachable.

Everything here is strictly read-only: no scraping-to-disk, no mutation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# The scraper package lives in the project root (one level above mcp/).
# Insert it on the path so we can reuse its modules. Note: this module does
# NOT import the `mcp` SDK, so adding the project root here cannot shadow it.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# --- Reused scraper code (single source of truth) -------------------------
from scraper.client import BASE_URL, DATA_DIR, fetch_page  # noqa: E402
from scraper.news import (  # noqa: E402
    _extract_article_content,
    _title_to_slug,
)
from scraper.party_info import _extract_content  # noqa: E402
from scraper.policies import (  # noqa: E402
    POLICY_SLUGS,
    _extract_markdown,
    _extract_pdf_links,
    _extract_title,
)
from scraper.team import (  # noqa: E402
    _extract_member_content,
    _extract_role,
    _name_to_slug,
)

__all__ = [
    "BASE_URL",
    "RepositoryError",
    "load_policies",
    "get_policy",
    "load_policy_documents",
    "get_policy_document",
    "load_news",
    "get_news_article",
    "load_team",
    "get_team_member",
    "load_party_info",
    "get_party_info_section",
    "search",
]


class RepositoryError(Exception):
    """Raised when requested information cannot be found in any source."""


# --------------------------------------------------------------------------
# Cache helpers
# --------------------------------------------------------------------------
def _read_index(category: str) -> list[dict]:
    """Read a scraper-produced ``index.json`` for a content category.

    Returns an empty list if the cache has not been populated yet.
    """
    index_path = DATA_DIR / category / "index.json"
    if not index_path.exists():
        return []
    try:
        data = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return data if isinstance(data, list) else []


def _read_json(category: str, filename: str) -> list | dict | None:
    path = DATA_DIR / category / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _read_markdown(category: str, filename: str) -> str | None:
    path = DATA_DIR / category / filename
    if not path.exists():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _summarise(content: str, limit: int = 280) -> str:
    """Produce a short plain-text summary from markdown content."""
    text = " ".join(content.split())
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


# --------------------------------------------------------------------------
# Policies
# --------------------------------------------------------------------------
def load_policies() -> list[dict]:
    """Return a lightweight listing of all known policy areas.

    Sourced from the local cache when available, otherwise derived from the
    scraper's known ``POLICY_SLUGS`` so a listing is always available even
    before the cache is populated.
    """
    cached = _read_index("policies")
    if cached:
        return [
            {
                "slug": p["slug"],
                "title": p.get("title", p["slug"]),
                "url": p.get("url", f"{BASE_URL}/{p['slug']}"),
                "has_documents": bool(p.get("pdf_downloads")),
                "summary": _summarise(p.get("content", "")),
            }
            for p in cached
        ]
    # Fallback: no cache yet — list known slugs only.
    return [
        {
            "slug": slug,
            "title": slug.replace("-", " ").title(),
            "url": f"{BASE_URL}{path}",
            "has_documents": False,
            "summary": "",
        }
        for slug, path in POLICY_SLUGS.items()
    ]


def _fetch_policy_live(slug: str) -> dict | None:
    """Fetch a single policy page directly from the website."""
    path = POLICY_SLUGS.get(slug)
    if not path:
        # Allow ad-hoc slugs discovered in the cache as well.
        cached = next((p for p in _read_index("policies") if p["slug"] == slug), None)
        if cached and cached.get("url", "").startswith(BASE_URL):
            path = cached["url"][len(BASE_URL):]
    if not path:
        return None
    soup = fetch_page(path)
    content = _extract_markdown(soup)
    if not content:
        return None
    return {
        "slug": slug,
        "title": _extract_title(soup),
        "url": f"{BASE_URL}{path}",
        "content": content,
        "documents": _extract_pdf_links(soup),
        "source": "live",
    }


def get_policy(slug: str, *, prefer_live: bool = True) -> dict:
    """Return the full content of a single policy by slug.

    Tries the live website first (so content is current), then falls back to
    the local cache. Raises ``RepositoryError`` if the policy is unknown.
    """
    if prefer_live:
        try:
            live = _fetch_policy_live(slug)
            if live:
                return live
        except Exception:  # noqa: BLE001 — any network/parse failure → cache
            pass

    cached = next((p for p in _read_index("policies") if p["slug"] == slug), None)
    if cached:
        return {
            "slug": cached["slug"],
            "title": cached.get("title", slug),
            "url": cached.get("url", f"{BASE_URL}/{slug}"),
            "content": cached.get("content", ""),
            "documents": cached.get("pdf_downloads", []),
            "source": "cache",
        }

    known = sorted({*POLICY_SLUGS, *(p["slug"] for p in _read_index("policies"))})
    raise RepositoryError(
        f"Unknown policy slug '{slug}'. Known policies: {', '.join(known)}"
    )


# --------------------------------------------------------------------------
# Policy documents (PDF-derived overviews / addenda)
# --------------------------------------------------------------------------
def _slugify_doc(text: str) -> str:
    keep = "abcdefghijklmnopqrstuvwxyz0123456789- "
    s = "".join(c if c in keep else "" for c in text.lower()).strip().replace(" ", "-")
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


def _resolve_doc_path(output_file: str) -> Path | None:
    """Resolve a pdf-index ``output_file`` (absolute or relative) to a real path."""
    p = Path(output_file)
    if p.is_absolute() and p.exists():
        return p
    # Relative to the policies cache directory.
    candidate = DATA_DIR / "policies" / output_file
    return candidate if candidate.exists() else None


def _policy_document_entries() -> list[dict]:
    """Build clean, de-duplicated policy-document entries from the PDF index.

    The on-disk PDF index can carry messy directory names and absolute paths,
    so we key each document by a stable id derived from its clean ``policy``
    and ``document_type`` fields and resolve the markdown path defensively.
    """
    index = _read_json("policies", "pdf-index.json")
    if not isinstance(index, list):
        return []
    entries: dict[str, dict] = {}
    for entry in index:
        policy = entry.get("policy", "") or "unknown"
        if policy.lower() == "unknown":
            continue  # skip junk/placeholder index rows
        doc_type = entry.get("document_type", "")
        doc_id = _slugify_doc(policy)
        if doc_type:
            doc_id += f"_{_slugify_doc(doc_type)}"
        path = _resolve_doc_path(entry.get("output_file", ""))
        if path is None:
            continue
        entries.setdefault(
            doc_id,
            {
                "id": doc_id,
                "title": entry.get("title", policy),
                "policy": policy,
                "date": entry.get("date", ""),
                "document_type": doc_type,
                "source_file": entry.get("source_file", ""),
                "_path": str(path),
            },
        )
    return list(entries.values())


def load_policy_documents() -> list[dict]:
    """Return the listing of detailed policy documents converted from PDFs."""
    return [{k: v for k, v in e.items() if not k.startswith("_")} for e in _policy_document_entries()]


def get_policy_document(doc_id: str) -> dict:
    """Return the full markdown of a converted policy document by id."""
    entry = next((e for e in _policy_document_entries() if e["id"] == doc_id), None)
    if entry is None:
        available = [e["id"] for e in _policy_document_entries()]
        raise RepositoryError(
            f"Unknown policy document '{doc_id}'. "
            f"Available documents: {', '.join(available) or '(none cached)'}"
        )
    try:
        content = Path(entry["_path"]).read_text(encoding="utf-8")
    except OSError as e:
        raise RepositoryError(f"Could not read document '{doc_id}': {e}") from e
    meta = {k: v for k, v in entry.items() if not k.startswith("_")}
    return {**meta, "content": content, "source": "cache"}


# --------------------------------------------------------------------------
# News / media releases
# --------------------------------------------------------------------------
def load_news() -> list[dict]:
    """Return a listing of news / media releases (newest cache order)."""
    return [
        {
            "slug": _title_to_slug(item["title"]),
            "title": item["title"],
            "url": item.get("url", ""),
            "date": item.get("date", ""),
            "summary": _summarise(item.get("content", "")),
        }
        for item in _read_index("news")
    ]


def get_news_article(slug: str, *, prefer_live: bool = True) -> dict:
    """Return a full news article by slug (cache first; live refresh attempt).

    News articles live at idiosyncratic root-level URLs, so the cache is the
    primary source. When ``prefer_live`` is set and the cached entry carries a
    URL, a fresh copy is fetched and used if successful.
    """
    cached = next(
        (i for i in _read_index("news") if _title_to_slug(i["title"]) == slug),
        None,
    )
    if cached is None:
        available = [_title_to_slug(i["title"]) for i in _read_index("news")]
        raise RepositoryError(
            f"Unknown news slug '{slug}'. Available: {', '.join(available)}"
        )

    content = cached.get("content", "")
    source = "cache"
    if prefer_live and cached.get("url", "").startswith(BASE_URL):
        try:
            soup = fetch_page(cached["url"][len(BASE_URL):])
            fresh = _extract_article_content(soup)
            if fresh:
                content, source = fresh, "live"
        except Exception:  # noqa: BLE001
            pass

    return {
        "slug": slug,
        "title": cached["title"],
        "url": cached.get("url", ""),
        "date": cached.get("date", ""),
        "content": content,
        "source": source,
    }


# --------------------------------------------------------------------------
# Team / candidates
# --------------------------------------------------------------------------
def load_team() -> list[dict]:
    """Return a listing of team members / candidates."""
    return [
        {
            "slug": _name_to_slug(m["name"]),
            "name": m["name"],
            "role": m.get("role", ""),
            "url": m.get("url", ""),
        }
        for m in _read_index("team")
    ]


def get_team_member(slug: str, *, prefer_live: bool = True) -> dict:
    """Return a full team-member / candidate profile by slug."""
    cached = next(
        (m for m in _read_index("team") if _name_to_slug(m["name"]) == slug),
        None,
    )
    if cached is None:
        available = [_name_to_slug(m["name"]) for m in _read_index("team")]
        raise RepositoryError(
            f"Unknown team member slug '{slug}'. Available: {', '.join(available)}"
        )

    content = cached.get("content", "")
    role = cached.get("role", "")
    source = "cache"
    if prefer_live and cached.get("url", "").startswith(BASE_URL):
        try:
            soup = fetch_page(cached["url"][len(BASE_URL):])
            fresh = _extract_member_content(soup)
            if fresh:
                content, source = fresh, "live"
                role = _extract_role(soup) or role
        except Exception:  # noqa: BLE001
            pass

    return {
        "slug": slug,
        "name": cached["name"],
        "role": role,
        "url": cached.get("url", ""),
        "content": content,
        "source": source,
    }


# --------------------------------------------------------------------------
# Party information (about / constitution / governance)
# --------------------------------------------------------------------------
def load_party_info() -> list[dict]:
    """Return the available party-information sections."""
    return [
        {
            "section": p["section"],
            "url": p.get("url", ""),
            "summary": _summarise(p.get("content", "")),
        }
        for p in _read_index("party-information")
    ]


def get_party_info_section(section: str, *, prefer_live: bool = True) -> dict:
    """Return a full party-information section (e.g. 'about')."""
    cached = next(
        (p for p in _read_index("party-information") if p["section"] == section),
        None,
    )
    if cached is None:
        available = [p["section"] for p in _read_index("party-information")]
        raise RepositoryError(
            f"Unknown party-info section '{section}'. Available: {', '.join(available)}"
        )

    content = cached.get("content", "")
    source = "cache"
    if prefer_live and cached.get("url", "").startswith(BASE_URL):
        try:
            soup = fetch_page(cached["url"][len(BASE_URL):])
            fresh = _extract_content(soup)
            if fresh:
                content, source = fresh, "live"
        except Exception:  # noqa: BLE001
            pass

    return {
        "section": section,
        "url": cached.get("url", ""),
        "content": content,
        "source": source,
    }


# --------------------------------------------------------------------------
# Cross-category search
# --------------------------------------------------------------------------
def _search_records() -> list[dict]:
    """Yield every searchable record across all cached categories."""
    records: list[dict] = []
    for p in _read_index("policies"):
        records.append(
            {
                "type": "policy",
                "id": p["slug"],
                "title": p.get("title", p["slug"]),
                "url": p.get("url", ""),
                "content": p.get("content", ""),
            }
        )
    for i in _read_index("news"):
        records.append(
            {
                "type": "news",
                "id": _title_to_slug(i["title"]),
                "title": i["title"],
                "url": i.get("url", ""),
                "content": i.get("content", ""),
            }
        )
    for m in _read_index("team"):
        records.append(
            {
                "type": "team",
                "id": _name_to_slug(m["name"]),
                "title": m["name"],
                "url": m.get("url", ""),
                "content": f"{m.get('role', '')}\n{m.get('content', '')}",
            }
        )
    for p in _read_index("party-information"):
        records.append(
            {
                "type": "party-info",
                "id": p["section"],
                "title": p["section"].replace("-", " ").title(),
                "url": p.get("url", ""),
                "content": p.get("content", ""),
            }
        )
    return records


def _snippet(content: str, query: str, width: int = 160) -> str:
    """Return a context snippet around the first match of ``query``."""
    lowered = content.lower()
    idx = lowered.find(query.lower())
    if idx == -1:
        return _summarise(content, width)
    start = max(0, idx - width // 2)
    end = min(len(content), idx + len(query) + width // 2)
    snippet = " ".join(content[start:end].split())
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(content) else ""
    return f"{prefix}{snippet}{suffix}"


def search(query: str, *, types: list[str] | None = None, limit: int = 20) -> list[dict]:
    """Full-text search across all cached Opportunity Party content.

    Matches are ranked by occurrence count of the query terms in the title
    (weighted higher) and body. Returns up to ``limit`` results.
    """
    q = query.strip().lower()
    if not q:
        return []
    terms = q.split()

    results: list[dict] = []
    for rec in _search_records():
        if types and rec["type"] not in types:
            continue
        haystack_title = rec["title"].lower()
        haystack_body = rec["content"].lower()
        score = 0
        for term in terms:
            score += haystack_title.count(term) * 5
            score += haystack_body.count(term)
        if score == 0:
            continue
        results.append(
            {
                "type": rec["type"],
                "id": rec["id"],
                "title": rec["title"],
                "url": rec["url"],
                "score": score,
                "snippet": _snippet(rec["content"], terms[0]),
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results[:limit]
