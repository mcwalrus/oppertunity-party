"""Per-PDF quirk patches — manual fixes for source-layer markdown extraction.

Each PDF can have quirks (extraction artifacts unique to that document) that
the standard pymupdf4llm pipeline doesn't handle. Quirks live here as small
named functions keyed by PDF filename, applied by the ``apply_pdf_quirks``
Dagster asset between extraction and clean.

Adding a quirk for a new PDF
----------------------------
1. Define the function below (keep it focused — one fix per function).
2. Register it in ``QUIRKS_BY_FILENAME[filename]`` with a one-line description.
3. Re-run ``pdf_job`` for the PDF's policy slug to verify the patched output.

Patches are deterministic, idempotent functions. They run on the source
markdown in place (the source layer is gitignored; unpatched raw output is
reproducible from the PDF binary).
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# ---------------------------------------------------------------------------
# Generic patches (reusable across PDFs)
# ---------------------------------------------------------------------------


def fix_sentence_space_after_period(text: str) -> str:
    """Restore missing space after a sentence-final period followed by a capital letter.

    PDF rendering collapses the space between sentences when the next sentence
    starts at column 0 (no paragraph break), so ``needed.Those`` renders as
    ``needed.Those`` rather than ``needed. Those``. The lookahead anchors on
    a capital letter so end-of-sentence bold closures like ``bill.**`` don't
    trigger — the ``*`` after the period doesn't satisfy ``[A-Z]``.
    """
    # ponytail: one-line fix; no word-boundary gate. False positives (e.g.
    # "e.g.X") haven't surfaced — add `\b` left-anchor when they do.
    return re.sub(r"\.(?=[A-Z])", ". ", text)


def merge_split_h2_headings(text: str, pairs: list[tuple[str, str]]) -> str:
    """Merge pairs of adjacent H2 lines whose text wraps across two visual lines.

    pymupdf4llm emits wrapped heading text as two separate ``##`` lines because
    the second visual line starts at column 0. Detection is explicit (not
    heuristic): pass the exact ``(first_text, second_text)`` pairs you want
    merged — the function joins each pair into one ``## `` heading.

    Both texts are matched inside ``## **...**`` bolded headings. The merged
    result preserves the first heading's bold markers.
    """
    for first, second in pairs:
        pattern = (
            rf"(##\s+\*\*){re.escape(first)}(\*\*)\s*\n[ \t]*\n"
            rf"(##\s+\*\*{re.escape(second)}\*\*)"
        )
        text = re.sub(
            pattern,
            lambda m, f=first, s=second: f"{m.group(1)}{f} {s}{m.group(2)}",
            text,
        )
    return text


# ---------------------------------------------------------------------------
# Per-PDF patches
# ---------------------------------------------------------------------------


def _tax_reset_policy_overview(text: str) -> str:
    """Quirks for Opportunity_Tax Reset_Policy Overview.pdf."""
    text = merge_split_h2_headings(
        text,
        [
            (
                "What does the Land Value Tax mean for ‘asset-rich, cash-poor’ Kiwis like",
                "retirees or farmers?",
            ),
            (
                "What was your process in designing the Tax Reset. Have independent",
                "economists reviewed this?",
            ),
            (
                "What about Temporary Residents and Workers. Increasing tax rates without a",
                "Citizen’s Income will dramatically raise their tax bill.",
            ),
        ],
    )
    text = fix_sentence_space_after_period(text)
    return text


# Per-PDF quirk registry: source-layer markdown filename -> [(description, callable)]
# Keys match `data/sources/opportunity-website/policies/{slug}/pdf-*.md` filenames.
QUIRKS_BY_FILENAME: dict[str, list[tuple[str, Callable]]] = {
    "pdf-policy-overview.md": [
        (
            "Tax Reset Policy Overview: merge 3 wrapped H2 FAQ headings + fix sentence-space after period",
            _tax_reset_policy_overview,
        ),
    ],
}


def apply_quirks(filename: str, text: str) -> str:
    """Apply all quirks registered for *filename* to *text*, in order."""
    for _, fn in QUIRKS_BY_FILENAME.get(filename, []):
        text = fn(text)
    return text
