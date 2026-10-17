"""Compact diagnostics for fixing the parser after an upstream SCF release.

Written for small-context agents: every command prints a bounded, line-per-fact
summary instead of the 30k-line validation report or a 400-column header row.

- diagnose: parse a workbook, and on a structural miss print what was being
  looked for plus the closest real tabs/headers, so the fix is one edit.
- triage:   group a validation report's findings by check, with samples + hints.
- headers:  one-line-per-column view of a tab (index, header, first data cells).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from rapidfuzz import fuzz, process as rf_process

from .normalize import norm_key
from .workbook import ColumnResolveError, SCFWorkbook, SheetResolveError

# check -> what that failure shape almost always means (and where to fix it).
HINTS = {
    "control-risk": "risk ids not found: a column was probably misread (e.g. rating text read as "
    "ids). Check _parse_controls risk/threat reading + sources.matrix_columns.",
    "control-threat": "same as control-risk, for threats.",
    "likelihood-value": "a rating outside Unlikely/Possible/Likely: new vocabulary upstream. "
    "Extend LIKELIHOODS in parse.py only if it clearly maps; otherwise report it.",
    "control-erl": "ERL ids unmatched: wrong ERL column, or genuine workbook typo "
    "(typo => add an entry to overrides/overrides.json with a reason).",
    "erl-control": "evidence tab maps to unknown control ids: wrong column or renumbered controls.",
    "ao-control": "assessment-objective rows cite unknown control ids.",
    "cc-control": "compensating controls cite unknown control ids.",
    "privacy-control": "privacy rows cite unknown control ids.",
    "family-domain": "control id prefix not in the domains tab: domains parse is wrong or a "
    "family was added without a domains row.",
    "dup-id": "duplicate ids in a tab: usually upstream data entry; override or report upstream.",
    "xwalk-source": "crosswalk column and focal-document row did not pair up. A few unmatched "
    "non-framework columns (MCR/DSR) are normal; many means the landmark slice moved.",
    "xwalk-unmatched": "see xwalk-source.",
    "resolution-alias": "an operator alias in overrides.json was needed: fold it into "
    "SHEET_PATTERNS / alts=(...) in the parser.",
    "override-unused": "an override matched nothing: upstream may have fixed it. Scope it with "
    "applies_to rather than deleting (older releases still need it).",
    "sheet-resolve": "run `scf-api diagnose` for the closest tab names.",
    "col-resolve": "run `scf-api diagnose` for the closest headers.",
}


def _first_line(value: object, width: int = 60) -> str:
    text = " ".join(str(value).split()) if value is not None else ""
    return text if len(text) <= width else text[: width - 1] + "…"


def _best_header_row(rows: list[tuple]) -> int:
    """Index of the row with the most filled cells (the real header, not prose)."""
    return max(range(len(rows)), key=lambda i: sum(c is not None for c in rows[i]), default=0)


def _closest(needle: str, choices: dict[int, str], n: int = 6) -> list[tuple[int, str, int]]:
    keyed = {i: norm_key(c) for i, c in choices.items() if c}
    hits = rf_process.extract(norm_key(needle), keyed, scorer=fuzz.partial_ratio, limit=n)
    return [(i, choices[i], int(score)) for _, score, i in hits]


def diagnose(workbook: Path, version: str, overrides_path: Path | None = None) -> int:
    from .overrides import load_overrides, load_resolution_aliases
    from .parse import parse_workbook
    from .validate import validate_result

    aliases = load_resolution_aliases(overrides_path, version)
    try:
        result = parse_workbook(workbook, version, aliases=aliases)
    except SheetResolveError as exc:
        print(f"STRUCTURE: no tab matches kind {exc.kind!r} (tried {list(exc.patterns)})")
        with SCFWorkbook(str(workbook)) as wb:
            names = dict(enumerate(wb.sheet_names))
            print("tabs:", ", ".join(repr(n) for n in names.values()))
            for pat in exc.patterns[:1]:
                for _, name, score in _closest(pat, names, 3):
                    print(f"  closest to {pat!r}: {name!r} (score {score})")
        print(
            "FIX: add the new tab name FIRST in SHEET_PATTERNS[kind] in src/scf_api/workbook.py, "
            "keeping the old name after it. Re-run diagnose."
        )
        return 1
    except ColumnResolveError as exc:
        print(f"STRUCTURE: tab {exc.sheet_title!r} has no column matching {list(exc.patterns)}")
        headers = {i: h for i, h in enumerate(exc.header) if h}
        for pat in exc.patterns[:1]:
            for i, header, score in _closest(pat, headers):
                print(f"  col {i}: {_first_line(header, 70)!r} (score {score})")
        print(
            "FIX: at the failing `sheet.col(...)` call in src/scf_api/parse.py, put the new header "
            "first and keep the old as alts=(...). If the column is gone, see "
            "`scf-api headers --sheet <tab> --sample` and decide whether the data moved elsewhere. "
            "Re-run diagnose."
        )
        return 1

    outcome = validate_result(result, load_overrides(overrides_path))
    f = result.files
    print(f"PARSED SCF {version}: {outcome.summary()}")
    print(
        f"  controls={len(result.catalog['controls'])} families={len(result.catalog['families'])} "
        f"frameworks={f['scf-crosswalks.json']['metadata']['total_frameworks']} "
        f"aos={f['scf-assessment-objectives.json']['total']} "
        f"erls={f['scf-evidence-requests.json']['total']} "
        f"compensating={f['scf-compensating-controls.json']['total']} "
        f"privacy={f['scf-privacy-principles.json']['total']} "
        f"risks={f['scf-risks.json']['total']} threats={f['scf-threats.json']['total']}"
    )
    print("  (compare with GROUND_TRUTH in tests/test_integration_real.py; a count that")
    print("   drops to 0 or halves means a column/sheet was misread even if validation passed)")
    if not outcome.ok:
        print(triage_text([x for x in outcome.as_dict()]))
        return 1
    return 0


def triage_text(findings: list[dict], limit: int = 3) -> str:
    by_check: dict[str, list[dict]] = {}
    for f in findings:
        by_check.setdefault(f["check"], []).append(f)
    counts = Counter({k: len(v) for k, v in by_check.items()})
    lines: list[str] = []
    for check, n in counts.most_common():
        group = by_check[check]
        sev = Counter(f["severity"] for f in group)
        lines.append(f"{check}: {n} ({', '.join(f'{k}={v}' for k, v in sorted(sev.items()))})")
        for f in group[:limit]:
            where = f"{f.get('sheet') or '?'}!{f.get('cell') or '?'}"
            lines.append(f"    {where} {_first_line(f['message'], 110)}")
        if hint := HINTS.get(check):
            lines.append(f"    hint: {hint}")
    return "\n".join(lines) or "no findings"


def triage(report_path: Path, limit: int = 3) -> int:
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    print(f"SCF {report['scf_version']}: {report['summary']}")
    print(triage_text(report["findings"], limit))
    return 0 if report["summary"]["ok"] else 1


def headers(workbook: Path, sheet: str, grep: str | None, sample: bool) -> int:
    with SCFWorkbook(str(workbook)) as wb:
        matches = [n for n in wb.sheet_names if norm_key(sheet) in norm_key(n)]
        if not matches:
            print("no tab contains", repr(sheet), "- tabs:", ", ".join(map(repr, wb.sheet_names)))
            return 1
        for title in matches:
            rows = wb.peek(title, 14)
            h = _best_header_row(rows)
            print(f"== {title!r} header_row={h + 1}")
            below = rows[h + 1] if sample and h + 1 < len(rows) else ()
            for i, cell in enumerate(rows[h]):
                if cell is None or (grep and norm_key(grep) not in norm_key(str(cell))):
                    continue
                tail = f"  | {_first_line(below[i], 40)!r}" if i < len(below) and below[i] else ""
                print(f"{i:4d} {_first_line(cell, 70)!r}{tail}")
    return 0
