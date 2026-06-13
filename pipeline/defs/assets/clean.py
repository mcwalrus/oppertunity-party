"""Clean layer assets — normalise raw scraper output to data/clean/."""

from pathlib import Path

import dagster as dg
from dagster import AssetExecutionContext

from pipeline.defs.partitions import policy_slug_partitions
from pipeline.transforms.sources.opportunity_website import (
    CLEAN_DIR,
    regenerate_clean_index,
    transform_opportunity_website,
)


def _item_count(path: Path) -> int:
    """Count immediate subdirectories (one per cleaned item) under *path*."""
    if not path.exists():
        return 0
    return sum(1 for p in path.iterdir() if p.is_dir())


@dg.asset(group_name="clean", deps=["raw_policies"])
def clean_policies() -> dg.MaterializeResult:
    """Normalise raw policy data → data/clean/policy/."""
    transform_opportunity_website(content_type="policy")
    output_dir = CLEAN_DIR / "policy"
    return dg.MaterializeResult(
        metadata={
            "item_count": _item_count(output_dir),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="clean", deps=["raw_team"])
def clean_team() -> dg.MaterializeResult:
    """Normalise raw team data → data/clean/team-member/."""
    transform_opportunity_website(content_type="team")
    output_dir = CLEAN_DIR / "team-member"
    return dg.MaterializeResult(
        metadata={
            "item_count": _item_count(output_dir),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="clean", deps=["raw_blog"])
def clean_blog() -> dg.MaterializeResult:
    """Normalise raw blog (and news) data → data/clean/blog-post/."""
    transform_opportunity_website(content_type="blog")
    output_dir = CLEAN_DIR / "blog-post"
    return dg.MaterializeResult(
        metadata={
            "item_count": _item_count(output_dir),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="clean", deps=["raw_events"])
def clean_events() -> dg.MaterializeResult:
    """Normalise raw event data → data/clean/event/."""
    transform_opportunity_website(content_type="events")
    output_dir = CLEAN_DIR / "event"
    return dg.MaterializeResult(
        metadata={
            "item_count": _item_count(output_dir),
            "output_path": str(output_dir),
        }
    )


@dg.asset(group_name="clean", deps=["raw_party_info"])
def clean_party_info() -> dg.MaterializeResult:
    """Normalise raw party-information data → data/clean/party-information/."""
    transform_opportunity_website(content_type="party-information")
    output_dir = CLEAN_DIR / "party-information"
    return dg.MaterializeResult(
        metadata={
            "item_count": _item_count(output_dir),
            "output_path": str(output_dir),
        }
    )


@dg.asset(
    group_name="clean",
    deps=["raw_pdfs"],
    partitions_def=policy_slug_partitions,
)
def clean_pdfs(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Normalise raw PDF-document data → data/clean/pdf-document/ for a single policy slug."""
    policy_slug = context.partition_key
    transform_opportunity_website(content_type="pdf-document", policy_slug=policy_slug)
    output_dir = CLEAN_DIR / "pdf-document"
    return dg.MaterializeResult(
        metadata={
            "policy_slug": policy_slug,
            "item_count": _item_count(output_dir),
            "output_path": str(output_dir),
        }
    )


@dg.asset(
    group_name="clean",
    deps=[
        "clean_policies",
        "clean_team",
        "clean_blog",
        "clean_events",
        "clean_party_info",
        "clean_pdfs",
    ],
)
def clean_index() -> dg.MaterializeResult:
    """Regenerate data/clean/_index.json from all existing clean content."""
    count = regenerate_clean_index()
    index_path = CLEAN_DIR / "_index.json"
    return dg.MaterializeResult(
        metadata={
            "item_count": count,
            "output_path": str(index_path),
        }
    )
