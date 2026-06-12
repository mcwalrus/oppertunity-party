"""Shared utilities for scraping the Opportunity Party website.

Uses curl subprocess for HTTP requests since the Python sandbox
restricts direct network access. All scraped output goes into the
data/ directory.

Rate-limiting / caching
-----------------------
All HTTP requests go through a :class:`~pipeline.ingestion.cache.RequestCache` that
stores raw responses on disk under ``data/.cache/{category}/``.  Call
:func:`configure_cache` once at startup (e.g. from ``main.py``) to
customise the force-refresh behaviour.

Per-category TTLs are defined in :data:`scraper.cache.CATEGORY_TTL`.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup

from pipeline.ingestion.cache import RequestCache
from pipeline.paths import CACHE_DIR, DATA_DIR

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

BASE_URL = "https://www.opportunity.org.nz"

# Re-export path constants for backward compatibility within ingestion modules
__all__ = ["BASE_URL", "CACHE_DIR", "DATA_DIR"]

# ---------------------------------------------------------------------------
# Cache singleton
# ---------------------------------------------------------------------------

#: Module-level cache instance; replace or reconfigure via :func:`configure_cache`.
_cache: RequestCache = RequestCache(CACHE_DIR)


def configure_cache(
    *,
    force_refresh: bool = False,
    refresh_categories: list[str] | None = None,
) -> RequestCache:
    """Re-initialise the module-level HTTP cache.

    Call this once at startup before any scraping begins.

    Parameters
    ----------
    force_refresh:
        When ``True``, every :func:`fetch_html` / :func:`fetch_json` call
        ignores cached data and goes to the network.  Fresh responses are
        still written to the cache so the *next* run benefits.
    refresh_categories:
        List of category names (``"policies"``, ``"team"``, ``"blog"``,
        ``"events"``, ``"party-info"``) whose cache should be bypassed.
        All other categories continue to serve cached responses normally.
        Ignored when ``force_refresh=True`` (everything is bypassed).

    Returns
    -------
    RequestCache
        The newly created cache instance (also stored as the module global).
    """
    global _cache  # module-level singleton, intentional
    _cache = RequestCache(
        CACHE_DIR,
        force_refresh=force_refresh,
        refresh_categories=frozenset(refresh_categories) if refresh_categories else None,
    )
    if force_refresh:
        logger.info("Cache: force-refresh enabled — all requests will hit the network")
    elif refresh_categories:
        logger.info("Cache: force-refresh for categories: %s", ", ".join(refresh_categories))
    return _cache


def get_cache() -> RequestCache:
    """Return the active module-level :class:`~scraper.cache.RequestCache`."""
    return _cache


def clean_data() -> None:
    """Remove all scraped data, preserving the pdfs folder.

    The HTTP cache lives at ``data/.cache/`` and is never touched here.
    """
    if DATA_DIR.exists():
        for child in DATA_DIR.iterdir():
            if child.name == "pdfs":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        logger.info("Cleaned data/sources/opportunity-website/ (preserved pdfs)")


def fetch_html(path: str, category: str = "default") -> str:
    """Fetch a page via curl and return raw HTML string.

    Results are cached on disk under ``data/.cache/{category}/`` and reused
    on subsequent calls until the category TTL expires.  Pass a ``category``
    matching one of the keys in :data:`scraper.cache.CATEGORY_TTL` to apply
    the correct staleness window.
    """
    url = f"{BASE_URL}{path}"

    cached = _cache.get(url, category)
    if cached is not None:
        logger.info("Cache HIT  [%s] %s", category, url)
        return cached

    logger.info("Fetching   [%s] %s", category, url)
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--max-time",
            "30",
            "--user-agent",
            "OpportunityPartyScraper/1.0 (research purpose)",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr}")
    _cache.set(url, category, result.stdout)
    return result.stdout


def fetch_page(path: str, category: str = "default") -> BeautifulSoup:
    """Fetch a page and return a parsed BeautifulSoup object.

    Delegates caching to :func:`fetch_html`; pass ``category`` to control
    the TTL bucket.
    """
    html = fetch_html(path, category=category)
    return BeautifulSoup(html, "lxml")


def fetch_json(path: str, category: str = "default") -> dict | list:
    """Fetch a JSON endpoint and return parsed data.

    Raw JSON text is cached on disk; subsequent calls within the TTL window
    parse from cache without hitting the network.
    """
    url = f"{BASE_URL}{path}"

    cached = _cache.get(url, category)
    if cached is not None:
        logger.info("Cache HIT  [%s] %s", category, url)
        return json.loads(cached)  # type: ignore[no-any-return]

    logger.info("Fetching JSON [%s] %s", category, url)
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--max-time",
            "30",
            "--header",
            "Accept: application/json",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr}")
    _cache.set(url, category, result.stdout)
    return json.loads(result.stdout)  # type: ignore[no-any-return]


def save_content(directory: Path, filename: str, content: str) -> Path:
    """Save content string to a directory, creating it if needed."""
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / filename
    filepath.write_text(content, encoding="utf-8")
    logger.info("Saved %s", filepath)
    return filepath


def extract_main_content(soup: BeautifulSoup) -> str:
    """Extract the main content area from a page, stripping nav/footer noise."""
    for selector in [
        "main",
        "[role='main']",
        ".page-content",
        "#content",
        ".content",
        ".main-content",
        "article",
    ]:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 100:
            return el.get_text(separator="\n", strip=True)

    body = soup.find("body")
    if body:
        for tag in body.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return body.get_text(separator="\n", strip=True)

    return soup.get_text(separator="\n", strip=True)
