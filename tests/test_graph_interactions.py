import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app
from snapgraph.graph_store import graph_for_space, load_graph_layout
from snapgraph.ingest import ingest_source
from snapgraph.models import INBOX_GRAPH_SPACE_ID
from snapgraph.workspace import Workspace, create_workspace


def test_graph_layout_persists_without_changing_graph_json(tmp_path: Path) -> None:
    """Layout writes coordinates to SQLite and leaves graph facts untouched."""
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    original_graph = workspace.graph_path.read_text(encoding="utf-8")

    from snapgraph.graph_store import save_graph_layout

    result = save_graph_layout(
        workspace,
        view_id="space:default",
        graph_space_id="default",
        positions=[{"node_id": "node_a", "x": 10.5, "y": -4, "locked": True}],
    )
    layout = load_graph_layout(workspace, "space:default")

    assert result == {"view_id": "space:default", "saved": 1}
    assert layout["positions"][0]["node_id"] == "node_a"
    assert layout["positions"][0]["locked"] is True
    assert workspace.graph_path.read_text(encoding="utf-8") == original_graph


def test_manual_edge_and_user_thought_are_written_to_graph(tmp_path: Path) -> None:
    """Manual connect and synthesize operations create confirmed graph facts."""
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("# First\n\nLLM Wiki base.\n", encoding="utf-8")
    second.write_text("# Second\n\nGraph recall layer.\n", encoding="utf-8")
    first_result = ingest_source(workspace, first, why="Preserve the base workflow.")
    second_result = ingest_source(workspace, second, why="Connect recall with graph paths.")

    from snapgraph.graph_store import create_manual_edge, create_user_thought

    edge = create_manual_edge(
        workspace,
        source=f"source_{first_result.source.id}",
        target=f"source_{second_result.source.id}",
        relation="related_to",
        reason="Both describe the SnapGraph architecture path.",
        graph_space_id=INBOX_GRAPH_SPACE_ID,
    )
    thought = create_user_thought(
        workspace,
        graph_space_id=INBOX_GRAPH_SPACE_ID,
        node_ids=[f"source_{first_result.source.id}", f"source_{second_result.source.id}"],
        label="LLM Wiki leads into graph recall",
        reason="The selected sources describe a single product direction.",
    )
    graph = graph_for_space(workspace, INBOX_GRAPH_SPACE_ID)

    assert edge["status"] == "confirmed"
    assert edge["evidence_kind"] == "manual"
    assert thought["edges_created"] == 2
    assert any(node["id"] == thought["thought_node"]["id"] for node in graph["nodes"])
    assert any(edge["relation"] == "supports" for edge in graph["edges"])

    with sqlite3.connect(workspace.sqlite_path) as conn:
        feedback_count = conn.execute("SELECT COUNT(*) FROM graph_feedback").fetchone()[0]
    assert feedback_count == 2


def test_graph_interaction_api_endpoints(tmp_path: Path, monkeypatch) -> None:
    """API endpoints expose layout, manual edge, thought, and theme operations."""
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    source_path = tmp_path / "product.md"
    source_path.write_text("# Product\n\nGraph interaction.\n", encoding="utf-8")
    upload = client.post(
        "/api/ingest",
        files={"file": ("product.md", source_path.read_bytes(), "text/markdown")},
        data={"why": "Test graph interaction."},
    )
    source_id = upload.json()["source_id"]

    layout = client.patch(
        "/api/graph/layout",
        json={
            "view_id": "space:inbox",
            "graph_space_id": "inbox",
            "positions": [{"node_id": f"source_{source_id}", "x": 1, "y": 2}],
        },
    )
    edge = client.post(
        "/api/graph/edges",
        json={
            "source": f"source_{source_id}",
            "target": f"thought_{source_id}",
            "relation": "related_to",
            "reason": "The source and saved reason should stay connected.",
            "graph_space_id": "inbox",
        },
    )
    thought = client.post(
        "/api/graph/thoughts",
        json={
            "graph_space_id": "inbox",
            "node_ids": [f"source_{source_id}", f"thought_{source_id}"],
            "label": "Source and reason form one memory",
            "reason": "The file and why-saved text must be read together.",
        },
    )
    theme = client.post(
        "/api/graph/themes",
        json={
            "graph_space_id": "inbox",
            "label": "Interaction test",
            "member_node_ids": [f"source_{source_id}", f"thought_{source_id}"],
        },
    )

    assert layout.status_code == 200
    assert edge.status_code == 200
    assert thought.status_code == 200
    assert theme.status_code == 200
    assert client.get("/api/graph/layout", params={"view_id": "space:inbox"}).json()["positions"]
    assert client.get("/api/graph/themes", params={"space_id": "inbox"}).json()["themes"]
