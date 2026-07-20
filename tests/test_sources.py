from scf_api.sources import SourceRow, assign_api_ids, reconcile


def _row(row: int, header: str, fdi: str) -> SourceRow:
    return SourceRow(
        row=row, geography="General", header=header, fdi=fdi, source="X", fdn=f"Name of {fdi}"
    )


def test_assign_api_ids_collision_suffix():
    rows = [
        _row(2, "A", "general-nist-800-53-r5"),
        _row(3, "B", "General-NIST-800-53-R5"),
        _row(4, "C", "general-other"),
    ]
    assign_api_ids(rows)
    assert [r.api_id for r in rows] == [
        "general-nist-800-53-r5",
        "general-nist-800-53-r5-2",
        "general-other",
    ]


def test_reconcile_exact_normalized_fuzzy_unmatched():
    rows = [
        _row(2, "NIST\n800-53\nR5", "general-nist-800-53-r5"),
        _row(3, "ISO\n27002 \n2022", "general-iso-27002-2022"),  # NBSP: normalized
        _row(4, "CIS\nCSC\n8.1", "general-cis-csc-8-1"),  # fuzzy vs "CIS CSC 8.1 (2024)"
        _row(5, "Totally\nAbsent", "usa-state-zz-orphan"),
    ]
    assign_api_ids(rows)
    columns = {
        10: "NIST\n800-53\nR5",
        11: "ISO\n27002 \n2022",
        12: "CIS\nCSC 8.1\n(2024)",
        13: "Never\nMatched Column",
    }
    recon = reconcile(rows, columns)
    by_fdi = {m.source.fdi: m for m in recon.matches}
    assert by_fdi["general-nist-800-53-r5"].method == "exact"
    assert by_fdi["general-iso-27002-2022"].method == "normalized"
    assert by_fdi["general-cis-csc-8-1"].method == "fuzzy"
    assert by_fdi["general-cis-csc-8-1"].column_index == 12
    assert by_fdi["usa-state-zz-orphan"].method == "unmatched"
    assert recon.unmatched_columns == ["Never\nMatched Column"]

    manifest = recon.manifest()
    assert len(manifest["sources"]) == 4
    assert manifest["sources"][0]["score"] == 100
