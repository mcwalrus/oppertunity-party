"""Tests for the per-PDF quirk patch registry."""

from __future__ import annotations

from pipeline.transforms.clean import strip_contents_section
from pipeline.transforms.pdf_quirks import (
    QUIRKS_BY_FILENAME,
    apply_quirks,
    demote_faq_question_headings,
    demote_h2_subnumbering,
    demote_h2_under_problems_we_are_solving,
    drop_picture_text_block,
    fix_mapped_table_cells,
    fix_sentence_space_after_period,
    fix_stripped_ligatures,
    merge_split_h2_headings,
)


def test_fix_stripped_ligatures_expands_double_letter_pairs():
    """Restore double-letter ligatures that pymupdf4llm stripped from the constitution PDF."""
    text = (
        "## **5. Oicers**\n\n"
        "- 5.4 An oicer is interested in a maer.\n"
        "- 6.10.1 a signed leer from the candidate.\n"
        "- 6.34 the board may appoint commiees of the Party.\n"
        "- 8.2.3 a wrien reference.\n"
        "- 2.5.4 **Eicacy** – we are our results.\n"
        "- The nominee would be a sound ElectorateCandidate.\n"
        "- Any act, maer or thing done, or suered in good faith.\n"
        "- Provision of financial gain may be an oence under the Act.\n"
        "- ex oicio member of the board.\n"
        "- measure eectiveness by influence.\n"
        "- the aairs of the Party.\n"
        "- 6.32 Wrien resolution.\n"
    )
    out = fix_stripped_ligatures(text)
    # Plurals + capitals restored
    assert "## **5. Officers**" in out
    assert "## **6. Officers**" not in out  # heading 5 only
    assert "An officer is interested in a matter." in out
    assert "a signed letter from the candidate." in out
    assert "appoint committees of the Party." in out
    assert "a written reference." in out
    assert "**Efficacy**" in out
    assert "Electorate Candidate" in out
    assert "Any act, matter or thing done, or suffered in good faith." in out
    assert "may be an offence under the Act." in out
    assert "ex officio member of the board." in out
    assert "measure effectiveness by influence." in out
    assert "the affairs of the Party." in out
    assert "Written resolution" in out


def test_fix_stripped_ligatures_leaves_real_words_alone():
    """Words that contain the broken-pattern letters as substrings are preserved."""
    text = (
        "Voice your choice — don't rejoice in invoice errors.\n"
        "The coherent, inherent argument is self-evident.\n"
        "Later, the letter will be delivered.\n"
    )
    out = fix_stripped_ligatures(text)
    assert out == text


def test_fix_stripped_ligatures_is_idempotent():
    """Re-running on already-fixed text is a no-op."""
    text = (
        "An officer is interested in a matter.\n"
        "## **Officers**\n"
        "Written resolution by the committee.\n"
    )
    once = fix_stripped_ligatures(text)
    twice = fix_stripped_ligatures(once)
    assert once == twice


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
# drop_picture_text_block — drop a picture-text block by content fingerprint
#
# Rule: only info-graphics (data-bearing visualizations: charts, diagrams,
# data infographics) should be referenced in markdown. Pure graphics
# (decorative cover imagery, word art, logos) are dropped using this function.
# ---------------------------------------------------------------------------


def test_drop_picture_text_block_removes_matching_block():
    """A picture-text block whose content contains the fingerprint is removed."""
    text = (
        "Some intro.\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "Making zero<br>the hero<br>"
        "**----- End of picture text -----**<br>\n"
        "\n"
        "Body text after.\n"
    )
    result = drop_picture_text_block(text, "Making zero<br>the hero")
    assert "Start of picture text" not in result
    assert "Making zero" not in result
    # Surrounding body text is preserved
    assert "Some intro." in result
    assert "Body text after." in result


def test_drop_picture_text_block_preserves_non_matching_blocks():
    """Picture-text blocks whose content does not contain the fingerprint are preserved."""
    text = (
        "**----- Start of picture text -----**<br>\n"
        "NPE strategy<br>diagram<br>**----- End of picture text -----**<br>\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "4% Not intending<br>**----- End of picture text -----**<br>\n"
    )
    result = drop_picture_text_block(text, "le R<br>k<br>e<br>R<br>c")
    # Neither block matches the fingerprint — both survive
    assert "NPE strategy" in result
    assert "4% Not intending" in result


def test_drop_picture_text_block_drops_only_matching_in_mixed_set():
    """In a mixed set of blocks, only the matching one is dropped."""
    text = (
        "**----- Start of picture text -----**<br>\n"
        "NPE strategy<br>diagram<br>**----- End of picture text -----**<br>\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "u<br>le R<br>k<br>e<br>R<br>c<br>**----- End of picture text -----**<br>\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "4% Not intending<br>**----- End of picture text -----**<br>\n"
    )
    result = drop_picture_text_block(text, "le R<br>k<br>e<br>R<br>c")
    # The matching block (vertical word art) is dropped
    assert "le R" not in result
    # The other blocks survive
    assert "NPE strategy" in result
    assert "4% Not intending" in result


