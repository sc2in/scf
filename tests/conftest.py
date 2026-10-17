"""Synthetic SCF workbook fixture, built at test time.

No SCF content and no binaries live in git — the workbook is constructed
here with openpyxl, mirroring the real sheet/column structure (2026.1.1
vintage) at miniature scale. Defects are opt-in so the clean fixture passes
the validation gate and each test injects exactly the failure it exercises:

- dangling-ao         AO row referencing a nonexistent control
- en-dash-erl         control's ERL ref written with an en-dash
- nbsp-erl-id         ERL sheet id carrying zero-width + NBSP corruption
- erl-control-id      control id in the ERL column (the MON-03.3 workbook typo)
- dup-control-id      duplicated control id row
- renamed-source-header  Sources header drifts from the column header (fuzzy match)

Upstream rename defects (the SCF 2026.2 shape, which broke autopilot):

- renamed-tab         "Authoritative Sources" tab renamed to "Focal Documents"
- renamed-cc-header   compensating "SCF Control #" header shortened to "SCF #"
- drifted-tab         same tab, NBSP + doubled space + zero-width space
- unknown-tab         a tab name no built-in pattern knows (operator-alias path)

Not a defect but a whole layout, the SCF 2026.3 shape (the default stays 2026.2):

- layout-2026-3       compensating controls inline on the controls tab (no separate
                      tab), a Risk/Threat likelihood matrix instead of the two summary
                      columns, "ERL Artifact", "Notes" instead of ODP, "Old Risk #"
"""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

VERSION = "2099.1.1"

DEFECTS = frozenset(
    {
        "dangling-ao",
        "en-dash-erl",
        "nbsp-erl-id",
        "erl-control-id",
        "dup-control-id",
        "renamed-source-header",
        # Upstream tab/header renames (SCF 2026.2 shape).
        "renamed-tab",  # "Authoritative Sources" -> "Focal Documents"
        "renamed-cc-header",  # "SCF Control #" -> "SCF #"
        "drifted-tab",  # same tab, NBSP + doubled space + zero-width space
        "unknown-tab",  # a name no built-in pattern knows (operator-alias path)
        "layout-2026-3",  # the 2026.3 workbook shape (see module docstring)
    }
)


RISK_IDS = ("R-AC-1", "R-GV-1")
THREAT_IDS = ("NT-1", "NT-2", "MT-1")

# The 2026.3 control tab carries compensating controls inline.
CC_HEADER = (
    "Risk if Primary Control\nNot Implemented",
    "Possible Compensating Control #1",
    "Compensating Control #1 Name",
    "Compensating Control # 1 Description",
    "Compensating Control #1 Justification",
    "Possible Compensating Control #2",
    "Compensating Control #2 Name",
    "Compensating Control # 2 Description",
    "Compensating Control #2 Justification",
)
CC_BLANK = ("N/A",) * len(CC_HEADER)
CC_INLINE = {
    "GOV-01.1": (
        "Risky without it.",
        "GOV-02",
        "Publish Things",
        "Mechanisms exist to publish things.",
        "Covers it.",
        "MON-01",
        "Monitor Things",
        "Mechanisms exist to monitor things.",
        "Watches it.",
    ),
}
MATRIX_HEADER = (
    *(f"Risk {rid}" for rid in RISK_IDS),
    *(f"Threat {tid}" for tid in THREAT_IDS),
)


def _matrix_cells(ids: tuple[str, ...], listed: str | None) -> list[str]:
    """Likelihood cells for one control: listed ids rate Likely, then Possible."""
    wanted = listed.split("\n") if listed else []
    return [
        "Unlikely" if i not in wanted else ("Likely" if wanted.index(i) == 0 else "Possible")
        for i in ids
    ]


