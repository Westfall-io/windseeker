from __future__ import annotations

from pathlib import Path

import networkx as nx

from windseeker.pipeline import run_pipeline


def test_run_pipeline_execute_false_skips_execute_and_extract(tmp_path: Path, monkeypatch) -> None:
    # Minimal package_text
    fake_package_text = {"A": "package A;\n"}

    # Minimal graph
    G = nx.DiGraph()
    G.add_node("A")

    # Patch pipeline dependencies (patch names as imported in windseeker.pipeline)
    monkeypatch.setattr("windseeker.pipeline.scan_folder", lambda folder: fake_package_text)
    monkeypatch.setattr("windseeker.pipeline.build_import_graph_from_package_text", lambda pt: G)
    monkeypatch.setattr("windseeker.pipeline.assert_acyclic_or_raise", lambda g: None)
    monkeypatch.setattr(
        "windseeker.pipeline.assert_no_unresolved_imports_or_raise", lambda *a, **k: None
    )
    monkeypatch.setattr("windseeker.pipeline.get_unresolved_imports", lambda *a, **k: {})
    monkeypatch.setattr("windseeker.pipeline.collect_all_views", lambda pt: ["A::Views::v1"])
    monkeypatch.setattr("windseeker.pipeline.visualize_graph_to_file", lambda *a, **k: None)
    monkeypatch.setattr("windseeker.pipeline.topological_packages", lambda *a, **k: ["A"])

    # Let sysml writer happen as real (writes to tmp_path)
    sysml_out = tmp_path / "out.sysml"
    nb_out = tmp_path / "out.ipynb"

    called = {"execute": 0, "extract": 0}

    monkeypatch.setattr(
        "windseeker.pipeline.write_notebook_in_dependency_order",
        lambda *a, **k: Path(nb_out).write_text("{}", encoding="utf-8"),
    )
    monkeypatch.setattr(
        "windseeker.pipeline.execute_and_fail_on_notebook_errors",
        lambda *a, **k: called.__setitem__("execute", called["execute"] + 1),
    )
    monkeypatch.setattr(
        "windseeker.pipeline.extract_view_images_from_executed_notebook",
        lambda *a, **k: called.__setitem__("extract", called["extract"] + 1) or [],
    )

    result = run_pipeline(
        folder=str(tmp_path),
        execute=False,
        export_views=True,
        sysml_out=str(sysml_out),
        notebook_out=str(nb_out),
    )

    assert called["execute"] == 0
    assert called["extract"] == 0
    assert result.written_view_files == []
    assert sysml_out.exists()


def test_run_pipeline_export_views_false_skips_extract(tmp_path: Path, monkeypatch) -> None:
    fake_package_text = {"A": "package A;\n"}
    G = nx.DiGraph()
    G.add_node("A")

    monkeypatch.setattr("windseeker.pipeline.scan_folder", lambda folder: fake_package_text)
    monkeypatch.setattr("windseeker.pipeline.build_import_graph_from_package_text", lambda pt: G)
    monkeypatch.setattr("windseeker.pipeline.assert_acyclic_or_raise", lambda g: None)
    monkeypatch.setattr(
        "windseeker.pipeline.assert_no_unresolved_imports_or_raise", lambda *a, **k: None
    )
    monkeypatch.setattr("windseeker.pipeline.get_unresolved_imports", lambda *a, **k: {})
    monkeypatch.setattr("windseeker.pipeline.collect_all_views", lambda pt: [])
    monkeypatch.setattr("windseeker.pipeline.visualize_graph_to_file", lambda *a, **k: None)
    monkeypatch.setattr("windseeker.pipeline.topological_packages", lambda *a, **k: ["A"])
    monkeypatch.setattr(
        "windseeker.pipeline.write_notebook_in_dependency_order",
        lambda *a, **k: None,
    )

    called = {"execute": 0, "extract": 0}
    monkeypatch.setattr(
        "windseeker.pipeline.execute_and_fail_on_notebook_errors",
        lambda *a, **k: called.__setitem__("execute", called["execute"] + 1),
    )
    monkeypatch.setattr(
        "windseeker.pipeline.extract_view_images_from_executed_notebook",
        lambda *a, **k: called.__setitem__("extract", called["extract"] + 1) or [],
    )

    result = run_pipeline(
        folder=str(tmp_path),
        execute=True,
        export_views=False,
        sysml_out=str(tmp_path / "out.sysml"),
        notebook_out=str(tmp_path / "out.ipynb"),
    )

    assert called["execute"] == 1
    assert called["extract"] == 0
    assert result.written_view_files == []