def test_drop_picture_text_block_handles_multiline_content():
    """Picture-text blocks with long single-line content (many <br>) are handled.

    pymupdf4llm emits all content on a single line (with ``<br>`` separators
    within the line), even when the OCR'd text is long. The regex anchors on
    line boundaries (``^\n`` and ``<br>\n``) so multi-line content works.
    """
    text = (
        "**----- Start of picture text -----**<br>\n"
        "NPE NPE NPE<br>strategy strategy strategy<br>d<br>i i i<br>n<br>e<br>a<br>"
        "in<br>h h h<br>e<br>d<br>r a<br>n n n<br>u e<br>n<br>t v h v<br>"
        "tn<br>**----- End of picture text -----**<br>\n"
    )
    result = drop_picture_text_block(text, "le R<br>k<br>e<br>R<br>c")
    # Fingerprint doesn't match — block preserved
    assert "NPE NPE NPE" in result
    assert "End of picture text" in result


def test_drop_picture_text_block_idempotent():
    """Re-running drop on already-dropped text is a no-op (no second drop)."""
    text = (
        "**----- Start of picture text -----**<br>\n"
        "Making zero<br>the hero<br>**----- End of picture text -----**<br>\n"
    )
    once = drop_picture_text_block(text, "Making zero<br>the hero")
    twice = drop_picture_text_block(once, "Making zero<br>the hero")
    assert once == twice
    assert once == ""


def test_drop_picture_text_block_no_fingerprint_match_is_passthrough():
    """When no block contains the fingerprint, the input is unchanged."""
    text = (
        "**----- Start of picture text -----**<br>\n"
        "Making zero<br>the hero<br>**----- End of picture text -----**<br>\n"
    )
    assert drop_picture_text_block(text, "not in any block") == text


def test_apply_quirks_making_zero_the_hero_drops_decorative_blocks():
    """MakingZeroTheHero Summary: drops the page-1 cover graphic and the page-4
    vertical word art, keeping the page-3 NPE diagram and page-5 survey chart.

    Rule applied: only info-graphics (data-bearing visualizations) are
    referenced in markdown; pure graphics (decorative cover imagery, word
    art) are dropped.
    """
    filename = "pdf-default.md"
    assert filename in QUIRKS_BY_FILENAME

    sample = (
        "# Healthy Land\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "Making zero<br>the hero<br>**----- End of picture text -----**<br>\n"
        "\n"
        "A roadmap towards sustainable plastics use in New Zealand\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "NPE NPE NPE<br>strategy strategy strategy<br>tn<br>"
        "**----- End of picture text -----**<br>\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "u<br>le R<br>k<br>e<br>R<br>c<br>**----- End of picture text -----**<br>\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "4% Not intending to<br>**----- End of picture text -----**<br>\n"
    )
    result = apply_quirks(filename, sample)

    # Decorative blocks dropped
    assert "Making zero" not in result  # page-1 cover graphic
    assert "le R<br>k" not in result  # page-4 word art

    # Info-graphic blocks kept
    assert "NPE NPE NPE" in result  # page-3 NPE diagram
    assert "4% Not intending to" in result  # page-5 survey chart

    # The two surviving blocks each keep their start/end markers
    assert result.count("Start of picture text") == 2
    assert result.count("End of picture text") == 2


def test_apply_quirks_making_zero_the_hero_charter_passthrough():
    """Charter/constitution share ``pdf-default.md`` with MakingZeroTheHero but
    have no decorative picture-text blocks. The quirk's fingerprint drops
    only match the MakingZeroTheHero PDF — charter content passes through."""
    filename = "pdf-default.md"
    sample = (
        "# Charter\n"
        "\n"
        "**----- Start of picture text -----**<br>\n"
        "Charter signature image<br>**----- End of picture text -----**<br>\n"
    )
    # No fingerprint matches → no drop. The other quirk (orphan empty H2) is
    # scoped to 'desirability of a pan-sector vision', so charter passes through.
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


# ---------------------------------------------------------------------------
# strip_contents_section — drop the '## **Contents**' TOC table from PDF bodies
# ---------------------------------------------------------------------------


def test_strip_contents_section_removes_toc_table():
    """The '## **Contents**' heading and its following TOC table are removed.

    pymupdf4llm emits a TOC table for PDFs that have one (constitution.pdf).
    The rendered document provides its own navigation, so the duplicated table
    is dropped during the source→clean transform.
    """
    text = (
        "## **Contents**\n"
        "\n"
        "|1.|Formation ................................................. 3|\n"
        "|---|---|\n"
        "||Name and establishment......................................3|\n"
        "\n"
        "## **1. Formation**\n"
        "\n"
        "Body content here.\n"
    )
    stripped, removed = strip_contents_section(text)
    assert removed is True
    assert "## **Contents**" not in stripped
    assert "|1.|Formation" not in stripped
    # The next content section is preserved
    assert "## **1. Formation**" in stripped
    assert "Body content here." in stripped


