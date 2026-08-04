import json

from scf_api.cli import infer_version, main


def test_infer_version():
    assert infer_version("Secure.Controls.Framework.SCF.-.2026.1.1.xlsx") == "2026.1.1"
    assert infer_version("secure-controls-framework-scf-2025-3-1.xlsx") == "2025.3.1"
    assert infer_version("secure-controls-framework-scf-2026-1.xlsx") == "2026.1"
    assert infer_version("noversion.xlsx") is None


def test_parse_validate_build_roundtrip(clean_workbook, tmp_path, capsys):
    data = tmp_path / "data"
    docs = tmp_path / "docs"
    report = tmp_path / "validation" / "validation-report.json"

    rc = main(
        [
            "parse",
            "--workbook",
            str(clean_workbook),
            "--scf-version",
            "2099.1.1",
            "--out",
            str(data),
            "--overrides",
            "/nonexistent",
            "--report",
            str(report),
        ]
    )
    assert rc == 0
    assert (data / "scf-2099-1-1.json").exists()
    rep = json.loads(report.read_text())
    assert rep["summary"]["ok"] is True
    assert rep["workbook_sha256"]
    assert rep["reconciliation"]["sources"]

    rc = main(["validate", "--data", str(data)])
    assert rc == 0

    rc = main(["build", "--data", str(data), "--out", str(docs)])
    assert rc == 0
    assert (docs / "api" / "summary.json").exists()

    rc = main(["verify-tree", str(docs / "api"), str(docs / "api")])
    assert rc == 0


def test_parse_gate_blocks_bad_workbook(workbook_factory, tmp_path):
    data = tmp_path / "data"
    report = tmp_path / "report.json"
    rc = main(
        [
            "parse",
            "--workbook",
            str(workbook_factory("dangling-ao")),
            "--scf-version",
            "2099.1.1",
            "--out",
            str(data),
            "--overrides",
            "/nonexistent",
            "--report",
            str(report),
        ]
    )
    assert rc == 1
    # The gate blocks data writes entirely.
    assert not data.exists()
    rep = json.loads(report.read_text())
    assert rep["summary"]["ok"] is False
    fails = [f for f in rep["findings"] if f["severity"] == "fail" and not f["resolution"]]
    assert fails and fails[0]["check"] == "ao-control"


def test_version_bump_removes_the_previous_catalog(clean_workbook, tmp_path):
    """A version bump must not leave the old catalog behind.

    find_catalog() takes the first sorted scf-*.json, so a leftover
    scf-2099-1-1.json would shadow scf-2099-2.json and the build would
    silently publish the previous release.
    """
    from scf_api.build import find_catalog

    data = tmp_path / "data"
    args = ["parse", "--workbook", str(clean_workbook), "--out", str(data), "--overrides", "/none"]

    assert main([*args, "--scf-version", "2099.1.1"]) == 0
    assert (data / "scf-2099-1-1.json").exists()

    assert main([*args, "--scf-version", "2099.2"]) == 0
    assert (data / "scf-2099-2.json").exists()
    assert not (data / "scf-2099-1-1.json").exists()
    assert find_catalog(data)[1] == "2099.2"

    # Non-catalog scf-*.json satellites must survive the prune.
    assert (data / "scf-crosswalks.json").exists()
    assert (data / "scf-risks.json").exists()


def test_changelog_between_versions(clean_workbook, workbook_factory, tmp_path):
    from scf_api import jsonio
    from scf_api.parse import parse_workbook

    old = tmp_path / "old"
    new = tmp_path / "new"
    old.mkdir()
    new.mkdir()
    for name, obj in parse_workbook(clean_workbook, "2099.1.1").files.items():
        jsonio.write(old / name, obj)
    result = parse_workbook(clean_workbook, "2099.2")
    result.catalog["controls"][0]["title"] = "Govern Things Harder"
    for name, obj in result.files.items():
        jsonio.write(new / name, obj)

    from scf_api.changelog import generate_changelog

    text = generate_changelog(old, new)
    assert "2099.1.1 → 2099.2" in text
    assert "GOV-01" in text and "title" in text
