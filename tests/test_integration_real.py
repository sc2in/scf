"""Integration against the real SCF workbook — gated on $SCF_WORKBOOK.

Ground truth is recorded per release, so one parser is proven against every
workbook vintage we support. Set $SCF_WORKBOOK (and optionally $SCF_VERSION
when the filename does not carry it) to run these.
"""

import os

import pytest

WORKBOOK = os.environ.get("SCF_WORKBOOK")

pytestmark = pytest.mark.skipif(
    not WORKBOOK, reason="set $SCF_WORKBOOK to run real-workbook integration tests"
)

# version -> (controls, families, frameworks, aos, erls, compensating,
#             privacy, threats, risks)
GROUND_TRUTH = {
    "2026.1.1": (1468, 33, 249, 5776, 303, 1305, 258, 41, 39),
    # 2026.2 renamed the "Authoritative Sources" tab to "Focal Documents" and
    # shortened the compensating "SCF Control #" header to "SCF #"; it also
    # added the QTS family and threat MT-28.
    "2026.2": (1534, 34, 252, 5956, 316, 1371, 258, 42, 39),
}


@pytest.fixture(scope="module")
def real_result():
    from scf_api.cli import infer_version
    from scf_api.parse import parse_workbook

    version = os.environ.get("SCF_VERSION") or infer_version(os.path.basename(WORKBOOK))
    return parse_workbook(WORKBOOK, version)


def test_counts(real_result):
    expected = GROUND_TRUTH.get(real_result.version)
    if expected is None:
        pytest.skip(f"no recorded ground truth for SCF {real_result.version}")
    controls, families, frameworks, aos, erls, compensating, privacy, threats, risks = expected

    catalog = real_result.catalog
    assert len(catalog["controls"]) == controls
    assert len(catalog["families"]) == families
    assert real_result.files["scf-crosswalks.json"]["metadata"]["total_frameworks"] == frameworks
    assert real_result.files["scf-assessment-objectives.json"]["total"] == aos
    assert real_result.files["scf-evidence-requests.json"]["total"] == erls
    assert real_result.files["scf-compensating-controls.json"]["total"] == compensating
    assert real_result.files["scf-privacy-principles.json"]["total"] == privacy
    assert real_result.files["scf-threats.json"]["total"] == threats
    assert real_result.files["scf-risks.json"]["total"] == risks


def test_no_operator_aliases_needed(real_result):
    """Every supported release resolves on built-in patterns alone.

    A resolution-alias finding here means a rename is being carried by
    overrides.json that should be folded into the parser.
    """
    assert real_result.findings == []


def test_sources_reconcile_without_guessing(real_result):
    """No crosswalk column may be matched by a low-confidence fuzzy guess."""
    weak = [
        s for s in real_result.manifest["sources"] if s["method"] == "fuzzy" and s["score"] < 90
    ]
    assert not weak, f"low-confidence source matches: {weak}"


def test_known_workbook_typo_is_caught(real_result):
    """MON-03.3 lists control id MON-03.2 in its ERL column.

    Present at 2026.1.1 and still present at 2026.2 — the reason the
    mon-03.3-erl-typo override is deliberately not version-scoped.
    """
    from scf_api.validate import validate_result

    if real_result.version not in ("2026.1.1", "2026.2"):
        pytest.skip(f"typo not characterized for SCF {real_result.version}")
    outcome = validate_result(real_result, [])
    fails = [f for f in outcome.findings if f.unresolved_fail]
    assert any(
        f.check == "control-erl" and f.owner == "MON-03.3" and f.value == "MON-03.2" for f in fails
    )