def test_strip_contents_section_no_match_returns_false():
    """When no Contents section is present, returns the body unchanged and removed=False."""
    text = "## **Some heading**\n\nBody content.\n"
    stripped, removed = strip_contents_section(text)
    assert removed is False
    assert stripped == text


def test_strip_contents_section_idempotent():
    """Re-running on already-stripped text returns (body, False) — no double-stripping."""
    text = (
        "## **Contents**\n"
        "\n"
        "|1.|Formation ................................................. 3|\n"
        "\n"
        "## **1. Formation**\n"
    )
    once, removed_once = strip_contents_section(text)
    twice, removed_twice = strip_contents_section(once)
    assert removed_once is True
    assert removed_twice is False
    assert once == twice


def test_strip_contents_section_preserves_trailing_content():
    """Content after the TOC table is preserved verbatim (no trailing whitespace churn)."""
    text = (
        "Intro paragraph.\n"
        "\n"
        "## **Contents**\n"
        "\n"
        "|1.|Formation ................................................. 3|\n"
        "\n"
        "## **1. Formation**\n"
        "\n"
        "Body content.\n"
    )
    stripped, removed = strip_contents_section(text)
    assert removed is True
    # Intro before Contents preserved
    assert stripped.startswith("Intro paragraph.\n")
    # TOC removed
    assert "## **Contents**" not in stripped
    assert "|1.|Formation" not in stripped
    # Content section after TOC preserved
    assert "## **1. Formation**\n\nBody content.\n" in stripped


def test_demote_faq_question_headings_basic():
    """FAQ question H2s under the parent wrapper are demoted; wrapper stays H2.

    Each policy overview ends with ``## **<Policy>—Frequently Asked Questions**``
    followed by 5-30 bolded question headings. pymupdf4llm emits the questions
    as H2, so this quirk demotes them to H3 so they nest under the wrapper.
    """
    text = (
        "## **Healthy Oceans—Frequently Asked Questions**\n"
        "\n"
        "## **How much will this cost?**\n"
        "\n"
        "Body for the first FAQ.\n"
        "\n"
        "## **How will this affect recreational fishers?**\n"
        "\n"
        "Body for the second FAQ.\n"
    )
    result = demote_faq_question_headings(text)
    assert "## **Healthy Oceans—Frequently Asked Questions**" in result  # wrapper preserved
    assert "### **How much will this cost?**" in result
    assert "### **How will this affect recreational fishers?**" in result
    # No remaining H2 line for the questions (### is a substring of ##, so anchor at line start)
    import re as _re

    assert not _re.search(r"^## \*\*How much will this cost\?\*\*", result, flags=_re.M)


def test_demote_faq_question_headings_preserves_h2_outside_faq():
    """Headings before the FAQ wrapper are left alone — only the FAQ subtree is demoted."""
    text = (
        "## **Top section**\n"
        "\n"
        "Body.\n"
        "\n"
        "## **The problems we're solving**\n"
        "\n"
        "## **A problem statement**\n"
        "\n"
        "Problem body.\n"
        "\n"
        "## **Healthy Oceans—Frequently Asked Questions**\n"
        "\n"
        "## **First question?**\n"
        "\n"
        "FAQ body.\n"
    )
    result = demote_faq_question_headings(text)
    # Pre-FAQ H2s untouched (these are handled by demote_h2_under_problems_we_are_solving, not this quirk)
    assert "## **Top section**" in result
    assert "## **The problems we're solving**" in result
    assert "## **A problem statement**" in result
    # FAQ question demoted
    assert "### **First question?**" in result


def test_demote_faq_question_headings_no_wrapper_is_passthrough():
    """Documents without an FAQ section are returned unchanged."""
    text = "## **Top section**\n\n## **Subsection**\n\nBody.\n"
    assert demote_faq_question_headings(text) == text


def test_demote_faq_question_headings_idempotent():
    """Re-running on already-demoted text produces the same output."""
    text = (
        "## **Healthy Oceans—Frequently Asked Questions**\n"
        "\n"
        "## **First question?**\n"
        "\n"
        "Body.\n"
        "\n"
        "## **Second question?**\n"
        "\n"
        "More body.\n"
    )
    once = demote_faq_question_headings(text)
    twice = demote_faq_question_headings(once)
    assert once == twice


def test_apply_quirks_demotes_faq_questions_in_policy_overview():
    """The FAQ quirk is registered for pdf-policy-overview.md and applied via apply_quirks."""
    filename = "pdf-policy-overview.md"
    assert filename in QUIRKS_BY_FILENAME
    # Quick sanity check that the function appears in the registered quirks.
    quirk_fns = [fn for _, fn in QUIRKS_BY_FILENAME[filename]]
    assert demote_faq_question_headings in quirk_fns

    sample = (
        "## **Healthy Oceans—Frequently Asked Questions**\n"
        "\n"
        "## **Why not keep the status quo?**\n"
        "\n"
        "Body.\n"
    )
    result = apply_quirks(filename, sample)
    assert "### **Why not keep the status quo?**" in result
