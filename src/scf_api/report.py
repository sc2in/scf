"""Validation report: the single artifact that carries a timestamp.

Everything else in this repo is deterministic; the report records when the
gate ran, over which workbook bytes, what it found, and how each finding was
resolved — the audit trail a human needs when autopilot summons them.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import jsonio
from .validate import ValidationOutcome


def build_report(
    version: str,
    workbook_sha256: str,
    outcome: ValidationOutcome,
    manifest: dict,
    workbook_path: str | None = None,
) -> dict:
    return {
        "scf_version": version,
        "workbook_sha256": workbook_sha256,
        "workbook": workbook_path,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "summary": outcome.summary(),
        "findings": outcome.as_dict(),
        "overrides": {
            "used": outcome.overrides_used,
            "unused": outcome.overrides_unused,
        },
        "reconciliation": manifest,
    }


def write_report(report: dict, path: Path) -> None:
    if str(path) == "/dev/null":
        return
    jsonio.write(Path(path), report)


def human_summary(report: dict) -> str:
    """Markdown summary for GitHub issues when the gate fails."""
    lines = [
        f"# SCF {report['scf_version']} validation failed",
        "",
        f"- workbook sha256: `{report['workbook_sha256']}`",
        f"- generated: {report['generated_at']}",
        f"- summary: {report['summary']}",
        "",
        "## Unresolved findings",
        "",
    ]
    for f in report["findings"]:
        if f["severity"] == "fail" and not f["resolution"]:
            where = f"{f.get('sheet') or '?'}!{f.get('cell') or '?'}"
            lines.append(f"- **{f['check']}** at {where}: {f['message']}")
    lines += [
        "",
        "Author an override-map entry (overrides/overrides.json) with a reason,",
        "or report the workbook bug upstream, then re-dispatch the update workflow.",
    ]
    return "\n".join(lines)
