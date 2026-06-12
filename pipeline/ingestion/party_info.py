"""Scraper for Opportunity Party information pages."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pymupdf4llm
from markdownify import markdownify

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

from pipeline.ingestion.client import DATA_DIR, fetch_page, save_content
from pipeline.ingestion.models import PartyInfo
from pipeline.paths import POLICY_ASSETS_DIR as PARTY_PDF_DIR

logger = logging.getLogger(__name__)


def scrape_party_info() -> list[PartyInfo]:
    """Scrape party information, about, and meet-q pages."""
    pages: list[PartyInfo] = []

    # Scrape the main party-information page
    try:
        soup = fetch_page("/party-information", category="party-info")
        content_md = _extract_content(soup)
        pdf_links = _extract_pdf_links(soup)

        pages.append(
            PartyInfo(
                section="party-information",
                url="https://www.opportunity.org.nz/party-information",
                content=content_md,
                pdf_downloads=pdf_links,
            )
        )
        logger.info("Scraped party-information page (found %d PDF links)", len(pdf_links))

        # Look for sub-links on the party-information page
        sub_links = _discover_sub_links(soup)
        for section_name, path in sub_links.items():
            try:
                sub_soup = fetch_page(path, category="party-info")
                sub_content = _extract_content(sub_soup)
                pages.append(
                    PartyInfo(
                        section=section_name,
                        url=f"https://www.opportunity.org.nz{path}",
                        content=sub_content,
                    )
                )
                logger.info("Scraped party info sub-page: %s", section_name)
            except Exception as e:
                logger.error("Failed to scrape sub-page %s: %s", section_name, e)

    except Exception as e:
        logger.error("Failed to scrape party-information: %s", e)

    # Scrape the about page
    try:
        about_soup = fetch_page("/about", category="party-info")
        about_content = _extract_content(about_soup)
        pages.append(
            PartyInfo(
                section="about",
                url="https://www.opportunity.org.nz/about",
                content=about_content,
            )
        )
        logger.info("Scraped about page")
    except Exception as e:
        logger.error("Failed to scrape about page: %s", e)

    # Scrape the /meet-q leader page (party-level page, not a candidate profile)
    try:
        meet_q_soup = fetch_page("/meet-q", category="party-info")
        meet_q_content = _extract_content(meet_q_soup)
        pages.append(
            PartyInfo(
                section="meet-q",
                url="https://www.opportunity.org.nz/meet-q",
                content=meet_q_content,
            )
        )
        logger.info("Scraped meet-q page")
    except Exception as e:
        logger.error("Failed to scrape meet-q page: %s", e)

    return pages


def save_party_info(pages: list[PartyInfo]) -> dict[str, Path]:
    """Save party information to markdown files and JSON index."""
    output_dir = DATA_DIR / "party-information"
    saved: dict[str, Path] = {}

    for page in pages:
        slug = page.section.replace(" ", "-").lower()
        md_path = save_content(
            output_dir,
            f"{slug}.md",
            _format_info_md(page),
        )
        saved[slug] = md_path

    json_data = [
        {
            "section": p.section,
            "url": p.url,
            "content": p.content,
            "pdf_downloads": [[label, url] for label, url in p.pdf_downloads],
            "scraped_at": p.scraped_at,
        }
        for p in pages
    ]
    json_path = save_content(
        output_dir,
        "index.json",
        json.dumps(json_data, indent=2, ensure_ascii=False),
    )
    saved["_index"] = json_path
    return saved


# PARTY_PDF_DIR imported from pipeline.paths (as POLICY_ASSETS_DIR)


def download_and_convert_party_pdfs(pages: list[PartyInfo]) -> list[dict]:
    """Download and convert PDFs linked from party-information pages.

    Raw PDFs are cached to data/pdfs/ (alongside policy PDFs).
    Converted markdown is saved to data/party-information/ and the text
    is injected back into party-information.md so everything is
    queryable in one place.
    """
    output_dir = DATA_DIR / "party-information"
    output_dir.mkdir(parents=True, exist_ok=True)
    PARTY_PDF_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    for page in pages:
        if not page.pdf_downloads:
            continue
        for label, url in page.pdf_downloads:
            try:
                # If the converted markdown already exists, skip download+conversion
                md_path = output_dir / f"{label}.md"
                if md_path.exists() and md_path.stat().st_size > 0:
                    results.append(
                        {
                            "label": label,
                            "url": url,
                            "output": str(md_path),
                            "status": "ok",
                        }
                    )
                    logger.info("Party PDF already converted: %s", md_path.name)
                    continue

                pdf_path = _download_party_pdf(label, url, PARTY_PDF_DIR)
                if pdf_path:
                    md_text = _convert_party_pdf(pdf_path, label, url)
                    md_path = save_content(output_dir, f"{label}.md", md_text)
                    results.append(
                        {
                            "label": label,
                            "url": url,
                            "output": str(md_path),
                            "status": "ok",
                        }
                    )
                    logger.info("Party PDF ready: %s -> %s", label, md_path.name)
                else:
                    results.append({"label": label, "url": url, "status": "failed"})
            except Exception as e:
                logger.error("Failed to process party PDF %s: %s", label, e)
                results.append({"label": label, "url": url, "status": "error", "error": str(e)})

    # Embed converted content back into party-information.md
    if results:
        _inject_pdf_content(output_dir, results)

    return results


def _download_party_pdf(label: str, url: str, pdf_dir: Path) -> Path | None:
    """Download a Google Drive PDF to pdf_dir; return local path or None.

    Tries gdown first (handles auth/confirmation pages); falls back to
    curl (direct export URL) if gdown cannot reach the network.  A hard
    timeout prevents a broken or private link hanging the scraper.
    """
    pdf_path = pdf_dir / f"{label}.pdf"
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        logger.info("Skipping %s (already downloaded)", label)
        return pdf_path

    file_id = _extract_gdrive_file_id(url)
    if not file_id:
        logger.error("Could not extract Google Drive file ID from %s", url)
        return None

    # --- attempt 1: gdown (handles Drive auth & confirmation pages) ---
    try:
        subprocess.run(
            ["uv", "run", "gdown", file_id, "-O", str(pdf_path)],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("gdown timed out for %s — trying curl fallback", label)
        pdf_path.unlink(missing_ok=True)

    if _is_valid_pdf(pdf_path):
        logger.info("Downloaded %s via gdown (%d bytes)", label, pdf_path.stat().st_size)
        return pdf_path

    pdf_path.unlink(missing_ok=True)

    # --- attempt 2: curl with direct export URL ---
    logger.info("Falling back to curl for %s", label)
    direct_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        subprocess.run(
            [
                "curl",
                "--silent",
                "--show-error",
                "--location",
                "--max-time",
                "60",
                "--user-agent",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "--output",
                str(pdf_path),
                direct_url,
            ],
            capture_output=True,
            timeout=90,
            check=False,
        )
    except subprocess.TimeoutExpired:
        logger.warning("curl timed out for %s", label)
        pdf_path.unlink(missing_ok=True)
        return None

    if _is_valid_pdf(pdf_path):
        logger.info("Downloaded %s via curl (%d bytes)", label, pdf_path.stat().st_size)
        return pdf_path

    pdf_path.unlink(missing_ok=True)
    logger.error("All download attempts failed for %s (%s)", label, url)
    return None


def _is_valid_pdf(path: Path) -> bool:
    """Return True if path exists, is non-empty, and starts with the PDF magic bytes."""
    return path.exists() and path.stat().st_size > 0 and path.read_bytes()[:4] == b"%PDF"


def _convert_party_pdf(pdf_path: Path, label: str, source_url: str) -> str:
    """Extract text from a PDF and format as plain markdown."""
    raw = pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)
    text = re.sub(r"\n{3,}", "\n\n", raw).strip()
    title = label.replace("-", " ").title()
    return f"# {title}\n\n> **Source**: {source_url}\n\n{text}\n"


def _extract_gdrive_file_id(url: str) -> str | None:
    """Extract the file ID from a Google Drive URL."""
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url)
    return m.group(1) if m else None


def _inject_pdf_content(output_dir: Path, results: list[dict]) -> None:
    """Embed converted PDF sections back into party-information.md.

    Appends each successfully converted document as a titled section
    separated by horizontal rules so the content is queryable in one
    place.  Re-running is idempotent: previously injected sections are
    stripped before the new ones are appended.
    """
    party_md_path = output_dir / "party-information.md"
    if not party_md_path.exists():
        logger.warning("party-information.md not found; skipping PDF injection")
        return

    current = party_md_path.read_text()

    # Strip any previously injected PDF sections (sentinel: first "---\n\n## " after a blank line)
    sentinel = "\n\n---\n\n## "
    cut_pos = current.find(sentinel)
    base_content = current[:cut_pos].rstrip() if cut_pos != -1 else current.rstrip()

    # Append each successfully converted PDF as its own section
    sections: list[str] = [base_content]
    for r in results:
        if r.get("status") != "ok":
            continue
        pdf_md = Path(r["output"]).read_text().strip()
        sections.append(f"\n\n---\n\n{pdf_md}")

    party_md_path.write_text("".join(sections) + "\n")
    injected = len(sections) - 1
    logger.info("Injected %d PDF section(s) into party-information.md", injected)


def _extract_pdf_links(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Extract (label, url) pairs for Google Drive PDFs linked from the page.

    Looks at each list item that contains a Google Drive file link and uses
    the nearest heading (h3/h4/strong) as the label, falling back to the
    link text if no heading is found.
    """
    results: list[tuple[str, str]] = []
    gdrive_re = re.compile(r"drive\.google\.com/file/d/")
    for li in soup.select("li"):
        link = li.find("a", href=gdrive_re)
        if not link:
            continue
        heading = li.find(["h3", "h4", "h5", "strong"])
        raw_label = heading.get_text(strip=True) if heading else link.get_text(strip=True)
        label = raw_label.lower().replace(" ", "-")
        label = re.sub(r"[^a-z0-9-]", "", label).strip("-")
        raw_link_href = link.get("href", "")
        if label and isinstance(raw_link_href, str):
            results.append((label, raw_link_href))
    return results


def _discover_sub_links(soup: BeautifulSoup) -> dict[str, str]:
    """Find sub-page links on the party-information page."""
    sub_links: dict[str, str] = {}
    for a_tag in soup.select("a[href]"):
        href = a_tag.get("href", "")
        if not isinstance(href, str):
            continue
        text = a_tag.get_text(strip=True)
        if any(
            keyword in href.lower()
            for keyword in ["constitution", "governance", "registration", "rules"]
        ):
            name = text if text else href.strip("/").split("/")[-1].replace("-", " ")
            sub_links[name] = href
    return sub_links


def _extract_content(soup: BeautifulSoup) -> str:
    for selector in ["main", "[role='main']", ".page-content", "article"]:
        el = soup.select_one(selector)
        if el and len(el.get_text(strip=True)) > 50:
            return markdownify(str(el), heading_style="ATX").strip()
    return ""


def _format_info_md(page: PartyInfo) -> str:
    lines = [
        f"# {page.section.replace('-', ' ').title()}",
        "",
        f"> **URL**: {page.url}",
        f"> **Scraped**: {page.scraped_at}",
        "",
        page.content,
    ]
    return "\n".join(lines) + "\n"
