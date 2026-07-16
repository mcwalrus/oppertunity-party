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
    The malformed 10-column implementation pathway table is left as-is —
    unrecoverable from extraction; see docs/pdf-pipeline.md.
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
    ],
    "pdf-policy-addendum.md": [
        (
            "Tax Reset Transition Plan: drop duplicate 'Document Type **Policy Addendum**' header + fix sentence-space after period",
            _tax_reset_transition_plan,
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
