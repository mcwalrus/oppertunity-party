"""Disk-based HTTP response cache with per-category TTLs.

Cached responses are stored as JSON files under::

    data/.cache/{category}/{url_hash}.json

Each file contains the raw response text (HTML or JSON string) alongside
the URL and the timestamp it was cached.  A fresh hit avoids a network
round-trip entirely; a stale or missing entry falls through to the live
fetch.

Usage (managed automatically by ``scraper.client``)::

    from scraper.cache import RequestCache

    cache = RequestCache(cache_dir=DATA_DIR / ".cache")
    content = cache.get(url, category="policies")  # None → cache miss
    cache.set(url, category="policies", content=html)

Category TTLs are defined in :data:`CATEGORY_TTL` and can be overridden by
editing that dict before the first fetch.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet
    from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-category TTLs (seconds)
# ---------------------------------------------------------------------------

#: How long each category's cached responses stay fresh.
#: Keys match the target names used in ``main.py`` and each scraper module.
CATEGORY_TTL: dict[str, int] = {
    "policies": 86_400,  # 24 hours — policy text rarely changes
    "team": 86_400,  # 24 hours — candidate profiles are stable
    "party-info": 86_400,  # 24 hours — constitutional docs don't move
    "blog": 21_600,  # 6 hours  — new posts can appear during the day
    "events": 7_200,  # 2 hours  — events calendar updates more often
    "default": 43_200,  # 12 hours — fallback for unknown categories
}


# ---------------------------------------------------------------------------
# Cache entry representation
# ---------------------------------------------------------------------------


class RequestCache:
    """Persistent, per-category HTTP response cache stored on disk.

    Parameters
    ----------
    cache_dir:
        Root directory for all cache files (e.g. ``data/.cache``).
    force_refresh:
        When ``True``, :meth:`get` always returns ``None`` so every request
        goes to the network.  New responses are still written to disk so the
        cache stays warm for the *next* run.
    refresh_categories:
        Optional set of category names to treat as always-stale, even when
        ``force_refresh`` is ``False``.  Useful for refreshing a single
        scraper target without busting the whole cache.
    """

    def __init__(
        self,
        cache_dir: Path,
        *,
        force_refresh: bool = False,
        refresh_categories: AbstractSet[str] | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.force_refresh = force_refresh
        self.refresh_categories: frozenset[str] = frozenset(refresh_categories or ())
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------
    # Core API
    # ------------------------------------------------------------------

    def get(self, url: str, category: str = "default") -> str | None:
        """Return cached content string if fresh, else ``None``.

        Returns ``None`` (cache miss) when:
        - ``force_refresh`` is ``True``
        - ``category`` is in ``refresh_categories``
        - no cache file exists for this URL
        - the cached entry is older than the category TTL
        - the cache file is malformed
        """
        if self.force_refresh or category in self.refresh_categories:
            self._misses += 1
            return None

        path = self._cache_path(url, category)
        if not path.exists():
            self._misses += 1
            return None

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(data["cached_at"])
            ttl = CATEGORY_TTL.get(category, CATEGORY_TTL["default"])
            age = datetime.now() - cached_at
            if age < timedelta(seconds=ttl):
                logger.debug(
                    "Cache HIT [%s] %s (age %s)",
                    category,
                    url,
                    _fmt_age(age),
                )
                self._hits += 1
                return str(data["content"])
            else:
                logger.debug(
                    "Cache STALE [%s] %s (age %s > ttl %ds)",
                    category,
                    url,
                    _fmt_age(age),
                    ttl,
                )
                self._misses += 1
                return None
        except Exception as exc:
            logger.debug("Cache read error for %s: %s", url, exc)
            self._misses += 1
            return None

    def set(self, url: str, category: str, content: str) -> None:
        """Write ``content`` to the cache for ``url`` under ``category``."""
        path = self._cache_path(url, category)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "url": url,
            "category": category,
            "cached_at": datetime.now().isoformat(),
            "content": content,
        }
        path.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        logger.debug("Cache SET [%s] %s", category, url)

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def invalidate(self, categories: list[str] | None = None) -> int:
        """Delete cache files.

        Parameters
        ----------
        categories:
            List of category names to clear.  Pass ``None`` to wipe the
            entire cache.

        Returns
        -------
        int
            Number of cache files deleted.
        """
        removed = 0
        if not self.cache_dir.exists():
            return 0

        if categories is None:
            targets = [d for d in self.cache_dir.iterdir() if d.is_dir()]
        else:
            targets = [self.cache_dir / cat for cat in categories]

        for cat_dir in targets:
            if not cat_dir.is_dir():
                continue
            for f in cat_dir.glob("*.json"):
                f.unlink()
                removed += 1

        if removed:
            logger.info("Cache invalidated: %d entries removed", removed)
        return removed

    def stats(self) -> dict[str, int]:
        """Return cached entry counts per category and session hit/miss totals.

        Returns a dict like::

            {
                "policies": 14,
                "team": 22,
                "_hits": 30,
                "_misses": 6,
            }
        """
        counts: dict[str, int] = {}
        if self.cache_dir.exists():
            for cat_dir in self.cache_dir.iterdir():
                if cat_dir.is_dir():
                    counts[cat_dir.name] = len(list(cat_dir.glob("*.json")))
        counts["_hits"] = self._hits
        counts["_misses"] = self._misses
        return counts

    def summary_line(self) -> str:
        """Return a one-line human-readable session summary."""
        total = self._hits + self._misses
        if total == 0:
            return "cache: no requests"
        return (
            f"cache: {self._hits} hits / {self._misses} misses "
            f"({self._hits * 100 // total}% hit rate)"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cache_path(self, url: str, category: str) -> Path:
        """Return the filesystem path for a given URL + category pair."""
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self.cache_dir / category / f"{url_hash}.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt_age(delta: timedelta) -> str:
    """Format a timedelta as a compact human-readable string."""
    total = int(delta.total_seconds())
    if total < 60:
        return f"{total}s"
    if total < 3600:
        return f"{total // 60}m"
    return f"{total // 3600}h{(total % 3600) // 60}m"
