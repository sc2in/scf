import pytest

from scf_api.workbook import (
    ColumnResolveError,
    ResolutionAliases,
    SCFWorkbook,
    SheetResolveError,
)


def test_sheet_resolution(clean_workbook):
    with SCFWorkbook(str(clean_workbook)) as wb:
        assert wb.resolve_sheet_name("controls") == "SCF 2099.1"
        assert wb.resolve_sheet_name("domains") == "SCF Domains & Principles"
        assert wb.resolve_sheet_name("sources") == "Authoritative Sources"
        assert wb.resolve_sheet_name("aos") == "Assessment Objectives 2099.1"
        assert wb.resolve_sheet_name("compensating") == "Compensating Controls 2099.1"
        assert wb.resolve_sheet_name("evidence") == "Evidence Request List 2099.1"
        assert wb.resolve_sheet_name("privacy") == "Data Privacy Mgmt Principles"
        assert wb.resolve_sheet_name("risks") == "Risk Catalog"
        assert wb.resolve_sheet_name("threats") == "Threat Catalog"


def test_missing_sheet_raises(clean_workbook):
    with SCFWorkbook(str(clean_workbook)) as wb:
        wb.sheet_names = [n for n in wb.sheet_names if "Risk" not in n]
        with pytest.raises(SheetResolveError):
            wb.resolve_sheet_name("risks")


def test_catalog_sheet_floating_header(clean_workbook):
    with SCFWorkbook(str(clean_workbook)) as wb:
        sheet = wb.catalog_sheet("risks", "Risk #")
        assert sheet.header_row == 6
        assert sheet.find_col("risk #") is not None


# --- rename resilience -----------------------------------------------------


def test_renamed_tab_resolves_via_builtin_alias(workbook_factory):
    """SCF 2026.2's "Focal Documents" resolves with no operator intervention."""
    wb_path = workbook_factory("renamed-tab")
    with SCFWorkbook(str(wb_path)) as wb:
        assert wb.resolve_sheet_name("sources") == "Focal Documents"
        # A built-in alias is the shipped manifest, so it must stay silent.
        assert wb.resolution_notes == []


def test_renamed_tab_does_not_steal_the_controls_sheet(workbook_factory):
    """ "Focal Documents" must not satisfy the `controls` pattern."""
    wb_path = workbook_factory("renamed-tab")
    with SCFWorkbook(str(wb_path)) as wb:
        assert wb.resolve_sheet_name("controls") == "SCF 2099.1"


def test_drifted_tab_name_is_normalized(workbook_factory):
    """Invisible whitespace drift resolves like column headers already do."""
    wb_path = workbook_factory("drifted-tab")
    with SCFWorkbook(str(wb_path)) as wb:
        assert wb.resolve_sheet_name("sources") == "Authoritative\xa0 \u200bSources"
        assert wb.resolution_notes == []


def test_unknown_tab_raises_without_an_alias(workbook_factory):
    wb_path = workbook_factory("unknown-tab")
    with SCFWorkbook(str(wb_path)) as wb:
        with pytest.raises(SheetResolveError):
            wb.resolve_sheet_name("sources")


def test_operator_sheet_alias_resolves_and_warns(workbook_factory):
    """An overrides.json alias rescues an unknown tab, loudly."""
    wb_path = workbook_factory("unknown-tab")
    aliases = ResolutionAliases(sheets={"sources": [("reference register", "ref-register-2099")]})
    with SCFWorkbook(str(wb_path), aliases=aliases) as wb:
        assert wb.resolve_sheet_name("sources") == "Reference Register"
        (note,) = wb.resolution_notes
        assert note["check"] == "resolution-alias"
        assert note["severity"] == "warn"
        assert note["value"] == "ref-register-2099"
        assert note["owner"] == "sheet:sources"


def test_builtin_patterns_win_over_operator_aliases(clean_workbook):
    """An alias can never steal a sheet the shipped manifest already resolves."""
    aliases = ResolutionAliases(sheets={"sources": [("lists", "bogus-alias")]})
    with SCFWorkbook(str(clean_workbook), aliases=aliases) as wb:
        assert wb.resolve_sheet_name("sources") == "Authoritative Sources"
        assert wb.resolution_notes == []


def test_renamed_column_resolves_via_builtin_alt(workbook_factory):
    """2026.2's "SCF #" and 2026.1.1's "SCF Control #" both resolve."""
    for defects, header in ((("renamed-cc-header",), "SCF #"), ((), "SCF Control #")):
        wb_path = workbook_factory(*defects)
        with SCFWorkbook(str(wb_path)) as wb:
            sheet = wb.sheet("compensating")
            assert sheet.header[sheet.col("scf #", alts=("scf control #",))] == header
            assert wb.resolution_notes == []


def test_operator_column_alias_resolves_and_warns(clean_workbook):
    aliases = ResolutionAliases(
        columns={"compensating": [("nonexistent col", "scf control #", "cc-alias-2099")]}
    )
    with SCFWorkbook(str(clean_workbook), aliases=aliases) as wb:
        sheet = wb.sheet("compensating")
        assert sheet.col("nonexistent col") == sheet.col("scf control #")
        (note,) = wb.resolution_notes
        assert note["check"] == "resolution-alias"
        assert note["value"] == "cc-alias-2099"
        assert note["owner"] == "column:compensating"


def test_unresolvable_column_lists_every_pattern_tried(clean_workbook):
    with SCFWorkbook(str(clean_workbook)) as wb:
        sheet = wb.sheet("compensating")
        with pytest.raises(ColumnResolveError) as exc:
            sheet.col("no such col", alts=("nor this one",))
        assert "'no such col', 'nor this one'" in exc.value.args[0]
