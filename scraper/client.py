"""Shared utilities for scraping the Opportunity Party website.

Uses curl subprocess for HTTP requests since the Python sandbox
restricts direct network access. All scraped output goes into the
data/ directory.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE_URL = "https://www.opportunity.org.nz"

# Project root is where pyproject.toml lives
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# All scraped data goes here
DATA_DIR = PROJECT_ROOT / "data"


def clean_data() -> None:
    """Remove all scraped data, preserving the policy-assets folder."""
    if DATA_DIR.exists():
        for child in DATA_DIR.iterdir():
            if child.name == "policy-assets":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
        logger.info("Cleaned data directory (preserved policy-assets)")


def fetch_html(path: str) -> str:
    """Fetch a page via curl and return raw HTML string."""
    url = f"{BASE_URL}{path}"
    logger.info("Fetching %s", url)
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--max-time", "30",
            "--user-agent",
            "OpportunityPartyScraper/1.0 (research purpose)",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr}")
    return result.stdout


def fetch_page(path: str) -> BeautifulSoup:
    """Fetch a page and return a parsed BeautifulSoup object."""
    html = fetch_html(path)
    return BeautifulSoup(html, "lxml")


def fetch_json(path: str) -> dict | list:
    """Fetch a JSON endpoint and return parsed data."""
    url = f"{BASE_URL}{path}"
    logger.info("Fetching JSON %s", url)
    result = subprocess.run(
        [
            "curl",
            "--silent",
            "--show-error",
            "--fail",
            "--location",
            "--max-time", "30",
            "--header", "Accept: application/json",
            url,
        ],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed for {url}: {result.stderr}")
    return json.loads(result.stdout)


def save_content(directory: Path, filename: str, content: str) -> Path:
    """Save content string to a directory, creating it if needed."""
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / filename
    filepath.write_text(content, encoding="utf-8")
    logger.info("Saved %s", filepath)
    return filepath


def extract_main_content(soup: BeautifulSoup) -> str:
    """Extract the main content area from a page, stripping nav/footer noise."""
    for selector in [
        "main",
        "[role='main']",
        ".page-content",
        "#content",
        ".content",
        ".main-content",
        "article",
    ]:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 100:
            return el.get_text(separator="\n", strip=True)

    body = soup.find("body")
    if body:
        for tag in body.find_all(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        return body.get_text(separator="\n", strip=True)

    return soup.get_text(separator="\n", strip=True)