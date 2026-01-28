from windseeker.parsing import extract_top_level_packages_with_text


def test_extract_simple_packages():
    text = """
    package A;
    package B { part x; }
    library package C;
    """

    pkgs = dict(extract_top_level_packages_with_text(text))

    assert set(pkgs.keys()) == {"A", "B", "C"}
    assert "package A;" in pkgs["A"]
    assert "package B" in pkgs["B"]
    assert "library package C" in pkgs["C"]
