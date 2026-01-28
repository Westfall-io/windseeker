from windseeker.graph import build_import_graph_from_package_text, topological_packages


def test_topological_order_dependencies_first():
    package_text = {
        "A": "package A { import B; }",
        "B": "package B { import C; }",
        "C": "package C;",
    }

    G = build_import_graph_from_package_text(package_text)
    order = topological_packages(G, dependencies_first=True)

    assert order.index("C") < order.index("B")
    assert order.index("B") < order.index("A")
