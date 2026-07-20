import json
from pathlib import Path

from scf_api import jsonio
from scf_api.build import build_docs
from scf_api.parse import parse_workbook
from scf_api.schemas import validate_schemas

VERSION = "2099.1.1"


def _data_dir(workbook, tmp_path) -> Path:
    result = parse_workbook(workbook, VERSION)
    data_dir = tmp_path / "data"
    data_dir.mkdir(exist_ok=True)
    for name, obj in result.files.items():
        jsonio.write(data_dir / name, obj)
    return data_dir


def test_build_tree_shape(clean_workbook, tmp_path):
    data_dir = _data_dir(clean_workbook, tmp_path)
    docs = tmp_path / "docs"
    summary = build_docs(data_dir, docs)

    assert summary["scf_version"] == VERSION
    assert summary["total_controls"] == 6
    assert summary["total_families"] == 3
    assert [f["family_code"] for f in summary["families"]] == ["GOV", "MON", "TST"]
    assert summary["weight_distribution"] == {"2": 1, "5": 1, "7": 1, "8": 1, "9": 1, "10": 1}

    api = docs / "api"
    assert (api / "controls" / "GOV-01.json").exists()
    assert (api / "families" / "GOV.json").exists()
    assert (api / "crosswalks" / "general-dup-fw-2.json").exists()
    assert (api / "assessment-objectives" / "GOV-02.json").exists()  # zero-AO control
    assert (api / "evidence-requests" / "E-GOV-01.json").exists()
    assert (api / "risks" / "R-AC-1.json").exists()
    assert (api / "threats" / "MT-1.json").exists()
    assert (api / "compensating-controls" / "GOV-01.1.json").exists()
    assert (docs / "index.html").exists()
    assert (docs / "llms.txt").exists()
    assert (docs / "llms-full.txt").exists()
    assert (api / "docs.md").exists()

    gov01 = json.loads((api / "controls" / "GOV-01.json").read_text())
    assert gov01["family_name"] == "Governance"
    assert gov01["crosswalks"]["general-aicpa-tsc-2017"] == ["CC1.1", "CC1.2"]
    # Enriched keys come after the base record keys.
    assert list(gov01)[-2:] == ["family_name", "crosswalks"]

    zero_ao = json.loads((api / "assessment-objectives" / "GOV-02.json").read_text())
    assert zero_ao == {"scf_control_id": "GOV-02", "total": 0, "assessment_objectives": []}

    controls_agg = json.loads((api / "controls.json").read_text())
    assert controls_agg["total"] == 6

    # Aggregates that mirror data files must be byte-identical to them.
    assert (api / "risks.json").read_bytes() == (data_dir / "scf-risks.json").read_bytes()
    assert (api / "assessment-objectives.json").read_bytes() == (
        data_dir / "scf-assessment-objectives.json"
    ).read_bytes()


def test_build_deterministic(clean_workbook, tmp_path):
    data_dir = _data_dir(clean_workbook, tmp_path)
    docs_a = tmp_path / "docs-a"
    docs_b = tmp_path / "docs-b"
    build_docs(data_dir, docs_a)
    build_docs(data_dir, docs_b)

    files_a = sorted(p.relative_to(docs_a) for p in docs_a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(docs_b) for p in docs_b.rglob("*") if p.is_file())
    assert files_a == files_b
    for rel in files_a:
        assert (docs_a / rel).read_bytes() == (docs_b / rel).read_bytes(), rel


def test_generated_data_passes_schemas(clean_workbook, tmp_path):
    data_dir = _data_dir(clean_workbook, tmp_path)
    assert validate_schemas(data_dir) == []


def test_no_trailing_newline(clean_workbook, tmp_path):
    data_dir = _data_dir(clean_workbook, tmp_path)
    payload = (data_dir / "scf-risks.json").read_bytes()
    assert payload.endswith(b"}")
