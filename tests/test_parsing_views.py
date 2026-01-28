from __future__ import annotations

from windseeker.parsing import (
    collect_all_views,
    collect_views_from_top_level_package_text,
)


def test_collect_views_from_top_level_package_text_finds_nested_views() -> None:
    pkg_name = "Top"
    pkg_text = """
package Top {
  package Inner1 {
    view V1 {
    }
  }
  package Inner2 {
    package Deep {
      view V2 {
      }
    }
  }
  view RootView {
  }
}
"""
    views = collect_views_from_top_level_package_text(pkg_name, pkg_text)

    assert "Top::Inner1::V1" in views
    assert "Top::Inner2::Deep::V2" in views
    assert "Top::RootView" in views


def test_collect_views_from_top_level_package_text_ignores_commented_lines() -> None:
    pkg_name = "Top"
    pkg_text = """
package Top {
  // view ShouldNotCount { }
  package Inner {
    // view AlsoShouldNotCount { }
    view RealOne {
    }
  }
}
"""
    views = collect_views_from_top_level_package_text(pkg_name, pkg_text)

    assert "Top::Inner::RealOne" in views
    assert all("ShouldNotCount" not in v for v in views)
    assert all("AlsoShouldNotCount" not in v for v in views)


def test_collect_all_views_across_packages_and_dedups() -> None:
    package_text = {
        "A": "package A {\n  view V {\n  }\n}\n",
        "B": "package B {\n  view V {\n  }\n}\n",
        # NOTE: key name doesn't matter; collect_all_views iterates by dict key
        # but uses the *top-level package name* (the dict key) as the prefix.
        "A_dup": "package A_dup {\n  view V {\n  }\n}\n",
    }

    views = collect_all_views(package_text)

    assert "A::V" in views
    assert "B::V" in views
    assert "A_dup::V" in views
    assert len(views) == len(set(views))
