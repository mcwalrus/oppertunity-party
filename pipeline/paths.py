"""Shared path constants for the pipeline.

All data directories are resolved relative to the project root
(where ``pyproject.toml`` lives).
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Source layer — raw scraper output (written by ingestion, never by consumers)
# ---------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data" / "sources" / "opportunity-website"

# ---------------------------------------------------------------------------
# Clean layer — normalised content, canonical source for all consumers
# ---------------------------------------------------------------------------
CLEAN_DIR = Path("data/clean")

# ---------------------------------------------------------------------------
# Site layer — Astro SSG input, rebuilt from clean on every run
# ---------------------------------------------------------------------------
CONTENT_DIR = Path("site/src/content")

# ---------------------------------------------------------------------------
# HTTP cache — ephemeral, separate from source data
# ---------------------------------------------------------------------------
CACHE_DIR = PROJECT_ROOT / "data" / ".cache"

# ---------------------------------------------------------------------------
# PDF artefacts — downloaded PDFs and their reference registry
# ---------------------------------------------------------------------------
POLICY_ASSETS_DIR = DATA_DIR / "pdfs"
REFERENCE_FILE = POLICY_ASSETS_DIR / "reference.json"
