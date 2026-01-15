from __future__ import annotations

from pathlib import Path
import typer

# Import the functions you already have in main.py
# (Adjust imports if your file/module names differ)
from main import (
    scan_folder,
    build_import_graph_from_package_text,
    assert_acyclic_or_raise,
    assert_no_unresolved_imports_or_raise,
    visualize_graph_to_file,
    topological_packages,
    output_package_text_in_dependency_order,
    write_notebook_in_dependency_order,
    extract_view_images_from_executed_notebook,
    execute_and_fail_on_notebook_errors,  # assuming you added this earlier
    collect_all_views,  # if you have it, else skip view cells
)

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
        True, "--export-views/--no-export-views", help="Extract rendered views as images"
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
        True, "--png-transparent/--png-opaque", help="PNG background transparency"
    ),
    png_bg: str = typer.Option(
        "#ffffff", "--png-bg", help="PNG background color if opaque (e.g. #ffffff)"
    ),
    ignore_missing: list[str] = typer.Option(
        ["<root>"], "--ignore-missing", help="Imported packages to ignore as missing"
    ),
):
    """
    End-to-end pipeline:
      scan -> graph -> validate -> outputs -> execute -> extract views
    """
    package_text = scan_folder(str(folder))
    G = build_import_graph_from_package_text(package_text)

    typer.echo(f"Packages (nodes): {len(G.nodes)}")
    typer.echo(f"Imports (edges): {len(G.edges)}")

    # Fail fast
    assert_acyclic_or_raise(G)
    assert_no_unresolved_imports_or_raise(G, ignore=set(ignore_missing))
    # Optional graph
    if write_graph:
        visualize_graph_to_file(G, str(graph_png), layout=graph_layout)
        typer.echo(f"Wrote graph: {graph_png}")

    # Write dependency-ordered sysml
    output_package_text_in_dependency_order(G, package_text, out_path=str(sysml_out))
    typer.echo(f"Wrote sysml: {sysml_out}")

    # Views (optional, if you have this function)
    try:
        views = collect_all_views(package_text)
    except Exception:
        views = []

    # Write notebook
    write_notebook_in_dependency_order(G, package_text, views=views, out_path=str(notebook_out))
    typer.echo(f"Wrote notebook: {notebook_out}")

    # Execute notebook
    if execute:
        execute_and_fail_on_notebook_errors(
            str(notebook_out), executed_out_path=str(executed_notebook_out)
        )
        typer.echo(f"Executed notebook: {executed_notebook_out}")

        # Extract views from executed notebook
        if export_views:
            written = extract_view_images_from_executed_notebook(
                str(executed_notebook_out),
                out_dir=str(views_dir),
                write_svg=write_svg,
                write_png=write_png,
                write_jpg=write_jpg,
                png_transparent_background=png_transparent,
                png_background_color=png_bg,
            )
            typer.echo(f"Extracted {len(written)} view files into: {views_dir}")
    else:
        typer.echo("Notebook execution skipped (--no-execute).")


@app.command("order")
def order(
    folder: Path = typer.Option(
        Path("./tests"), "--folder", "-f", exists=True, file_okay=False, dir_okay=True
    ),
    dependencies_first: bool = typer.Option(True, "--deps-first/--importers-first"),
):
    """Print the topological package order."""
    package_text = scan_folder(str(folder))
    G = build_import_graph_from_package_text(package_text)
    assert_acyclic_or_raise(G)
    order_list = topological_packages(G, dependencies_first=dependencies_first)
    for i, pkg in enumerate(order_list, 1):
        typer.echo(f"{i:4d}. {pkg}")


def main():
    app()


if __name__ == "__main__":
    main()
