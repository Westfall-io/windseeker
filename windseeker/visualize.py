from __future__ import annotations

from typing import Tuple

import matplotlib.pyplot as plt
import networkx as nx

from windseeker.graph import assert_acyclic_or_raise


def visualize_graph_to_file(
    G: nx.DiGraph,
    out_path: str,
    *,
    title: str | None = "SysML Package Import Graph",
    figsize: Tuple[float, float] = (16, 10),
    dpi: int = 200,
    layout: str = "kamada_kawai",  # spring|kamada_kawai|shell
    seed: int = 42,
) -> None:
    """
    Write a NetworkX visualization to an image file.
    Refuses to write if there are cycles (critical recursion loop).
    """
    assert_acyclic_or_raise(G)

    if G.number_of_nodes() == 0:
        raise ValueError("Graph is empty: no packages/imports found.")

    if layout == "spring":
        pos = nx.spring_layout(G, seed=seed)
    elif layout == "kamada_kawai":
        pos = nx.kamada_kawai_layout(G)
    elif layout == "shell":
        pos = nx.shell_layout(G)
    else:
        raise ValueError(f"Unknown layout: {layout}")

    plt.figure(figsize=figsize)
    if title:
        plt.title(title)

    nx.draw_networkx_nodes(G, pos, node_size=900)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=15, width=1.2)
    nx.draw_networkx_labels(G, pos, font_size=8)

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=dpi)
    plt.close()
