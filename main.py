"""Main runner for the Opportunity Party web scraper."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable
from typing import Any

from pipeline.ingestion.blog_posts import save_blog_posts, scrape_blog_posts
from pipeline.ingestion.cache import CATEGORY_TTL
from pipeline.ingestion.client import CACHE_DIR, DATA_DIR, clean_data, configure_cache
from pipeline.ingestion.events import save_events, scrape_events
from pipeline.ingestion.models import PartyInfo, PolicyPage
from pipeline.ingestion.party_info import (
    download_and_convert_party_pdfs,
    save_party_info,
    scrape_party_info,
)
from pipeline.ingestion.pdf_convert import convert_all_pdfs
from pipeline.ingestion.pdf_download import download_policy_pdfs, migrate_existing_pdfs
from pipeline.ingestion.policies import save_policies, scrape_policies
from pipeline.ingestion.team import save_team, scrape_team

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# (label, scrape_fn, save_fn) — or None for non-scraping tasks.
# Annotated loosely because this is a dispatch table: each (scrape, save) pair
# is matched at runtime. Individual functions remain strongly typed.
_ScraperEntry = tuple[str, Callable[[], list[Any]], Callable[[list[Any]], Any]]

SCRAPER_MAP: dict[str, _ScraperEntry | None] = {
    "policies": ("policies", scrape_policies, save_policies),
    "team": ("team", scrape_team, save_team),
    "blog": ("blog posts", scrape_blog_posts, save_blog_posts),
    "events": ("events", scrape_events, save_events),
    "party-info": ("party information", scrape_party_info, save_party_info),
    "pdfs": None,
}

ALL_TARGETS = list(SCRAPER_MAP.keys())


def run_scrapers(
    targets: list[str] | None = None,
    *,
    clean: bool = False,
    force_refresh: bool = False,
    refresh_categories: list[str] | None = None,
) -> None:
    """Run selected scrapers and save results into data/.

    After web scraping, also converts any PDFs in data/pdfs/ to markdown.

    Parameters
    ----------
    targets:
        Scraper targets to run (default: all).
    clean:
        Clear the ``data/`` directory before scraping (preserves ``pdfs/``
        and ``.cache/``).
    force_refresh:
        Bypass the HTTP cache for *all* categories — every URL is fetched
        live from the website regardless of when it was last cached.
    refresh_categories:
        Bypass the cache only for the named categories (e.g.
        ``["blog", "events"]``).  All other categories continue to serve
        cached responses.
    """
    start = time.time()

    # Initialise the HTTP cache before any network activity
    cache = configure_cache(
        force_refresh=force_refresh,
        refresh_categories=refresh_categories,
    )

    if clean:
        clean_data()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if targets:
        selected = {k: v for k, v in SCRAPER_MAP.items() if k in targets}
        unknown = set(targets) - set(SCRAPER_MAP)
        if unknown:
            logger.error("Unknown scraper targets: %s", unknown)
            logger.info("Available: %s", ", ".join(ALL_TARGETS))
            sys.exit(1)
    else:
        selected = SCRAPER_MAP

    logger.info("=== Starting Opportunity Party scraper ===")
    logger.info("Output directory: %s", DATA_DIR)
    logger.info("Targets: %s", ", ".join(selected))

    totals = {}
    for key, entry in selected.items():
        if entry is None:
            # PDF conversion (no web scraping)
            logger.info("--- Converting policy PDFs ---")
            results = convert_all_pdfs()
            totals["policy PDFs"] = len(results)
            continue

        label, scrape_fn, save_fn = entry
        logger.info("--- Scraping %s ---", label)
        items = scrape_fn()
        save_fn(items)
        totals[label] = len(items)

        # After scraping party-info, download and convert linked PDFs
        if key == "party-info" and items and isinstance(items[0], PartyInfo):
            logger.info("--- Downloading party-information PDFs ---")
            party_pages = [p for p in items if isinstance(p, PartyInfo)]
            pdf_results = download_and_convert_party_pdfs(party_pages)
            ok = sum(1 for r in pdf_results if r["status"] == "ok")
            failed = sum(1 for r in pdf_results if r["status"] in ("failed", "error"))
            logger.info("Party PDFs: %d converted, %d failed", ok, failed)
            totals["party PDFs"] = ok

        # After scraping policies, download PDFs and convert them
        if key == "policies" and items and isinstance(items[0], PolicyPage):
            # Migrate any existing PDFs that aren't in reference.json
            if not (DATA_DIR / "pdfs" / "reference.json").exists():
                migrate_existing_pdfs()

            policy_pages = [p for p in items if isinstance(p, PolicyPage)]
            downloads = download_policy_pdfs(policy_pages)
            downloaded = sum(1 for r in downloads if r["status"] == "downloaded")
            skipped = sum(1 for r in downloads if r["status"] == "skipped_existing")
            failed = sum(1 for r in downloads if r["status"] == "failed")
            logger.info(
                "PDF downloads: %d downloaded, %d skipped, %d failed", downloaded, skipped, failed
            )

            # Then convert PDFs to markdown
            logger.info("--- Converting policy PDFs ---")
            pdf_results = convert_all_pdfs()
            totals["policy PDFs"] = len(pdf_results)

    elapsed = time.time() - start
    summary = ", ".join(f"{v} {k}" for k, v in totals.items())
    logger.info("=== Done in %.1fs: %s ===", elapsed, summary)
    logger.info("=== %s ===", cache.summary_line())


def _run_media(args: argparse.Namespace) -> None:
    """Entry point for the ``media`` sub-command."""
    from media.youtube import YouTubePlatform

    platform: YouTubePlatform
    if args.platform == "youtube":
        platform = YouTubePlatform(year_filter=getattr(args, "year", None))
    else:
        logger.error("Unknown media platform: %s", args.platform)
        sys.exit(1)

    mode: str = getattr(args, "mode", "download")
    refresh: bool = getattr(args, "refresh", False)

    items = platform.enumerate(refresh=refresh)
    grouped = platform.group(items)

    if mode == "list":
        platform.list_summary(grouped)
    elif mode == "download":
        queue = platform.select(grouped)
        platform.download(queue)
    else:
        logger.error("Unknown mode: %s", mode)
        sys.exit(1)


def _build_media_parser() -> argparse.ArgumentParser:
    """Build the standalone argument parser for the ``media`` sub-command."""
    p = argparse.ArgumentParser(
        prog="main.py media",
        description="Download off-platform media.",
    )
    sub = p.add_subparsers(dest="platform")

    yt = sub.add_parser("youtube", help="YouTube channel downloader (@OpportunityNZ)")
    yt.add_argument(
        "--mode",
        choices=["list", "download"],
        default="download",
        help="list: show year summary; download: interactive pick + download (default)",
    )
    yt.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-enumeration, replacing the JSON cache",
    )
    yt.add_argument(
        "--year",
        metavar="YYYY",
        help="Filter to a specific year (e.g. 2024)",
    )
    return p


def main() -> None:
    # Early dispatch: if first arg is "media", use the dedicated media parser
    # to avoid argparse conflicts with the nargs="*" targets positional.
    if len(sys.argv) > 1 and sys.argv[1] == "media":
        media_parser = _build_media_parser()
        media_args = media_parser.parse_args(sys.argv[2:])
        if not media_args.platform:
            media_parser.print_help()
            sys.exit(1)
        _run_media(media_args)
        return

    # Build a readable list of category TTLs for the help text
    _ttl_help = ", ".join(
        f"{cat}={ttl // 3600}h" if ttl >= 3600 else f"{cat}={ttl // 60}m"
        for cat, ttl in CATEGORY_TTL.items()
        if cat != "default"
    )

    parser = argparse.ArgumentParser(
        description="Scrape the Opportunity Party website and convert policy PDFs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Cache TTLs by category (default TTL=12h):\n"
            f"  {_ttl_help}\n\n"
            "Examples:\n"
            "  # Normal run — serve from cache if fresh\n"
            "  python main.py\n\n"
            "  # Force-refresh everything\n"
            "  python main.py --force-refresh\n\n"
            "  # Force-refresh only blog and events\n"
            "  python main.py --refresh-categories blog events\n\n"
            "  # Run only the team scraper, force-refresh its cache\n"
            "  python main.py team --refresh-categories team\n"
        ),
    )
    parser.add_argument(
        "targets",
        nargs="*",
        choices=ALL_TARGETS,
        help="Scraper targets to run (default: all)",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clear data/sources/opportunity-website/ before scraping (preserves pdfs/)",
    )

    refresh_group = parser.add_mutually_exclusive_group()
    refresh_group.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass the HTTP cache for all categories — re-fetch every URL from the website",
    )
    refresh_group.add_argument(
        "--refresh-categories",
        nargs="+",
        metavar="CATEGORY",
        choices=list(CATEGORY_TTL.keys()),
        help=(
            "Bypass the cache for specific categories only "
            f"(choices: {', '.join(c for c in CATEGORY_TTL if c != 'default')})"
        ),
    )

    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Print cache entry counts per category and exit (no scraping)",
    )

    args = parser.parse_args()

    if args.cache_stats:
        _print_cache_stats()
        return

    run_scrapers(
        args.targets or None,
        clean=args.clean,
        force_refresh=args.force_refresh,
        refresh_categories=args.refresh_categories,
    )


def _print_cache_stats() -> None:
    """Print a summary of the current HTTP cache state and exit."""
    from pipeline.ingestion.client import get_cache

    cache = get_cache()
    stats = cache.stats()
    print("HTTP cache contents:")
    print(f"  Location : {CACHE_DIR}")
    total = 0
    for cat, ttl in CATEGORY_TTL.items():
        if cat == "default":
            continue
        count = stats.get(cat, 0)
        ttl_str = f"{ttl // 3600}h" if ttl >= 3600 else f"{ttl // 60}m"
        print(f"  {cat:<15} {count:>4} entries  (TTL {ttl_str})")
        total += count
    other = sum(v for k, v in stats.items() if k not in CATEGORY_TTL and not k.startswith("_"))
    if other:
        print(f"  {'other':<15} {other:>4} entries")
        total += other
    print(f"  {'TOTAL':<15} {total:>4} entries")


if __name__ == "__main__":
    main()
