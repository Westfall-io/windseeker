from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import networkx as nx

from windseeker.graph import (
    assert_acyclic_or_raise,
    assert_no_unresolved_imports_or_raise,
    build_import_graph_from_package_text,
    get_unresolved_imports,
    topological_packages,
)
from windseeker.notebook.build import write_notebook_in_dependency_order
from windseeker.notebook.execute import execute_and_fail_on_notebook_errors
from windseeker.parsing import collect_all_views
from windseeker.scan import scan_folder
from windseeker.visualize import visualize_graph_to_file
from windseeker.views.extract import extract_view_images_from_executed_notebook
from windseeker.views.render import SvgRenderLimits


@dataclass(frozen=True)
class PipelineResult:
    package_text: Dict[str, str]
    graph: nx.DiGraph
    topo_order: List[str]
    views: List[str]
    unresolved_imports: dict[str, set[str]]
    written_view_files: List[str]


def run_pipeline(
    *,
    folder: str,
    write_graph: bool = True,
    graph_png: str = "imports.png",
    graph_layout: str = "kamada_kawai",
    sysml_out: str = "packages_in_dependency_order.sysml",
    notebook_out: str = "packages_in_dependency_order.ipynb",
    execute: bool = True,
    executed_notebook_out: str = "packages_in_dependency_order_executed.ipynb",
    export_views: bool = True,
    views_dir: str = "views",
    write_svg: bool = True,
    write_png: bool = True,
    write_jpg: bool = False,
    png_transparent: bool = True,
    png_bg: str = "#ffffff",
    ignore_missing: Optional[Set[str]] = None,
    strict_missing: bool = False,
    # If True, view-cell errors become fatal (default False = warn only)
    fail_on_view_errors: bool = False,
    svg_limits: SvgRenderLimits | None = None,
) -> PipelineResult:
    ignore_missing = ignore_missing or {"<root>"}
    svg_limits = svg_limits or SvgRenderLimits()

    package_text = scan_folder(folder)
    G = build_import_graph_from_package_text(package_text)

    # Fail fast on cycles
    assert_acyclic_or_raise(G)

    # Missing imports: record + optionally raise (strict_missing)
    assert_no_unresolved_imports_or_raise(G, ignore=ignore_missing, strict=strict_missing)
    unresolved = get_unresolved_imports(G, ignore=ignore_missing)

    # Views (fully qualified)
    views = collect_all_views(package_text)

    # Optional graph output
    if write_graph:
        visualize_graph_to_file(G, graph_png, layout=graph_layout)

    # Topological order (deps first)
    order = topological_packages(G, dependencies_first=True)

    # Dependency ordered SysML concatenation
    _write_sysml_in_dependency_order(G, package_text, out_path=sysml_out)

    # Notebook build
    write_notebook_in_dependency_order(G, package_text, views=views, out_path=notebook_out)

    written_views: List[str] = []

    # Notebook execute + extract
    if execute:
        execute_and_fail_on_notebook_errors(
            notebook_out,
            executed_out_path=executed_notebook_out,
            fail_on_view_errors=fail_on_view_errors,
        )

        if export_views:
            written_views = extract_view_images_from_executed_notebook(
                executed_notebook_out,
                out_dir=views_dir,
                write_svg=write_svg,
                write_png=write_png,
                write_jpg=write_jpg,
                png_transparent_background=png_transparent,
                png_background_color=png_bg,
                svg_limits=svg_limits,
            )

    return PipelineResult(
        package_text=package_text,
        graph=G,
        topo_order=order,
        views=views,
        unresolved_imports=unresolved,
        written_view_files=written_views,
    )


def order_only(*, folder: str, dependencies_first: bool = True) -> List[str]:
    package_text = scan_folder(folder)
    G = build_import_graph_from_package_text(package_text)
    assert_acyclic_or_raise(G)
    return topological_packages(G, dependencies_first=dependencies_first)


def _write_sysml_in_dependency_order(
    G: nx.DiGraph, package_text: Dict[str, str], *, out_path: str
) -> None:
    order = topological_packages(G, dependencies_first=True)
    order = [p for p in order if p in package_text]

    chunks: List[str] = []
    for pkg in order:
        chunks.append(f"// ===== PACKAGE: {pkg} =====")
        chunks.append(package_text[pkg].rstrip())
        chunks.append("")

    from pathlib import Path

    Path(out_path).write_text("\n".join(chunks), encoding="utf-8")
