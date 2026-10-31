"""The validation gate: cross-sheet referential integrity over normalized ids.

Root cause of every past SCF pipeline stall: the master workbook is manually
maintained, and ids in one sheet don't reliably match other sheets. Every
id-bearing cell is checked here, normalized first, raw preserved. Fail-severity
findings block the release unless an override entry resolves them; the exit
status of `scf-api validate` is the hard gate everywhere (CI, autopilot).

Runs in two modes:
- workbook mode: over a ParseResult (sheet/cell provenance, reconciliation
  manifest, override application mutates the parsed data before writing)
- JSON-input mode: over a committed data/ directory (hermetic re-check; the
  data already has overrides applied, so unused overrides don't warn)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path

from . import jsonio
from .normalize import norm_key, split_multivalue
from .overrides import Override
from .parse import LEGACY_MAP_FILE, IdOccurrence, ParseResult, Ref

FAIL = "fail"
WARN = "warn"

# check -> target id-space
_REF_TARGET = {
    "ao-control": "control",
    "erl-control": "control",
    "cc-control": "control",
    "privacy-control": "control",
    "control-erl": "erl",
    "control-risk": "risk",
    "control-threat": "threat",
    "family-domain": "family",
}

CATALOG_RE = re.compile(r"scf-\d{4}-\d+(?:-\d+)*\.json$")

# Control counts of past releases (tests/test_integration_real.py GROUND_TRUTH).
# When the previous catalog itself is not at hand (JSON-input mode), a legacy
# map's old-id set must at least be exactly this large.
RELEASE_CONTROL_COUNTS = {
    "2026.1.1": 1468,
    "2026.2": 1534,
}


@dataclass
class Finding:
    check: str
    severity: str
    message: str
    owner: str
    value: str
    sheet: str | None = None
    cell: str | None = None
    resolution: str | None = None  # "override:<id>" | "normalized:<canonical>" | None

    @property
    def unresolved_fail(self) -> bool:
        return self.severity == FAIL and self.resolution is None


@dataclass
class ValidationOutcome:
    findings: list[Finding] = field(default_factory=list)
    overrides_used: list[str] = field(default_factory=list)
    overrides_unused: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.unresolved_fail for f in self.findings)

    def summary(self) -> dict:
        return {
            "fail": sum(1 for f in self.findings if f.unresolved_fail),
            "warn": sum(1 for f in self.findings if f.severity == WARN and not f.resolution),
            "resolved": sum(1 for f in self.findings if f.resolution),
            "ok": self.ok,
        }

    def as_dict(self) -> list[dict]:
        return [asdict(f) for f in self.findings]


def validate_result(
    result: ParseResult,
    overrides: list[Override],
    warn_unused_overrides: bool = True,
) -> ValidationOutcome:
    """Validate a ParseResult; overrides MUTATE result.files where they apply."""
    outcome = ValidationOutcome()
    outcome.findings.extend(Finding(**f) if isinstance(f, dict) else f for f in result.findings)

    id_spaces = _id_spaces(result.ids)
    _check_dup_ids(result.ids, outcome)
    _check_refs(result, id_spaces, overrides, outcome)
    _check_manifest(result.manifest, outcome)
    _check_legacy(result, outcome)

    used = set(outcome.overrides_used)
    for ov in overrides:
        if ov.id not in used:
            if ov.applies_to and result.version not in ov.applies_to:
                continue  # scoped to another version; silent
            if warn_unused_overrides:
                outcome.findings.append(
                    Finding(
                        check="override-unused",
                        severity=WARN,
                        message=f"override {ov.id!r} matched no finding this run",
                        owner=ov.control,
                        value=ov.match,
                    )
                )
            outcome.overrides_unused.append(ov.id)
    return outcome


def validate_data_dir(
    data_dir: Path, overrides: list[Override], version: str
) -> ValidationOutcome:
    """JSON-input mode: rebuild the reference model from committed data files."""
    result = _result_from_data(data_dir, version)
    # Committed data already has overrides applied; matching entries simply
    # confirm known deviations, and unmatched entries are expected.
    return validate_result(result, overrides, warn_unused_overrides=False)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _id_spaces(ids: dict[str, list[IdOccurrence]]) -> dict[str, tuple[set, dict]]:
    spaces = {}
    for entity, occurrences in ids.items():
        raw = {o.value for o in occurrences}
        normalized = {norm_key(o.value): o.value for o in occurrences}
        spaces[entity] = (raw, normalized)
    return spaces


def _check_dup_ids(ids: dict[str, list[IdOccurrence]], outcome: ValidationOutcome) -> None:
    for entity, occurrences in ids.items():
        seen: dict[str, IdOccurrence] = {}
        for occ in occurrences:
            if occ.value in seen:
                first = seen[occ.value]
                outcome.findings.append(
                    Finding(
                        check="dup-id",
                        severity=FAIL,
                        message=(
                            f"duplicate {entity} id {occ.value!r} "
                            f"(first at {first.sheet}!{first.cell})"
                        ),
                        owner=occ.value,
                        value=occ.value,
                        sheet=occ.sheet,
                        cell=occ.cell,
                    )
                )
            else:
                seen[occ.value] = occ


def _check_refs(
    result: ParseResult,
    id_spaces: dict[str, tuple[set, dict]],
    overrides: list[Override],
    outcome: ValidationOutcome,
) -> None:
    for ref in result.refs:
        target = _REF_TARGET.get(ref.check)
        if target is None or target not in id_spaces:
            continue
        raw, normalized = id_spaces[target]
        if ref.value in raw:
            continue
        canonical = normalized.get(norm_key(ref.value))
        if canonical is not None:
            outcome.findings.append(
                Finding(
                    check="normalized-only",
                    severity=WARN,
                    message=(
                        f"{ref.check}: {ref.owner!r} references {ref.value!r}, which resolves "
                        f"to {canonical!r} only after normalization"
                    ),
                    owner=ref.owner,
                    value=ref.value,
                    sheet=ref.sheet,
                    cell=ref.cell,
                    resolution=f"normalized:{canonical}",
                )
            )
            continue
        finding = Finding(
            check=ref.check,
            severity=FAIL,
            message=(f"{ref.owner!r} references unknown {target} id {ref.value!r}"),
            owner=ref.owner,
            value=ref.value,
            sheet=ref.sheet,
            cell=ref.cell,
        )
        ov = next(
            (o for o in overrides if o.applies(result.version, ref.check, ref.owner, ref.value)),
            None,
        )
        if ov is not None:
            _apply_override(result, ref, ov)
            finding.resolution = f"override:{ov.id}"
            if ov.id not in outcome.overrides_used:
                outcome.overrides_used.append(ov.id)
            if ov.action == "accept":
                finding.severity = WARN
        outcome.findings.append(finding)


def _check_manifest(manifest: dict, outcome: ValidationOutcome) -> None:
    if not manifest:
        return
    for src in manifest.get("sources", []):
        if src["matched_column"] is None:
            outcome.findings.append(
                Finding(
                    check="xwalk-source",
                    severity=WARN,
                    message=(
                        f"Authoritative Sources row {src['sheet_row']} "
                        f"({src['fdi']}) matched no crosswalk column"
                    ),
                    owner=src["fdi"],
                    value=src["header"],
                )
            )
        elif src["score"] < 100:
            outcome.findings.append(
                Finding(
                    check="xwalk-source",
                    severity=WARN,
                    message=(
                        f"{src['fdi']} matched column {src['matched_column']!r} "
                        f"only fuzzily (score {src['score']})"
                    ),
                    owner=src["fdi"],
                    value=src["header"],
                )
            )
    for col in manifest.get("unmatched_columns", []):
        outcome.findings.append(
            Finding(
                check="xwalk-source",
                severity=WARN,
                message=f"crosswalk column {col!r} matched no Authoritative Sources row",
                owner="",
                value=col,
            )
        )


def _check_legacy(result: ParseResult, outcome: ValidationOutcome) -> None:
    """The legacy (old -> new id) map must be a function onto real controls
    that covers the previous release exactly, and agree with controls[].legacy_ids."""
    catalog = result.files.get(result.catalog_name, {})
    controls = catalog.get("controls", [])
    legacy = result.files.get(LEGACY_MAP_FILE)
    carriers = [c for c in controls if "legacy_ids" in c]

    def fail(check: str, message: str, owner: str = "", value: str = "") -> None:
        outcome.findings.append(
            Finding(check=check, severity=FAIL, message=message, owner=owner, value=value)
        )

    if not carriers:
        if legacy is not None:
            fail("legacy-map-drift", f"{LEGACY_MAP_FILE} present but no control has legacy_ids")
        return
    if legacy is None:
        fail("legacy-map-drift", f"controls carry legacy_ids but {LEGACY_MAP_FILE} is missing")
        return

    # Old id -> every control claiming it. More than one = not a function.
    owners: dict[str, list[str]] = {}
    for c in carriers:
        for old in c["legacy_ids"]:
            owners.setdefault(old, []).append(c["control_id"])
    for old, news in owners.items():
        if len(news) > 1:
            fail(
                "legacy-map-split",
                f"old id {old!r} maps to several new controls: {news}",
                owner=old,
                value=", ".join(news),
            )

    mapping: dict[str, dict] = legacy.get("map", {})
    control_ids = {c["control_id"] for c in controls}
    for old, entry in mapping.items():
        if entry["new"] not in control_ids:
            fail(
                "legacy-map-target",
                f"old id {old!r} maps to {entry['new']!r}, which is not a "
                f"{result.version} control",
                owner=old,
                value=entry["new"],
            )

    # The map must be exactly what controls[].legacy_ids say.
    by_new = {c["control_id"]: c["legacy_ids"] for c in carriers}
    if set(mapping) != set(owners):
        diff = sorted(set(mapping) ^ set(owners))
        fail("legacy-map-drift", f"map keys differ from controls[].legacy_ids: {diff[:10]}")
    for old, entry in mapping.items():
        news = owners.get(old)
        if not news:
            continue
        olds = by_new.get(entry["new"], [])
        if entry["new"] != news[0] or entry["merged"] != (len(olds) > 1):
            fail(
                "legacy-map-drift",
                f"map entry {old!r} -> {entry} disagrees with controls[].legacy_ids",
                owner=old,
                value=entry["new"],
            )

    if legacy.get("to_version") != result.version:
        fail(
            "legacy-map-drift",
            f"legacy map to_version {legacy.get('to_version')!r} != {result.version!r}",
        )

    # Coverage: the old ids are exactly the previous release's control ids.
    from_version = legacy.get("from_version")
    previous = result.previous
    olds = set(mapping)
    if previous is not None and previous.control_ids is not None:
        missing = sorted(previous.control_ids - olds)
        extra = sorted(olds - previous.control_ids)
        if missing:
            fail(
                "legacy-map-coverage",
                f"{len(missing)} {previous.version} control(s) have no new id: {missing[:10]}",
                value=", ".join(missing[:10]),
            )
        if extra:
            fail(
                "legacy-map-coverage",
                f"{len(extra)} legacy id(s) are not {previous.version} controls: {extra[:10]}",
                value=", ".join(extra[:10]),
            )
    elif from_version in RELEASE_CONTROL_COUNTS:
        want = RELEASE_CONTROL_COUNTS[from_version]
        if len(olds) != want:
            fail(
                "legacy-map-coverage",
                f"legacy map covers {len(olds)} old ids; SCF {from_version} had {want} controls",
                value=str(len(olds)),
            )
    elif from_version is not None:
        outcome.findings.append(
            Finding(
                check="legacy-map-coverage",
                severity=WARN,
                message=(
                    f"no {from_version} catalog or recorded control count: old-id coverage "
                    f"of the legacy map is unchecked"
                ),
                owner="",
                value=str(from_version),
            )
        )


def _apply_override(result: ParseResult, ref: Ref, ov: Override) -> None:
    """Mutate parsed data per the override action."""
    if ov.action == "accept":
        return

    catalog = result.files.get(result.catalog_name, {})

    def edit_list(values: list[str]) -> list[str]:
        if ov.action == "drop":
            return [v for v in values if v != ref.value]
        return [ov.replacement if v == ref.value else v for v in values]

    if ref.check in ("control-erl", "control-risk", "control-threat"):
        key = {
            "control-erl": "evidence_requests",
            "control-risk": "risks",
            "control-threat": "threats",
        }[ref.check]
        for control in catalog.get("controls", []):
            if control["control_id"] == ref.owner:
                control[key] = edit_list(control[key])
    elif ref.check == "erl-control":
        data = result.files.get("scf-evidence-requests.json", {})
        for er in data.get("evidence_requests", []):
            if er["erl_id"] == ref.owner:
                er["scf_controls"] = edit_list(er["scf_controls"])
    elif ref.check == "ao-control":
        data = result.files.get("scf-assessment-objectives.json", {})
        records = data.get("assessment_objectives", [])
        if ov.action == "drop":
            records[:] = [r for r in records if r["ao_id"] != ref.owner]
        else:
            for r in records:
                if r["ao_id"] == ref.owner:
                    r["scf_control_id"] = ov.replacement
        data["total"] = len(records)
    elif ref.check == "privacy-control":
        data = result.files.get("scf-privacy-principles.json", {})
        records = data.get("privacy_principles", [])
        if ov.action == "drop":
            records[:] = [r for r in records if r["scf_control_id"] != ref.value]
        else:
            for r in records:
                if r["scf_control_id"] == ref.value:
                    r["scf_control_id"] = ov.replacement
        data["total"] = len(records)
    elif ref.check == "cc-control":
        data = result.files.get("scf-compensating-controls.json", {})
        records = data.get("compensating_controls", [])
        if ov.action == "drop":
            records[:] = [r for r in records if r["control_id"] != ref.owner]
        else:
            for r in records:
                if r["control_id"] != ref.owner:
                    continue
                for key in ("compensating_control_1", "compensating_control_2"):
                    block = r.get(key)
                    if block and block["control_id"] == ref.value:
                        block["control_id"] = ov.replacement
        data["total"] = len(records)


def _result_from_data(data_dir: Path, version: str) -> ParseResult:
    """Reconstruct the reference model from committed data/*.json files."""
    data_dir = Path(data_dir)
    result = ParseResult(version=version, files={})
    for path in sorted(data_dir.glob("*.json")):
        result.files[path.name] = jsonio.read(path)

    if result.catalog_name not in result.files:
        result.findings.append(
            Finding(
                check="sheet-resolve",
                severity=FAIL,
                message=f"{result.catalog_name} missing from {data_dir}",
                owner="",
                value=result.catalog_name,
            )
        )
        return result

    catalog = result.catalog

    def occurrences(entity: str, values: list[str], source: str) -> None:
        result.ids[entity] = [IdOccurrence(v, source, "") for v in values]

    occurrences("family", list(catalog.get("families", {})), "families")
    occurrences("control", [c["control_id"] for c in catalog.get("controls", [])], "controls")
    erl = result.files.get("scf-evidence-requests.json", {})
    occurrences("erl", [e["erl_id"] for e in erl.get("evidence_requests", [])], "evidence")
    risks = result.files.get("scf-risks.json", {})
    occurrences("risk", [r["risk_id"] for r in risks.get("risks", [])], "risks")
    threats = result.files.get("scf-threats.json", {})
    occurrences("threat", [t["threat_id"] for t in threats.get("threats", [])], "threats")
    aos = result.files.get("scf-assessment-objectives.json", {})
    occurrences("ao", [a["ao_id"] for a in aos.get("assessment_objectives", [])], "aos")

    for c in catalog.get("controls", []):
        cid = c["control_id"]
        for v in c.get("evidence_requests", []):
            result.refs.append(Ref("control-erl", v, cid, "data", cid))
        for v in c.get("risks", []):
            result.refs.append(Ref("control-risk", v, cid, "data", cid))
        for v in c.get("threats", []):
            result.refs.append(Ref("control-threat", v, cid, "data", cid))
        result.refs.append(
            Ref("family-domain", c.get("family", cid.split("-")[0]), cid, "data", cid)
        )
    for a in aos.get("assessment_objectives", []):
        result.refs.append(Ref("ao-control", a["scf_control_id"], a["ao_id"], "data", a["ao_id"]))
    for e in erl.get("evidence_requests", []):
        for v in e.get("scf_controls", []):
            result.refs.append(Ref("erl-control", v, e["erl_id"], "data", e["erl_id"]))
    cc = result.files.get("scf-compensating-controls.json", {})
    for r in cc.get("compensating_controls", []):
        result.refs.append(
            Ref("cc-control", r["control_id"], r["control_id"], "data", r["control_id"])
        )
        for key in ("compensating_control_1", "compensating_control_2"):
            block = r.get(key)
            if block:
                result.refs.append(
                    Ref(
                        "cc-control", block["control_id"], r["control_id"], "data", r["control_id"]
                    )
                )
    pp = result.files.get("scf-privacy-principles.json", {})
    for p in pp.get("privacy_principles", []):
        result.refs.append(
            Ref(
                "privacy-control",
                p["scf_control_id"],
                p["principle_name"],
                "data",
                p["scf_control_id"],
            )
        )
    return result
