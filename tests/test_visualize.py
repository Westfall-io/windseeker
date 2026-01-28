from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from windseeker.visualize import visualize_graph_to_file


def test_visualize_raises_on_empty_graph(tmp_path: Path) -> None:
    G = nx.DiGraph()
    with pytest.raises(ValueError):
        visualize_graph_to_file(G, out_path=str(tmp_path / "x.png"))


def test_visualize_raises_on_unknown_layout(tmp_path: Path) -> None:
    G = nx.DiGraph()
    G.add_node("A")
    with pytest.raises(ValueError):
        visualize_graph_to_file(G, out_path=str(tmp_path / "x.png"), layout="nope")


def test_visualize_refuses_cycles(tmp_path: Path) -> None:
    G = nx.DiGraph()
    G.add_edge("A", "B")
    G.add_edge("B", "A")  # cycle
    with pytest.raises(Exception):
        visualize_graph_to_file(G, out_path=str(tmp_path / "x.png"))
