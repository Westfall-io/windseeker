from __future__ import annotations

from typing import Dict, List, Set

import networkx as nx

from windseeker.errors import ImportCycleError, MissingPackageError
from windseeker.parsing import parse_imports_from_package_text


def build_import_graph_from_package_text(package_text: Dict[str, str]) -> nx.DiGraph:
    """
    Build directed graph:
        package --> imported_package

    Side effect:
        G.graph["unresolved_imports"] = dict[imported_pkg -> set(importers)]
    """
    G = nx.DiGraph()
    unresolved: dict[str, set[str]] = {}

    known_packages = set(package_text.keys())  # top-level only

    for pkg_name, pkg_full_text in package_text.items():
        G.add_node(pkg_name)

        imports = parse_imports_from_package_text(pkg_name, pkg_full_text)
        for imp_top in imports:
            G.add_node(imp_top)
            G.add_edge(pkg_name, imp_top)

            if imp_top not in known_packages:
                unresolved.setdefault(imp_top, set()).add(pkg_name)

    G.graph["unresolved_imports"] = unresolved
    return G


def find_cycles(G: nx.DiGraph) -> List[List[str]]:
    return list(nx.simple_cycles(G))


def _format_cycles(cycles: List[List[str]], max_show: int = 25) -> str:
    lines = []
    for i, cyc in enumerate(cycles[:max_show], start=1):
        if not cyc:
            continue
        loop = " -> ".join(cyc + [cyc[0]])
        lines.append(f"{i}. {loop}")
    if len(cycles) > max_show:
        lines.append(f"... and {len(cycles) - max_show} more")
    return "\n".join(lines)


def assert_acyclic_or_raise(G: nx.DiGraph) -> None:
    """Ensure there are no cycles; raise ImportCycleError if cycles exist."""
    if nx.is_directed_acyclic_graph(G):
        return
    cycles = list(nx.simple_cycles(G))
    msg = "Critical import recursion loop(s) detected:\n" + _format_cycles(cycles)
    raise ImportCycleError(msg)


def topological_packages(G: nx.DiGraph, *, dependencies_first: bool = True) -> List[str]:
    """
    Return a topological sort of package nodes.

    With edge direction (package -> imported_package):
      - dependencies_first=True: imported packages appear BEFORE importers
      - dependencies_first=False: importers appear before dependencies
    """
    assert_acyclic_or_raise(G)
    H = G.reverse(copy=False) if dependencies_first else G
    return list(nx.topological_sort(H))


def get_unresolved_imports(G: nx.DiGraph, *, ignore: Set[str] | None = None) -> dict[str, set[str]]:
    """
    Return unresolved imports dict, optionally filtering ignored imports.
    """
    ignore = ignore or set()
    unresolved: dict[str, set[str]] = G.graph.get("unresolved_imports", {}) or {}
    return {k: v for k, v in unresolved.items() if k not in ignore}


def format_unresolved_imports(unresolved: dict[str, set[str]]) -> str:
    lines = ["Missing imported package definitions detected:"]
    for imported_pkg in sorted(unresolved.keys()):
        importers = ", ".join(sorted(unresolved[imported_pkg]))
        lines.append(f"  - {imported_pkg}  (imported by: {importers})")
    return "\n".join(lines)


def assert_no_unresolved_imports_or_raise(
    G: nx.DiGraph,
    *,
    ignore: Set[str] | None = None,
    strict: bool = False,
) -> None:
    """
    Optional missing-import enforcement.

    By default (strict=False), we DO NOT raise because SysML standard libs may be
    valid imports but not present in scanned files.

    When strict=True, raise MissingPackageError if unresolved imports exist.
    """
    unresolved = get_unresolved_imports(G, ignore=ignore)

    if not unresolved:
        return

    if strict:
        raise MissingPackageError(format_unresolved_imports(unresolved))
