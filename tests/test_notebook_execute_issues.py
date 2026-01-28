from __future__ import annotations

import nbformat

from windseeker.notebook.execute import (
    collect_notebook_issues,
    format_notebook_issues,
    split_notebook_issues,
)


def _nb_with_one_cell(source: str, *, stderr_text: str):
    nb = nbformat.v4.new_notebook()
    nb.cells = [
        nbformat.v4.new_code_cell(
            source=source,
            outputs=[
                nbformat.v4.new_output(
                    output_type="stream",
                    name="stderr",
                    text=stderr_text,
                )
            ],
        )
    ]
    return nb


def test_collect_notebook_issues_marks_view_cells() -> None:
    nb = _nb_with_one_cell(
        "%view A::B::v1\n",
        stderr_text="Exception java.lang.StringIndexOutOfBoundsException: boom",
    )
    issues = collect_notebook_issues(nb)

    assert len(issues) == 1
    assert issues[0]["is_view"] is True
    assert issues[0]["view_name"] == "A::B::v1"


def test_collect_notebook_issues_marks_non_view_cells() -> None:
    nb = _nb_with_one_cell(
        "package A;\n",
        stderr_text="Exception: something bad",
    )
    issues = collect_notebook_issues(nb)

    assert len(issues) == 1
    assert issues[0]["is_view"] is False
    assert issues[0]["view_name"] is None


def test_split_notebook_issues_separates_fatal_and_view() -> None:
    issues = [
        {"is_view": False, "cell_index": 0, "type": "stderr", "text": "Exception..."},
        {"is_view": True, "cell_index": 1, "type": "stderr", "text": "Exception..."},
    ]
    fatal, view = split_notebook_issues(issues)

    assert len(fatal) == 1
    assert len(view) == 1
    assert fatal[0]["cell_index"] == 0
    assert view[0]["cell_index"] == 1


def test_format_notebook_issues_includes_view_prefix() -> None:
    issues = [
        {
            "cell_index": 3,
            "type": "stderr",
            "text": "Exception: boom",
            "is_view": True,
            "view_name": "A::B::v1",
        }
    ]
    msg = format_notebook_issues(issues)
    assert "VIEW A::B::v1" in msg
    assert "Cell 3" in msg
