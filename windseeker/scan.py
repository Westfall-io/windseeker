from __future__ import annotations

from pathlib import Path
from typing import Dict

from windseeker.parsing import strip_line_comments, extract_top_level_packages_with_text


def scan_folder(root_folder: str) -> Dict[str, str]:
    """
    Recursively scan for .sysml files and return a map:
      top_level_package_name -> full package declaration text
    """
    root = Path(root_folder)
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {root_folder}")

    package_text: Dict[str, str] = {}

    for path in root.rglob("*.sysml"):
        if not path.is_file():
            continue

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"Warning: could not read {path}: {e}")
            continue

        clean_text = strip_line_comments(text)

        for pkg_name, pkg_full_text in extract_top_level_packages_with_text(clean_text):
            # keep first if duplicates occur
            package_text.setdefault(pkg_name, pkg_full_text)

    return package_text
