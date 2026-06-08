"""Reference: pymupdf4llm-based extraction to replace pdftotext.

Drop-in replacement for `extract_text()` + the header/footer cleanup in
`scraper/pdf_convert.py`. pymupdf4llm already produces structured markdown
(headings, reflowed paragraphs, real tables), so most of the hand-rolled
`format_body()` logic in the current module becomes unnecessary — the only
post-processing left is stripping three known artifacts.

Install:  uv add pymupdf4llm      (pure-Python, no poppler/system dep)

Artifacts pymupdf4llm leaves, and how we handle them:
  1. `**==> picture [86 x 35] intentionally omitted <==**`  -> drop the line
  2. Bold page footers `**Opportunity Party Energy**` / `**Page 1**`
        -> de-bold, then the existing PAGE_FOOTER_RE catches "Opportunity Party..."
  3. Header on one line:
        `Date **February 2026** Policy **Abundant Energy** Document Type **...**`
        -> parse_header() pulls the bold values into the front-matter table.

Not fixable by any converter: genuine source typos in the PDF text layer
(e.g. "do better.We" has no space in the original).
"""

from __future__ import annotations

import re
from pathlib import Path

import pymupdf4llm

PICTURE_RE = re.compile(r"^\s*\**==>\s*picture.*<==\**\s*$")
PAGE_FOOTER_RE = re.compile(r"^Opportunity\s+Party\b.*$")
PAGE_NUMBER_RE = re.compile(r"^Page\s+\d+\s*$")
HEADER_FIELD_RE = re.compile(r"(Date|Policy|Document Type)\s+\*\*(.+?)\*\*")


def extract_markdown(pdf_path: Path) -> str:
    """Return cleaned markdown for a policy PDF."""
    raw = pymupdf4llm.to_markdown(str(pdf_path), show_progress=False)
    return _clean(raw)


def parse_header(raw_md: str) -> dict[str, str]:
    """Pull Date / Policy / Document Type out of the first header line(s)."""
    header: dict[str, str] = {}
    for key, value in HEADER_FIELD_RE.findall(raw_md):
        header[key.lower().replace(" ", "_")] = value.strip()
    return header


def _clean(md: str) -> str:
    out: list[str] = []
    for line in md.split("\n"):
        stripped = line.strip()

        # 1. picture placeholders
        if PICTURE_RE.match(stripped):
            continue

        # 2. page footers / numbers — de-bold first so the regexes match
        bare = stripped.strip("*").strip()
        if PAGE_FOOTER_RE.match(bare) or PAGE_NUMBER_RE.match(bare):
            continue

        # 3. the one-line header block (already captured by parse_header)
        if HEADER_FIELD_RE.search(stripped) and stripped.startswith("Date"):
            continue

        out.append(line.rstrip())

    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)  # collapse blank runs
    return text.strip() + "\n"


if __name__ == "__main__":
    import sys

    for arg in sys.argv[1:]:
        p = Path(arg)
        print(f"--- {p.name} : header={parse_header(pymupdf4llm.to_markdown(str(p)))}")
        print(extract_markdown(p)[:1200])
