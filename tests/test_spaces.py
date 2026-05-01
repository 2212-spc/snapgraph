import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.answer import answer_question
from snapgraph.api import app
from snapgraph.graph_store import graph_for_space, load_graph
from snapgraph.ingest import ingest_source
from snapgraph.models import DEFAULT_GRAPH_SPACE_ID, INBOX_GRAPH_SPACE_ID
from snapgraph.spaces import create_graph_space, create_route_suggestion, accept_suggestion
from snapgraph.workspace import Workspace, create_workspace


class RaisingLLM:
    def synthesize_answer(self, question: str, contexts: list[dict], graph_paths: list[str]) -> str:
        raise AssertionError("LLM should not be called when retrieval has no evidence")


def test_workspace_seeds_spaces_and_migrates_graph_json(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    workspace.graph_path.write_text(
        json.dumps(
            {
                "nodes": [{"id": "n1", "type": "source", "label": "Legacy", "properties": {}}],
                "edges": [
                    {
                        "id": "e1",
                        "source": "n1",
                        "target": "n1",
                        "relation": "self",
                        "evidence_source_id": None,
                        "confidence": 1.0,
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    create_workspace(workspace)
    graph = load_graph(workspace)

    with sqlite3.connect(workspace.sqlite_path) as conn:
        space_ids = {row[0] for row in conn.execute("SELECT id FROM graph_spaces").fetchall()}

    assert {INBOX_GRAPH_SPACE_ID, DEFAULT_GRAPH_SPACE_ID} <= space_ids
    assert graph["nodes"][0]["graph_space_id"] == DEFAULT_GRAPH_SPACE_ID
    assert graph["nodes"][0]["status"] == "confirmed"
    assert graph["edges"][0]["graph_space_id"] == DEFAULT_GRAPH_SPACE_ID


def test_ingest_defaults_to_inbox_and_route_suggestion_can_move_source(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    create_graph_space(
        workspace,
        name="Product Insights",
        purpose="Product Insights SnapGraph usefulness and product value.",
    )
    source_path = tmp_path / "product.md"
    source_path.write_text(
        "# Product Insights\n\nSnapGraph usefulness and product value.\n",
        encoding="utf-8",
    )

    result = ingest_source(workspace, source_path, why="Validate product value.")
    suggestion = create_route_suggestion(workspace, result.source.id)
    accepted = accept_suggestion(workspace, suggestion["id"])
    graph = graph_for_space(workspace, "product_insights")

    assert result.source.graph_space_id == INBOX_GRAPH_SPACE_ID
    assert accepted["status"] == "accepted"
    assert graph["nodes"]
    assert all(node["graph_space_id"] == "product_insights" for node in graph["nodes"])

    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            "SELECT graph_space_id FROM sources WHERE id = ?",
            (result.source.id,),
        ).fetchone()
    assert row == ("product_insights",)


def test_answer_space_filter_and_no_match_fail_closed(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    source_path = tmp_path / "product.md"
    source_path.write_text("# Product Memory\n\nProduct graph recall.\n", encoding="utf-8")
    ingest_source(workspace, source_path, why="Product graph recall.")

    inbox_answer = answer_question(workspace, "Product Memory", space_id=INBOX_GRAPH_SPACE_ID)
    default_answer = answer_question(workspace, "Product Memory", space_id=DEFAULT_GRAPH_SPACE_ID)
    no_match = answer_question(workspace, "unrelated quantum pineapple", llm=RaisingLLM())

    assert inbox_answer.retrieval.contexts
    assert default_answer.retrieval.contexts == []
    assert "Low confidence" in default_answer.text
    assert "Low confidence" in no_match.text


def test_api_spaces_inbox_suggestions_and_accept_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    created = client.post(
        "/api/spaces",
        json={
            "name": "Product Insights",
            "purpose": "Product Insights SnapGraph usefulness and product value.",
        },
    )
    upload = client.post(
        "/api/ingest",
        files={"file": ("product.md", b"# Product Insights\n\nSnapGraph usefulness.\n", "text/markdown")},
        data={"why": "Validate product value."},
    )

    assert created.status_code == 200
    assert upload.status_code == 200
    assert upload.json()["graph_space_id"] == INBOX_GRAPH_SPACE_ID
    assert upload.json()["routing_suggestion_id"]

    inbox = client.get("/api/spaces/inbox/sources")
    suggestions = client.get("/api/suggestions", params={"status": "pending"})
    suggestion = suggestions.json()["suggestions"][0]
    accepted = client.post(f"/api/suggestions/{suggestion['id']}/accept")

    assert inbox.status_code == 200
    assert len(inbox.json()) == 1
    assert suggestion["payload"]["target_space_id"] == "product_insights"
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"

    target_sources = client.get("/api/spaces/product_insights/sources")
    target_graph = client.get("/api/spaces/product_insights/graph")

    assert len(target_sources.json()) == 1
    assert target_graph.json()["node_count"] > 0
