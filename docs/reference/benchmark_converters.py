#!/usr/bin/env python3
"""Benchmark PDF -> Markdown converters against the policy PDF set.

Reference script used to evaluate replacements for the current
`pdftotext -layout` pipeline in `scraper/pdf_convert.py`.

Run inside a throwaway venv:

    uv venv .expvenv && source .expvenv/bin/activate
    uv pip install pymupdf4llm "markitdown[pdf]"   # docling optional, needs network + torch
    python docs/reference/benchmark_converters.py data/pdfs/*.pdf

For each converter it reports three structure-quality signals:
  - headings      : count of markdown heading lines (`#`). pdftotext = 0.
  - reflow_breaks : lines ending mid-sentence (lowercase / comma). High = the
                    converter failed to re-join wrapped lines into prose.
  - tables        : count of markdown table rows (`|`). pdftotext mangles these.

Findings (Jun 2026, 6 policy PDFs):
  pymupdf4llm  -> headings yes, 0 reflow_breaks, real tables, offline, fast  ** winner **
  markitdown   -> 0 headings, ~225 reflow_breaks, no tables (raw text dump)
  pdftotext    -> 0 headings, ~228 reflow_breaks, broken tables (current)
  docling      -> best layout model BUT needs to download models from HF/modelscope
                  (no offline run), torch dependency, minutes of CPU per doc.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def signals(md: str) -> dict[str, int]:
    return {
        "lines": md.count("\n"),
        "headings": len(re.findall(r"(?m)^#", md)),
        "reflow_breaks": len(re.findall(r"(?m)[a-z,]$", md)),
        "tables": len(re.findall(r"(?m)^\s*\|", md)),
    }


def via_pdftotext(pdf: Path) -> str:
    """Current approach: poppler's pdftotext with layout preservation."""
    out = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return out.stdout


def via_pymupdf4llm(pdf: Path) -> str:
    import pymupdf4llm

    return pymupdf4llm.to_markdown(str(pdf), show_progress=False)


def via_markitdown(pdf: Path) -> str:
    from markitdown import MarkItDown  # ty: ignore[unresolved-import]

    return MarkItDown().convert(str(pdf)).text_content


def via_docling(pdf: Path) -> str:
    # Requires model download (HuggingFace) -> will fail offline. OCR disabled
    # because these PDFs already carry a real text layer.
    from docling.datamodel.base_models import InputFormat  # ty: ignore[unresolved-import]
    from docling.datamodel.pipeline_options import (  # ty: ignore[unresolved-import]
        PdfPipelineOptions,
    )
    from docling.document_converter import (  # ty: ignore[unresolved-import]
        DocumentConverter,
        PdfFormatOption,
    )

    opts = PdfPipelineOptions()
    opts.do_ocr = False
    conv = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)}
    )
    return conv.convert(str(pdf)).document.export_to_markdown()


CONVERTERS = {
    "pdftotext": via_pdftotext,
    "pymupdf4llm": via_pymupdf4llm,
    "markitdown": via_markitdown,
    "docling": via_docling,
}


def main(argv: list[str]) -> int:
    pdfs = [Path(p) for p in argv]
    if not pdfs:
        print(__doc__)
        return 1

    for pdf in pdfs:
        print(f"\n# {pdf.name}")
        for name, fn in CONVERTERS.items():
            try:
                s = signals(fn(pdf))
                print(
                    f"  {name:14} lines={s['lines']:5} headings={s['headings']:3} "
                    f"reflow_breaks={s['reflow_breaks']:4} tables={s['tables']:4}"
                )
            except Exception as e:  # reference script: report and keep going
                print(f"  {name:14} FAILED: {type(e).__name__}: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
