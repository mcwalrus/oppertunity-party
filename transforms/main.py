"""Transform scraped data from data/ into clean Astro-compatible markdown in site/src/content/."""

import shutil
from pathlib import Path

from transforms.blog import transform_blog
from transforms.events import transform_events
from transforms.party_info import transform_party_info
from transforms.policies import transform_policies
from transforms.team import transform_team

DATA_DIR = Path("data")
CONTENT_DIR = Path("site/src/content")


def transform_all() -> None:
    """Run all transforms: wipe and rebuild site/src/content/ from data/."""
    # Wipe and recreate content dir for idempotency
    if CONTENT_DIR.exists():
        shutil.rmtree(CONTENT_DIR)

    CONTENT_DIR.mkdir(parents=True, exist_ok=True)

    transform_policies(DATA_DIR, CONTENT_DIR)
    transform_blog(DATA_DIR, CONTENT_DIR)
    transform_events(DATA_DIR, CONTENT_DIR)
    transform_team(DATA_DIR, CONTENT_DIR)
    transform_party_info(DATA_DIR, CONTENT_DIR)

    print("✅ All transforms complete.")


if __name__ == "__main__":
    transform_all()
