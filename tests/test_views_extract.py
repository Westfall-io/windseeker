from __future__ import annotations

from pathlib import Path

import nbformat
import pytest

from windseeker.views.extract import extract_view_images_from_executed_notebook


def _make_nb_with_view_svg(svg_text: str) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell(
            source="%view A::B::V\n",
            outputs=[
                nbformat.v4.new_output(
                    output_type="execute_result",
                    data={"image/svg+xml": svg_text},
                    metadata={},
                    execution_count=1,
                )
            ],
        )
    ]
    return nb


def _make_nb_with_view_png(png_b64: str) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell(
            source="%view A::B::V\n",
            outputs=[
                nbformat.v4.new_output(
                    output_type="execute_result",
                    data={"image/png": png_b64},
                    metadata={},
                    execution_count=1,
                )
            ],
        )
    ]
    return nb


def test_extract_writes_svg_only(tmp_path: Path) -> None:
    svg = "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>"
    nb = _make_nb_with_view_svg(svg)

    nb_path = tmp_path / "executed.ipynb"
    nbformat.write(nb, str(nb_path))

    out_dir = tmp_path / "views"
    written = extract_view_images_from_executed_notebook(
        str(nb_path),
        out_dir=str(out_dir),
        write_svg=True,
        write_png=False,  # avoid cairosvg requirement
        write_jpg=False,
    )

    assert any(p.endswith(".svg") for p in written)
    svg_files = list(out_dir.glob("*.svg"))
    assert len(svg_files) == 1
    assert svg_files[0].read_text(encoding="utf-8").startswith("<svg")


def test_extract_writes_png_bytes(tmp_path: Path) -> None:
    # 1x1 transparent PNG
    png_b64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMB"
        "/p2q0mQAAAAASUVORK5CYII="
    )
    nb = _make_nb_with_view_png(png_b64)

    nb_path = tmp_path / "executed.ipynb"
    nbformat.write(nb, str(nb_path))

    out_dir = tmp_path / "views"
    written = extract_view_images_from_executed_notebook(
        str(nb_path),
        out_dir=str(out_dir),
        write_svg=False,
        write_png=True,
        write_jpg=False,
    )

    assert any(p.endswith(".png") for p in written)
    png_files = list(out_dir.glob("*.png"))
    assert len(png_files) == 1
    assert png_files[0].stat().st_size > 0


def test_extract_raises_if_view_has_no_extractable_output(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_code_cell(source="%view A::B::V\n", outputs=[])]
    nb_path = tmp_path / "executed.ipynb"
    nbformat.write(nb, str(nb_path))

    with pytest.raises(RuntimeError):
        extract_view_images_from_executed_notebook(
            str(nb_path),
            out_dir=str(tmp_path / "views"),
            write_svg=True,
            write_png=False,
        )
