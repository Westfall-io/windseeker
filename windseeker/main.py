from __future__ import annotations

import re
import uuid
import json
from pathlib import Path
from typing import Dict, List
import networkx as nx
import matplotlib.pyplot as plt
import shutil
import subprocess
import nbformat
import base64
import io


class ImportCycleError(RuntimeError):
    """Raised when the import graph contains one or more cycles."""


class MissingPackageError(RuntimeError):
    """Raised when an import references a package we did not find/parse."""


# Matches lines that are NOT "line-commented out" at the start (allowing leading whitespace)
# and contain a whole-word 'import' or 'package', capturing the following token.
#
# Capture rules for the token after keyword:
#   1) 'single quoted string'   -> may contain spaces
#   2) bare token (identifier-like) -> stops at whitespace or delimiters
#
# Note: We only exclude lines that *start* with '//' (after optional whitespace),
# as requested. Inline comments after code are not treated as "commented out".
IMPORT_RE = re.compile(
    r"""
    ^(?!\s*//)                 # line must NOT start with optional whitespace then //
    .*?                        # allow anything before 'import' (e.g., "package A {")
    \bimport\b                 # whole word 'import' (won't match 'important')
    \s+                        # at least one space
    (                          # capture the target
        '(?:[^'\\]|\\.)*'      # single-quoted string
        |
        [A-Za-z_][\w.:/-]*     # bare token (e.g. B::)
    )
    """,
    re.VERBOSE,
)

PACKAGE_START_RE = re.compile(
    r"""
    (?m)^(?!\s*//)\s*          # not a line comment
    (?:\w+\s+)*                # optional modifiers like 'library'
    \bpackage\b\s+
    (                          # capture package name
        '(?:[^'\\]|\\.)*'
        |
        [A-Za-z_][\w.:/-]*
    )
    """,
    re.VERBOSE,
)

VIEW_START_RE = re.compile(
    r"""
    ^(?!\s*//)\s*              # not a line comment
    \bview\b\s+
    (                          # capture view name
        '(?:[^'\\]|\\.)*'
        |
        [A-Za-z_][\w.:/-]*
    )
    \s*\{                      # views are blocks
    """,
    re.VERBOSE,
)

INNER_PACKAGE_OPEN_RE = re.compile(
    r"""
    ^(?!\s*//)\s*
    (?:\w+\s+)*                # optional modifiers
    \bpackage\b\s+
    (                          # capture package name
        '(?:[^'\\]|\\.)*'
        |
        [A-Za-z_][\w.:/-]*
    )
    \s*\{                      # only track nested packages that open a block
    """,
    re.VERBOSE,
)


ERROR_PATTERNS = [
    re.compile(r"\bERROR\b", re.IGNORECASE),
    re.compile(r"\bException\b", re.IGNORECASE),
    re.compile(r"\bTraceback\b", re.IGNORECASE),
]


def _safe_filename(name: str) -> str:
    """
    Make a filesystem-safe name while keeping it readable.
    """
    name = name.strip()
    name = name.replace("::", "__")
    # replace anything sketchy with underscore
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name


