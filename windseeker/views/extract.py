from __future__ import annotations

import base64
import io
import re
from pathlib import Path
from typing import List

import nbformat

from windseeker.views.render import SvgRenderLimits, png_to_jpg, svg_to_png


def _safe_filename(name: str) -> str:
    name = name.strip().replace("::", "__")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name


def extract_view_images_from_executed_notebook(
    executed_notebook_path: str,
    *,
    out_dir: str = "views",
    write_svg: bool = True,
    write_png: bool = True,
    write_jpg: bool = False,
    png_transparent_background: bool = True,
    png_background_color: str = "#ffffff",
    svg_limits: SvgRenderLimits = SvgRenderLimits(),
) -> List[str]:
    """
    Extract view outputs from an executed notebook and save them to disk.

    For each code cell whose source begins with:
        %view Fully::Qualified::ViewName

    We look for output data in this order:
      - image/svg+xml (SVG XML)
      - image/png (base64)
      - text/plain containing <svg ...> (fallback)
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    nb = nbformat.read(executed_notebook_path, as_version=4)
    written: List[str] = []

    def save_svg_and_renders(view_name: str, svg_text: str) -> None:
        base = _safe_filename(view_name)

        if write_svg:
            svg_file = out_path / f"{base}.svg"
            svg_file.write_text(svg_text, encoding="utf-8")
            written.append(str(svg_file))

        if write_png:
            png_file = out_path / f"{base}.png"
            svg_to_png(
                svg_text,
                str(png_file),
                transparent_background=png_transparent_background,
                background_color=png_background_color,
                limits=svg_limits,
            )
            written.append(str(png_file))

            if write_jpg:
                jpg_file = out_path / f"{base}.jpg"
                png_to_jpg(str(png_file), str(jpg_file))
                written.append(str(jpg_file))

    def save_png_bytes(view_name: str, png_bytes: bytes) -> None:
        base = _safe_filename(view_name)
        png_file = out_path / f"{base}.png"
        png_file.write_bytes(png_bytes)
        written.append(str(png_file))

        if write_jpg:
            from PIL import Image  # type: ignore

            jpg_file = out_path / f"{base}.jpg"
            with Image.open(io.BytesIO(png_bytes)) as im:
                im = im.convert("RGB")
                im.save(jpg_file, quality=95)
            written.append(str(jpg_file))

    for cell_idx, cell in enumerate(nb.cells):
        if cell.get("cell_type") != "code":
            continue

        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        src_stripped = str(src).lstrip()

        if not src_stripped.startswith("%view"):
            continue

        parts = src_stripped.split(None, 1)
        if len(parts) < 2:
            continue
        view_name = parts[1].strip()

        outputs = cell.get("outputs", []) or []

        svg_text = None
        png_bytes = None

        for out in outputs:
            data = out.get("data", {}) or {}

            if "image/svg+xml" in data and data["image/svg+xml"]:
                svg_text = data["image/svg+xml"]
                break

            if "image/png" in data and data["image/png"]:
                b64 = data["image/png"]
                try:
                    png_bytes = base64.b64decode(b64)
                    break
                except Exception:
                    pass

            if "text/plain" in data and data["text/plain"]:
                txt = data["text/plain"]
                if "<svg" in txt:
                    svg_text = txt
                    break

        if svg_text is not None:
            save_svg_and_renders(view_name, svg_text)
        elif png_bytes is not None:
            save_png_bytes(view_name, png_bytes)
        else:
            raise RuntimeError(
                f"View cell {cell_idx} ('{view_name}') produced no extractable SVG/PNG outputs."
            )

    return written
