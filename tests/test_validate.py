import json

from scf_api.overrides import Override, load_overrides
from scf_api.parse import parse_workbook
from scf_api.validate import validate_data_dir, validate_result

VERSION = "2099.1.1"


def _validate(workbook, overrides=()):
    result = parse_workbook(workbook, VERSION)
    outcome = validate_result(result, list(overrides))
    return result, outcome


def _findings(outcome, check):
    return [f for f in outcome.findings if f.check == check]


def test_clean_workbook_passes(clean_workbook):
    _, outcome = _validate(clean_workbook)
    assert not [f for f in outcome.findings if f.unresolved_fail], outcome.findings
    # The orphan source row surfaces as an xwalk-source warning, not a failure.
    warns = _findings(outcome, "xwalk-source")
    assert any("usa-state-zz-orphan" in f.message for f in warns)
    assert outcome.ok


def test_dangling_ao_fails(workbook_factory):
    _, outcome = _validate(workbook_factory("dangling-ao"))
    fails = _findings(outcome, "ao-control")
    assert len(fails) == 1
    assert fails[0].value == "ZZZ-99"
    assert fails[0].sheet == "Assessment Objectives 2099.1"
    assert fails[0].cell  # provenance recorded
    assert not outcome.ok


def test_en_dash_erl_resolves_normalized(workbook_factory):
    _, outcome = _validate(workbook_factory("en-dash-erl"))
    assert outcome.ok
    warns = _findings(outcome, "normalized-only")
    assert len(warns) == 1
    assert warns[0].value == "E–GOV-01"
    assert warns[0].resolution == "normalized:E-GOV-01"


def test_nbsp_erl_id_resolves_normalized(workbook_factory):
    _, outcome = _validate(workbook_factory("nbsp-erl-id"))
    assert outcome.ok
    warns = _findings(outcome, "normalized-only")
    # MON-01 and MON-02 both reference the NBSP-carrying ERL id.
    assert {w.owner for w in warns} == {"MON-01", "MON-02"}


def test_control_id_in_erl_column_fails_then_override_drops(workbook_factory):
    # The MON-03.3 workbook-typo class: a control id in the ERL column.
    _, outcome = _validate(workbook_factory("erl-control-id"))
    fails = _findings(outcome, "control-erl")
    assert len(fails) == 1 and fails[0].value == "MON-01"
    assert not outcome.ok

    ov = Override(
        id="mon-02-erl-typo",
        check="control-erl",
        control="MON-02",
        match="MON-01",
        action="drop",
        reason="workbook typo: control id in ERL column",
        applies_to=[VERSION],
    )
    result, outcome = _validate(workbook_factory("erl-control-id"), [ov])
    assert outcome.ok
    assert outcome.overrides_used == ["mon-02-erl-typo"]
    resolved = _findings(outcome, "control-erl")
    assert resolved[0].resolution == "override:mon-02-erl-typo"
    mon02 = next(c for c in result.catalog["controls"] if c["control_id"] == "MON-02")
    assert mon02["evidence_requests"] == ["E-MON-01"]


def test_override_replace_action(workbook_factory):
    ov = Override(
        id="mon-02-erl-fix",
        check="control-erl",
        control="MON-02",
        match="MON-01",
        action="replace",
        replacement="E-MON-01",
        reason="typo for E-MON-01",
    )
    result, outcome = _validate(workbook_factory("erl-control-id"), [ov])
    assert outcome.ok
    mon02 = next(c for c in result.catalog["controls"] if c["control_id"] == "MON-02")
    # Replacement collapses into the existing E-MON-01 duplicate entry.
    assert mon02["evidence_requests"] == ["E-MON-01", "E-MON-01"]


def test_override_accept_action(workbook_factory):
    ov = Override(
        id="accept-dangling-ao",
        check="ao-control",
        control="ZZZ-99_A01",
        match="ZZZ-99",
        action="accept",
        reason="future control; upstream confirms it lands next release",
    )
    result, outcome = _validate(workbook_factory("dangling-ao"), [ov])
    assert outcome.ok
    # accept keeps the data untouched
    aos = result.files["scf-assessment-objectives.json"]["assessment_objectives"]
    assert any(a["scf_control_id"] == "ZZZ-99" for a in aos)


def test_dup_control_id_fails(workbook_factory):
    _, outcome = _validate(workbook_factory("dup-control-id"))
    fails = _findings(outcome, "dup-id")
    assert len(fails) == 1
    assert fails[0].value == "TST-01"
    assert not outcome.ok


def test_renamed_source_header_warns_fuzzy(workbook_factory):
    _, outcome = _validate(workbook_factory("renamed-source-header"))
    assert outcome.ok
    warns = _findings(outcome, "xwalk-source")
    assert any("general-cis-csc-8-1" in f.message and "fuzzily" in f.message for f in warns)


def test_unused_override_warns(clean_workbook):
    ov = Override(
        id="stale-entry",
        check="control-erl",
        control="GOV-99",
        match="NOPE",
        action="drop",
        reason="obsolete",
    )
    _, outcome = _validate(clean_workbook, [ov])
    assert outcome.ok
    assert outcome.overrides_unused == ["stale-entry"]
    assert _findings(outcome, "override-unused")


def test_version_scoped_override_is_silent(clean_workbook):
    ov = Override(
        id="other-version",
        check="control-erl",
        control="GOV-99",
        match="NOPE",
        action="drop",
        reason="scoped elsewhere",
        applies_to=["1999.1"],
    )
    _, outcome = _validate(clean_workbook, [ov])
    assert not _findings(outcome, "override-unused")


def test_load_overrides_requires_reason(tmp_path):
    path = tmp_path / "overrides.json"
    path.write_text(
        json.dumps(
            {
                "overrides": [
                    {
                        "id": "x",
                        "check": "control-erl",
                        "control": "A",
                        "match": "B",
                        "action": "drop",
                        "reason": "",
                    }
                ]
            }
        )
    )
    try:
        load_overrides(path)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


def test_json_input_mode_roundtrip(clean_workbook, tmp_path):
    from scf_api import jsonio

    result, outcome = _validate(clean_workbook)
    assert outcome.ok
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    for name, obj in result.files.items():
        jsonio.write(data_dir / name, obj)

    outcome2 = validate_data_dir(data_dir, [], VERSION)
    assert outcome2.ok, [f for f in outcome2.findings if f.unresolved_fail]
