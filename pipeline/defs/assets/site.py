"""Site layer assets — content generation, build, sitemap resolution, deploy."""

# NOTE: do NOT add `from __future__ import annotations` here. Dagster inspects
# the ``context`` parameter's annotation at decoration time to validate it
# against ``AssetExecutionContext``; PEP-563 string annotations break that.

import os
import shutil
import subprocess
from pathlib import Path

import dagster as dg
from dagster import AssetExecutionContext

from pipeline.paths import CLEAN_DIR, CONTENT_DIR
from pipeline.transforms.blog import transform_blog
from pipeline.transforms.events import transform_events
from pipeline.transforms.party_info import transform_party_info
from pipeline.transforms.policies import transform_policies
from pipeline.transforms.team import transform_team

# ---------------------------------------------------------------------------
# Site build paths
# ---------------------------------------------------------------------------

SITE_ROOT = Path("site")
DIST_DIR = SITE_ROOT / "dist"


def _file_count(path: Path) -> int:
    """Count .md files written directly under *path*."""
    if not path.exists():
        return 0
    return sum(1 for p in path.iterdir() if p.suffix == ".md")


def _run_pnpm(context: AssetExecutionContext, script: str) -> subprocess.CompletedProcess[str]:
    """Run a pnpm script inside ``site/`` and stream output to the Dagster log.

    Returns the completed :class:`subprocess.CompletedProcess` so callers can
    surface their own metadata.  Callers are responsible for raising on a
    non-zero exit code.
    """
    context.log.info("Running `pnpm %s` in %s/", script, SITE_ROOT)
    result = subprocess.run(
        ["pnpm", script],
        cwd=SITE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        context.log.info(result.stdout.rstrip())
    if result.stderr:
        context.log.warning(result.stderr.rstrip())
    return result


def _raise_on_failure(
    context: AssetExecutionContext,
    script: str,
    result: subprocess.CompletedProcess[str],
) -> None:
    """Raise a Dagster :class:`Failure` if the subprocess exited non-zero."""
    if result.returncode != 0:
        # Trim very long output to keep failure metadata readable.
        stdout = (result.stdout or "")[-2000:]
        stderr = (result.stderr or "")[-2000:]
        raise dg.Failure(
            description=f"`pnpm {script}` exited {result.returncode}",
            metadata={
                "returncode": result.returncode,
                "stdout_tail": stdout,
                "stderr_tail": stderr,
            },
        )


# ---------------------------------------------------------------------------
# Site content generation — write site/src/content/{collection}/ from data/clean/
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Site build — `astro build` produces site/dist/ from site/src/content/
# ---------------------------------------------------------------------------


@dg.asset(
    group_name="site",
    deps=[
        "site_policies",
        "site_blog",
        "site_events",
        "site_team",
        "site_party_info",
    ],
)
def site_build(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Run ``astro build`` to produce site/dist/ from site/src/content/."""
    result = _run_pnpm(context, "build")
    _raise_on_failure(context, "build", result)
    return dg.MaterializeResult(
        metadata={
            "output_path": str(DIST_DIR),
            "dist_exists": DIST_DIR.exists(),
        }
    )


# ---------------------------------------------------------------------------
# Sitemap resolution — rewrite docs_site_map.md with absolute URLs from SITE_URL
# ---------------------------------------------------------------------------


@dg.asset(group_name="site", deps=["site_build"])
def site_sitemap_resolved(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Rewrite ``site/dist/docs_site_map.md`` with absolute URLs.

    Requires ``SITE_URL`` to be set either via environment variable or in
    ``site/.env.local``.  Without it, the underlying script aborts fast.
    """
    if "SITE_URL" not in os.environ and not (SITE_ROOT / ".env.local").exists():
        raise dg.Failure(
            description=(
                "SITE_URL is not set. Provide it via environment variable or "
                "site/.env.local before resolving the sitemap."
            ),
        )

    result = _run_pnpm(context, "generate:sitemap")
    _raise_on_failure(context, "generate:sitemap", result)

    sitemap_path = DIST_DIR / "docs_site_map.md"
    return dg.MaterializeResult(
        metadata={
            "sitemap_path": str(sitemap_path),
            "site_url": os.environ.get("SITE_URL", "(from .env.local)"),
        }
    )


# ---------------------------------------------------------------------------
# Site deploy — publish site/dist to Cloudflare Workers via wrangler
# ---------------------------------------------------------------------------


@dg.asset(group_name="site", deps=["site_sitemap_resolved"])
def site_deploy(context: AssetExecutionContext) -> dg.MaterializeResult:
    """Deploy ``site/dist`` to Cloudflare Workers via ``pnpm deploy`` (wrangler).

    This asset is excluded from :data:`pipeline.defs.jobs.full_pipeline` and
    must be launched explicitly via the ``site_deploy_job`` job — it is a
    production-affecting action.
    """
    result = _run_pnpm(context, "deploy")
    _raise_on_failure(context, "deploy", result)
    return dg.MaterializeResult(
        metadata={
            "deploy_target": "cloudflare-workers",
        }
    )
