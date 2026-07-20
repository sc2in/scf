"""Crosswalk-column <-> Authoritative Sources reconciliation.

The controls sheet carries one column per mapped framework, delimited by the
AICPA landmark on the left and "Risk Threat Summary" on the right. The
Authoritative Sources sheet carries one row per framework with its column
header text and Focal Document Identifier (FDI). Header text drifts between
releases, so matching runs exact -> normalized -> rapidfuzz token_sort_ratio
(threshold 70), and every match lands in an auditable manifest.

Framework api ids come from the FDI, lowercased; a collision gets a numeric
suffix (-2, -3, ...) in sheet order — the same convention the upstream ids
already use (e.g. general-nist-800-53-r5-2).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rapidfuzz import fuzz, process as rf_process

from .normalize import norm_key

FUZZY_THRESHOLD = 70

MAPPING_LEFT_MARKER = "AICPA"
MAPPING_RIGHT_MARKER = "Risk Threat Summary"


@dataclass
class SourceRow:
    """One Authoritative Sources row (raw fields, sheet provenance)."""

    row: int  # 1-based sheet row
    geography: str | None
    header: str  # "SCF Column Header" cell — the column-matching key
    fdi: str  # Focal Document Identifier
    source: str | None
    fdn: str | None  # Focal Document Name — becomes display_name
    api_id: str = ""  # lowercased FDI, collision-suffixed


@dataclass
class SourceMatch:
    """Reconciliation result for one source row."""

    source: SourceRow
    column_index: int | None  # index into the controls sheet header, None = unmatched
    column_header: str | None
    score: int  # 100 exact/normalized, fuzzy score otherwise
    method: str  # exact | normalized | fuzzy | unmatched


@dataclass
class Reconciliation:
    matches: list[SourceMatch] = field(default_factory=list)
    unmatched_columns: list[str] = field(default_factory=list)

    def manifest(self) -> dict:
        return {
            "sources": [
                {
                    "fdi": m.source.fdi,
                    "api_id": m.source.api_id,
                    "sheet_row": m.source.row,
                    "header": m.source.header,
                    "matched_column": m.column_header,
                    "method": m.method,
                    "score": m.score,
                }
                for m in self.matches
            ],
            "unmatched_columns": self.unmatched_columns,
        }


def assign_api_ids(rows: list[SourceRow]) -> None:
    """FDI -> api_id: lowercase, numeric suffix on collision (sheet order)."""
    seen: dict[str, int] = {}
    for row in rows:
        base = row.fdi.strip().lower()
        n = seen.get(base, 0) + 1
        seen[base] = n
        row.api_id = base if n == 1 else f"{base}-{n}"


def reconcile(
    rows: list[SourceRow],
    columns: dict[int, str],
) -> Reconciliation:
    """Match each source row's header to a crosswalk column.

    columns: {controls-sheet column index: header text} for the landmark slice.

    When several source rows carry the SAME column header (a real 2026.1.1
    data-entry bug: usa-state-nv-privacy-law-2023 repeats the SB220 header),
    the LAST row in sheet order claims the column and earlier claimants go
    unmatched — the resolution the published dataset established.
    """
    result = Reconciliation()
    by_exact = {h: i for i, h in columns.items()}
    by_norm = {norm_key(h): i for i, h in columns.items()}
    remaining = dict(columns)  # candidates for fuzzy, drained as matched

    exact_claim = {row.header: row.row for row in rows}
    norm_claim = {norm_key(row.header): row.row for row in rows}

    fuzzy_queue: list[SourceRow] = []
    for row in rows:
        if row.header in by_exact and exact_claim[row.header] == row.row:
            idx = by_exact[row.header]
            result.matches.append(SourceMatch(row, idx, columns[idx], 100, "exact"))
            remaining.pop(idx, None)
        elif (
            norm_key(row.header) in by_norm
            and row.header not in by_exact
            and norm_claim[norm_key(row.header)] == row.row
        ):
            idx = by_norm[norm_key(row.header)]
            result.matches.append(SourceMatch(row, idx, columns[idx], 100, "normalized"))
            remaining.pop(idx, None)
        elif row.header in by_exact or norm_key(row.header) in by_norm:
            # Displaced by a later duplicate-header row: the header names a
            # column that belongs to another source. Guessing a different
            # column by fuzz would silently invent a crosswalk — refuse.
            result.matches.append(SourceMatch(row, None, None, 0, "unmatched"))
        else:
            fuzzy_queue.append(row)

    for row in fuzzy_queue:
        if remaining:
            choices = {i: norm_key(h) for i, h in remaining.items()}
            best = rf_process.extractOne(
                norm_key(row.header),
                choices,
                scorer=fuzz.token_sort_ratio,
            )
        else:
            best = None
        if best is not None and best[1] >= FUZZY_THRESHOLD:
            _, score, idx = best
            result.matches.append(SourceMatch(row, idx, columns[idx], int(score), "fuzzy"))
            remaining.pop(idx, None)
        else:
            result.matches.append(SourceMatch(row, None, None, 0, "unmatched"))

    result.unmatched_columns = [columns[i] for i in sorted(remaining)]
    # Keep manifest order = sheet order.
    result.matches.sort(key=lambda m: m.source.row)
    return result
