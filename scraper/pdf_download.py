#!/usr/bin/env python3
"""Download policy PDFs from Google Drive and other sources."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from .client import DATA_DIR

logger = logging.getLogger(__name__)

POLICY_ASSETS_DIR = DATA_DIR / "policy-assets"
REFERENCE_FILE = POLICY_ASSETS_DIR / "reference.json"

GDRIVE_FILE_ID_RE = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")


def download_policy_pdfs(policies: list, dry_run: bool = False) -> list[dict]:
    POLICY_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    reference = _load_reference()
    results: list[dict] = []

    for policy in policies:
        if not policy.pdf_downloads:
            continue
        for url in policy.pdf_downloads:
            result = _download_single(url, policy.slug, reference, dry_run=dry_run)
            results.append(result)

    _save_reference(reference)
    return results


def _load_reference() -> dict:
    if REFERENCE_FILE.exists():
        try:
            return json.loads(REFERENCE_FILE.read_text())
        except (json.JSONDecodeError, IOError) as e:
            logger.warning("Could not load reference.json: %s, starting fresh", e)
    return {"downloads": {}}


def _save_reference(reference: dict) -> None:
    REFERENCE_FILE.write_text(json.dumps(reference, indent=2, ensure_ascii=False))
    logger.info("Updated reference registry at %s", REFERENCE_FILE)


def _extract_file_id(url: str) -> str | None:
    match = GDRIVE_FILE_ID_RE.search(url)
    return match.group(1) if match else None


def _make_direct_download_url(url: str) -> str:
    file_id = _extract_file_id(url)
    if file_id:
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def _slug_from_filename(filename: str) -> str:
    name = filename.replace("Opportunity_", "").replace(".pdf", "")
    parts = name.split("_")
    if parts:
        return parts[0].lower().replace(" ", "-").strip("-")
    return "unknown"


def _download_single(url: str, policy_slug: str, reference: dict, dry_run: bool = False) -> dict:
    file_id = _extract_file_id(url)

    if file_id and file_id in reference.get("downloads", {}):
        entry = reference["downloads"][file_id]
        existing_path = POLICY_ASSETS_DIR / entry.get("filename", "")
        if existing_path.exists():
            logger.info("Skipping %s (already exists)", policy_slug)
            return {"policy_slug": policy_slug, "url": url, "filename": str(existing_path.name), "status": "skipped_existing"}
        logger.info("Re-downloading %s (file missing)", file_id)

    if file_id:
        temp_filename = f"{file_id}.pdf"
    else:
        parsed = urlparse(url)
        temp_filename = Path(parsed.path).name or "download.pdf"
        if not temp_filename.lower().endswith(".pdf"):
            temp_filename += ".pdf"

    output_path = POLICY_ASSETS_DIR / temp_filename

    if dry_run:
        logger.info("[DRY RUN] Would download %s", url)
        return {"policy_slug": policy_slug, "url": url, "filename": temp_filename, "status": "dry_run"}

    direct_url = _make_direct_download_url(url)
    content_type, effective_filename = None, None

    headers_file = POLICY_ASSETS_DIR / "_headers.tmp"
    result = subprocess.run(
        ["curl", "--silent", "--show-error", "--location", "--max-time", "60",
         "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
         "--write-out", "%{http_code}\n%{content_type}\n%{filename_effective}",
         "--output", str(output_path), "-D", str(headers_file), direct_url],
        capture_output=True, text=True, timeout=90,
    )

    lines = result.stdout.strip().split("\n")
    if len(lines) >= 3:
        content_type = lines[-2]
        effective_filename = lines[-1]

    response_text = output_path.read_text(errors="replace") if output_path.exists() else ""

    if content_type and "text/html" in content_type and "<form" in response_text.lower():
        logger.debug("Detected virus scan interstitial")
        output_path.unlink(missing_ok=True)

        confirm_match = re.search(r'name="confirm" value="([^"]+)"', response_text)
        uuid_match = re.search(r'name="uuid" value="([^"]+)"', response_text)

        if confirm_match and uuid_match:
            confirm_token = confirm_match.group(1)
            uuid_val = uuid_match.group(1)
            retry_url = f"{direct_url}&confirm={confirm_token}&uuid={uuid_val}"

            headers_file.unlink(missing_ok=True)
            result = subprocess.run(
                ["curl", "--silent", "--show-error", "--location", "--max-time", "120",
                 "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                 "--write-out", "%{http_code}\n%{content_type}\n%{filename_effective}",
                 "--output", str(output_path), "-D", str(headers_file), retry_url],
                capture_output=True, text=True, timeout=150,
            )

            lines = result.stdout.strip().split("\n")
            if len(lines) >= 3:
                content_type = lines[-2]
                effective_filename = lines[-1]
        else:
            logger.warning("Could not extract confirm token from virus scan page")

    headers_file.unlink(missing_ok=True)

    if not output_path.exists() or output_path.stat().st_size == 0:
        error_msg = result.stderr or "Empty response"
        logger.error("Failed to download %s: %s", url, error_msg)
        return {"policy_slug": policy_slug, "url": url, "filename": temp_filename, "status": "failed", "error": error_msg}

    actual_filename = effective_filename if effective_filename and effective_filename.endswith(".pdf") else temp_filename
    if actual_filename != temp_filename:
        real_path = POLICY_ASSETS_DIR / actual_filename
        if not real_path.exists():
            output_path.rename(real_path)
            output_path = real_path

    entry = {
        "source_url": url,
        "policy_slug": policy_slug,
        "filename": actual_filename,
        "downloaded_at": datetime.now().isoformat(),
        "size_bytes": output_path.stat().st_size,
    }
    key = file_id if file_id else url
    reference["downloads"][key] = entry

    logger.info("Downloaded %s -> %s (%d bytes)", policy_slug, actual_filename, entry["size_bytes"])
    return {"policy_slug": policy_slug, "url": url, "filename": actual_filename, "status": "downloaded"}


def migrate_existing_pdfs() -> None:
    if not POLICY_ASSETS_DIR.exists():
        return

    reference = _load_reference()
    existing_filenames = {e["filename"] for e in reference.get("downloads", {}).values()}

    for pdf_path in sorted(POLICY_ASSETS_DIR.glob("*.pdf")):
        if pdf_path.name in existing_filenames:
            continue
        slug = _slug_from_filename(pdf_path.name)
        reference["downloads"][f"_migrated_{pdf_path.name}"] = {
            "source_url": None,
            "policy_slug": slug,
            "filename": pdf_path.name,
            "downloaded_at": datetime.fromtimestamp(pdf_path.stat().st_mtime).isoformat(),
            "size_bytes": pdf_path.stat().st_size,
        }
        logger.info("Migrated existing PDF: %s", pdf_path.name)

    _save_reference(reference)
    logger.info("Migration complete: %d PDFs registered", len(reference["downloads"]))
