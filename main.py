"""Main runner for the Opportunity Party web scraper."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from scraper.client import DATA_DIR, clean_data
from scraper.news import save_news, scrape_news
from scraper.party_info import save_party_info, scrape_party_info
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

SCRAPER_MAP = {
    "policies": ("policies", scrape_policies, save_policies),
    "team": ("team", scrape_team, save_team),
    "news": ("news", scrape_news, save_news),
    "party-info": ("party information", scrape_party_info, save_party_info),
}


def run_scrapers(targets: list[str] | None = None, *, clean: bool = False) -> None:
    """Run selected scrapers and save results into data/."""
    start = time.time()

    if clean:
        clean_data()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if targets:
        selected = {k: v for k, v in SCRAPER_MAP.items() if k in targets}
        unknown = set(targets) - set(SCRAPER_MAP)
        if unknown:
            logger.error("Unknown scraper targets: %s", unknown)
            logger.info("Available: %s", ", ".join(SCRAPER_MAP))
            sys.exit(1)
    else:
        selected = SCRAPER_MAP

    logger.info("=== Starting Opportunity Party scraper ===")
    logger.info("Output directory: %s", DATA_DIR)
    logger.info("Targets: %s", ", ".join(selected) if selected else "all")

    totals = {}
    for key, (label, scrape_fn, save_fn) in selected.items():
        logger.info("--- Scraping %s ---", label)
        items = scrape_fn()
        save_fn(items)
        totals[label] = len(items)

    elapsed = time.time() - start
    summary = ", ".join(f"{v} {k}" for k, v in totals.items())
    logger.info("=== Done in %.1fs: %s ===", elapsed, summary)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape the Opportunity Party website",
    )
    parser.add_argument(
        "targets",
        nargs="*",
        choices=list(SCRAPER_MAP),
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