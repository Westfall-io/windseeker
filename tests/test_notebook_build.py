from __future__ import annotations

import json
from pathlib import Path

import networkx as nx

from windseeker.notebook.build import write_notebook_in_dependency_order


def test_write_notebook_in_dependency_order_topo_cells(tmp_path: Path) -> None:
    # Edge direction in your project: pkg -> imported_pkg
    # If A imports B: edge A->B, deps-first order should be B then A.
    G = nx.DiGraph()
    G.add_edge("A", "B")

    package_text = {
        "A": "package A { private import B::*; }\n",
        "B": "package B;\n",
    }

    out = tmp_path / "out.ipynb"
    write_notebook_in_dependency_order(G, package_text, out_path=str(out))

    nb = json.loads(out.read_text(encoding="utf-8"))
    cells = nb["cells"]

    assert cells[0]["cell_type"] == "code"
    assert "package B" in "".join(cells[0]["source"])
    assert "package A" in "".join(cells[1]["source"])


def test_write_notebook_includes_view_cells(tmp_path: Path) -> None:
    G = nx.DiGraph()
    G.add_node("A")

    package_text = {"A": "package A;\n"}

    out = tmp_path / "out.ipynb"
    write_notebook_in_dependency_order(
        G,
        package_text,
        views=["A::Views::v1"],
        out_path=str(out),
    )

    nb = json.loads(out.read_text(encoding="utf-8"))
    cells = nb["cells"]

    # Expect: 1 code cell for A, then markdown title + %view cell
    assert len(cells) == 3
    assert cells[1]["cell_type"] == "markdown"
    assert "A::Views::v1" in "".join(cells[1]["source"])
    assert cells[2]["cell_type"] == "code"
    assert "".join(cells[2]["source"]).lstrip().startswith("%view A::Views::v1")
