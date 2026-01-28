from __future__ import annotations

from pathlib import Path

import pytest

from windseeker.scan import scan_folder


def test_scan_folder_finds_sysml_files_recursively(tmp_path: Path) -> None:
    (tmp_path / "root.sysml").write_text(
        """
        // comment
        package A { private import B::*; }
        """,
        encoding="utf-8",
    )
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "nested.sysml").write_text(
        """
        package B;
        """,
        encoding="utf-8",
    )
    (tmp_path / "ignore.txt").write_text("package C;", encoding="utf-8")

    result = scan_folder(str(tmp_path))

    assert "A" in result
    assert "B" in result
    assert "C" not in result  # ignore non-.sysml files


def test_scan_folder_raises_if_folder_missing(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    with pytest.raises(FileNotFoundError):
        scan_folder(str(missing))


def test_scan_folder_raises_for_missing_dir(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    with pytest.raises(FileNotFoundError):
        scan_folder(str(missing))


def test_scan_folder_finds_sysml_and_extracts_packages(tmp_path: Path) -> None:
    root = tmp_path / "models"
    root.mkdir()

    (root / "a.sysml").write_text(
        """
        // comment line should be stripped
        package A {
          private import B::*;
        }
        """,
        encoding="utf-8",
    )
    (root / "b.sysml").write_text("package B;\n", encoding="utf-8")

    package_text = scan_folder(str(root))
    assert "A" in package_text
    assert "B" in package_text
    assert "package A" in package_text["A"]
    assert "package B" in package_text["B"]
