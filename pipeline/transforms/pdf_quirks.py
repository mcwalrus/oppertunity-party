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


def demote_h2_subnumbering(text: str) -> str:
    """Demote bolded sub-numbered H2 headings like ``## **1.1 ...**`` to H3.

    pymupdf4llm emits every numbered heading at the same level, so a document
    with sections like ``1.`` / ``1.1`` / ``1.2`` / ``2.`` / ``2.1`` lands as
    a flat list of H2s. Top-level sections (``## **1. ...**``) stay H2; their
    children (``## **1.1 ...**``) get demoted one level so the heading tree
    reflects the document's numbering hierarchy.

    Anchored on ``## **`` + ``\\d+\\.\\d+`` so:
    - Single-numbered headings (``## **1. ...**``) are not touched.
    - Unbolded headings (``## 1.1 ...``) are not touched.
    - Already-demoted H3s (``### **1.1 ...**``) are not re-demoted (the
      ``##`` marker doesn't match).
    """
    # ponytail: one-line regex. False positives only if a top-level H2 happens
    # to be bolded and starts with "N.M text" — add a check for the preceding
    # blank line + body context if one surfaces.
    return re.sub(r"^## \*\*(\d+\.\d+)", r"### **\1", text, flags=re.MULTILINE)


def fix_mapped_table_cells(text: str) -> str:
    """Fix data rows in mapped markdown tables so they render cleanly.

    Two fixes applied per data row:

    - ``$m`` (the ``$millions`` column unit) → ``\\$m`` so renderers with math
      support don't treat the header as inline math.
    - Empty cells (``||``) → ``|-`` so they show as a visible placeholder
      instead of an invisible gap in the rendered table.

    Detection uses markdown table blocks: a separator row (``|---|---|...``)
    plus the rows adjacent to it. Single-cell TOC-style lines (which start
    with ``||`` but only have 2 cells — a title and a page number) are
    skipped because they lack both the 4+ pipe count and the separator
    adjacency. Idempotent — re-running produces the same output.
    """
    sep_re = re.compile(r"^\|[\s\-:|]+\|$")
    lines = text.split("\n")

    # Find separator row indices (table block anchors).
    sep_indices = [
        i
        for i, line in enumerate(lines)
        if sep_re.match(line.strip()) and line.strip().count("|") >= 3
    ]

    # Mark header (line above each separator) and all data rows below it.
    process_indices: set[int] = set()
    for sep_idx in sep_indices:
        if sep_idx > 0:
            process_indices.add(sep_idx - 1)
        j = sep_idx + 1
        while j < len(lines) and _is_table_data_row(lines[j]):
            process_indices.add(j)
            j += 1

    for i in process_indices:
        _rewrite_table_row(lines, i)

    return "\n".join(lines)