def extract_view_images_from_executed_notebook(
    executed_notebook_path: str,
    *,
    out_dir: str = "views",
    write_svg: bool = True,
    write_png: bool = True,
    write_jpg: bool = False,
) -> List[str]:
    """
    Extract view outputs from an executed notebook and save them to disk.

    For each cell whose source begins with:
        %view Fully::Qualified::ViewName

    We look for output data in this order:
      - image/svg+xml (XML SVG)  -> save .svg + render to .png/.jpg
      - image/png (base64)       -> save .png (+ optional jpg)
      - text/plain containing <svg ...> -> treat as SVG as a fallback

    Returns a list of output file paths written.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    nb = nbformat.read(executed_notebook_path, as_version=4)

    written: List[str] = []

    # Optional converters
    try:
        _has_cairosvg = True
    except Exception:
        _has_cairosvg = False

    try:
        _has_pil = True
    except Exception:
        _has_pil = False

    def save_svg_and_renders(view_name: str, svg_text: str) -> None:
        base = _safe_filename(view_name)

        if write_svg:
            svg_file = out_path / f"{base}.svg"
            svg_file.write_text(svg_text, encoding="utf-8")
            written.append(str(svg_file))

        if write_png:
            if not _has_cairosvg:
                raise RuntimeError(
                    "cairosvg is required to render SVG to PNG, but it is not installed."
                )
            png_file = out_path / f"{base}.png"
            # cairosvg accepts bytestring
            import cairosvg  # type: ignore

            cairosvg.svg2png(
                bytestring=svg_text.encode("utf-8"),
                write_to=str(png_file),
                background_color="#ffffff",
            )
            written.append(str(png_file))

            if write_jpg:
                if not _has_pil:
                    raise RuntimeError(
                        "Pillow (PIL) is required to convert PNG to JPG, but it is not installed."
                    )
                from PIL import Image  # type: ignore

                jpg_file = out_path / f"{base}.jpg"
                with Image.open(png_file) as im:
                    im = im.convert("RGB")
                    im.save(jpg_file, quality=95)
                written.append(str(jpg_file))

    def save_png_bytes(view_name: str, png_bytes: bytes) -> None:
        base = _safe_filename(view_name)
        png_file = out_path / f"{base}.png"
        png_file.write_bytes(png_bytes)
        written.append(str(png_file))

        if write_jpg:
            if not _has_pil:
                raise RuntimeError(
                    "Pillow (PIL) is required to convert PNG to JPG, but it is not installed."
                )
            from PIL import Image  # type: ignore

            jpg_file = out_path / f"{base}.jpg"
            with Image.open(io.BytesIO(png_bytes)) as im:
                im = im.convert("RGB")
                im.save(jpg_file, quality=95)
            written.append(str(jpg_file))

    for cell_idx, cell in enumerate(nb.cells):
        if cell.get("cell_type") != "code":
            continue

        src = (
            "".join(cell.get("source", ""))
            if isinstance(cell.get("source", ""), list)
            else cell.get("source", "")
        )
        src_stripped = src.lstrip()

        if not src_stripped.startswith("%view"):
            continue

        # Parse view name
        # e.g. "%view Flashlight_StarterModel::Views1::flashlightPartsTree"
        parts = src_stripped.split(None, 1)
        if len(parts) < 2:
            continue
        view_name = parts[1].strip()

        # Scan outputs for svg/png
        outputs = cell.get("outputs", []) or []

        svg_text = None
        png_bytes = None

        for out in outputs:
            data = out.get("data", {}) or {}

            # Best case: SVG is directly available
            if "image/svg+xml" in data and data["image/svg+xml"]:
                svg_text = data["image/svg+xml"]
                break

            # PNG might be present
            if "image/png" in data and data["image/png"]:
                b64 = data["image/png"]
                try:
                    png_bytes = base64.b64decode(b64)
                    break
                except Exception:
                    pass

            # Fallback: sometimes SVG is inside text/plain
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


def _top_level_of_qualified_name(name: str) -> str:
    """
    If name is 'A::B::C', return 'A'. Otherwise return name.
    """
    return name.split("::", 1)[0]


def _brace_depth_prefix(text: str) -> List[int]:
    """
    Return prefix brace depth at each character index.
    depth[i] is the brace depth *before* processing text[i].
    Assumes comments have already been stripped.
    """
    depth = [0] * (len(text) + 1)
    d = 0
    for i, ch in enumerate(text):
        depth[i] = d
        if ch == "{":
            d += 1
        elif ch == "}":
            d = max(0, d - 1)
    depth[len(text)] = d
    return depth


def collect_views_from_package_text(package_name: str, package_full_text: str) -> List[str]:
    """
    Collect fully-qualified view names from within a *top-level* package text block.

    Example result:
      Flashlight_StarterModel::Views1::flashlightPartsTree
    """
    # Strip inline // comments for consistent parsing
    clean_lines = [line.split("//", 1)[0] for line in package_full_text.splitlines()]

    views: List[str] = []

    depth = 0
    stack: List[tuple[str, int]] = []  # (nested_package_name, enter_depth_after_open_brace)

    for raw_line in clean_lines:
        line = raw_line

        # Pop stack if we've exited nested package blocks
        # (done at top of loop in case previous line closed braces)
        while stack and depth < stack[-1][1]:
            stack.pop()

        # Detect nested package openings: package X {
        m_pkg = INNER_PACKAGE_OPEN_RE.search(line)
        if m_pkg:
            inner = _normalize_qualified_name(_strip_quotes_if_needed(m_pkg.group(1)))

            # Skip the outermost package declaration if it appears inside its own text
            # (common: the first line is "package Flashlight_StarterModel {")
            if inner != package_name:
                # This "package {" increases depth by 1 on this line
                stack.append((inner, depth + 1))

        # Detect view openings: view Y {
        m_view = VIEW_START_RE.search(line)
        if m_view:
            view_name = _normalize_qualified_name(_strip_quotes_if_needed(m_view.group(1)))
            prefix = [package_name] + [p for p, _ in stack]
            views.append("::".join(prefix + [view_name]))

        # Update depth at end of processing line
        depth += line.count("{") - line.count("}")

    return views


def collect_all_views(package_text: Dict[str, str]) -> List[str]:
    """
    Collect all fully-qualified view names across all top-level packages.
    """
    all_views: List[str] = []
    for pkg, txt in package_text.items():
        all_views.extend(collect_views_from_package_text(pkg, txt))
    # de-dup while preserving order
    seen = set()
    ordered = []
    for v in all_views:
        if v not in seen:
            seen.add(v)
            ordered.append(v)
    return ordered


def collect_notebook_issues(nb) -> list[dict]:
    """
    Collect issues from a notebook execution.
    Handles both:
      - output_type == "error"
      - stderr stream text like "ERROR:..."
    Returns list of dicts with cell index + message.
    """
    issues: list[dict] = []

    for idx, cell in enumerate(nb.cells):
        if cell.get("cell_type") != "code":
            continue

        for out in cell.get("outputs", []) or []:
            ot = out.get("output_type")

            # Standard Jupyter errors
            if ot == "error":
                issues.append(
                    {
                        "cell_index": idx,
                        "type": "error_output",
                        "ename": out.get("ename", ""),
                        "evalue": out.get("evalue", ""),
                        "traceback": out.get("traceback", []),
                    }
                )
                continue

            # SysML kernel errors often appear on stderr as streams
            if ot == "stream" and out.get("name") == "stderr":
                text = out.get("text", "") or ""
                if any(p.search(text) for p in ERROR_PATTERNS):
                    issues.append(
                        {
                            "cell_index": idx,
                            "type": "stderr",
                            "text": text,
                        }
                    )

    return issues


def format_notebook_issues(issues: list[dict], max_show: int = 50) -> str:
    lines = [f"Notebook execution produced {len(issues)} issue(s):"]
    for i, issue in enumerate(issues[:max_show], start=1):
        cell = issue.get("cell_index")
        t = issue.get("type")
        if t == "error_output":
            ename = issue.get("ename", "")
            evalue = issue.get("evalue", "")
            lines.append(f"{i}. Cell {cell}: {ename}: {evalue}".strip())
        else:
            text = (issue.get("text", "") or "").rstrip()
            # keep it readable
            preview = text if len(text) <= 400 else text[:400] + "…"
            lines.append(f"{i}. Cell {cell} stderr: {preview}")
    if len(issues) > max_show:
        lines.append(f"... and {len(issues) - max_show} more")
    return "\n".join(lines)


def execute_notebook(
    in_path: str,
    out_path: str,
    *,
    timeout_sec: int = 600,
) -> None:
    """
    Execute a notebook and write the executed notebook to out_path.

    Tries nbclient first. If not available, falls back to:
      jupyter nbconvert --execute

    NOTE: This assumes the SysML kernel is installed and available
    in the environment where this script runs.
    """
    # --- Try nbclient (best, no subprocess) ---
    try:
        from nbclient import NotebookClient  # type: ignore

        nb = nbformat.read(in_path, as_version=4)
        kernel_name = (nb.get("metadata", {}).get("kernelspec", {}).get("name")) or "sysml"

        client = NotebookClient(nb, timeout=timeout_sec, kernel_name=kernel_name)
        client.execute()
        nbformat.write(nb, out_path)
        return
    except ModuleNotFoundError:
        pass  # fall back to nbconvert
    except Exception as e:
        # If nbclient is installed but execution fails, keep the error visible
        raise RuntimeError(f"Notebook execution failed via nbclient: {e}") from e

    # --- Fallback: jupyter nbconvert --execute ---
    if shutil.which("jupyter") is None:
        raise RuntimeError(
            "Cannot execute notebook: nbclient not installed and 'jupyter' command not found.\n"
            "Install one of:\n"
            "  pip install nbclient\n"
            "or ensure Jupyter is installed and 'jupyter' is on PATH."
        )

    cmd = [
        "jupyter",
        "nbconvert",
        "--to",
        "notebook",
        "--execute",
        "--ExecutePreprocessor.timeout={}".format(timeout_sec),
        "--output",
        str(Path(out_path).name),
        "--output-dir",
        str(Path(out_path).parent),
        str(in_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            "Notebook execution failed via nbconvert.\n"
            f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
        )


def execute_and_fail_on_notebook_errors(
    notebook_path: str,
    executed_out_path: str = "packages_in_dependency_order_executed.ipynb",
) -> None:
    execute_notebook(notebook_path, executed_out_path)

    nb = nbformat.read(executed_out_path, as_version=4)
    issues = collect_notebook_issues(nb)

    if issues:
        raise RuntimeError(format_notebook_issues(issues))

    print(f"Notebook executed cleanly: {executed_out_path}")


def write_notebook_in_dependency_order(
    G: nx.DiGraph,
    package_text: Dict[str, str],
    *,
    views: List[str] | None = None,
    out_path: str = "packages_in_dependency_order.ipynb",
) -> None:
    """
    Write a Jupyter notebook where the entire notebook uses the SysML kernel.
    Each package becomes one code cell, ordered by dependency (dependencies first).
    """
    order = topological_packages(G, dependencies_first=True)
    order = [p for p in order if p in package_text]  # only packages we have text for

    cells = []
    for pkg in order:
        body = package_text[pkg].rstrip() + "\n"
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "id": uuid.uuid4().hex,
                "metadata": {},  # matches the single-kernel example style
                "outputs": [],
                "source": body.splitlines(True),  # list[str] with newlines preserved
            }
        )

    # After package cells, append view rendering cells
    views = views or []
    for v in views:
        # Title cell (so the notebook visually labels each view)
        title = f"# {v}After\n"
        cells.append(
            {
                "cell_type": "markdown",
                "execution_count": None,
                "id": uuid.uuid4().hex,
                "metadata": {},
                "outputs": [],
                "source": [title],
            }
        )

        # SysML magic cell to generate the view image
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "id": uuid.uuid4().hex,
                "metadata": {},
                "outputs": [],
                "source": [f"%view {v}\n"],
            }
        )

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "SysML", "language": "sysml", "name": "sysml"},
            "language_info": {
                # Mirrors the typical SysML notebook metadata (as in your example)
                "codemirror_mode": "sysml",
                "file_extension": ".sysml",
                "mimetype": "text/x-sysml",
                "name": "SysML",
                "pygments_lexer": "java",
                "version": "1.0.0",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    Path(out_path).write_text(json.dumps(nb, indent=2), encoding="utf-8")


def assert_no_unresolved_imports_or_raise(G: nx.DiGraph, *, ignore: set[str] | None = None) -> None:
    ignore = ignore or set()
    unresolved: dict[str, set[str]] = G.graph.get("unresolved_imports", {}) or {}

    # Apply ignore list
    filtered = {k: v for k, v in unresolved.items() if k not in ignore}

    if not filtered:
        return

    lines = ["Missing imported package definitions detected:"]
    for imported_pkg in sorted(filtered.keys()):
        importers = ", ".join(sorted(filtered[imported_pkg]))
        lines.append(f"  - {imported_pkg}  (imported by: {importers})")

    # raise MissingPackageError("\n".join(lines))


def _find_matching_brace(text: str, open_brace_index: int) -> int:
    """Return index of matching '}' for the '{' at open_brace_index, or -1 if not found."""
    depth = 0
    i = open_brace_index
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def extract_packages_with_text(text: str) -> list[tuple[str, str]]:
    """
    Extract ONLY top-level packages and store their full declaration text.
    Nested packages are left inside the parent's captured text and are NOT
    returned as separate entries.
    """
    results: list[tuple[str, str]] = []

    depths = _brace_depth_prefix(text)

    for m in PACKAGE_START_RE.finditer(text):
        # Only accept packages that start at top-level brace depth
        if depths[m.start()] != 0:
            continue

        raw_name = m.group(1)
        name = _normalize_qualified_name(_strip_quotes_if_needed(raw_name))

        # Find token after name: ';' or '{'
        j = m.end()
        n = len(text)
        while j < n and text[j].isspace():
            j += 1
        if j >= n:
            continue

        if text[j] == ";":
            end = j + 1
            while end < n and text[end] != "\n":
                end += 1
            results.append((name, text[m.start() : end]))

        elif text[j] == "{":
            close = _find_matching_brace(text, j)
            if close == -1:
                results.append((name, text[m.start() :]))
                continue
            end = close + 1

            # include trailing ';' if present
            k = end
            while k < n and text[k].isspace():
                k += 1
            if k < n and text[k] == ";":
                end = k + 1

            results.append((name, text[m.start() : end]))

        else:
            end = j
            while end < n and text[end] != "\n":
                end += 1
            results.append((name, text[m.start() : end]))

    return results


def topological_packages(G: nx.DiGraph, *, dependencies_first: bool = True) -> List[str]:
    """
    Return a topological sort of package nodes.

    With your edge direction (package -> imported_package):
      - dependencies_first=True: returns an order where imported packages appear BEFORE importers
        (good for build/load/compile ordering)
      - dependencies_first=False: returns importers before their dependencies
    """
    assert_acyclic_or_raise(G)

    H = G.reverse(copy=False) if dependencies_first else G
    return list(nx.topological_sort(H))


def output_package_text_in_dependency_order(
    G: nx.DiGraph, package_text: Dict[str, str], *, out_path: str | None = None
) -> None:
    """
    Print/write each package's full text in dependency order (dependencies first).
    Only outputs packages that we actually have text for.
    """
    order = topological_packages(G, dependencies_first=True)

    # Filter to only packages we have definitions for
    order = [p for p in order if p in package_text]

    chunks: List[str] = []
    for pkg in order:
        chunks.append(f"// ===== PACKAGE: {pkg} =====")
        chunks.append(package_text[pkg].rstrip())
        chunks.append("")  # blank line between packages

    output = "\n".join(chunks)

    if out_path:
        Path(out_path).write_text(output, encoding="utf-8")
    else:
        print(output)


def build_import_graph_from_package_text(package_text: Dict[str, str]) -> nx.DiGraph:
    G = nx.DiGraph()
    unresolved: dict[str, set[str]] = {}

    known_packages = set(package_text.keys())  # top-level only

    for pkg_name, pkg_full_text in package_text.items():
        G.add_node(pkg_name)

        for raw_line in pkg_full_text.splitlines():
            line = raw_line.split("//", 1)[0]

            m_imp = IMPORT_RE.search(line)
            if not m_imp:
                continue

            imp_full = _normalize_qualified_name(_strip_quotes_if_needed(m_imp.group(1)))
            imp_top = _top_level_of_qualified_name(imp_full)

            # ignore self-imports at top-level
            if imp_top == pkg_name:
                continue

            G.add_node(imp_top)
            G.add_edge(pkg_name, imp_top)

            if imp_top not in known_packages:
                unresolved.setdefault(imp_top, set()).add(pkg_name)

    G.graph["unresolved_imports"] = unresolved
    return G


def _normalize_qualified_name(name: str) -> str:
    """
    Normalize captured names:
    - strip surrounding single quotes already handled elsewhere
    - remove a trailing '::' (common in patterns like A::*)
    """
    return re.sub(r"::\s*$", "", name)


def _strip_quotes_if_needed(token: str) -> str:
    """Remove surrounding single quotes if token is a single-quoted string; keep content as-is."""
    if len(token) >= 2 and token[0] == "'" and token[-1] == "'":
        return token[1:-1]
    return token


def scan_folder(root_folder="./tests") -> Dict[str, str]:
    """
    Recursively scan for .sysml files and return a map:
      package_name -> full package declaration text
    """
    root = Path(root_folder)
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root}")

    package_text: Dict[str, str] = {}

    for path in root.rglob("*.sysml"):
        if not path.is_file():
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"Warning: could not read {path}: {e}")
            continue

        clean_text = "\n".join(line.split("//", 1)[0] for line in text.splitlines())
        for pkg_name, pkg_full_text in extract_packages_with_text(clean_text):
            package_text.setdefault(pkg_name, pkg_full_text)

    return package_text


def find_cycles(G):
    return list(nx.simple_cycles(G))


def _format_cycles(cycles: list[list[str]], max_show: int = 25) -> str:
    """
    Pretty-print cycles.
    Each cycle from networkx.simple_cycles is like [A, B, C] meaning A->B->C->A.
    """
    lines = []
    for i, cyc in enumerate(cycles[:max_show], start=1):
        if not cyc:
            continue
        # Close the loop for display
        loop = " -> ".join(cyc + [cyc[0]])
        lines.append(f"{i}. {loop}")
    if len(cycles) > max_show:
        lines.append(f"... and {len(cycles) - max_show} more")
    return "\n".join(lines)


def assert_acyclic_or_raise(G: nx.DiGraph) -> None:
    """
    Ensure there are no cycles. If cycles exist, raise ImportCycleError.
    Uses a fast check first, then enumerates cycles for diagnostics.
    """
    if nx.is_directed_acyclic_graph(G):
        return

    cycles = list(nx.simple_cycles(G))
    msg = "Critical import recursion loop(s) detected:\n" + _format_cycles(cycles)
    raise ImportCycleError(msg)


def visualize_graph_to_file(
    G: nx.DiGraph,
    out_path: str = "sysml_import_graph.png",
    *,
    title: str | None = "SysML Package Import Graph",
    figsize: tuple[float, float] = (16, 10),
    dpi: int = 200,
    layout: str = "spring",  # "spring" | "kamada_kawai" | "shell"
    seed: int = 42,
) -> None:
    """
    Write a NetworkX visualization to an image file.
    Refuses to write if there are cycles (critical recursion loop).
    """
    assert_acyclic_or_raise(G)

    if G.number_of_nodes() == 0:
        raise ValueError("Graph is empty: no packages/imports found.")

    # Pick a layout
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

    # Draw nodes/edges (no explicit colors set)
    nx.draw_networkx_nodes(G, pos, node_size=900)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=15, width=1.2)
    nx.draw_networkx_labels(G, pos, font_size=8)

    plt.axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=dpi)
    plt.close()


def main(folder="./tests"):
    package_text = scan_folder(folder)
    G = build_import_graph_from_package_text(package_text)

    print(f"Packages (nodes): {len(G.nodes)}")
    print(f"Imports (edges): {len(G.edges)}")

    views = collect_all_views(package_text)
    print(f"Views found: {len(views)}")
    for v in views:
        print("  view:", v)
    print("*" * 20)

    # Fail fast on cycles
    assert_acyclic_or_raise(G)
    assert_no_unresolved_imports_or_raise(G, ignore={"<root>"})

    # Optional: graph image
    visualize_graph_to_file(G, "imports.png", layout="kamada_kawai")
    print("Wrote graph to imports.png (no cycles detected).")
    print("*" * 20)

    # Topological order list
    order = topological_packages(G, dependencies_first=True)
    print("Topological order (dependencies first):")
    for i, pkg in enumerate(order, 1):
        print(f"{i:4d}. {pkg}")
    print("*" * 20)

    # Output full package text in dependency order
    output_package_text_in_dependency_order(
        G, package_text, out_path="packages_in_dependency_order.sysml"
    )
    print("Wrote packages_in_dependency_order.sysml")
    print("*" * 20)

    # Output notebook with one cell per package in dependency order
    write_notebook_in_dependency_order(
        G, package_text, views=views, out_path="packages_in_dependency_order.ipynb"
    )
    print("Wrote packages_in_dependency_order.ipynb")
    execute_and_fail_on_notebook_errors(
        "packages_in_dependency_order.ipynb",
        executed_out_path="packages_in_dependency_order_executed.ipynb",
    )
    print("*" * 20)

    written = extract_view_images_from_executed_notebook(
        "packages_in_dependency_order_executed.ipynb",
        out_dir="views",
        write_svg=False,
        write_png=True,
        write_jpg=False,  # flip to True if you want jpg too
    )
    print(f"Extracted {len(written)} view image file(s) into ./views")

    return G


if __name__ == "__main__":
    G = main()
