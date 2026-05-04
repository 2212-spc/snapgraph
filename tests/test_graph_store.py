import json
import sqlite3
from pathlib import Path

from snapgraph.graph_store import (
    _short_label,
    _slug,
    graph_diagnostics,
    graph_insights,
    load_graph,
)
from snapgraph.ingest import ingest_source
from snapgraph.linting import lint_workspace
from snapgraph.workspace import Workspace, create_workspace


def test_ingest_creates_graph_nodes_edges_and_sqlite_rows(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text(
        "# SnapGraph Note\n\n"
        "SnapGraph should preserve cognitive context.\n\n"
        "Open loop: inspect graph paths before building ask.\n",
        encoding="utf-8",
    )
    workspace = Workspace(tmp_path)
    create_workspace(workspace)

    result = ingest_source(workspace, source_path, why="Saved to test graph recall.")
    graph = load_graph(workspace)

    node_ids = {node["id"] for node in graph["nodes"]}
    edge_relations = {edge["relation"] for edge in graph["edges"]}

    assert f"source_{result.source.id}" in node_ids
    assert f"thought_{result.source.id}" in node_ids
    assert any(node["type"] == "task" for node in graph["nodes"])
    assert any(node["type"] == "project" and node["label"] == "SnapGraph" for node in graph["nodes"])
    assert {"triggered_thought", "follow_up", "belongs_to", "evidence_for"} <= edge_relations

    with sqlite3.connect(workspace.sqlite_path) as conn:
        node_count = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]

    assert node_count == len(graph["nodes"])
    assert edge_count == len(graph["edges"])


def test_graph_diagnostics_reports_counts_hubs_and_no_orphans(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text(
        "# GraphRAG Note\n\n"
        "GraphRAG connects evidence paths.\n\n"
        "Open loop: compare graph recall with keyword search.\n",
        encoding="utf-8",
    )
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest_source(workspace, source_path)

    diagnostics = graph_diagnostics(workspace)

    assert diagnostics.node_count >= 4
    assert diagnostics.edge_count >= 4
    assert diagnostics.node_types["source"] == 1
    assert diagnostics.top_hubs
    assert diagnostics.orphans == []
    assert diagnostics.warnings == []


def test_lint_reports_missing_graph_source_node(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text("# SnapGraph Note\n\nA source.\n", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    result = ingest_source(workspace, source_path)

    graph = load_graph(workspace)
    graph["nodes"] = [
        node for node in graph["nodes"] if node["id"] != f"source_{result.source.id}"
    ]
    workspace.graph_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    lint = lint_workspace(workspace)

    assert lint.status == "WARN"
    assert any("has no source node" in warning for warning in lint.warnings)
    assert any("graph.json nodes do not match SQLite nodes table" in warning for warning in lint.warnings)


def test_slug_handles_punctuation_and_emoji() -> None:
    assert _slug("!!!")
    assert _slug("🙂🙂")


def test_short_label_prefers_sentence_boundary() -> None:
    text = "这是第一句。" + ("后续内容" * 80)

    label = _short_label(text)

    assert label == "这是第一句。"


def test_graph_insights_summarize_cognitive_paths(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    source_path = tmp_path / "note.md"
    source_path.write_text(
        "# SnapGraph Note\n\n"
        "SnapGraph should preserve cognitive context.\n\n"
        "Open loop: inspect recall paths.\n",
        encoding="utf-8",
    )
    ingest_source(workspace, source_path, why="Saved to test recall paths.")

    insights = graph_insights(workspace)

    assert insights["project_clusters"]
    assert insights["bridge_sources"]
    assert insights["open_loop_hotspots"]
    assert insights["high_value_review_paths"]
    assert insights["low_confidence_contexts"] == []
