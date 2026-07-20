import json

from scf_api.verify_tree import Deviation, compare_trees


def _tree(root, files):
    for rel, obj in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj))
    return root


def test_equivalent_trees_pass(tmp_path):
    files = {"api/a.json": {"x": 1}, "api/sub/b.json": [1, 2]}
    ours = _tree(tmp_path / "ours", files)
    theirs = _tree(tmp_path / "theirs", files)
    assert compare_trees(ours, theirs, []) == []


def test_key_order_is_semantic_not_byte(tmp_path):
    ours = _tree(tmp_path / "ours", {"a.json": {"x": 1, "y": 2}})
    theirs = tmp_path / "theirs"
    theirs.mkdir()
    (theirs / "a.json").write_text('{"y": 2, "x": 1}')
    assert compare_trees(ours, theirs, []) == []


def test_missing_and_extra_files(tmp_path):
    ours = _tree(tmp_path / "ours", {"a.json": {}, "extra.json": {}})
    theirs = _tree(tmp_path / "theirs", {"a.json": {}, "gone.json": {}})
    diffs = compare_trees(ours, theirs, [])
    assert "missing from ours: gone.json" in diffs
    assert "extra in ours: extra.json" in diffs


def test_content_difference_reported(tmp_path):
    ours = _tree(tmp_path / "ours", {"a.json": {"controls": [{"control_id": "X", "risks": [1]}]}})
    theirs = _tree(
        tmp_path / "theirs", {"a.json": {"controls": [{"control_id": "X", "risks": [2]}]}}
    )
    diffs = compare_trees(ours, theirs, [])
    assert len(diffs) == 1
    assert "a.json" in diffs[0]


def test_allowlisted_deviation_passes(tmp_path):
    # The TDA-11.2 / MON-03.3 pattern: one field on one control may differ.
    ours = _tree(
        tmp_path / "ours",
        {"controls.json": {"controls": [{"control_id": "TDA-11.2", "risks": []}]}},
    )
    theirs = _tree(
        tmp_path / "theirs",
        {
            "controls.json": {
                "controls": [{"control_id": "TDA-11.2", "risks": ["[object Object]"]}]
            }
        },
    )
    assert compare_trees(ours, theirs, []) != []
    allow = [Deviation("TDA-11.2", "risks", "upstream exceljs parser bug")]
    assert compare_trees(ours, theirs, allow) == []
    # The allowlist is control-scoped: other controls still compare.
    theirs2 = _tree(
        tmp_path / "theirs2",
        {"controls.json": {"controls": [{"control_id": "GOV-01", "risks": ["R-1"]}]}},
    )
    ours2 = _tree(
        tmp_path / "ours2",
        {"controls.json": {"controls": [{"control_id": "GOV-01", "risks": []}]}},
    )
    assert compare_trees(ours2, theirs2, allow) != []
