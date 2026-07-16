"""Shared text cleanup helpers used by both PDF extraction and validation.

The PDF parser embeds font-glyph fallbacks as zero-width / replacement /
Private Use Area characters when a font glyph is unavailable. Both
production output (``pdf_convert.clean_body``) and validation
ground-truth comparison (``pdf_validation._normalise_for_compare``) need
to strip these so the two compare cleanly — kept in one place so they
can't drift apart.
"""

from __future__ import annotations

import re

# Zero-width + replacement + soft-hyphen + BOM. Constitution.pdf embeds
# these when 'ffi' / 'ffl' ligatures or accented chars can't be rendered.
_INLINE_GLYPH_RE = re.compile(r"[\u200b-\u200f\ufeff\ufffd\u00ad]")
# Private Use Area chars between letters are font-glyph fallbacks (the
# 'ffi' ligature renders as e.g. 'o<PUA>icers').
_PUA_BETWEEN_LETTERS_RE = re.compile(r"(?<=[A-Za-z])[\ue000-\uf8ff](?=[A-Za-z])")


def strip_glyphs(text: str) -> str:
    """Remove zero-width / replacement / PUA-between-letters characters.

    Ponytail: the regex set is tuned for the constitution PDF font —
    extending it requires re-running validation to confirm no regression.
    """
    return _PUA_BETWEEN_LETTERS_RE.sub("", _INLINE_GLYPH_RE.sub("", text))
