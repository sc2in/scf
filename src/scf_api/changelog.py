"""Human-readable changelog between two data/ directories."""

from __future__ import annotations

from pathlib import Path

from . import jsonio
from .build import find_catalog

_ENTITIES = [
    # (label, data file, collection key, id key)
    ("Controls", None, "controls", "control_id"),  # catalog file, special-cased
    ("Assessment objectives", "scf-assessment-objectives.json", "assessment_objectives", "ao_id"),
    ("Evidence requests", "scf-evidence-requests.json", "evidence_requests", "erl_id"),
    ("Risks", "scf-risks.json", "risks", "risk_id"),
    ("Threats", "scf-threats.json", "threats", "threat_id"),
    (
        "Compensating controls",
        "scf-compensating-controls.json",
        "compensating_controls",
        "control_id",
    ),
]


def _records(data_dir: Path, filename: str | None, key: str, id_key: str) -> dict[str, dict]:
    if filename is None:
        path, _ = find_catalog(data_dir)
    else:
        path = data_dir / filename
        if not path.exists():
            return {}
    obj = jsonio.read(path)
    return {r[id_key]: r for r in obj[key]}


def generate_changelog(old_dir: Path, new_dir: Path) -> str:
    old_dir, new_dir = Path(old_dir), Path(new_dir)
    _, old_version = find_catalog(old_dir)
    _, new_version = find_catalog(new_dir)

    lines = [f"## SCF {old_version} → {new_version}", ""]

    for label, filename, key, id_key in _ENTITIES:
        old = _records(old_dir, filename, key, id_key)
        new = _records(new_dir, filename, key, id_key)
        added = sorted(set(new) - set(old))
        removed = sorted(set(old) - set(new))
        changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
        if not (added or removed or changed):
            continue
        lines.append(f"### {label}")
        lines.append("")
        lines.append(
            f"{len(added)} added, {len(removed)} removed, {len(changed)} changed "
            f"({len(new)} total)"
        )
        lines.append("")
        if added:
            lines.append("**Added:** " + ", ".join(added[:50]) + (" …" if len(added) > 50 else ""))
        if removed:
            lines.append(
                "**Removed:** " + ", ".join(removed[:50]) + (" …" if len(removed) > 50 else "")
            )
        if changed:
            details = []
            for k in changed[:50]:
                fields = sorted(
                    f for f in old[k].keys() | new[k].keys() if old[k].get(f) != new[k].get(f)
                )
                details.append(f"{k} ({', '.join(fields)})")
            lines.append(
                "**Changed:** " + "; ".join(details) + (" …" if len(changed) > 50 else "")
            )
        lines.append("")

    # Crosswalk framework set changes
    old_x = jsonio.read(old_dir / "scf-crosswalks.json")
    new_x = jsonio.read(new_dir / "scf-crosswalks.json")
    old_fw = set(old_x["scf_to_framework"])
    new_fw = set(new_x["scf_to_framework"])
    added_fw = sorted(new_fw - old_fw)
    removed_fw = sorted(old_fw - new_fw)
    changed_fw = sorted(
        f for f in old_fw & new_fw if old_x["scf_to_framework"][f] != new_x["scf_to_framework"][f]
    )
    if added_fw or removed_fw or changed_fw:
        lines.append("### Crosswalk frameworks")
        lines.append("")
        lines.append(
            f"{len(added_fw)} added, {len(removed_fw)} removed, "
            f"{len(changed_fw)} with mapping changes ({len(new_fw)} total)"
        )
        lines.append("")
        if added_fw:
            lines.append("**Added:** " + ", ".join(added_fw))
        if removed_fw:
            lines.append("**Removed:** " + ", ".join(removed_fw))
        if changed_fw:
            lines.append(
                "**Mapping changes:** "
                + ", ".join(changed_fw[:30])
                + (" …" if len(changed_fw) > 30 else "")
            )
        lines.append("")

    if len(lines) == 2:
        lines.append("No dataset changes.")
        lines.append("")
    return "\n".join(lines)
