"""Ingestion layer assets — raw scraper output per content type."""

from __future__ import annotations

import json

import dagster as dg

from pipeline.ingestion.blog_posts import save_blog_posts, scrape_blog_posts
from pipeline.ingestion.client import DATA_DIR
from pipeline.ingestion.events import save_events, scrape_events
from pipeline.ingestion.models import PolicyPage
from pipeline.ingestion.party_info import (
    download_and_convert_party_pdfs,
    save_party_info,
    scrape_party_info,
)
from pipeline.ingestion.pdf_download import download_policy_pdfs
from pipeline.ingestion.policies import save_policies, scrape_policies
from pipeline.ingestion.team import save_team, scrape_team


@dg.asset(group_name="ingestion")
def raw_policies() -> dg.MaterializeResult:
    """Scrape all policy pages and save raw data to data/sources/."""
    items = scrape_policies()
    save_policies(items)
    output_dir = DATA_DIR / "policies"
    return dg.MaterializeResult(
        metadata={
            "item_count": len(items),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="ingestion")
def raw_team() -> dg.MaterializeResult:
    """Scrape team member pages and save raw data to data/sources/."""
    members = scrape_team()
    save_team(members)
    output_dir = DATA_DIR / "team"
    return dg.MaterializeResult(
        metadata={
            "item_count": len(members),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="ingestion")
def raw_blog() -> dg.MaterializeResult:
    """Scrape blog posts and save raw data to data/sources/."""
    items = scrape_blog_posts()
    save_blog_posts(items)
    output_dir = DATA_DIR / "blog"
    return dg.MaterializeResult(
        metadata={
            "item_count": len(items),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="ingestion")
def raw_events() -> dg.MaterializeResult:
    """Scrape event listings and save raw data to data/sources/."""
    items = scrape_events()
    save_events(items)
    output_dir = DATA_DIR / "events"
    return dg.MaterializeResult(
        metadata={
            "item_count": len(items),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="ingestion")
def raw_party_info() -> dg.MaterializeResult:
    """Scrape party information pages (including PDFs) and save raw data to data/sources/."""
    pages = scrape_party_info()
    save_party_info(pages)
    download_and_convert_party_pdfs(pages)
    output_dir = DATA_DIR / "party-information"
    return dg.MaterializeResult(
        metadata={
            "item_count": len(pages),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="ingestion", deps=["raw_policies"])
def raw_pdfs() -> dg.MaterializeResult:
    """Download policy PDFs — depends on raw_policies being materialised first.

    Loads the policy index written by ``raw_policies`` to obtain PDF URLs,
    then delegates to :func:`~scraper.pdf_download.download_policy_pdfs`.
    """
    index_path = DATA_DIR / "policies" / "index.json"
    if index_path.exists():
        data: list[dict] = json.loads(index_path.read_text(encoding="utf-8"))
        policies: list[PolicyPage] = [
            PolicyPage(
                slug=entry["slug"],
                title=entry["title"],
                url=entry["url"],
                content=entry.get("content", ""),
                pdf_downloads=entry.get("pdf_downloads", []),
                scraped_at=entry.get("scraped_at", ""),
            )
            for entry in data
        ]
    else:
        policies = []

    results = download_policy_pdfs(policies)
    output_dir = DATA_DIR / "pdfs"
    return dg.MaterializeResult(
        metadata={
            "item_count": len(results),
            "output_path": str(output_dir),
        }
    )
