from scf_api.normalize import norm_key, normalize, split_multivalue


def test_normalize_folds_dashes():
    assert normalize("E–GOV-01") == "E-GOV-01"  # en dash
    assert normalize("E—GOV-01") == "E-GOV-01"  # em dash
    assert normalize("E−GOV-01") == "E-GOV-01"  # minus sign


def test_normalize_nbsp_and_whitespace():
    assert normalize("GOV-01\xa0") == "GOV-01"
    assert normalize("  GOV   01 ") == "GOV 01"
    assert normalize("A​B") == "AB"  # zero-width space


def test_norm_key_casefolds():
    assert norm_key("Gov-01") == norm_key("GOV-01")


def test_split_multivalue():
    assert split_multivalue("A\nB\n\n C ") == ["A", "B", "C"]
    assert split_multivalue(None) == []
    assert split_multivalue("") == []
    assert split_multivalue(5) == ["5"]
