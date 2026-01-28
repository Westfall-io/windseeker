from __future__ import annotations

from typer.testing import CliRunner

from windseeker.cli import app


def test_cli_order_prints_packages(monkeypatch) -> None:
    monkeypatch.setattr("windseeker.cli.order_only", lambda *a, **k: ["B", "A"])

    runner = CliRunner()
    result = runner.invoke(app, ["order", "--folder", "tests"])

    assert result.exit_code == 0
    assert "1" in result.stdout
    assert "B" in result.stdout
    assert "A" in result.stdout


def test_cli_run_prints_summary(monkeypatch) -> None:
    # Import PipelineResult dataclass type from pipeline module
    from windseeker.pipeline import PipelineResult
    import networkx as nx

    G = nx.DiGraph()
    G.add_node("A")

    fake = PipelineResult(
        package_text={"A": "package A;\n"},
        graph=G,
        topo_order=["A"],
        views=["A::Views::v1"],
        unresolved_imports={"SysML": {"A"}},
        written_view_files=["views/A.png"],
    )

    monkeypatch.setattr("windseeker.cli.run_pipeline", lambda *a, **k: fake)

    runner = CliRunner()
    result = runner.invoke(app, ["run", "--folder", "tests", "--no-execute"])

    assert result.exit_code == 0
    assert "Packages (nodes)" in result.stdout
    assert "Imports (edges)" in result.stdout
    assert "Views found" in result.stdout
    assert "Unresolved imports" in result.stdout
