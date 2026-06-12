"""Site layer assets — generate site/src/content/ from data/clean/."""

from __future__ import annotations

import shutil
from typing import TYPE_CHECKING

import dagster as dg

from transforms.blog import transform_blog
from transforms.events import transform_events
from transforms.main import CLEAN_DIR, CONTENT_DIR
from transforms.party_info import transform_party_info
from transforms.policies import transform_policies
from transforms.team import transform_team

if TYPE_CHECKING:
    from pathlib import Path


def _file_count(path: Path) -> int:
    """Count .md files written directly under *path*."""
    if not path.exists():
        return 0
    return sum(1 for p in path.iterdir() if p.suffix == ".md")


@dg.asset(group_name="site", deps=["clean_policies"])
def site_policies() -> dg.MaterializeResult:
    """Write site/src/content/policies/ from data/clean/policy/."""
    out_dir = CONTENT_DIR / "policies"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    transform_policies(CLEAN_DIR, CONTENT_DIR)
    return dg.MaterializeResult(
        metadata={
            "item_count": _file_count(out_dir),
            "output_path": str(out_dir),
        }
    )


@dg.asset(group_name="site", deps=["clean_blog"])
def site_blog() -> dg.MaterializeResult:
    """Write site/src/content/blog/ from data/clean/blog-post/."""
    out_dir = CONTENT_DIR / "blog"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    transform_blog(CLEAN_DIR, CONTENT_DIR)
    return dg.MaterializeResult(
        metadata={
            "item_count": _file_count(out_dir),
            "output_path": str(out_dir),
        }
    )


@dg.asset(group_name="site", deps=["clean_events"])
def site_events() -> dg.MaterializeResult:
    """Write site/src/content/events/ from data/clean/event/."""
    out_dir = CONTENT_DIR / "events"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    transform_events(CLEAN_DIR, CONTENT_DIR)
    return dg.MaterializeResult(
        metadata={
            "item_count": _file_count(out_dir),
            "output_path": str(out_dir),
        }
    )


@dg.asset(group_name="site", deps=["clean_team"])
def site_team() -> dg.MaterializeResult:
    """Write site/src/content/team/ from data/clean/team-member/."""
    out_dir = CONTENT_DIR / "team"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    transform_team(CLEAN_DIR, CONTENT_DIR)
    return dg.MaterializeResult(
        metadata={
            "item_count": _file_count(out_dir),
            "output_path": str(out_dir),
        }
    )


@dg.asset(group_name="site", deps=["clean_party_info"])
def site_party_info() -> dg.MaterializeResult:
    """Write site/src/content/party-info/ from data/clean/party-information/."""
    out_dir = CONTENT_DIR / "party-info"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    transform_party_info(CLEAN_DIR, CONTENT_DIR)
    return dg.MaterializeResult(
        metadata={
            "item_count": _file_count(out_dir),
            "output_path": str(out_dir),
        }
    )
