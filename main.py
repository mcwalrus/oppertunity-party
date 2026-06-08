"""Main runner for the Opportunity Party web scraper."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from collections.abc import Callable
from typing import Any

from scraper.client import DATA_DIR, clean_data
from scraper.models import PartyInfo, PolicyPage
from scraper.news import save_news, scrape_news
from scraper.party_info import download_and_convert_party_pdfs, save_party_info, scrape_party_info
from scraper.pdf_convert import convert_all_pdfs
from scraper.pdf_download import download_policy_pdfs, migrate_existing_pdfs
from scraper.policies import save_policies, scrape_policies
from scraper.team import save_team, scrape_team

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
    "news": ("news", scrape_news, save_news),
    "party-info": ("party information", scrape_party_info, save_party_info),
    "pdfs": None,
}

ALL_TARGETS = list(SCRAPER_MAP.keys())


def run_scrapers(targets: list[str] | None = None, *, clean: bool = False) -> None:
    """Run selected scrapers and save results into data/.

    After web scraping, also converts any PDFs in policy-assets/ to markdown.
    """
    start = time.time()

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
            if not (DATA_DIR / "policy-assets" / "reference.json").exists():
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape the Opportunity Party website and convert policy PDFs",
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
        help="Clear data/ directory before scraping (preserves policy-assets/)",
    )
    args = parser.parse_args()
    run_scrapers(args.targets or None, clean=args.clean)


if __name__ == "__main__":
    main()
