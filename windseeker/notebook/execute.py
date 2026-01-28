from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Tuple

import nbformat


ERROR_PATTERNS = [
    re.compile(r"\bERROR\b", re.IGNORECASE),
    re.compile(r"\bException\b", re.IGNORECASE),
    re.compile(r"\bTraceback\b", re.IGNORECASE),
]


def _cell_source_as_str(cell: Dict[str, Any]) -> str:
    src = cell.get("source", "")
    if isinstance(src, list):
        return "".join(str(x) for x in src)
    return str(src)


def _windseeker_meta(cell: Dict[str, Any]) -> Dict[str, Any]:
    meta = cell.get("metadata", {}) or {}
    if not isinstance(meta, dict):
        return {}
    wind = meta.get("windseeker", {}) or {}
    return wind if isinstance(wind, dict) else {}


def _is_view_cell(cell: Dict[str, Any]) -> bool:
    # Preferred: explicit tag set by notebook generator
    wind = _windseeker_meta(cell)
    if wind.get("kind") == "view":
        return True

    # Fallback: source begins with %view
    src = _cell_source_as_str(cell).lstrip()
    return src.startswith("%view")


def _view_name_from_cell(cell: Dict[str, Any]) -> str | None:
    # From metadata (preferred)
    wind = _windseeker_meta(cell)

    # build.py writes "name"; keep "view_name" as backward-compatible fallback
    for key in ("name", "view_name"):
        vn = wind.get(key)
        if isinstance(vn, str) and vn.strip():
            return vn.strip()

    # From source (fallback)
    src = _cell_source_as_str(cell).lstrip()
    if not src.startswith("%view"):
        return None
    parts = src.split(None, 1)
    if len(parts) < 2:
        return None
    return parts[1].strip() or None


def execute_notebook(
    in_path: str,
    out_path: str,
    *,
    timeout_sec: int = 600,
    default_kernel: str = "sysml",
) -> None:
    """
    Execute a notebook and write the executed notebook to out_path.

    Tries nbclient first. If not available, falls back to:
      jupyter nbconvert --execute
    """
    try:
        from nbclient import NotebookClient  # type: ignore

        nb = nbformat.read(in_path, as_version=4)
        kernel_name = nb.get("metadata", {}).get("kernelspec", {}).get("name") or default_kernel

        client = NotebookClient(nb, timeout=timeout_sec, kernel_name=kernel_name)
        client.execute()
        nbformat.write(nb, out_path)
        return
    except ModuleNotFoundError:
        pass
    except Exception as e:
        raise RuntimeError(f"Notebook execution failed via nbclient: {e}") from e

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
        f"--ExecutePreprocessor.timeout={timeout_sec}",
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


def collect_notebook_issues(nb) -> List[Dict[str, Any]]:
    """
    Collect issues from a notebook execution.
    Handles both:
      - output_type == "error"
      - stderr stream text like "ERROR:..."
    Adds:
      - is_view: bool
      - view_name: Optional[str]
    """
    issues: List[Dict[str, Any]] = []

    for idx, cell in enumerate(nb.cells):
        if cell.get("cell_type") != "code":
            continue

        is_view = _is_view_cell(cell)
        view_name = _view_name_from_cell(cell) if is_view else None

        for out in cell.get("outputs", []) or []:
            ot = out.get("output_type")

            if ot == "error":
                issues.append(
                    {
                        "cell_index": idx,
                        "type": "error_output",
                        "ename": out.get("ename", ""),
                        "evalue": out.get("evalue", ""),
                        "traceback": out.get("traceback", []),
                        "is_view": is_view,
                        "view_name": view_name,
                    }
                )
                continue

            if ot == "stream" and out.get("name") == "stderr":
                text = out.get("text", "") or ""
                if any(p.search(text) for p in ERROR_PATTERNS):
                    issues.append(
                        {
                            "cell_index": idx,
                            "type": "stderr",
                            "text": text,
                            "is_view": is_view,
                            "view_name": view_name,
                        }
                    )

    return issues


def split_notebook_issues(
    issues: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns (fatal_issues, view_issues).
    fatal_issues are those NOT associated with a %view cell.
    """
    fatal: List[Dict[str, Any]] = []
    view: List[Dict[str, Any]] = []
    for it in issues:
        if it.get("is_view"):
            view.append(it)
        else:
            fatal.append(it)
    return fatal, view


def format_notebook_issues(issues: List[Dict[str, Any]], max_show: int = 50) -> str:
    lines = [f"Notebook execution produced {len(issues)} issue(s):"]
    for i, issue in enumerate(issues[:max_show], start=1):
        cell = issue.get("cell_index")
        t = issue.get("type")

        prefix = ""
        if issue.get("is_view"):
            vn = issue.get("view_name") or "UNKNOWN_VIEW"
            prefix = f"[VIEW {vn}] "

        if t == "error_output":
            ename = issue.get("ename", "")
            evalue = issue.get("evalue", "")
            lines.append(f"{i}. {prefix}Cell {cell}: {ename}: {evalue}".strip())
        else:
            text = (issue.get("text", "") or "").rstrip()
            preview = text if len(text) <= 400 else text[:400] + "…"
            lines.append(f"{i}. {prefix}Cell {cell} stderr: {preview}")
    if len(issues) > max_show:
        lines.append(f"... and {len(issues) - max_show} more")
    return "\n".join(lines)


def execute_and_fail_on_notebook_errors(
    notebook_path: str,
    *,
    executed_out_path: str = "packages_in_dependency_order_executed.ipynb",
    timeout_sec: int = 600,
    fail_on_view_errors: bool = False,
) -> None:
    """
    Execute the notebook and:
      - Fail if there are errors in non-view cells (package/model execution)
      - By default, do NOT fail if only %view cells error (warn instead)
      - If fail_on_view_errors=True, view errors become fatal
    """
    execute_notebook(notebook_path, executed_out_path, timeout_sec=timeout_sec)

    nb = nbformat.read(executed_out_path, as_version=4)
    issues = collect_notebook_issues(nb)

    fatal, view = split_notebook_issues(issues)

    if fatal:
        raise RuntimeError(format_notebook_issues(fatal))

    if view and fail_on_view_errors:
        raise RuntimeError(format_notebook_issues(view))

    if view and not fail_on_view_errors:
        print(
            "WARNING: One or more view cells failed to render. "
            "Continuing because fail_on_view_errors=False.\n" + format_notebook_issues(view)
        )

    print(f"Notebook executed: {executed_out_path}")
