"""Legacy SCF # column -> controls[].legacy_ids and scf-legacy-map.json."""

import json

import pytest
from conftest import PREVIOUS_IDS

from scf_api.cli import main
from scf_api.parse import LEGACY_MAP_FILE, PreviousRelease, legacy_ids, parse_workbook
from scf_api.validate import validate_data_dir, validate_result

VERSION = "2099.1.1"
PREVIOUS = PreviousRelease("2099.1", PREVIOUS_IDS)


def _parse(workbook, previous=PREVIOUS):
    return parse_workbook(workbook, VERSION, previous=previous)


def _fails(outcome, check):
    return [f for f in outcome.findings if f.check == check and f.unresolved_fail]


@pytest.mark.parametrize(
    ("cell", "expected"),
    [
        ("GOV-01", ["GOV-01"]),  # single id
        ("NONE", []),  # new control
        (" NONE ", []),
        ("GOV-02\nGOV-03", ["GOV-02", "GOV-03"]),  # two-id merge
        ("A-1\nB-2\nC-3", ["A-1", "B-2", "C-3"]),  # three-id merge
        (None, []),
    ],
)
def test_legacy_cell(cell, expected):
    assert legacy_ids(cell) == expected


def test_legacy_ids_per_control(workbook_factory):
    controls = {
        c["control_id"]: c for c in _parse(workbook_factory("layout-2026-3")).catalog["controls"]
    }
    assert controls["GOV-01"]["legacy_ids"] == []  # NONE
    assert controls["GOV-01.1"]["legacy_ids"] == ["GOV-01"]  # single (renumbered)
    assert controls["GOV-02"]["legacy_ids"] == ["GOV-02", "GOV-03"]  # merge
    assert controls["MON-02"]["legacy_ids"] == ["MON-05"]
    # Additive field: last in the record, after the optional errata.
    assert list(controls["GOV-01"])[-1] == "legacy_ids"


def test_no_legacy_column_emits_no_legacy_data(clean_workbook):
    """2026.2 and earlier have no Legacy SCF # column: no field, no map file."""
    result = _parse(clean_workbook)
    assert LEGACY_MAP_FILE not in result.files
    assert all("legacy_ids" not in c for c in result.catalog["controls"])
    assert validate_result(result, []).ok


def test_legacy_map(workbook_factory):
    result = _parse(workbook_factory("layout-2026-3"))
    legacy = result.files[LEGACY_MAP_FILE]
    assert legacy["from_version"] == "2099.1"
    assert legacy["to_version"] == VERSION
    assert legacy["map"] == {
        "GOV-01": {"new": "GOV-01.1", "merged": False, "deprecated": False},
        "GOV-02": {"new": "GOV-02", "merged": True, "deprecated": False},
        "GOV-03": {"new": "GOV-02", "merged": True, "deprecated": True},
        "MON-01": {"new": "MON-01", "merged": False, "deprecated": False},
        "MON-05": {"new": "MON-02", "merged": False, "deprecated": False},
        "TST-01": {"new": "TST-01", "merged": False, "deprecated": False},
    }
    outcome = validate_result(result, [])
    assert outcome.ok, [f.message for f in outcome.findings if f.unresolved_fail]


def test_map_is_a_function_onto_current_controls(workbook_factory):
    """Every old id has exactly one new id, and it is a real current control."""
    result = _parse(workbook_factory("layout-2026-3"))
    controls = result.catalog["controls"]
    current = {c["control_id"] for c in controls}
    olds = [old for c in controls for old in c["legacy_ids"]]
    assert len(olds) == len(set(olds))  # no old id on two rows
    mapping = result.files[LEGACY_MAP_FILE]["map"]
    assert set(mapping) == set(olds) == PREVIOUS_IDS
    assert {e["new"] for e in mapping.values()} <= current
    for c in controls:
        for old in c["legacy_ids"]:
            assert mapping[old]["new"] == c["control_id"]


def test_split_old_id_fails_the_gate(workbook_factory):
    result = _parse(workbook_factory("layout-2026-3", "legacy-split"))
    outcome = validate_result(result, [])
    assert not outcome.ok
    (split,) = _fails(outcome, "legacy-map-split")
    assert split.owner == "MON-01"
    # MON-05 lost its row, so the map no longer covers the previous release.
    assert any("MON-05" in f.message for f in _fails(outcome, "legacy-map-coverage"))


def test_deprecated_destination_mismatch_fails_the_gate(workbook_factory):
    result = _parse(workbook_factory("layout-2026-3", "legacy-deprecated-mismatch"))
    (finding,) = _fails(validate_result(result, []), "legacy-deprecated")
    assert finding.owner == "GOV-03"


def test_old_ids_must_equal_the_previous_release(workbook_factory):
    result = _parse(
        workbook_factory("layout-2026-3"), PreviousRelease("2099.1", PREVIOUS_IDS | {"X-1"})
    )
    (missing,) = _fails(validate_result(result, []), "legacy-map-coverage")
    assert "X-1" in missing.message


def test_unknown_target_fails_the_gate(workbook_factory):
    result = _parse(workbook_factory("layout-2026-3"))
    result.files[LEGACY_MAP_FILE]["map"]["TST-01"]["new"] = "TST-99"
    assert _fails(validate_result(result, []), "legacy-map-target")


def test_unknown_previous_release_warns(workbook_factory):
    result = _parse(workbook_factory("layout-2026-3"), previous=None)
    assert result.files[LEGACY_MAP_FILE]["from_version"] is None
    outcome = validate_result(result, [])
    assert outcome.ok
    assert any(f.check == "legacy-from-version" for f in outcome.findings)


def test_cli_finds_the_previous_release_in_the_data_dir(workbook_factory, tmp_path):
    """The autopilot parses over the previous release's data/: that catalog is
    the legacy map's from_version and its exact old-id set."""
    data = tmp_path / "data"
    data.mkdir()
    previous = {
        "framework": {"id": "scf-2099-1", "name": "SCF", "version": "2099.1"},
        "families": {},
        "controls": [{"control_id": cid} for cid in sorted(PREVIOUS_IDS)],
    }
    (data / "scf-2099-1.json").write_text(json.dumps(previous))
    args = [
        "parse",
        "--workbook",
        str(workbook_factory("layout-2026-3")),
        "--scf-version",
        VERSION,
        "--out",
        str(data),
        "--overrides",
        "/nonexistent",
        "--report",
        str(tmp_path / "report.json"),
    ]
    assert main(args) == 0
    legacy = json.loads((data / LEGACY_MAP_FILE).read_text())
    assert legacy["from_version"] == "2099.1"
    assert not (data / "scf-2099-1.json").exists()  # pruned

    # Re-parsing the same release reuses the committed map's from_version.
    assert main(args) == 0
    assert json.loads((data / LEGACY_MAP_FILE).read_text()) == legacy
    assert main(["validate", "--data", str(data)]) == 0
    assert validate_data_dir(data, [], VERSION).ok


def test_release_without_legacy_column_removes_the_stale_map(workbook_factory, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / LEGACY_MAP_FILE).write_text("{}")
    rc = main(
        [
            "parse",
            "--workbook",
            str(workbook_factory()),
            "--scf-version",
            VERSION,
            "--out",
            str(data),
            "--overrides",
            "/nonexistent",
            "--report",
            str(tmp_path / "report.json"),
        ]
    )
    assert rc == 0
    assert not (data / LEGACY_MAP_FILE).exists()