def _is_table_data_row(line: str) -> bool:
    """True if *line* looks like a markdown table data row (not a separator or TOC entry)."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return False
    # 4+ pipes = 3+ cells; this skips TOC entries like `||Title...Pg|` (3 pipes).
    if stripped.count("|") < 4:
        return False
    # Skip separator rows like `|---|---|---|`.
    return not re.match(r"^\|[\s\-:|]+\|$", stripped)


def _rewrite_table_row(lines: list[str], i: int) -> None:
    """Fill empty cells with '-' and escape ``$m`` in *lines[i]* in place."""
    line = lines[i]
    m = re.match(r"^(\s*)(.*?)(\s*)$", line)
    if not m:
        return
    leading, content, trailing = m.group(1), m.group(2), m.group(3)
    if not _is_table_data_row(content):
        return
    cells = content.split("|")[1:-1]
    cells = [c if c else "-" for c in cells]
    # Escape `$m` to `\$m`, but skip already-escaped `\$m` so the function is
    # idempotent (a plain `.replace` double-escapes on the second pass).
    cells = [re.sub(r"(?<!\\)\$m", "\\$m", c) for c in cells]
    lines[i] = f"{leading}|{'|'.join(cells)}|{trailing}"


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


def _healthy_oceans_policy_overview(text: str) -> str:
    """Quirks for Opportunity_Policy_Healthy Oceans.pdf."""
    # Drop the `**Oceans**` page-footer label that lands mid-paragraph on page
    # breaks (4 occurrences). Collapse the surrounding blank lines so the
    # surrounding paragraph rejoins.
    text = re.sub(r"\n\n\*\*Oceans\*\*\n\n", "\n\n", text)
    # Promote two sub-section headings that pymupdf4llm emitted as bold body
    # text (missing `## ` prefix) to match their siblings (1.1, 1.2, 1.4, ...).
    text = re.sub(
        r"\*\*1\.3 Install cameras and maintain observers on all commercial fishing vessels\*\*",
        "## **1.3 Install cameras and maintain observers on all commercial fishing vessels**",
        text,
    )
    text = re.sub(
        r"\*\*4\.3 Develop long-term regional ocean plans in partnership with communities\*\*",
        "## **4.3 Develop long-term regional ocean plans in partnership with communities**",
        text,
    )
    text = fix_sentence_space_after_period(text)
    return text


def _tax_reset_transition_plan(text: str) -> str:
    """Quirks for Opportunity_Tax Reset_Transition Plan.pdf.

    Drops the duplicate ``Document Type **Policy Addendum**`` header that
    appears after the frontmatter table (already present as a table row).
    The malformed 10-column implementation pathway table column structure is
    unrecoverable from extraction; ``fix_mapped_table_cells`` (registered
    separately) fills its empty cells with ``-`` so it still renders.
    """
    text = re.sub(r"\nDocument Type \*\*Policy Addendum\*\*\n\n", "\n\n", text)
    text = fix_sentence_space_after_period(text)
    return text


def _abundant_energy_policy_overview(text: str) -> str:
    """Quirks for Opportunity_Policy_Abundant Energy.pdf."""
    # Drop the `**Energy**` page-footer label that lands mid-paragraph on page
    # breaks (3 occurrences). Same pattern as `**Oceans**` in Healthy Oceans.
    text = re.sub(r"\n\n\*\*Energy\*\*\n\n", "\n\n", text)
    text = fix_sentence_space_after_period(text)
    return text


def _citizens_voice_policy_overview(text: str) -> str:
    """Quirks for Opportunity_Policy_Citizens Voice.pdf."""
    # Drop the `**Direct Democracy**` page-header label that lands mid-paragraph
    # on page 2's break (1 occurrence). Same pattern as `**Energy**` /
    # `**Oceans**` in the other policy overviews — the bare section name (no
    # "Opportunity Party" prefix) slips past the page-footer stripper in
    # ``pdf_convert.clean_body``.
    text = re.sub(r"\n\n\*\*Direct Democracy\*\*\n\n", "\n\n", text)
    text = fix_sentence_space_after_period(text)
    return text


def _making_zero_the_hero_summary(text: str) -> str:
    """Quirks for MakingZeroTheHero-Summary-Report.pdf.

    Drops an orphan empty ``##`` heading that pymupdf4llm emits at a page
    break where the PDF's section heading text was lost — the body paragraph
    "desirability of a pan-sector vision..." continues mid-sentence from the
    previous page. Anchored to that unique body text so it is a no-op on
    charter/constitution (which also write to ``pdf-default.md``).
    """
    # ponytail: scoped to one phrase; no generic empty-H2 stripper. Add a
    # generic helper if a second Scion PDF hits the same artifact.
    text = re.sub(
        r"^##[ \t]*\n\ndesirability of a pan-sector vision",
        "desirability of a pan-sector vision",
        text,
        flags=re.MULTILINE,
    )
    return text


# Per-PDF quirk registry: source-layer markdown filename -> [(description, callable)]
# Keys match `data/sources/opportunity-website/policies/{slug}/pdf-*.md` filenames.
QUIRKS_BY_FILENAME: dict[str, list[tuple[str, Callable]]] = {
    "pdf-policy-overview.md": [
        (
            "Tax Reset Policy Overview: merge 3 wrapped H2 FAQ headings + fix sentence-space after period",
            _tax_reset_policy_overview,
        ),
        (
            "Tax Reset Policy Overview: fix mapped table cells ($m escape + empty-cell fill)",
            fix_mapped_table_cells,
        ),
        (
            "Healthy Oceans Policy Overview: drop mid-paragraph `**Oceans**` footer label, promote 2 bold-only sub-headings to H2 + fix sentence-space after period",
            _healthy_oceans_policy_overview,
        ),
        (
            "Abundant Energy Policy Overview: drop mid-paragraph `**Energy**` footer label + fix sentence-space after period",
            _abundant_energy_policy_overview,
        ),
        (
            "Citizens Voice Policy Overview: drop mid-paragraph `**Direct Democracy**` page-header label + fix sentence-space after period",
            _citizens_voice_policy_overview,
        ),
        (
            "Policy Overview: demote bolded sub-numbered ## **N.M ...** headings to ### so sub-sections nest under their N. parent",
            demote_h2_subnumbering,
        ),
    ],
    "pdf-policy-addendum.md": [
        (
            "Tax Reset Transition Plan: drop duplicate 'Document Type **Policy Addendum**' header + fix sentence-space after period",
            _tax_reset_transition_plan,
        ),
        (
            "Tax Reset Transition Plan: fix mapped table cells (empty-cell fill in implementation pathway table)",
            fix_mapped_table_cells,
        ),
    ],
    "pdf-default.md": [
        (
            "MakingZeroTheHero Summary: drop orphan empty H2 before 'desirability...' paragraph (page-break artifact)",
            _making_zero_the_hero_summary,
        ),
    ],
}


def apply_quirks(filename: str, text: str) -> str:
    """Apply all quirks registered for *filename* to *text*, in order."""
    for _, fn in QUIRKS_BY_FILENAME.get(filename, []):
        text = fn(text)
    return text
