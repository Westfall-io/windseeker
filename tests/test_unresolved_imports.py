import pytest

from windseeker.main import (
    build_import_graph_from_package_text,
    assert_no_unresolved_imports_or_raise,
    MissingPackageError,
)


def test_missing_import_raises():
    package_text = {
        "A": "package A { import B; }",
    }

    G = build_import_graph_from_package_text(package_text)

    # Diagnostic: ensure builder actually recorded unresolved imports
    unresolved = G.graph.get("unresolved_imports", {})
    assert "B" in unresolved, f"Expected unresolved import 'B', got: {unresolved}"

    with pytest.raises(MissingPackageError) as exc:
        assert_no_unresolved_imports_or_raise(G)

    assert "B" in str(exc.value)
