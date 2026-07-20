"""Equivalence proof: semantic JSON compare of two docs/api trees.

Compares every *.json file under both trees (branding pages — docs.md,
index.html, llms*.txt — are deliberately ours and excluded). A committed
deviation allowlist names (control_id, field) pairs whose values are
permitted to differ, wherever that control record appears in the tree;
each entry carries its reason.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Deviation:
    control_id: str
    field: str
    reason: str


def load_allowlist(path: Path | None) -> list[Deviation]:
    if path is None or not Path(path).exists():
        return []
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = raw["deviations"] if isinstance(raw, dict) else raw
    return [Deviation(e["control_id"], e["field"], e["reason"]) for e in entries]


def _scrub(node: object, allowlist: list[Deviation]) -> object:
    """Blank allowlisted fields on any control-shaped record, recursively."""
    if isinstance(node, dict):
        out = {}
        for key, value in node.items():
            out[key] = _scrub(value, allowlist)
        cid = out.get("control_id") or out.get("scf_control_id")
        if isinstance(cid, str):
            for dev in allowlist:
                if dev.control_id == cid and dev.field in out:
                    out[dev.field] = f"<allowlisted:{dev.reason}>"
        return out
    if isinstance(node, list):
        return [_scrub(v, allowlist) for v in node]
    return node


def compare_trees(ours: Path, theirs: Path, allowlist: list[Deviation]) -> list[str]:
    """Returns a list of human-readable differences; empty means equivalent."""
    ours, theirs = Path(ours), Path(theirs)
    our_files = {p.relative_to(ours) for p in ours.rglob("*.json")}
    their_files = {p.relative_to(theirs) for p in theirs.rglob("*.json")}

    diffs: list[str] = []
    for missing in sorted(str(p) for p in their_files - our_files):
        diffs.append(f"missing from ours: {missing}")
    for extra in sorted(str(p) for p in our_files - their_files):
        diffs.append(f"extra in ours: {extra}")

    for rel in sorted(our_files & their_files, key=str):
        a = _scrub(json.loads((ours / rel).read_text(encoding="utf-8")), allowlist)
        b = _scrub(json.loads((theirs / rel).read_text(encoding="utf-8")), allowlist)
        if a != b:
            diffs.append(f"content differs: {rel} ({_first_diff(a, b)})")
    return diffs


def _first_diff(a: object, b: object, path: str = "$") -> str:
    if type(a) is not type(b):
        return f"{path}: type {type(a).__name__} != {type(b).__name__}"
    if isinstance(a, dict):
        for key in a.keys() | b.keys():
            if key not in a:
                return f"{path}.{key}: missing in ours"
            if key not in b:
                return f"{path}.{key}: extra in ours"
            if a[key] != b[key]:
                return _first_diff(a[key], b[key], f"{path}.{key}")
        if list(a.keys()) != list(b.keys()):
            return f"{path}: key order differs"
        return f"{path}: ?"
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            if x != y:
                return _first_diff(x, y, f"{path}[{i}]")
        return f"{path}: ?"
    return f"{path}: {a!r} != {b!r}"