def build_workbook(path: Path, defects: frozenset[str] = frozenset()) -> Path:
    unknown = defects - DEFECTS
    assert not unknown, f"unknown defects: {unknown}"
    new = "layout-2026-3" in defects
    wb = Workbook()
    wb.remove(wb.active)

    # --- Domains ---
    ws = wb.create_sheet("SCF Domains & Principles")
    ws.append(
        [
            "#",
            "SCF Domain",
            "SCF Identifier",
            "Security, Compliance & Resilience (SCR) Principles",
            "Principle Intent",
            "Control Count",
            "Control %",
        ]
    )
    ws.append([1, "Governance", "GOV", "Govern well.", "Because.", 3, 0.5])
    ws.append([2, "Monitoring", "MON", "Watch everything.", "Because.", 2, 0.33])
    ws.append([3, "Testing", "TST", "Test things.", "Because.", 1, 0.17])
    ws.append([None, None, None, None, "Total Control Count", 6, None])

    # --- Authoritative Sources (2026.2 renamed this tab to "Focal Documents") ---
    if "unknown-tab" in defects:
        sources_tab = "Reference Register"  # no built-in pattern matches this
    elif "drifted-tab" in defects:
        # NBSP + a doubled space + a zero-width space: invisible drift that
        # norm_key absorbs for column headers and now for tab names too.
        sources_tab = "Authoritative\xa0 \u200bSources"
    elif "renamed-tab" in defects:
        sources_tab = "Focal Documents"
    else:
        sources_tab = "Authoritative Sources"
    ws = wb.create_sheet(sources_tab)
    ws.append(
        [
            "Geography",
            "SCF Column Header",
            "Focal Document Identifier (FDI)",
            "Source",
            "Focal Document Name (FDN)",
            "Focal Document Title (FDT)",
            "Focal Document Source (FDS)",
            "Set Theory Relationship Mapping (STRM)",
        ]
    )
    cis_header = "CIS\nCSC\n8.1" if "renamed-source-header" in defects else "CIS\nCSC 8.1\n(2024)"
    ws.append(
        [
            "General",
            "AICPA\nTSC 2017:2022 (used for SOC 2)",
            "general-aicpa-tsc-2017",
            "AICPA",
            "Trust Services Criteria (TSC) (2017)",
            "t",
            "u",
            "s",
        ]
    )
    ws.append(
        [
            "General",
            "NIST\n800-53\nR5",
            "general-nist-800-53-r5",
            "NIST",
            "NIST SP 800-53 R5",
            "t",
            "u",
            "s",
        ]
    )
    ws.append(
        [
            "General",
            cis_header,
            "general-cis-csc-8-1",
            "CIS",
            "Critical Security Controls (CSC) (v8.1)",
            "t",
            "u",
            "s",
        ]
    )
    ws.append(
        [
            "General",
            "Dup\nFW\nOne",
            "general-dup-fw",
            "DUP",
            "Duplicated Framework (One)",
            "t",
            "u",
            "s",
        ]
    )
    ws.append(
        [
            "General",
            "Dup\nFW\nTwo",
            "general-dup-fw",
            "DUP",
            "Duplicated Framework (Two)",
            "t",
            "u",
            "s",
        ]
    )
    ws.append(
        [
            "USA",
            "ZZ\nOrphan Source",
            "usa-state-zz-orphan",
            "ZZ",
            "Orphan Source (no column)",
            "t",
            "u",
            "s",
        ]
    )

    # --- Controls ---
    ws = wb.create_sheet("SCF 2099.1")
    header = [
        "SCF Domain",
        "SCF Control",
        "SCF #",
        "Secure Controls Framework (SCF)\nControl Description",
        "Conformity Validation\nCadence",
        "Evidence Request List (ERL) #",
        "Possible Solutions & Considerations\nMicro-Small Business (<10 staff)\nBLS Firm Size Classes 1-2",
        "Possible Solutions & Considerations\nSmall Business (10-49 staff)\nBLS Firm Size Classes 3-4",
        "Possible Solutions & Considerations\nMedium Business (50-249 staff)\nBLS Firm Size Classes 5-6",
        "Possible Solutions & Considerations\nLarge Business (250-999 staff)\nBLS Firm Size Classes 7-8",
        "Possible Solutions & Considerations\nEnterprise (> 1,000 staff)\nBLS Firm Size Class 9",
        "SCF Control Question",
        "Relative Control Weighting",
        "PPTDF\nApplicability",
        "NIST CSF\nFunction Grouping",
        "SCRM Focus\n\nTIER 1\nSTRATEGIC",
        "SCRM Focus\n\nTIER 2\nOPERATIONAL",
        "SCRM Focus\n\nTIER 3\nTACTICAL",
        *(CC_HEADER if new else ()),
        "SCR-CMM Level 0\nNot Performed",
        "SCR-CMM Level 1\nPerformed Informally",
        "SCR-CMM Level 2\nPlanned & Tracked",
        "SCR-CMM Level 3\nWell Defined",
        "SCR-CMM Level 4\nQuantitatively Controlled",
        "SCR-CMM Level 5\nContinuously Improving",
        "SCF\nCommunity Derived",
        "SCF\nCORE\nFundamentals",
        "AICPA\nTSC 2017:2022 (used for SOC 2)",
        "NIST\n800-53\nR5",
        "ISO\n27002\n2022",
        "CIS\nCSC 8.1\n(2024)",
        "Dup\nFW\nOne",
        "Dup\nFW\nTwo",
        *(MATRIX_HEADER if new else ("Risk Threat Summary", "Control Threat Summary")),
        "Errata\n2099.1",
    ]
    ws.append(header)

    def control_row(
        domain: str,
        title: str,
        cid: str,
        erl: str | None,
        weight: int,
        marks: dict | None = None,
        xwalk: tuple = (None, None, None, None, None, None),
        risks: str | None = "R-AC-1\nR-GV-1",
        threats: str | None = "NT-1\nMT-1",
        errata: str | None = None,
    ) -> list:
        marks = marks or {}
        if new:
            tail = [*_matrix_cells(RISK_IDS, risks), *_matrix_cells(THREAT_IDS, threats)]
        else:
            tail = [risks, threats]
        return [
            domain,
            title,
            cid,
            f"Mechanisms exist to {title.lower()}.",
            "Annual",
            erl,
            "solo tip",
            "small tip",
            "medium tip",
            "large tip",
            "enterprise tip",
            f"Does the organization {title.lower()}?",
            weight,
            "Process",
            "Govern",
            marks.get("t1"),
            marks.get("t2"),
            marks.get("t3"),
            *(CC_INLINE.get(cid, CC_BLANK) if new else ()),
            "Not performed.",
            "Informal.",
            "Planned.",
            "Defined.",
            "Measured.",
            "Improving.",
            marks.get("community"),
            marks.get("core"),
            *xwalk,
            *tail,
            errata,
        ]

    gov01_erl = "E–GOV-01\nE-GOV-02" if "en-dash-erl" in defects else "E-GOV-01\nE-GOV-02"
    ws.append(
        control_row(
            "Governance",
            "Govern Things",
            "GOV-01",
            gov01_erl,
            10,
            {"t1": "x", "t2": "x", "t3": "x", "community": "x", "core": "x"},
            ("CC1.1\nCC1.2", "PM-1", "5.1\n5.4", "1.1", "D-1", "DD-1"),
            errata="- reworded",
        )
    )
    ws.append(
        control_row(
            "Governance",
            "Steer Things",
            "GOV-01.1",
            None,
            8,
            {"t3": "x", "core": "x"},
            (None, "PM-2", None, None, None, None),
        )
    )
    ws.append(
        control_row(
            "Governance",
            "Publish Things",
            "GOV-02",
            "E-GOV-02",
            5,
            {},
            ("CC1.2", None, "5.1", None, None, None),
            risks=None,
            threats=None,
        )
    )
    mon01_erl = "E-MON-01"
    ws.append(control_row("Monitoring", "Monitor Things", "MON-01", mon01_erl, 9))
    mon02_erl = "MON-01\nE-MON-01" if "erl-control-id" in defects else "E-MON-01"
    ws.append(control_row("Monitoring", "Log Things", "MON-02", mon02_erl, 7))
    ws.append(
        control_row(
            "Testing",
            "Test Things",
            "TST-01",
            "E-TST-01",
            2,
            {},
            ("CC9.9", None, None, None, None, None),
        )
    )
    if "dup-control-id" in defects:
        ws.append(control_row("Testing", "Test Things Twice", "TST-01", None, 1))

    # --- Compensating Controls (a separate tab until 2026.3 folded it in) ---
    ws = wb.create_sheet("Compensating Controls 2099.1")
    ws.append(
        [
            "SCF Control Name",
            "SCF #" if "renamed-cc-header" in defects else "SCF Control #",
            "SCF Control Description",
            "PPTDF\nApplicability",
            "Risk if Primary Control\nNot Implemented",
            "Possible Compensating Control #1",
            "Compensating Control Name",
            "Compensating Control #",
            "Compensating Control Justification",
            "Possible Compensating Control #2",
            "Compensating Control Name",
            "Compensating Control #",
            "Compensating Control Justification",
        ]
    )
    ws.append(
        [
            "Govern Things",
            "GOV-01",
            "desc",
            "Process",
            "Not Applicable (N/A)",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
            "N/A",
        ]
    )
    ws.append(
        [
            "Steer Things",
            "GOV-01.1",
            "desc",
            "Process",
            "Risky without it.",
            "GOV-02",
            "Publish Things",
            "Mechanisms exist to publish things.",
            "Covers it.",
            "MON-01",
            "Monitor Things",
            "Mechanisms exist to monitor things.",
            "Watches it.",
        ]
    )

    if new:
        wb.remove(ws)  # 2026.3 folded this tab into the controls tab

    # --- Evidence Request List ---
    ws = wb.create_sheet("Evidence Request List 2099.1")
    ws.append(
        [
            "#",
            "ERL #",
            "Area of Focus",
            "ERL Artifact" if new else "Documentation Artifact",
            "Artifact Description",
            "SCF Control Mappings",
            "Relevant\nCMMC 2.0 L2 Control",
        ]
    )
    ws.append([1, "E-GOV-01", "Governance", "Charter", "A charter.", "GOV-01", None])
    ws.append(
        [2, "E-GOV-02", "Governance", "Policy", "A policy.", "GOV-01\nGOV-02", "AC.L2-3.1.1"]
    )
    # Zero-width space inside + trailing NBSP: strip() handles the tail, but
    # only normalization resolves the embedded corruption.
    mon_erl_id = "E-MON​-01\xa0" if "nbsp-erl-id" in defects else "E-MON-01"
    ws.append(
        [3, mon_erl_id, "Monitoring", "Log config", "Log configuration.", "MON-01\nMON-02", None]
    )
    ws.append([4, "E-TST-01", "Testing", "Test report", "A test report.", "TST-01", None])

    # --- Assessment Objectives ---
    ws = wb.create_sheet("Assessment Objectives 2099.1")
    ws.append(
        [
            "SCF #",
            "SCF AO #",
            "SCF Assessment Objective (AO)\nIn addition to relevant policies, standards and "
            "procedures, the assessor shall examine, interview, and/or test to determine if "
            "appropriately scoped evidence exists to support the claim that:",
            "PPTDF\nApplicability",
            "SCF Assessment Objective (AO) Origin(s)",
            "Notes" if new else "Notes / Errata",
            "Assessment\nRigor (AR)",
            "SCF Defined Parameters (SDP)",
            "Organization Defined Parameters (ODP)",
        ]
    )
    ws.append(
        [
            "GOV-01",
            "GOV-01_A01",
            "governance is governed.",
            "Process",
            "SCF Created",
            None,
            1,
            None,
            None,
        ]
    )
    ws.append(
        [
            "GOV-01",
            "GOV-01_A02",
            "governance is reviewed.",
            "Process",
            "SCF Created",
            None,
            2,
            "at least annually",
            None,
        ]
    )
    ws.append(
        [
            "MON-01",
            "MON-01_A01",
            "monitoring is monitored.",
            "Technology",
            "53A_R5_SI-04a.[01]",
            None,
            "NIST 800-171",
            None,
            None,
        ]
    )
    if "dangling-ao" in defects:
        ws.append(
            [
                "ZZZ-99",
                "ZZZ-99_A01",
                "nothing exists.",
                "Process",
                "SCF Created",
                None,
                1,
                None,
                None,
            ]
        )

    if new:  # 2026.3 has no Organization Defined Parameters column
        ws.delete_cols(9)

    # --- Data Privacy Mgmt Principles ---
    ws = wb.create_sheet("Data Privacy Mgmt Principles")
    ws.append(
        [
            "#",
            "Principle Name",
            "SCF Data Privacy Management Principle (SCF-DPMP) Description",
            "SCF Control",
            "SCF #",
            "Secure Controls Framework (SCF)\nControl Description",
            "AICPA\nTSC 2017:2022 (used for SOC 2)",
            "EU\nGDPR",
        ]
    )
    ws.append(
        [
            1,
            "Privacy by Design",
            "Do privacy on purpose.",
            "Govern Things",
            "GOV-01",
            "desc",
            "CC1.1\nCC1.2",
            "Art 25",
        ]
    )
    ws.append([None, None, None, "Publish Things", "GOV-02", "desc", None, "Art 5"])

    # --- Threat Catalog ---
    ws = wb.create_sheet("Threat Catalog")
    ws.append(["THREAT CATALOG use case: things.", None, None, None, None])
    ws.append(["* Definition of threat", None, None, None, None])
    ws.append(["noun A thing.", None, None, None, None])
    ws.append(["verb To threaten.", None, None, None, None])
    ws.append([None, None, None, None, None])
    ws.append(
        [
            "Threat Grouping",
            "Threat #",
            "Threat*",
            "Threat Description",
            "Materiality Considerations\nWould it be material?",
        ]
    )
    ws.append([None, None, None, None, "≥ 5% of pre-tax income"])
    ws.append(["Natural Threat", "NT-1", "Flood", "Water everywhere.", "Unknown"])
    ws.append([None, "NT-2", "Fire", "Fire everywhere.", "Unknown"])
    ws.append(["Man-Made Threat", "MT-1", "Outage", "Nothing works.", "Unknown"])
    ws.append([None, None, None, None, None])
    ws.append(["Note: These are POSSIBLE threats.", None, None, None, None])

    # --- Risk Catalog ---
    ws = wb.create_sheet("Risk Catalog")
    ws.append(["RISK CATALOG use case: things.", None, None, None, None])
    ws.append(["* Definition of risk", None, None, None, None])
    ws.append(["noun A situation.", None, None, None, None])
    ws.append(["verb To expose.", None, None, None, None])
    ws.append([None, None, None, None, None])
    ws.append(
        [
            "Risk Grouping",
            "Risk #",
            *(["Old Risk #"] if new else []),
            "Risk*\nNote - Some of these risks indicate a deficiency",
            "Description of Possible Risk Due To Control Deficiency",
            "NIST CSF \nFunction",
        ]
    )
    ws.append([None, None, None, "IF THE CONTROL FAILS...", None])
    old = lambda rid: [rid] if new else []  # noqa: E731
    ws.append(
        [
            "Access Control",
            "R-AC-1",
            *old("R-AC-1"),
            "No accountability",
            "Cannot attribute.",
            "Protect",
        ]
    )
    ws.append(
        ["Governance", "R-GV-1", *old("R-GV-1"), "No governance", "Nobody steers.", "Govern"]
    )
    ws.append([None, None, None, None, None])
    ws.append(["Note: These are POSSIBLE risks.", None, None, None, None])

    # --- Lists (noise sheet, must be ignored) ---
    ws = wb.create_sheet("Lists")
    ws.append(["Threat Materiality"])

    wb.save(path)
    return path


@pytest.fixture
def workbook_factory(tmp_path):
    """Build a synthetic workbook with the requested defect set."""

    def factory(*defects: str) -> Path:
        return build_workbook(tmp_path / "scf-fixture.xlsx", frozenset(defects))

    return factory


@pytest.fixture
def clean_workbook(workbook_factory) -> Path:
    return workbook_factory()
