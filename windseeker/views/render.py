from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

# svg size parsing
import re


@dataclass(frozen=True)
class SvgRenderLimits:
    """
    Limits to reduce Cairo 'INVALID_SIZE' errors.
    - max_dim_px: clamp width/height (in px) to this
    - max_pixels: clamp total area (w*h) to this
    """

    max_dim_px: int = 8000
    max_pixels: int = 40_000_000  # 40 MP


_SVG_SIZE_RE = re.compile(
    r"""<svg[^>]*\b(width|height)\s*=\s*["']\s*([0-9.]+)\s*(px)?\s*["']""",
    re.IGNORECASE,
)


def _extract_svg_wh(svg_text: str) -> tuple[Optional[float], Optional[float]]:
    """
    Best-effort extraction of width/height from SVG attributes.
    Returns (w, h) in px if found.
    """
    w = None
    h = None
    for m in _SVG_SIZE_RE.finditer(svg_text):
        key = m.group(1).lower()
        val = float(m.group(2))
        if key == "width":
            w = val
        elif key == "height":
            h = val
    return w, h


def _compute_scale(w: Optional[float], h: Optional[float], limits: SvgRenderLimits) -> float:
    """
    Compute a downscale factor <= 1.0 to satisfy max_dim_px and max_pixels.
    """
    if not w or not h or w <= 0 or h <= 0:
        return 1.0

    s_dim = min(1.0, limits.max_dim_px / max(w, h))
    s_area = min(1.0, math.sqrt(limits.max_pixels / (w * h)))
    return min(s_dim, s_area)


def svg_to_png(
    svg_text: str,
    out_path: str,
    *,
    transparent_background: bool = True,
    background_color: str = "#ffffff",
    limits: SvgRenderLimits = SvgRenderLimits(),
) -> None:
    """
    Render SVG to PNG using cairosvg, with optional background transparency and scaling limits.
    """
    import cairosvg  # type: ignore

    w, h = _extract_svg_wh(svg_text)
    scale = _compute_scale(w, h, limits)

    # cairosvg uses background_color=None for transparency
    bg = None if transparent_background else background_color

    cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        write_to=out_path,
        background_color=bg,
        scale=scale,
    )


def png_to_jpg(png_path: str, jpg_path: str, *, quality: int = 95) -> None:
    from PIL import Image  # type: ignore

    with Image.open(png_path) as im:
        im = im.convert("RGB")
        im.save(jpg_path, quality=quality)
