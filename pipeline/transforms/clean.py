"""Shared text-cleaning utilities for all transforms."""

import re


def strip_contents_section(body: str) -> tuple[str, bool]:
    """Remove a ``## **Contents**`` section and its TOC table from a PDF markdown body.

    pymupdf4llm emits a ``## **Contents**`` heading followed by a dot-leader TOC
    table for any PDF that has a TOC page (e.g. constitution.pdf). The rendered
    document provides its own navigation, so the duplicated table is dropped
    during the source→clean transform.

    Returns ``(stripped_body, removed_flag)``. The flag is ``True`` when a
    Contents section was actually removed; callers can use it to emit a comment
    explaining the removal.

    Idempotent: re-running on already-stripped text returns ``(body, False)``
    because the ``## **Contents**`` heading no longer matches.
    """
    # ponytail: one pattern, one replacement. The lookahead anchors at the next
    # `\n## ` (the first real content section) or end-of-string so we don't
    # swallow unrelated content. False positives only if a PDF body has another
    # `## **Contents**` heading unrelated to a TOC — none observed.
    pattern = r"## \*\*Contents\*\*\s*\n(?:.*\n)*?(?=\n## |\Z)"
    match = re.search(pattern, body)
    if not match:
        return body, False
    return body[: match.start()] + body[match.end() :], True


def strip_metadata_blockquote(body: str) -> str:
    """Remove leading '> **URL**: ...' and '> **Scraped**: ...' blockquote lines."""
    lines = body.split("\n")
    cleaned: list[str] = []
    for line in lines:
        if re.match(r"^>\s*\*\*(URL|Scraped)\*\*:", line):
            continue
        cleaned.append(line)
    # Strip leading blank lines after removal
    while cleaned and cleaned[0].strip() == "":
        cleaned.pop(0)
    return "\n".join(cleaned)


def strip_image_lines(body: str) -> str:
    """Remove all markdown image lines: ![alt](url) and [![alt](url)](link)."""
    lines = body.split("\n")
    cleaned: list[str] = []
    for line in lines:
        # Skip lines that are purely an image (possibly wrapped in a link)
        if re.match(r"^\[?!\[.*?\]\(.*?\)\]?\(.*?\)?\s*$", line.strip()):
            continue
        # Skip lines that are just an image with nothing else meaningful
        if re.match(r"^!\[.*?\]\(.*?\)\s*$", line.strip()):
            continue
        cleaned.append(line)
    # Remove runs of blank lines left behind (max 2 consecutive)
    return _normalise_blank_lines("\n".join(cleaned))


def strip_footer_sections(body: str) -> str:
    """Remove everything from '### Check out more policies' or '## Get Involved' to end-of-file."""
    body = re.sub(
        r"(?:###\s*Check out more policies|##\s*Get Involved).*",
        "",
        body,
        flags=re.DOTALL,
    )
    return body.rstrip()


def strip_duplicate_h1(body: str, title: str) -> str:
    """Remove duplicate # H1 headings that match the title (page template already adds H1)."""
    # Remove first one or more H1 lines that match the title
    escaped = re.escape(title.strip())
    # Match '# Title' at start of body (possibly with leading blank lines)
    # Also handles duplicate copies like '# Title\n# Title'
    pattern = rf"^(?:#\s+{escaped}\s*\n)+"
    body = re.sub(pattern, "", body, count=1)
    # Strip leading blank lines left behind
    body = body.lstrip("\n")
    return body


def extract_metadata_fields(body: str) -> tuple[dict[str, str], str]:
    """Extract '**Key**: Value' metadata lines from the body, returning them as a dict and the body with those lines removed."""
    fields: dict[str, str] = {}
    field_names = {
        "Title",
        "Date",
        "Author",
        "Location",
        "URL",
        "Scraped",
        "When",
        "Venue",
        "Address",
        "Role",
        "Electorate",
    }
    lines = body.split("\n")
    cleaned: list[str] = []
    for line in lines:
        m = re.match(r"^\*\*(.+?)\*\*:\s*(.+)$", line.strip())
        if m and m.group(1) in field_names:
            fields[m.group(1)] = m.group(2).strip()
            continue
        # Also match the prefix format: "**Role**: Candidate"
        m2 = re.match(r"^\*\*(.+?)\*\*:\s*(.+)$", line)
        if m2 and m2.group(1) in field_names:
            fields[m2.group(1)] = m2.group(2).strip()
            continue
        cleaned.append(line)
    return fields, "\n".join(cleaned)


def normalise_blank_runs(body: str) -> str:
    """Collapse 3+ consecutive blank lines into 2."""
    return _normalise_blank_lines(body)


def remove_close_x_carousel(body: str) -> str:
    """Remove trailing CLOSE (X) and carousel navigation sections."""
    body = re.sub(r"CLOSE\s*\(X\).*", "", body, flags=re.DOTALL | re.IGNORECASE)
    body = re.sub(r"Previous\s*\n\s*Next\s*$", "", body, flags=re.DOTALL)
    return body.rstrip()


def remove_media_contact(body: str) -> str:
    """Remove '##### Media Contact' sections at the end of files."""
    body = re.sub(r"#####\s*Media Contact.*", "", body, flags=re.DOTALL)
    return body.rstrip()


def clean_body(
    body: str,
    *,
    title: str = "",
    strip_footer: bool = True,
    strip_media_contact: bool = True,
) -> str:
    """Apply the full cleaning pipeline to a markdown body."""
    if strip_footer:
        body = strip_footer_sections(body)
    body = strip_metadata_blockquote(body)
    body = strip_image_lines(body)
    body = remove_close_x_carousel(body)
    if strip_media_contact:
        body = remove_media_contact(body)
    if title:
        body = strip_duplicate_h1(body, title)
    body = normalise_blank_runs(body)
    return body


def _normalise_blank_lines(text: str) -> str:
    """Collapse 3+ consecutive blank lines into at most 2 (i.e., one paragraph gap)."""
    return re.sub(r"\n{3,}", "\n\n", text)
