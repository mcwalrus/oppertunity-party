"""Tests for the per-PDF quirk patch registry."""

from __future__ import annotations

from pipeline.transforms.pdf_quirks import (
    QUIRKS_BY_FILENAME,
    apply_quirks,
    demote_h2_subnumbering,
    demote_h2_under_problems_we_are_solving,
    fix_mapped_table_cells,
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


def test_demote_h2_subnumbering_basic():
    """A bolded H2 with sub-numbering like '## **1.1 ...**' becomes an H3."""
    text = "## **1.1 The Citizen's Income**\n"
    assert demote_h2_subnumbering(text) == "### **1.1 The Citizen's Income**\n"


def test_demote_h2_subnumbering_multiple_subsections():
    """All sub-numbered H2 lines in a block are demoted in one pass."""
    text = (
        "## **1. Give every Kiwi the basics to live well and contribute**\n\n"
        "## **1.1 The Citizen's Income**\n\n"
        "## **1.2 Income Tax Realignment**\n\n"
        "## **1.3 A Simplified Benefit System**\n"
    )
    expected = (
        "## **1. Give every Kiwi the basics to live well and contribute**\n\n"
        "### **1.1 The Citizen's Income**\n\n"
        "### **1.2 Income Tax Realignment**\n\n"
        "### **1.3 A Simplified Benefit System**\n"
    )
    assert demote_h2_subnumbering(text) == expected


def test_demote_h2_subnumbering_preserves_single_numbered_h2():
    """A bolded H2 with a single number like '## **1. ...**' is a top-level section — keep as H2."""
    text = "## **1. Give every Kiwi the basics to live well and contribute**\n"
    assert demote_h2_subnumbering(text) == text


def test_demote_h2_subnumbering_preserves_unbolded_h2():
    """Unbolded '## 1.1 ...' (no ** markers) is not touched — only bolded sub-numbered H2s are demoted."""
    text = "## 1.1 Some unbolded heading\n"
    assert demote_h2_subnumbering(text) == text


def test_demote_h2_subnumbering_handles_deeper_subnumbering():
    """Three-level numbering '## **1.1.1 ...**' is also demoted — the regex doesn't bound to two digits."""
    text = "## **1.1.1 Nested sub-numbered heading**\n"
    assert demote_h2_subnumbering(text) == "### **1.1.1 Nested sub-numbered heading**\n"


def test_demote_h2_subnumbering_idempotent():
    """Re-running the function on already-demoted output is a no-op (no double-demotion)."""
    text = "### **1.1 The Citizen's Income**\n"
    assert demote_h2_subnumbering(text) == text


def test_apply_quirks_demotes_subnumbering_in_policy_overview():
    """pdf-policy-overview.md runs demote_h2_subnumbering: ## **N.M ...** → ### **N.M ...**."""
    filename = "pdf-policy-overview.md"
    assert filename in QUIRKS_BY_FILENAME

    sample = (
        "## **1. Give every Kiwi the basics to live well and contribute**\n"
        "\n"
        "The Citizen's Income is a tax-free universal payment.\n"
        "\n"
        "## **1.1 The Citizen's Income**\n"
        "\n"
        "Every New Zealand Citizen and resident aged 18 and over.\n"
        "\n"
        "## **2. Make housing affordable through a Land Value Tax**\n"
        "\n"
        "## **2.1 A Land Value Tax of 1.75% on urban and 0.5% on rural land.**\n"
    )
    result = apply_quirks(filename, sample)

    # Top-level numbered H2s preserved
    assert "## **1. Give every Kiwi the basics to live well and contribute**" in result
    assert "## **2. Make housing affordable through a Land Value Tax**" in result

    # Sub-numbered H2s demoted to H3 (full line begins with `### **N.M`)
    assert "### **1.1 The Citizen's Income**" in result
    assert "### **2.1 A Land Value Tax of 1.75% on urban and 0.5% on rural land.**" in result

    # The demoted lines no longer exist as a full H2 line (anchored on `\n## **N.M`,
    # not a substring — `### **` contains `## **` and would falsely match)
    assert "\n## **1.1 The Citizen's Income**\n" not in result
    assert "\n## **2.1 A Land Value Tax of 1.75% on urban and 0.5% on rural land.**\n" not in result


# ---------------------------------------------------------------------------
# demote_h2_under_problems_we_are_solving — demote unnumbered ## **...** sub-headings
# that follow the '## **The problems we're solving**' wrapper down to H3.
# ---------------------------------------------------------------------------


def test_demote_h2_under_problems_we_are_solving_basic():
    """Sub-headings under 'The problems we're solving' are demoted; wrapper stays H2.

    Sub-headings are distinguished from wrappers by having body content
    between them and the next H2 — wrappers are immediately followed by
    another heading (typically a numbered top-level). Note: PDF-extracted
    markdown uses curly apostrophes (\u2019), so the wrapper regex matches
    that form.
    """
    text = (
        "## **The problems we\u2019re solving**\n"
        "\n"
        "Some intro text.\n"
        "\n"
        "## **The cost-of-living crisis is crushing working families**\n"
        "\n"
        "Body content here.\n"
        "\n"
        "## **Welfare isn't working\u2014it traps people in poverty**\n"
        "\n"
        "More body content.\n"
        "\n"
        "## **1. Give every Kiwi the basics**\n"
    )
    result = demote_h2_under_problems_we_are_solving(text)
    assert "## **The problems we\u2019re solving**" in result  # wrapper preserved
    assert "### **The cost-of-living crisis is crushing working families**" in result
    assert "### **Welfare isn't working\u2014it traps people in poverty**" in result
    assert "## **1. Give every Kiwi the basics**" in result  # numbered top-level preserved


def test_demote_h2_under_problems_we_are_solving_stops_at_numbered_h2():
    """Stops demoting at the first numbered H2 (## **1. ...**) — that ends the section."""
    text = (
        "## **The problems we\u2019re solving**\n"
        "\n"
        "## **Problem one**\n"
        "\n"
        "Body text for problem one.\n"
        "\n"
        "## **Problem two**\n"
        "\n"
        "Body text for problem two.\n"
        "\n"
        "## **1. Top-level section**\n"
        "\n"
        "## **1.1 Sub of top-level**\n"
    )
    result = demote_h2_under_problems_we_are_solving(text)
    # Both problems demoted
    assert "### **Problem one**" in result
    assert "### **Problem two**" in result
    # Numbered H2 not touched
    assert "\n## **1. Top-level section**\n" in result
    assert "\n## **1.1 Sub of top-level**\n" in result


def test_demote_h2_under_problems_we_are_solving_stops_at_label_h2():
    """Stops at a colon-label H2 ('Our reforms will:') — that's a bullet-list label, not a sub-heading."""
    text = (
        "## **The problems we\u2019re solving**\n"
        "\n"
        "## **Problem one**\n"
        "\n"
        "Body text for problem one.\n"
        "\n"
        "## **Our reforms will:**\n"
        "\n"
        "- bullet one\n"
        "\n"
        "- bullet two\n"
    )
    result = demote_h2_under_problems_we_are_solving(text)
    assert "### **Problem one**" in result
    # Label H2 not demoted
    assert "\n## **Our reforms will:**\n" in result
    assert "\n### **Our reforms will:**\n" not in result


def test_demote_h2_under_problems_we_are_solving_stops_at_policy_pillars_wrapper():
    """Stops at an H2 wrapper for the next section (e.g. '## **The X policy pillars**') when
    the wrapper is immediately followed by a numbered H2 (no body content between) — that
    wrapper belongs to the next section, not to 'The problems we're solving'."""
    text = (
        "## **The problems we\u2019re solving**\n"
        "\n"
        "## **Problem one**\n"
        "\n"
        "Body text for problem one.\n"
        "\n"
        "## **Problem two**\n"
        "\n"
        "Body text for problem two.\n"
        "\n"
        "## **The Abundant Energy policy pillars**\n"
        "\n"
        "## **1. Boost Renewable Generation**\n"
    )
    result = demote_h2_under_problems_we_are_solving(text)
    assert "### **Problem one**" in result
    assert "### **Problem two**" in result
    # 'policy pillars' wrapper stays as H2 (it's a wrapper for the next numbered section)
    assert "\n## **The Abundant Energy policy pillars**\n" in result
    assert "\n### **The Abundant Energy policy pillars**\n" not in result


def test_demote_h2_under_problems_we_are_solving_no_wrapper_is_passthrough():
    """When the wrapper isn't in the text, the function returns the input unchanged."""
    text = "## **Some other heading**\n\n## **Another heading**\n"
    assert demote_h2_under_problems_we_are_solving(text) == text


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


def test_apply_quirks_healthy_oceans_policy_overview():
    """Healthy Oceans Overview: drops mid-paragraph `**Oceans**` footer label,
    promotes 2 bold-only sub-headings to H2, and restores sentence spacing."""
    filename = "pdf-policy-overview.md"
    assert filename in QUIRKS_BY_FILENAME

    sample = (
        # Mid-paragraph `**Oceans**` footer label sitting between two paragraphs
        "bottom-trawling. Destruction of coral reefs\n\n"
        "**Oceans**\n\n"
        "and seafloor ecosystems promise damage.\n\n"
        # Bold-only sub-heading missing the `## ` prefix
        "**1.3 Install cameras and maintain observers on all commercial fishing vessels** "
        "Transparency is non-negotiable.\n\n"
        # Another bold-only sub-heading
        "**4.3 Develop long-term regional ocean plans in partnership with communities** "
        "Effective governance requires local knowledge.\n\n"
        # Missing sentence-space after period
        "marine protection planning processes.Many iwi are leading.\n"
    )
    result = apply_quirks(filename, sample)

    # `**Oceans**` footer label gone, surrounding paragraphs rejoined
    assert "**Oceans**" not in result
    assert "coral reefs\n\nand seafloor ecosystems" in result

    # 1.3 promoted to a heading then demoted to H3 (sub-numbered under section 1)
    assert (
        "### **1.3 Install cameras and maintain observers on all commercial fishing vessels**"
        in result
    )
    assert (
        "\n**1.3 Install cameras and maintain observers on all commercial fishing vessels**"
        not in result
    )

    # 4.3 promoted to a heading then demoted to H3 (sub-numbered under section 4)
    assert (
        "### **4.3 Develop long-term regional ocean plans in partnership with communities**"
        in result
    )
    assert (
        "\n**4.3 Develop long-term regional ocean plans in partnership with communities**"
        not in result
    )

    # Sentence spacing restored
    assert "processes. Many iwi are leading." in result


def test_apply_quirks_unknown_pdf_is_passthrough():
    """An unregistered PDF passes through unchanged."""
    text = "## **Whatever**\n"
    assert apply_quirks("Not_A_Real.pdf", text) == text


def test_apply_quirks_tax_reset_transition_plan():
    """The Tax Reset Transition Plan PDF drops the duplicate header and applies sentence-space fix."""
    filename = "pdf-policy-addendum.md"
    assert filename in QUIRKS_BY_FILENAME

    sample = (
        "| Source | `Opportunity_Tax Reset_Transition Plan.pdf` |\n"
        "\n"
        "Document Type **Policy Addendum**\n"
        "\n"
        "## **Tax Reset**\n"
        "\n"
        "Body text needed.Those earning more.\n"
    )
    result = apply_quirks(filename, sample)
    # Duplicate header line is removed (frontmatter table row is preserved separately).
    assert "Document Type **Policy Addendum**\n\n## **Tax Reset**" not in result
    assert "## **Tax Reset**" in result
    # Sentence-space-after-period fix applies to the uppercase-followed case.
    assert "needed. Those earning more." in result


def test_apply_quirks_abundant_energy_policy_overview():
    """Abundant Energy Overview: drops mid-paragraph `**Energy**` footer label
    and restores sentence spacing."""
    filename = "pdf-policy-overview.md"
    assert filename in QUIRKS_BY_FILENAME

    sample = (
        # Mid-paragraph `**Energy**` footer label splitting a sentence on a page break
        "successive governments have been\n\n"
        "**Energy**\n\n"
        "incentivised not to modify the regulatory structures.\n\n"
        # Missing sentence-space after period (caught by fix_sentence_space_after_period)
        "can do better.We can have abundant energy.\n"
    )
    result = apply_quirks(filename, sample)

    # `**Energy**` footer label gone, surrounding paragraphs rejoined
    assert "**Energy**" not in result
    assert "have been\n\nincentivised not to modify" in result

    # Sentence spacing restored
    assert "better. We can have abundant energy." in result


def test_apply_quirks_citizens_voice_policy_overview():
    """Citizens Voice Overview: drops mid-paragraph `**Direct Democracy**`
    page-header label and restores sentence spacing."""
    filename = "pdf-policy-overview.md"
    assert filename in QUIRKS_BY_FILENAME

    sample = (
        # Mid-paragraph `**Direct Democracy**` page-header label on page 2's break
        "impact on New Zealand but are too slow-moving to result.\n\n"
        "**Direct Democracy**\n\n"
        "**Photo: Climate Assembly UK**\n\n"
        # Missing sentence-space after period (caught by fix_sentence_space_after_period)
        "long-term future.Citizens coming together to debate.\n"
    )
    result = apply_quirks(filename, sample)

    # `**Direct Democracy**` page-header label gone
    assert "**Direct Democracy**" not in result
    assert "to result.\n\n**Photo: Climate Assembly UK**" in result

    # Sentence spacing restored
    assert "future. Citizens coming together to debate." in result


def test_apply_quirks_making_zero_the_hero():
    """MakingZeroTheHero Summary: drops the orphan empty H2 page-break artifact.

    The pattern targets the specific 'desirability of a pan-sector vision'
    paragraph so charter/constitution (which share ``pdf-default.md``) are
    unaffected — they never emit this exact phrase.
    """
    filename = "pdf-default.md"
    assert filename in QUIRKS_BY_FILENAME

    sample = (
        "A roadmap towards sustainable plastics use in New Zealand\n"
        "\n"
        "##\n"
        "\n"
        "desirability of a pan-sector vision for plastic's use in New Zealand.\n"
        "\n"
        "## Kate Kreba\n"
    )
    result = apply_quirks(filename, sample)
    # Empty H2 is removed; the body paragraph flows directly after the previous one
    assert "##\n\ndesirability" not in result
    assert "desirability of a pan-sector vision for plastic's use in New Zealand." in result
    # Real H2 headings are untouched
    assert "## Kate Kreba" in result


def test_apply_quirks_making_zero_the_hero_no_match_is_passthrough():
    """When the orphan empty H2 isn't present, charter/constitution content passes through unchanged."""
    filename = "pdf-default.md"
    sample = "# Charter\n\n## **VISION**\n\nSome body text.\n"
    assert apply_quirks(filename, sample) == sample


# ---------------------------------------------------------------------------
# fix_mapped_table_cells — fix $m escape + empty-cell fill in data tables
# ---------------------------------------------------------------------------


def test_fix_mapped_table_cells_fills_empty_cells():
    """Empty cells in table data rows become '-' so they display as placeholders."""
    text = "|**Cost**||**15788**|**Revenue**|**24323**|\n|---|---|---|---|\n|**Less**|(23381)||||\n"
    result = fix_mapped_table_cells(text)
    # Header: empty cell 2 becomes '-'
    assert "|**Cost**|-|**15788**|**Revenue**|**24323**|" in result
    # Data row: trailing empty cells become '-'
    assert "|**Less**|(23381)|-|-|-|" in result


def test_fix_mapped_table_cells_escapes_dollar_m():
    """$m column header is escaped to \\$m so markdown renderers don't treat it as math."""
    text = (
        "|**Cost**||**$m**|**Revenue**|**$m**|\n|---|---|---|---|\n|**Net**||15788|**LVT**|24323|\n"
    )
    result = fix_mapped_table_cells(text)
    assert "|**Cost**|-|**\\$m**|**Revenue**|**\\$m**|" in result
    assert "|**Net**|-|15788|**LVT**|24323|" in result
    # The $m itself must not appear unescaped in any data-row cell
    assert "**$m**" not in result


def test_fix_mapped_table_cells_skips_separator_rows():
    """Separator rows like |---|---|---|--- are not modified."""
    text = "|**Cost**||**$m**|\n|---|---|\n|**Net**||15788|\n"
    result = fix_mapped_table_cells(text)
    # Separator unchanged
    assert "|---|---|\n" in result


def test_fix_mapped_table_cells_skips_toc_lines():
    """Single-cell TOC-style lines (||...| with dot-leaders) pass through unchanged.

    TOC entries are extracted as ``||Title......Pg|`` — only 3 pipes, 2 cells.
    Real tables have 4+ pipes (3+ cells). The detection gate uses pipe count.
    """
    text = (
        "## **Contents**\n"
        "\n"
        "|1.|Formation ................................................. 3|\n"
        "|---|---|\n"
        "||Name and establishment......................................3|\n"
    )
    result = fix_mapped_table_cells(text)
    # TOC lines unchanged — empty cell NOT filled, dot-leaders preserved
    assert "||Name and establishment......................................3|" in result
    assert "|1.|Formation ................................................. 3|" in result
    # The TOC's separator is also untouched
    assert "|---|---|\n" in result


def test_fix_mapped_table_cells_skips_non_table_lines():
    """Regular prose lines containing '$m' or '|' are not modified."""
    text = "Some prose text mentioning $m and |pipes| in it.\nAnother line.\n"
    assert fix_mapped_table_cells(text) == text


def test_fix_mapped_table_cells_idempotent():
    """Running the fix twice produces the same result as running once."""
    text = (
        "|**Cost**||**$m**|**Revenue**|**$m**|\n"
        "|---|---|---|---|\n"
        "|**Net**||15788|**LVT**|24323|\n"
        "|**Less**|(23381)||||\n"
    )
    once = fix_mapped_table_cells(text)
    twice = fix_mapped_table_cells(once)
    assert once == twice


def test_apply_quirks_tax_reset_overview_fixes_mapped_table():
    """Tax Reset Overview: the 'How will you pay' table is fixed (empty cells + $m)."""
    filename = "pdf-policy-overview.md"
    sample = (
        "## **How will you pay for the Citizen’s Income?**\n"
        "\n"
        "Some intro text.\n"
        "\n"
        "|revenue.|||||\n"
        "|---|---|---|---|---|\n"
        "|**Cost**||**$m**|**Revenue**|**$m**|\n"
        "|**Net cost of CI**||**15788**|**Land Value Tax**|**24323**|\n"
        "|**Total cost**||**24067**|**Total revenue**|**28148**|\n"
        "\n"
        "A previous version of this table was incorrect.\n"
    )
    result = apply_quirks(filename, sample)
    # Header escaped
    assert "|**\\$m**|" in result
    # Empty cells filled
    assert "|revenue.|-|-|-|-|" in result
    assert "|**Cost**|-|**\\$m**|" in result
    assert "|**Net cost of CI**|-|**15788**|" in result
    assert "|**Total cost**|-|**24067**|" in result


def test_apply_quirks_tax_reset_addendum_fills_empty_cells():
    """Tax Reset Transition Plan: empty cells in the implementation pathway table get filled."""
    filename = "pdf-policy-addendum.md"
    sample = (
        "## **Overview**\n"
        "\n"
        "|H1|**H2**|**H3**|**H4|**H5**|\n"
        "|---|---|---|---|---|\n"
        "||**CI/New tax**|**LVT**|||**Contributions**||**Tax exemption**|||\n"
    )
    result = apply_quirks(filename, sample)
    # All empty cells filled with '-'
    assert "|H1|**H2**|**H3**|**H4|**H5**|" in result  # header unchanged (no empty cells)
    # Original row had 4 empty cells interspersed — all become '-'
    assert "|-|**CI/New tax**|**LVT**|-|-|**Contributions**|-|**Tax exemption**|-|-|" in result
