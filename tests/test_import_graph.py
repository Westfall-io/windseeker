from windseeker.main import build_import_graph_from_package_text


def test_build_import_graph():
    package_text = {
        "A": "package A { import B; }",
        "B": "package B;",
    }

    G = build_import_graph_from_package_text(package_text)

    assert set(G.nodes) == {"A", "B"}
    assert ("A", "B") in G.edges
