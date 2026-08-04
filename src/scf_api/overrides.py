"""Override map: version-scoped, human-authored resolutions for workbook bugs.

Every entry documents WHY (reason is mandatory) and which versions it applies
to. Actions:

- drop     remove the offending reference (list-valued checks: remove the
           value; record-keyed checks: drop the record)
- replace  substitute `replacement` for the offending reference
- accept   keep the data as-is; the finding is downgraded to accepted

An entry that matched nothing this run is itself a warning — stale overrides
must not accumulate silently.

The same file also carries a `resolution` section: operator-supplied fallback
patterns for sheet tabs and column headers the upstream workbook has renamed.
That section exists so a rename discovered by autopilot in production can be
fixed by editing JSON — no code change, no release — which is exactly what the
summon-a-human issue body tells the reader to do. Aliases are tried only after
the parser's built-in patterns miss, and a hit raises a WARN rather than
passing silently, so the alias gets folded into the parser later.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .workbook import ResolutionAliases

ACTIONS = ("drop", "replace", "accept")


@dataclass
class Override:
    id: str
    check: str
    control: str  # owning record id the finding is attached to
    match: str  # offending raw value
    action: str
    reason: str
    sheet: str | None = None
    replacement: str | None = None
    reported_upstream: str | None = None
    applies_to: list[str] | None = None

    def applies(self, version: str, check: str, owner: str, value: str) -> bool:
        if self.applies_to and version not in self.applies_to:
            return False
        return self.check == check and self.control == owner and self.match == value


def load_overrides(path: Path | None) -> list[Override]:
    if path is None or not Path(path).exists():
        return []
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = raw["overrides"] if isinstance(raw, dict) else raw
    out = []
    for e in entries:
        if not e.get("reason"):
            raise ValueError(f"override {e.get('id')!r} is missing its mandatory reason")
        if e.get("action") not in ACTIONS:
            raise ValueError(f"override {e.get('id')!r} has invalid action {e.get('action')!r}")
        out.append(
            Override(
                id=e["id"],
                check=e["check"],
                control=e["control"],
                match=e["match"],
                action=e["action"],
                reason=e["reason"],
                sheet=e.get("sheet"),
                replacement=e.get("replacement"),
                reported_upstream=e.get("reported_upstream"),
                applies_to=e.get("applies_to"),
            )
        )
    return out


def load_resolution_aliases(path: Path | None, version: str | None = None) -> ResolutionAliases:
    """Load the `resolution` section: operator fallbacks for renamed tabs/columns.

    Entries scoped with `applies_to` are filtered against `version` (when one
    is given), matching the semantics of the override map above.
    """
    aliases = ResolutionAliases()
    if path is None or not Path(path).exists():
        return aliases
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return aliases
    section = raw.get("resolution") or {}

    def scoped(entry: dict) -> bool:
        applies_to = entry.get("applies_to")
        return not (applies_to and version is not None and version not in applies_to)

    for e in section.get("sheets", []):
        if not e.get("reason"):
            raise ValueError(f"resolution alias {e.get('id')!r} is missing its mandatory reason")
        if not scoped(e):
            continue
        aliases.sheets.setdefault(e["kind"], []).append((e["pattern"], e["id"]))

    for e in section.get("columns", []):
        if not e.get("reason"):
            raise ValueError(f"resolution alias {e.get('id')!r} is missing its mandatory reason")
        if not scoped(e):
            continue
        aliases.columns.setdefault(e["kind"], []).append((e["pattern"], e["alias"], e["id"]))

    return aliases
