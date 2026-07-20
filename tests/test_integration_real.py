"""Integration against the real SCF workbook — gated on $SCF_WORKBOOK.

Verified ground truth at 2026.1.1: 1,468 controls, 33 families, 249
crosswalk frameworks, 5,776 AOs, 303 ERLs, 1,305 compensating controls,
258 privacy principles, 41 threats, 39 risks.
"""

import os

import pytest

WORKBOOK = os.environ.get("SCF_WORKBOOK")

pytestmark = pytest.mark.skipif(
    not WORKBOOK, reason="set $SCF_WORKBOOK to run real-workbook integration tests"
)


@pytest.fixture(scope="module")
def real_result():
    from scf_api.cli import infer_version
    from scf_api.parse import parse_workbook

    version = os.environ.get("SCF_VERSION") or infer_version(os.path.basename(WORKBOOK))
    return parse_workbook(WORKBOOK, version)


def test_counts(real_result):
    catalog = real_result.catalog
    assert len(catalog["controls"]) == 1468
    assert len(catalog["families"]) == 33
    xwalk = real_result.files["scf-crosswalks.json"]
    assert xwalk["metadata"]["total_frameworks"] == 249
    assert real_result.files["scf-assessment-objectives.json"]["total"] == 5776
    assert real_result.files["scf-evidence-requests.json"]["total"] == 303
    assert real_result.files["scf-compensating-controls.json"]["total"] == 1305
    assert real_result.files["scf-privacy-principles.json"]["total"] == 258
    assert real_result.files["scf-threats.json"]["total"] == 41
    assert real_result.files["scf-risks.json"]["total"] == 39


def test_known_workbook_typo_is_caught(real_result):
    """MON-03.3 lists control id MON-03.2 in its ERL column at 2026.1.1."""
    from scf_api.validate import validate_result

    if real_result.version != "2026.1.1":
        pytest.skip("typo is specific to 2026.1.1")
    outcome = validate_result(real_result, [])
    fails = [f for f in outcome.findings if f.unresolved_fail]
    assert any(
        f.check == "control-erl" and f.owner == "MON-03.3" and f.value == "MON-03.2" for f in fails
    )
