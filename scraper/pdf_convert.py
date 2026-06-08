"""Convert Opportunity Party policy PDFs to structured markdown.

Uses pymupdf4llm for text extraction — produces structured markdown with
headings, reflowed paragraphs, and real tables, with no system dependencies
(pure-Python; no poppler required).

Each PDF has:
  - A header block: Date, Policy, Document Type (bold values on one line)
  - Body content with bullet lists, section headings, tables
  - Page footers: "Opportunity Party  <Section>  Page N"

These footers and headers are stripped to produce clean content.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

import pymupdf4llm

from .client import DATA_DIR, save_content

logger = logging.getLogger(__name__)

POLICY_ASSETS_DIR = DATA_DIR / "pdfs"
REFERENCE_FILE = POLICY_ASSETS_DIR / "reference.json"

# Header fields are emitted by pymupdf4llm as bold values on a single line:
# "Date **February 2026** Policy **Abundant Energy** Document Type **...**"
HEADER_FIELD_RE = re.compile(r"(Date|Policy|Document Type)\s+\*\*(.+?)\*\*")
# Page footer: "Opportunity Party   Tax   Page 3"  (may be bold after extraction)
PAGE_FOOTER_RE = re.compile(r"^Opportunity\s+Party\b")
PAGE_NUMBER_RE = re.compile(r"^Page\s+\d+\s*$")
# Picture placeholders inserted by pymupdf4llm
PICTURE_RE = re.compile(r"^\s*\**==>\s*picture.*<==\**\s*$")


def convert_all_pdfs() -> list[dict]:
    """Find all PDFs in data/pdfs and convert them to markdown.

    Output is organized into subdirectories under data/policies/{slug}/.
    """
    if not POLICY_ASSETS_DIR.exists():
        logger.warning("No data/pdfs directory found")
        return []

    pdfs = sorted(POLICY_ASSETS_DIR.glob("*.pdf"))
    logger.info("Found %d policy PDFs", len(pdfs))

    results: list[dict] = []
    for pdf_path in pdfs:
        try:
            entry = convert_pdf(pdf_path)
            results.append(entry)
            logger.info("Converted: %s -> %s", pdf_path.name, entry["output_file"])
        except Exception as e:
            logger.error("Failed to convert %s: %s", pdf_path.name, e)

    # Save a combined index of all PDF sources
    index_data = [
        {
            "source_file": r["source_file"],
            "title": r["title"],
            "policy": r["policy"],
            "policy_slug": r["policy_slug"],
            "date": r["date"],
            "document_type": r["document_type"],
            "output_file": r["output_file"],
        }
        for r in results
    ]
    save_content(
        DATA_DIR / "policies",
        "pdf-index.json",
        json.dumps(index_data, indent=2, ensure_ascii=False),
    )

    return results


def convert_pdf(pdf_path: Path) -> dict:
    """Convert a single policy PDF to markdown and save it.

    Saves output into data/policies/{slug}/{output_file} based on filename pattern.
    """
    raw_md = _extract_raw_markdown(pdf_path)
    header = parse_header(raw_md)
    body_md = _clean_body(raw_md)
    markdown = format_markdown(header, body_md, pdf_path)

    # Try to get policy_slug from reference.json first (for downloaded PDFs)
    policy_slug = _get_policy_slug_from_reference(pdf_path.name)
    if not policy_slug:
        policy_slug = _slug_from_filename(pdf_path.name)
    doc_type_slug = _slugify(header.get("document_type", ""))

    # Build output filename
    output_file = f"pdf-{doc_type_slug}.md" if doc_type_slug else "pdf-default.md"

    # Save into the policy's directory
    policy_dir = DATA_DIR / "policies" / policy_slug
    save_content(policy_dir, output_file, markdown)

    return {
        "source_file": pdf_path.name,
        "title": header.get("policy", policy_slug),
        "policy": header.get("policy", ""),
        "policy_slug": policy_slug,
        "date": header.get("date", ""),
        "document_type": header.get("document_type", ""),
        "output_file": str(policy_dir / output_file),
    }


def _extract_raw_markdown(pdf_path: Path) -> str:
    """Return raw markdown from pymupdf4llm (no post-processing)."""
    return pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)


def parse_header(raw_md: str) -> dict[str, str]:
    """Pull Date / Policy / Document Type out of the bold header line(s).

    pymupdf4llm renders the header as:
      Date **February 2026** Policy **Abundant Energy** Document Type **Policy Overview**
    """
    header: dict[str, str] = {}
    for key, value in HEADER_FIELD_RE.findall(raw_md):
        header[key.lower().replace(" ", "_")] = value.strip()
    return header


def _clean_body(raw_md: str) -> str:
    """Strip artifacts from pymupdf4llm output and return clean body markdown.

    Removes:
      1. Picture placeholders  (**==> picture ... <==**)
      2. Page footers / standalone page numbers (de-bolded before matching)
      3. The one-line header block already captured by parse_header()
    """
    out: list[str] = []
    for line in raw_md.split("\n"):
        stripped = line.strip()

        # 1. Picture placeholders
        if PICTURE_RE.match(stripped):
            continue

        # 2. Page footers / numbers — strip bold markers before matching
        bare = stripped.strip("*").strip()
        if PAGE_FOOTER_RE.match(bare) or PAGE_NUMBER_RE.match(bare):
            continue

        # 3. Header line (already captured into front-matter table)
        if HEADER_FIELD_RE.search(stripped) and stripped.startswith("Date"):
            continue

        out.append(line.rstrip())

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse excessive blank lines
    return text.strip()


def format_markdown(header: dict[str, str], body_md: str, pdf_path: Path) -> str:
    """Format header + body into a well-structured markdown document."""
    policy_name = header.get("policy", "")
    doc_type = header.get("document_type", "")
    if doc_type and doc_type.lower() != "policy overview":
        title = f"{policy_name} — {doc_type}"
    else:
        title = policy_name

    lines = [
        f"# {title}",
        "",
        "| Field | Value |",
        "|-------|-------|",
    ]
    for key, label in [("date", "Date"), ("policy", "Policy"), ("document_type", "Document Type")]:
        if header.get(key):
            lines.append(f"| {label} | {header[key]} |")
    lines.append(f"| Source | `{pdf_path.name}` |")
    lines.append("")
    lines.append(body_md)

    return "\n".join(lines) + "\n"


def _slugify(text: str) -> str:
    """Convert text to a filesystem-friendly slug."""
    slug = text.lower().strip()
    slug = slug.replace("'", "")
    slug = re.sub(r"[^a-z0-9\- ]", "", slug)
    slug = slug.replace(" ", "-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


def _slug_from_filename(filename: str) -> str:
    """Derive policy slug from PDF filename (fallback when not in reference.json).

    Handles patterns:
    - Opportunity_Abundant Energy_Policy Overview.pdf -> abundant-energy
    - Opportunity_Tax Reset_Transition Plan.pdf -> tax-reset
    - _migrated_{filename} -> derive from the original filename
    - Any other pattern -> unknown
    """
    # Strip migration prefix and extension
    name = filename.replace("_migrated_", "").replace(".pdf", "")
    # Strip "Opportunity_" brand prefix, then "Policy_" category prefix
    name = name.replace("Opportunity_", "").replace("Policy_", "")
    parts = name.split("_")
    if parts and parts[0]:
        slug = parts[0].lower().replace(" ", "-").strip("-")
        # Reject Google Drive-style file IDs (long alphanumeric strings)
        if len(slug) > 30 or not any(c.isalpha() for c in slug):
            return "unknown"
        return slug
    return "unknown"


def _get_policy_slug_from_reference(filename: str) -> str | None:
    """Look up the policy_slug for a PDF from reference.json.

    Returns the policy_slug if found, None otherwise.
    """
    if not REFERENCE_FILE.exists():
        return None
    try:
        ref = json.loads(REFERENCE_FILE.read_text())
        for entry in ref.get("downloads", {}).values():
            if Path(entry.get("filename", "")).name == filename:
                return entry.get("policy_slug")
    except (OSError, json.JSONDecodeError):
        pass
    return None
