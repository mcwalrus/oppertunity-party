#!/usr/bin/env python3
"""Download policy PDFs from Google Drive and other sources."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from pipeline.paths import POLICY_ASSETS_DIR, REFERENCE_FILE

logger = logging.getLogger(__name__)

# Path constants imported from pipeline.paths

GDRIVE_FILE_ID_RE = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


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


def migrate_existing_pdfs() -> None:
    """Register PDFs already on disk into reference.json (idempotent)."""
    if not POLICY_ASSETS_DIR.exists():
        return

    reference = _load_reference()
    known_filenames = {e["filename"] for e in reference.get("downloads", {}).values()}

    for pdf_path in sorted(POLICY_ASSETS_DIR.glob("*.pdf")):
        if pdf_path.name in known_filenames:
            continue
        slug = _slug_from_filename(pdf_path.name)
        reference["downloads"][f"_migrated_{pdf_path.name}"] = {
            "source_url": None,
            "policy_slug": slug,
            "filename": pdf_path.name,
            "downloaded_at": datetime.fromtimestamp(pdf_path.stat().st_mtime).isoformat(),
            "size_bytes": pdf_path.stat().st_size,
            "md5": _file_md5(pdf_path),
        }
        logger.info("Migrated existing PDF: %s", pdf_path.name)

    _save_reference(reference)
    logger.info("Migration complete: %d PDFs registered", len(reference["downloads"]))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _load_reference() -> dict:
    if REFERENCE_FILE.exists():
        try:
            return json.loads(REFERENCE_FILE.read_text())
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Could not load reference.json: %s — starting fresh", e)
    return {"downloads": {}}


def _save_reference(reference: dict) -> None:
    REFERENCE_FILE.write_text(json.dumps(reference, indent=2, ensure_ascii=False) + "\n")
    logger.info("Updated reference registry at %s", REFERENCE_FILE)


def _file_md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _canonical_for_hash(md5: str, reference: dict) -> str | None:
    """Return the filename already registered with this MD5, if any."""
    for entry in reference.get("downloads", {}).values():
        if entry.get("md5") == md5:
            return entry.get("filename")
    return None


def _extract_file_id(url: str) -> str | None:
    match = GDRIVE_FILE_ID_RE.search(url)
    return match.group(1) if match else None


def _slug_from_filename(filename: str) -> str:
    name = filename.replace("Opportunity_", "").replace(".pdf", "")
    parts = name.split("_")
    if parts:
        return parts[0].lower().replace(" ", "-").strip("-")
    return "unknown"


# ---------------------------------------------------------------------------
# Download dispatch
# ---------------------------------------------------------------------------


def _download_single(url: str, policy_slug: str, reference: dict, dry_run: bool = False) -> dict:
    file_id = _extract_file_id(url)
    key = file_id if file_id else url

    # Already registered and file present — skip
    existing = reference.get("downloads", {}).get(key)
    if existing:
        existing_path = POLICY_ASSETS_DIR / existing.get("filename", "")
        if existing_path.exists():
            logger.info("Skipping %s (already at %s)", key, existing["filename"])
            return {
                "policy_slug": policy_slug,
                "url": url,
                "filename": existing["filename"],
                "status": "skipped",
            }

    if dry_run:
        logger.info("[DRY RUN] Would download %s", url)
        return {"policy_slug": policy_slug, "url": url, "filename": "?", "status": "dry_run"}

    if file_id:
        return _download_gdrive(file_id, url, policy_slug, key, reference)
    else:
        return _download_direct(url, policy_slug, key, reference)


def _download_gdrive(file_id: str, url: str, policy_slug: str, key: str, reference: dict) -> dict:
    """Download a Google Drive file via gdown (handles auth + proper filename)."""
    try:
        import gdown
    except ImportError:
        logger.error("gdown not installed — run: uv add gdown")
        return {
            "policy_slug": policy_slug,
            "url": url,
            "filename": "",
            "status": "failed",
            "error": "gdown not installed",
        }

    # Download into a temp file so we can hash-check before committing
    tmp = POLICY_ASSETS_DIR / f"_tmp_{file_id}.pdf"
    tmp.unlink(missing_ok=True)

    downloaded = gdown.download(id=file_id, output=str(tmp), quiet=False)
    if not downloaded or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        return {
            "policy_slug": policy_slug,
            "url": url,
            "filename": "",
            "status": "failed",
            "error": "gdown returned no file",
        }

    digest = _file_md5(tmp)
    canonical = _canonical_for_hash(digest, reference)

    if canonical:
        # Content already on disk under a proper name — discard the temp copy
        tmp.unlink()
        logger.info("GDrive %s matches existing %s — no duplicate stored", file_id, canonical)
        status = "deduplicated"
        filename = canonical
    else:
        # New content — keep it; gdown may have used the Drive filename inside tmp
        # but we saved to a fixed temp path, so just keep it named by file_id
        filename = f"{file_id}.pdf"
        final = POLICY_ASSETS_DIR / filename
        tmp.rename(final)
        status = "downloaded"
        logger.info("Downloaded %s -> %s (%d bytes)", policy_slug, filename, final.stat().st_size)

    reference["downloads"][key] = {
        "source_url": url,
        "policy_slug": policy_slug,
        "filename": filename,
        "downloaded_at": datetime.now().isoformat(),
        "size_bytes": (POLICY_ASSETS_DIR / filename).stat().st_size,
        "md5": digest,
    }
    return {"policy_slug": policy_slug, "url": url, "filename": filename, "status": status}


def _download_direct(url: str, policy_slug: str, key: str, reference: dict) -> dict:
    """Download a plain URL (non-GDrive) using curl."""
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "download.pdf"
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"

    output_path = POLICY_ASSETS_DIR / filename

    result = subprocess.run(
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
            str(output_path),
            url,
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )

    if not output_path.exists() or output_path.stat().st_size == 0:
        return {
            "policy_slug": policy_slug,
            "url": url,
            "filename": filename,
            "status": "failed",
            "error": result.stderr,
        }

    digest = _file_md5(output_path)
    canonical = _canonical_for_hash(digest, reference)
    if canonical and canonical != filename:
        logger.info(
            "Direct download %s matches existing %s — removing duplicate", filename, canonical
        )
        output_path.unlink()
        filename = canonical

    reference["downloads"][key] = {
        "source_url": url,
        "policy_slug": policy_slug,
        "filename": filename,
        "downloaded_at": datetime.now().isoformat(),
        "size_bytes": (POLICY_ASSETS_DIR / filename).stat().st_size,
        "md5": digest,
    }
    logger.info("Downloaded %s -> %s", policy_slug, filename)
    return {"policy_slug": policy_slug, "url": url, "filename": filename, "status": "downloaded"}
