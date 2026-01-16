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

    with pytest.raises(MissingPackageError) as exc:
        assert_no_unresolved_imports_or_raise(G)

    assert "B" in str(exc.value)
