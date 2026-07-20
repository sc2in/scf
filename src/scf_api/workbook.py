"""Workbook access: pattern-based sheet resolution and cell flattening.

Sheets are found by case-insensitive substring pattern, never by index —
sheet order and exact names change between SCF releases. Cells are read
with openpyxl in read_only+data_only mode, so formula cells yield their
cached values (the TEXTJOIN risk/threat summaries) and rich text arrives
as plain strings.
"""

from __future__ import annotations

from dataclasses import dataclass

from openpyxl import load_workbook

from .normalize import norm_key


class SheetResolveError(KeyError):
    """A required sheet could not be found by pattern."""


class ColumnResolveError(KeyError):
    """A required column could not be found in a sheet header."""


# pattern, exclude-patterns — all case-insensitive substrings.
SHEET_PATTERNS: dict[str, tuple[str, tuple[str, ...]]] = {
    "domains": ("domain", ()),
    "sources": ("authoritative sources", ()),
    "controls": (
        "scf",
        ("domain", "authoritative", "privacy", "objective", "list", "compensating", "catalog"),
    ),
    "compensating": ("compensating", ()),
    "evidence": ("evidence request", ()),
    "aos": ("assessment objectives", ("evidence",)),
    "privacy": ("privacy", ("evidence",)),
    "risks": ("risk catalog", ()),
    "threats": ("threat catalog", ()),
}


def cell_text(value: object) -> str | None:
    """Flatten a cell value to text. Numbers keep their shortest repr."""
    if value is None:
        return None
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return repr(value)
    return str(value)


@dataclass
class Sheet:
    """A materialized sheet: title, header row, and data rows (raw values)."""

    title: str
    header: list[str | None]
    rows: list[tuple]
    header_row: int  # 1-based row number of the header (provenance)

    def col(self, pattern: str, exclude: tuple[str, ...] = ()) -> int:
        """First column whose header contains pattern (normalized, case-insensitive)."""
        idx = self.find_col(pattern, exclude)
        if idx is None:
            raise ColumnResolveError(
                f"no column matching {pattern!r} in sheet {self.title!r} "
                f"(headers: {[h for h in self.header if h][:12]}...)"
            )
        return idx

    def find_col(self, pattern: str, exclude: tuple[str, ...] = ()) -> int | None:
        want = norm_key(pattern)
        for i, h in enumerate(self.header):
            if h is None:
                continue
            key = norm_key(str(h))
            if want in key and not any(norm_key(x) in key for x in exclude):
                return i
        return None


class SCFWorkbook:
    """The SCF master workbook, resolved sheet by pattern."""

    def __init__(self, path: str):
        self.path = path
        self._wb = load_workbook(path, read_only=True, data_only=True)
        self.sheet_names: list[str] = list(self._wb.sheetnames)

    def close(self) -> None:
        self._wb.close()

    def __enter__(self) -> "SCFWorkbook":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def resolve_sheet_name(self, kind: str) -> str:
        pattern, excludes = SHEET_PATTERNS[kind]
        for name in self.sheet_names:
            low = name.casefold()
            if pattern in low and not any(x in low for x in excludes):
                return name
        raise SheetResolveError(
            f"no sheet matching {pattern!r} (exclude={excludes!r}) in {self.sheet_names}"
        )

    def sheet(self, kind: str, header_row: int = 1) -> Sheet:
        """Materialize a sheet. header_row is 1-based; rows are what follows it."""
        name = self.resolve_sheet_name(kind)
        ws = self._wb[name]
        all_rows = list(ws.iter_rows(values_only=True))
        if len(all_rows) < header_row:
            raise ColumnResolveError(f"sheet {name!r} has no header row {header_row}")
        header = [cell_text(c) for c in all_rows[header_row - 1]]
        return Sheet(
            title=name,
            header=header,
            rows=all_rows[header_row:],
            header_row=header_row,
        )

    def catalog_sheet(self, kind: str, id_header: str) -> Sheet:
        """Resolve a catalog-style sheet (Risk/Threat) whose header row floats.

        These sheets carry several rows of prose before the real header; find
        the first row containing id_header and treat it as the header row.
        """
        name = self.resolve_sheet_name(kind)
        ws = self._wb[name]
        all_rows = list(ws.iter_rows(values_only=True))
        want = norm_key(id_header)
        for i, row in enumerate(all_rows):
            if any(c is not None and want in norm_key(str(c)) for c in row):
                return Sheet(
                    title=name,
                    header=[cell_text(c) for c in row],
                    rows=all_rows[i + 1 :],
                    header_row=i + 1,
                )
        raise ColumnResolveError(f"no header row containing {id_header!r} in sheet {name!r}")
