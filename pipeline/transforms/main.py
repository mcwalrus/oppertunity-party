"""Transform pipeline: sources → clean layer → site/src/content/.

Pipeline stages
---------------
1. **Source transform** — reads ``data/sources/{source}/`` and writes
   normalized items to ``data/clean/{content-type}/{slug}/``.
   Each item gets a ``{slug}.md`` (YAML frontmatter + body) and
   ``meta.json`` (identical provenance fields).

2. **Site transform** — reads ``data/clean/{content-type}/`` and writes
   Astro-compatible markdown to ``site/src/content/{collection}/``.
   The site layer is ephemeral: it is rebuilt on every run and must not
   be hand-edited.
"""

import shutil

from pipeline.paths import CLEAN_DIR, CONTENT_DIR
from pipeline.transforms.blog import transform_blog
from pipeline.transforms.events import transform_events
from pipeline.transforms.party_info import transform_party_info
from pipeline.transforms.policies import transform_policies
from pipeline.transforms.sources.opportunity_website import transform_opportunity_website
from pipeline.transforms.team import transform_team


def transform_all() -> None:
    """Run the full pipeline: source → clean → site/src/content/."""
    # -----------------------------------------------------------------------
    # Stage 1: source → clean
    # -----------------------------------------------------------------------
    print("🔄 Stage 1: opportunity-website → data/clean/")
    transform_opportunity_website()

    # -----------------------------------------------------------------------
    # Stage 2: clean → site/src/content/
    # -----------------------------------------------------------------------
    print("\n🔄 Stage 2: data/clean/ → site/src/content/")

    # Wipe and recreate content dir for idempotency
    if CONTENT_DIR.exists():
        shutil.rmtree(CONTENT_DIR)
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    transform_policies(CLEAN_DIR, CONTENT_DIR)
    transform_blog(CLEAN_DIR, CONTENT_DIR)
    transform_events(CLEAN_DIR, CONTENT_DIR)
    transform_team(CLEAN_DIR, CONTENT_DIR)
    transform_party_info(CLEAN_DIR, CONTENT_DIR)

    print("\n✅ All transforms complete.")


if __name__ == "__main__":
    transform_all()
