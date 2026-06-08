"""Convert Opportunity Party policy PDFs to structured markdown.

Uses pdftotext (poppler) for text extraction, then parses the
consistent header format and page footers to produce clean markdown.

Each PDF has:
  - A header block: Date, Policy, Document Type (key-value pairs separated by blanks)
  - Body content with bullet lists, section headings, tables
  - Page footers: "Opportunity Party  <Section>  Page N"

These footers and headers are stripped to produce clean content.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

from .client import DATA_DIR, save_content

logger = logging.getLogger(__name__)

POLICY_ASSETS_DIR = DATA_DIR / "policy-assets"
REFERENCE_FILE = POLICY_ASSETS_DIR / "reference.json"

# Regex for the header key-value format: "Date                February 2026"
HEADER_FIELD_RE = re.compile(r"^(Date|Policy|Document Type)\s{2,}(.+)$")
# Regex for page footer: "Opportunity Party   Tax   Page 3"
PAGE_FOOTER_RE = re.compile(r"^Opportunity\s+Party\s+")


def convert_all_pdfs() -> list[dict]:
    """Find all PDFs in policy-assets and convert them to markdown.

    Output is organized into subdirectories under data/policies/{slug}/.
    """
    if not POLICY_ASSETS_DIR.exists():
        logger.warning("No policy-assets directory found")
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
    raw_text = extract_text(pdf_path)
    header, body_start = parse_header(raw_text)
    body = extract_body(raw_text, body_start)
    body_md = format_body(body)
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


def extract_text(pdf_path: Path) -> str:
    """Extract text from a PDF using pdftotext with layout preservation."""
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"pdftotext failed for {pdf_path}: {result.stderr}")
    return result.stdout


def parse_header(raw_text: str) -> tuple[dict, int]:
    """Parse the header block from raw pdftext output.

    Header fields (Date, Policy, Document Type) are key-value pairs
    separated by multiple spaces, with blank lines between them.
    We scan until we've seen all three or hit the first content line.

    Returns (header_dict, line_index_where_body_starts).
    """
    lines = raw_text.split("\n")
    header: dict[str, str] = {}
    body_start = 0

    for i, line in enumerate(lines):
        m = HEADER_FIELD_RE.match(line)
        if m:
            key = m.group(1).lower().replace(" ", "_")
            header[key] = m.group(2).strip()
            body_start = i + 1
        elif line.strip() and header and not HEADER_FIELD_RE.match(line):
            # First non-blank, non-header line — body starts here
            body_start = i
            break

    # Skip blank lines between header and body content
    while body_start < len(lines) and not lines[body_start].strip():
        body_start += 1

    return header, body_start


def extract_body(raw_text: str, body_start: int) -> list[str]:
    """Extract body lines, stripping page footers and header cruft."""
    lines = raw_text.split("\n")
    body_lines: list[str] = []

    for line in lines[body_start:]:
        # Skip page footer lines: "Opportunity Party   Tax   Page 3"
        if PAGE_FOOTER_RE.match(line.strip()):
            continue
        body_lines.append(line)

    return body_lines


def format_body(body_lines: list[str]) -> str:
    """Convert body lines into clean markdown.

    Handles:
    - Bullet points (• → -)
    - Sub-bullet indentation
    - Collapse excessive blank lines
    """
    output: list[str] = []
    prev_blank = False

    for line in body_lines:
        stripped = line.strip()

        # Skip consecutive blank lines (max 1 blank line between paragraphs)
        if not stripped:
            if not prev_blank:
                output.append("")
                prev_blank = True
            continue

        prev_blank = False

        # Convert bullet characters to markdown bullets
        if stripped.startswith("•") or stripped.startswith("·"):
            indent = len(line) - len(line.lstrip())
            bullet_text = stripped[1:].strip()
            if indent > 4:
                output.append(f"  - {bullet_text}")
            else:
                output.append(f"- {bullet_text}")
            continue

        output.append(line)

    text = "\n".join(output)

    # Collapse 3+ consecutive newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def format_markdown(header: dict, body_md: str, pdf_path: Path) -> str:
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
