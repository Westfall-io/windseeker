from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List

import networkx as nx

from windseeker.graph import topological_packages


def write_notebook_in_dependency_order(
    G: nx.DiGraph,
    package_text: Dict[str, str],
    *,
    views: List[str] | None = None,
    out_path: str = "packages_in_dependency_order.ipynb",
) -> None:
    """
    Write a Jupyter notebook where the entire notebook uses the SysML kernel.
    Each top-level package becomes one code cell, ordered by dependency (deps first).

    We also tag cells with metadata so later steps can distinguish between:
      - package compilation cells
      - view rendering cells (%view ...)
    """
    order = topological_packages(G, dependencies_first=True)
    order = [p for p in order if p in package_text]  # only packages we have text for

    cells: List[dict] = []

    # ---- Package cells (code) ----
    for pkg in order:
        body = package_text[pkg].rstrip() + "\n"
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "id": uuid.uuid4().hex,
                "metadata": {
                    "windseeker": {
                        "kind": "package",
                        "name": pkg,
                    }
                },
                "outputs": [],
                "source": body.splitlines(True),
            }
        )

    # ---- View cells (markdown + code) ----
    views = views or []
    for v in views:
        # Title cell
        cells.append(
            {
                "cell_type": "markdown",
                "execution_count": None,
                "id": uuid.uuid4().hex,
                "metadata": {
                    "windseeker": {
                        "kind": "view_title",
                        "name": v,
                    }
                },
                "outputs": [],
                "source": [f"# {v}\n"],
            }
        )

        # SysML magic cell
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "id": uuid.uuid4().hex,
                "metadata": {
                    "windseeker": {
                        "kind": "view",
                        "name": v,
                    }
                },
                "outputs": [],
                "source": [f"%view {v}\n"],
            }
        )

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "SysML", "language": "sysml", "name": "sysml"},
            "language_info": {
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
