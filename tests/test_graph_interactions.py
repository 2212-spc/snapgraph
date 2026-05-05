import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app
from snapgraph.graph_store import (
    create_graph_theme,
    create_manual_edge,
    create_user_thought,
    graph_for_space,
    load_graph_layout,
    save_graph_layout,
)
from snapgraph.ingest import ingest_source, update_cognitive_context
from snapgraph.models import INBOX_GRAPH_SPACE_ID
from snapgraph.workspace import Workspace, create_workspace


def test_graph_layout_persists_without_changing_graph_json(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    original_graph = workspace.graph_path.read_text(encoding="utf-8")

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


def test_manual_edge_thought_and_theme_record_feedback(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("# First\n\nLLM Wiki base.\n", encoding="utf-8")
    second.write_text("# Second\n\nGraph recall layer.\n", encoding="utf-8")
    first_result = ingest_source(workspace, first, why="Preserve the base workflow.")
    second_result = ingest_source(workspace, second, why="Connect recall with graph paths.")
    first_node_id = f"source_{first_result.source.id}"
    second_node_id = f"source_{second_result.source.id}"

    edge = create_manual_edge(
        workspace,
        source=first_node_id,
        target=second_node_id,
        relation="related_to",
        reason="Both describe the SnapGraph architecture path.",
        graph_space_id=INBOX_GRAPH_SPACE_ID,
    )
    thought = create_user_thought(
        workspace,
        graph_space_id=INBOX_GRAPH_SPACE_ID,
        node_ids=[first_node_id, second_node_id],
        label="LLM Wiki leads into graph recall",
        reason="The selected sources describe a single product direction.",
    )
    theme = create_graph_theme(
        workspace,
        graph_space_id=INBOX_GRAPH_SPACE_ID,
        label="Architecture path",
        member_node_ids=[first_node_id, second_node_id],
        reason="These captures should be reviewed together.",
    )
    graph = graph_for_space(workspace, INBOX_GRAPH_SPACE_ID)

    assert edge["status"] == "confirmed"
    assert edge["evidence_kind"] == "manual"
    assert thought["edges_created"] == 2
    assert theme["origin"] == "user"
    assert any(node["id"] == thought["thought_node"]["id"] for node in graph["nodes"])
    assert any(edge["relation"] == "supports" for edge in graph["edges"])

    with sqlite3.connect(workspace.sqlite_path) as conn:
        feedback_count = conn.execute("SELECT COUNT(*) FROM graph_feedback").fetchone()[0]
    assert feedback_count == 3


def test_context_update_preserves_manual_edge_and_synthesized_thought(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("# First\n\nMemory persistence needs evidence paths.\n", encoding="utf-8")
    second.write_text("# Second\n\nScreenshots are input, not the product core.\n", encoding="utf-8")
    first_result = ingest_source(workspace, first, why="This anchors the evidence path.")
    second_result = ingest_source(workspace, second, why="This reframes screenshots as capture inputs.")
    first_node_id = f"source_{first_result.source.id}"
    second_node_id = f"source_{second_result.source.id}"
    manual_edge = create_manual_edge(
        workspace,
        source=first_node_id,
        target=second_node_id,
        relation="clarifies",
        reason="The second source explains a boundary in the first source.",
        graph_space_id=INBOX_GRAPH_SPACE_ID,
    )
    thought = create_user_thought(
        workspace,
        graph_space_id=INBOX_GRAPH_SPACE_ID,
        node_ids=[first_node_id, second_node_id],
        label="Screenshots feed recall; they are not the recall layer",
        reason="The product value is finding the thought behind the capture.",
    )

    update_cognitive_context(
        workspace,
        first_result.source.id,
        why_saved="Updated user-stated reason that should not erase manual facts.",
        confirm=True,
    )
    graph = graph_for_space(workspace, INBOX_GRAPH_SPACE_ID)

    assert any(edge["id"] == manual_edge["id"] for edge in graph["edges"])
    assert any(node["id"] == thought["thought_node"]["id"] for node in graph["nodes"])
    assert any(
        edge.get("target") == thought["thought_node"]["id"] and edge.get("origin") == "user"
        for edge in graph["edges"]
    )


def test_graph_interaction_api_endpoints_coexist_with_v2_ingest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    source_path = tmp_path / "product.md"
    source_path.write_text("# Product\n\nGraph interaction.\n", encoding="utf-8")
    upload = client.post(
        "/api/ingest",
        files={"file": ("product.md", source_path.read_bytes(), "text/markdown")},
        data={"route_mode": "auto", "why": "Test graph interaction."},
    )
    assert upload.status_code == 200
    payload = upload.json()
    source_id = payload["source_id"]
    assert payload["routing_suggestion"]
    graph_space_id = payload["graph_space_id"]

    layout = client.patch(
        "/api/graph/layout",
        json={
            "view_id": f"space:{graph_space_id}",
            "graph_space_id": graph_space_id,
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
            "graph_space_id": graph_space_id,
        },
    )
    thought = client.post(
        "/api/graph/thoughts",
        json={
            "graph_space_id": graph_space_id,
            "node_ids": [f"source_{source_id}", f"thought_{source_id}"],
            "label": "Source and reason form one memory",
            "reason": "The file and why-saved text must be read together.",
        },
    )
    theme = client.post(
        "/api/graph/themes",
        json={
            "graph_space_id": graph_space_id,
            "label": "Interaction test",
            "member_node_ids": [f"source_{source_id}", f"thought_{source_id}"],
            "reason": "Review this small memory cluster.",
        },
    )

    assert layout.status_code == 200
    assert edge.status_code == 200
    assert thought.status_code == 200
    assert theme.status_code == 200
    assert client.get("/api/graph/layout", params={"view_id": f"space:{graph_space_id}"}).json()["positions"]
    assert client.get("/api/graph/themes", params={"space_id": graph_space_id}).json()["themes"]


def test_prune_requires_reason_for_destructive_edge_status(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    source_path = tmp_path / "source.md"
    source_path.write_text("# Source\n\nGraph fact.\n", encoding="utf-8")
    result = ingest_source(workspace, source_path, why="Create graph fact.")
    edge_id = next(
        edge["id"]
        for edge in json.loads(workspace.graph_path.read_text(encoding="utf-8"))["edges"]
        if edge["source"] == f"source_{result.source.id}"
    )

    client = TestClient(app)
    original_cwd = Path.cwd()
    try:
        import os

        os.chdir(tmp_path)
        rejected = client.patch(f"/api/graph/edges/{edge_id}", json={"status": "rejected"})
        weakened = client.patch(
            f"/api/graph/edges/{edge_id}",
            json={"status": "weakened", "reason": "Evidence is too indirect."},
        )
    finally:
        os.chdir(original_cwd)

    assert rejected.status_code == 400
    assert weakened.status_code == 200
    assert weakened.json()["edge"]["weakened_reason"] == "Evidence is too indirect."
