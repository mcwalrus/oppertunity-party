"""Tests for the per-PDF quirk patch registry."""

from __future__ import annotations

from pipeline.transforms.pdf_quirks import (
    QUIRKS_BY_FILENAME,
    apply_quirks,
    fix_sentence_space_after_period,
    merge_split_h2_headings,
)


def test_fix_sentence_space_after_period():
    """Restore space after sentence-final period followed by a capital letter."""
    assert (
        fix_sentence_space_after_period("most needed.Those earning") == "most needed. Those earning"
    )
    # End-of-heading bold closures don't trigger (no capital letter after `.`)
    assert fix_sentence_space_after_period("their tax bill.**") == "their tax bill.**"
    # No change when not at sentence boundary
    assert fix_sentence_space_after_period("hello world") == "hello world"


def test_merge_split_h2_headings_merges_pair():
    """Two adjacent H2 lines that wrap are joined into one."""
    text = (
        "## **What does the LVT mean for ‘asset-rich’ Kiwis like**\n\n## **retirees or farmers?**\n"
    )
    result = merge_split_h2_headings(
        text,
        [("What does the LVT mean for ‘asset-rich’ Kiwis like", "retirees or farmers?")],
    )
    assert (
        result == "## **What does the LVT mean for ‘asset-rich’ Kiwis like retirees or farmers?**\n"
    )


def test_merge_split_h2_headings_no_match_is_noop():
    """Pairs that don't appear in the text don't change it."""
    text = "## **Some other heading**\n\nBody text.\n"
    assert merge_split_h2_headings(text, [("Not in text", "also not")]) == text


def test_apply_quirks_tax_reset_overview():
    """The Tax Reset Overview PDF has both quirks registered."""
    filename = "pdf-policy-overview.md"
    assert filename in QUIRKS_BY_FILENAME

    sample = (
        "## **What does the Land Value Tax mean for ‘asset-rich, cash-poor’ Kiwis like**\n"
        "\n"
        "## **retirees or farmers?**\n"
        "\n"
        "most needed.Those earning less.\n"
    )
    result = apply_quirks(filename, sample)
    assert (
        "## **What does the Land Value Tax mean for ‘asset-rich, cash-poor’ Kiwis like retirees or farmers?**"
        in result
    )
    assert "most needed. Those earning less." in result


def test_apply_quirks_unknown_pdf_is_passthrough():
    """An unregistered PDF passes through unchanged."""
    text = "## **Whatever**\n"
    assert apply_quirks("Not_A_Real.pdf", text) == text
