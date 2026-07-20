import pytest

from scf_api.workbook import SCFWorkbook, SheetResolveError


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
