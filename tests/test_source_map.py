from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app
from snapgraph.models import DEFAULT_GRAPH_SPACE_ID
from snapgraph.source_map import (
    expand_source,
    find_path_between_sources,
    source_map_graph,
)
from snapgraph.workspace import Workspace, create_workspace


def _demo_workspace(tmp_path: Path) -> Workspace:
    """Create a workspace with two demo sources ingested."""
    workspace = Workspace(tmp_path)
    create_workspace(workspace)

    from snapgraph.demo_data import DEMO_WHYS
    from snapgraph.ingest import ingest_source

    demo_dir = Path(__file__).parents[1] / "examples" / "demo_sources"
    for source_path in sorted(demo_dir.glob("*.md")):
        ingest_source(
            workspace,
            source_path,
            why=DEMO_WHYS.get(source_path.name),
            space_id=DEFAULT_GRAPH_SPACE_ID,
        )
    return workspace


def test_source_map_graph_returns_only_sources(tmp_path: Path) -> None:
    workspace = _demo_workspace(tmp_path)
    result = source_map_graph(workspace, DEFAULT_GRAPH_SPACE_ID)

    assert result["space_id"] == DEFAULT_GRAPH_SPACE_ID
    assert len(result["sources"]) > 0
    # All enriched entries should have source type nodes
    for entry in result["sources"]:
        assert entry["node"]["type"] == "source"
        assert "source_detail" in entry
        assert "title" in entry["source_detail"]


def test_source_map_graph_has_enriched_metadata(tmp_path: Path) -> None:
    workspace = _demo_workspace(tmp_path)
    result = source_map_graph(workspace, DEFAULT_GRAPH_SPACE_ID)

    for entry in result["sources"]:
        detail = entry["source_detail"]
        assert "id" in detail
        assert "why_saved" in detail
        assert "why_saved_status" in detail
        assert "confidence" in detail
        assert entry.get("thought_count", 0) >= 0
        assert entry.get("task_count", 0) >= 0


def test_source_map_synthetic_edges_structure(tmp_path: Path) -> None:
    workspace = _demo_workspace(tmp_path)
    result = source_map_graph(workspace, DEFAULT_GRAPH_SPACE_ID)

    for edge in result["synthetic_edges"]:
        assert edge["id"].startswith("synth_")
        assert edge["source"].startswith("source_")
        assert edge["target"].startswith("source_")
        assert edge["relation"] == "related_thoughts"
        assert 0 < edge["confidence"] <= 1.0
        assert edge["reason"]


def test_expand_source_returns_local_subgraph(tmp_path: Path) -> None:
    workspace = _demo_workspace(tmp_path)
    result = source_map_graph(workspace, DEFAULT_GRAPH_SPACE_ID)
    if not result["sources"]:
        return

    source_id = result["sources"][0]["source_detail"]["id"]
    subgraph = expand_source(workspace, source_id, DEFAULT_GRAPH_SPACE_ID)

    assert "nodes" in subgraph
    assert "edges" in subgraph
    assert len(subgraph["nodes"]) > 0
    # Should include the source node itself
    source_nodes = [n for n in subgraph["nodes"] if n["id"] == f"source_{source_id}"]
    assert len(source_nodes) == 1


def test_find_path_two_sources(tmp_path: Path) -> None:
    workspace = _demo_workspace(tmp_path)
    result = source_map_graph(workspace, DEFAULT_GRAPH_SPACE_ID)
    sources = result["sources"]
    if len(sources) < 2:
        return

    source_ids = [sources[0]["source_detail"]["id"], sources[1]["source_detail"]["id"]]
    path = find_path_between_sources(workspace, source_ids, DEFAULT_GRAPH_SPACE_ID)

    # May or may not find a path depending on graph structure
    assert "path_nodes" in path
    assert "path_edges" in path
    assert "path_description" in path


def test_find_path_requires_two_sources(tmp_path: Path) -> None:
    workspace = _demo_workspace(tmp_path)
    try:
        find_path_between_sources(workspace, ["only_one"], DEFAULT_GRAPH_SPACE_ID)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_find_path_nonexistent_source(tmp_path: Path) -> None:
    workspace = _demo_workspace(tmp_path)
    path = find_path_between_sources(
        workspace,
        ["nonexistent_a", "nonexistent_b"],
        DEFAULT_GRAPH_SPACE_ID,
    )
    assert path["path_nodes"] == []


# ── API tests ──


def test_api_source_map_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get(f"/api/spaces/{DEFAULT_GRAPH_SPACE_ID}/source-map")
    assert response.status_code == 200
    payload = response.json()
    assert "sources" in payload
    assert "synthetic_edges" in payload
    assert "insights" in payload


def test_api_source_expand_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    # Get a source ID from the source-map
    sm = client.get(f"/api/spaces/{DEFAULT_GRAPH_SPACE_ID}/source-map").json()
    if not sm["sources"]:
        return
    source_id = sm["sources"][0]["source_detail"]["id"]

    response = client.get(
        f"/api/spaces/{DEFAULT_GRAPH_SPACE_ID}/sources/{source_id}/expand"
    )
    assert response.status_code == 200
    payload = response.json()
    assert "nodes" in payload
    assert "edges" in payload


def test_api_graph_path_endpoint(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    sm = client.get(f"/api/spaces/{DEFAULT_GRAPH_SPACE_ID}/source-map").json()
    sources = sm["sources"]
    if len(sources) < 2:
        return

    response = client.post(
        "/api/graph/path",
        json={
            "source_ids": [
                sources[0]["source_detail"]["id"],
                sources[1]["source_detail"]["id"],
            ],
            "space_id": DEFAULT_GRAPH_SPACE_ID,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "path_nodes" in payload
    assert "path_edges" in payload
    assert "path_description" in payload


def test_api_graph_path_requires_two_sources(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/graph/path",
        json={"source_ids": ["single"], "space_id": DEFAULT_GRAPH_SPACE_ID},
    )
    assert response.status_code == 400
