"""Text normalization for id matching and validation.

Normalization is used ONLY to match identifiers across sheets (and to fold
header text for column resolution). Output data always carries the raw cell
text; when a reference resolves only after normalization, the validator
records a `normalized-only` finding with both forms.

Pipeline: NFKC -> unicode-dash fold -> NBSP/zero-width removal ->
whitespace collapse -> strip. Case folding is applied for *matching* only,
never to stored values.
"""

from __future__ import annotations

import re
import unicodedata

# Every unicode dash/hyphen variant folds to ASCII hyphen-minus.
_DASHES = dict.fromkeys(
    map(
        ord,
        "‐‑‒–—―−﹘﹣－",
    ),
    "-",
)

# Zero-width and joiner characters vanish entirely.
_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)

_WS_RUN = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Normalize a cell value for identifier comparison (case preserved)."""
    s = unicodedata.normalize("NFKC", text)
    s = s.translate(_DASHES)
    s = s.translate(_ZERO_WIDTH)
    s = s.replace("\xa0", " ")
    s = _WS_RUN.sub(" ", s)
    return s.strip()


def norm_key(text: str) -> str:
    """Case-folded normalization — the actual match key."""
    return normalize(text).casefold()


def split_multivalue(cell: object) -> list[str]:
    """Split a newline-separated cell into raw, stripped, non-empty items.

    Duplicate lines (the workbook repeats refs inside some cells) collapse
    to their first occurrence — the published dataset's convention.
    """
    if cell is None:
        return []
    return list(dict.fromkeys(part.strip() for part in str(cell).split("\n") if part.strip()))
