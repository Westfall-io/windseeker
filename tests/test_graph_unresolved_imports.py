from __future__ import annotations

import pytest

from windseeker.graph import (
    assert_no_unresolved_imports_or_raise,
    build_import_graph_from_package_text,
    get_unresolved_imports,
)


def test_unresolved_imports_recorded_and_returned() -> None:
    package_text = {
        "A": "package A {\n  private import B::*;\n  private import StdLib::*;\n}\n",
        "B": "package B;\n",
    }

    G = build_import_graph_from_package_text(package_text)

    unresolved = get_unresolved_imports(G, ignore={"<root>"})
    assert "StdLib" in unresolved
    assert unresolved["StdLib"] == {"A"}

    # With strict=False, should not raise by default
    assert_no_unresolved_imports_or_raise(G, ignore={"<root>"}, strict=False)


def test_unresolved_imports_can_be_ignored() -> None:
    package_text = {"A": "package A { private import StdLib::*; }\n"}
    G = build_import_graph_from_package_text(package_text)

    assert get_unresolved_imports(G, ignore={"StdLib"}) == {}
    assert_no_unresolved_imports_or_raise(G, ignore={"StdLib"}, strict=True)


def test_unresolved_imports_strict_raises() -> None:
    package_text = {"A": "package A { private import Missing::*; }\n"}
    G = build_import_graph_from_package_text(package_text)

    with pytest.raises(Exception):
        assert_no_unresolved_imports_or_raise(G, ignore={"<root>"}, strict=True)
