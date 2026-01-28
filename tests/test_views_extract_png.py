from __future__ import annotations

from pathlib import Path

import nbformat

from windseeker.views.extract import extract_view_images_from_executed_notebook


# 1x1 PNG (transparent) base64
_ONE_BY_ONE_PNG_B64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
    "/w8AAn8B9p3eKQAAAABJRU5ErkJggg=="
)


def test_extract_view_images_from_executed_notebook_png(tmp_path: Path) -> None:
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell(
            source="%view A::Views::v1\n",
            outputs=[
                nbformat.v4.new_output(
                    output_type="display_data",
                    data={"image/png": _ONE_BY_ONE_PNG_B64},
                    metadata={},
                )
            ],
        )
    ]

    executed = tmp_path / "executed.ipynb"
    nbformat.write(nb, str(executed))

    out_dir = tmp_path / "views"
    written = extract_view_images_from_executed_notebook(
        str(executed),
        out_dir=str(out_dir),
        write_svg=False,
        write_png=True,
        write_jpg=False,
    )

    assert len(written) == 1
    assert written[0].endswith(".png")
    assert Path(written[0]).exists()
    assert Path(written[0]).read_bytes().startswith(b"\x89PNG")
