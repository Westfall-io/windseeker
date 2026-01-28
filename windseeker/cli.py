from __future__ import annotations

from pathlib import Path
from typing import List

import typer

from windseeker.pipeline import order_only, run_pipeline
from windseeker.views.render import SvgRenderLimits

app = typer.Typer(add_completion=True, help="SysML v2 dependency + notebook + view pipeline")


@app.command("run")
def run(
    folder: Path = typer.Option(
        Path("./tests"), "--folder", "-f", exists=True, file_okay=False, dir_okay=True
    ),
    write_graph: bool = typer.Option(True, "--graph/--no-graph", help="Write graph image"),
    graph_png: Path = typer.Option(
        Path("imports.png"), "--graph-png", help="Graph image output path"
    ),
    graph_layout: str = typer.Option(
        "kamada_kawai", "--graph-layout", help="spring|kamada_kawai|shell"
    ),
    sysml_out: Path = typer.Option(
        Path("packages_in_dependency_order.sysml"), "--sysml-out", help="Output .sysml file"
    ),
    notebook_out: Path = typer.Option(
        Path("packages_in_dependency_order.ipynb"), "--notebook-out", help="Output notebook"
    ),
    execute: bool = typer.Option(
        True, "--execute/--no-execute", help="Execute the generated notebook"
    ),
    executed_notebook_out: Path = typer.Option(
        Path("packages_in_dependency_order_executed.ipynb"),
        "--executed-notebook-out",
        help="Executed notebook path",
    ),
    export_views: bool = typer.Option(
        True, "--export-views/--no-export-views", help="Extract rendered views"
    ),
    views_dir: Path = typer.Option(
        Path("views"), "--views-dir", help="Directory to write view images"
    ),
    write_svg: bool = typer.Option(
        True, "--write-svg/--no-write-svg", help="Write raw SVG XML files"
    ),
    write_png: bool = typer.Option(True, "--write-png/--no-write-png", help="Write PNG files"),
    write_jpg: bool = typer.Option(
        False, "--write-jpg/--no-write-jpg", help="Also write JPG files"
    ),
    png_transparent: bool = typer.Option(
        True, "--png-transparent/--png-opaque", help="PNG transparency"
    ),
    png_bg: str = typer.Option("#ffffff", "--png-bg", help="PNG background color if opaque"),
    ignore_missing: List[str] = typer.Option(
        ["<root>"],
        "--ignore-missing",
        help="Imported packages to ignore as missing (useful for standard libs)",
    ),
    strict_missing: bool = typer.Option(
        False,
        "--strict-missing/--allow-missing",
        help="If strict, fail when an import is not found in scanned files",
    ),
    fail_on_view_errors: bool = typer.Option(
        False,
        "--fail-on-view-errors/--allow-view-errors",
        help="If set, a %view rendering error fails the run (default: allow view errors)",
    ),
    svg_max_dim_px: int = typer.Option(
        8000,
        "--svg-max-dim-px",
        help="Max SVG width/height (px) before Windseeker will attempt to scale down/limit",
    ),
    svg_max_pixels: int = typer.Option(
        40_000_000,
        "--svg-max-pixels",
        help="Max SVG pixel count (w*h) before Windseeker will attempt to scale down/limit",
    ),
):
    """
    End-to-end pipeline:
      scan -> graph -> validate -> outputs -> execute -> extract views
    """
    svg_limits = SvgRenderLimits(max_dim_px=svg_max_dim_px, max_pixels=svg_max_pixels)

    result = run_pipeline(
        folder=str(folder),
        write_graph=write_graph,
        graph_png=str(graph_png),
        graph_layout=graph_layout,
        sysml_out=str(sysml_out),
        notebook_out=str(notebook_out),
        execute=execute,
        executed_notebook_out=str(executed_notebook_out),
        export_views=export_views,
        views_dir=str(views_dir),
        write_svg=write_svg,
        write_png=write_png,
        write_jpg=write_jpg,
        png_transparent=png_transparent,
        png_bg=png_bg,
        ignore_missing=set(ignore_missing),
        strict_missing=strict_missing,
        fail_on_view_errors=fail_on_view_errors,
        svg_limits=svg_limits,
    )

    typer.echo(f"Packages (nodes): {len(result.graph.nodes)}")
    typer.echo(f"Imports (edges): {len(result.graph.edges)}")
    typer.echo(f"Views found: {len(result.views)}")

    if result.unresolved_imports:
        typer.echo(
            f"Unresolved imports (ignored/allowed missing): {len(result.unresolved_imports)}"
        )
        for k in sorted(result.unresolved_imports.keys()):
            typer.echo(f"  - {k} (imported by: {', '.join(sorted(result.unresolved_imports[k]))})")

    typer.echo(f"Wrote sysml: {sysml_out}")
    typer.echo(f"Wrote notebook: {notebook_out}")

    if execute:
        typer.echo(f"Executed notebook: {executed_notebook_out}")
        if export_views:
            typer.echo(f"Extracted {len(result.written_view_files)} view file(s) into: {views_dir}")


@app.command("order")
def order(
    folder: Path = typer.Option(
        Path("./tests"), "--folder", "-f", exists=True, file_okay=False, dir_okay=True
    ),
    dependencies_first: bool = typer.Option(True, "--deps-first/--importers-first"),
):
    """Print the topological package order."""
    order_list = order_only(folder=str(folder), dependencies_first=dependencies_first)
    for i, pkg in enumerate(order_list, 1):
        typer.echo(f"{i:4d}. {pkg}")


def main():
    app()


if __name__ == "__main__":
    main()
