import json
import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.answer import answer_question
from snapgraph.api import app
from snapgraph.graph_store import graph_for_space, load_graph
from snapgraph.ingest import ingest_source
from snapgraph.models import DEFAULT_GRAPH_SPACE_ID, INBOX_GRAPH_SPACE_ID
from snapgraph.spaces import (
    accept_suggestion,
    create_graph_space,
    create_route_suggestion,
    move_source_to_space,
)
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
    assert "低置信度" in default_answer.text
    assert "低置信度" in no_match.text


def test_move_source_rejects_exact_duplicate_in_target_space(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    source_path = tmp_path / "same.md"
    source_path.write_text("# Same\n\nExact duplicate.\n", encoding="utf-8")
    first = ingest_source(workspace, source_path, space_id=DEFAULT_GRAPH_SPACE_ID)
    second = ingest_source(workspace, source_path, space_id=INBOX_GRAPH_SPACE_ID)
    before_graph = load_graph(workspace)

    try:
        move_source_to_space(workspace, second.source.id, DEFAULT_GRAPH_SPACE_ID)
    except ValueError as exc:
        assert "duplicate content_hash already exists in target space" in str(exc)
    else:
        raise AssertionError("Expected duplicate route to be rejected")

    after_graph = load_graph(workspace)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        target_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM sources
            WHERE graph_space_id = ? AND content_hash = ?
            """,
            (DEFAULT_GRAPH_SPACE_ID, first.source.content_hash),
        ).fetchone()[0]
    assert before_graph == after_graph
    assert target_count == 1


def test_api_ingest_auto_route_accepts_high_confidence_suggestion(tmp_path: Path, monkeypatch) -> None:
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
    payload = upload.json()
    assert payload["graph_space_id"] == "product_insights"
    assert payload["routing_suggestion_id"]
    assert payload["routing_suggestion"]["status"] == "accepted"

    inbox = client.get("/api/spaces/inbox/sources")
    suggestions = client.get("/api/suggestions", params={"status": "pending"})

    assert inbox.status_code == 200
    assert inbox.json() == []
    assert suggestions.json()["suggestions"] == []

    target_sources = client.get("/api/spaces/product_insights/sources")
    target_graph = client.get("/api/spaces/product_insights/graph")

    assert len(target_sources.json()) == 1
    assert target_graph.json()["node_count"] > 0


def test_api_ingest_auto_route_keeps_low_confidence_default_in_inbox(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    upload = client.post(
        "/api/ingest",
        files={"file": ("misc.md", b"# Sour Plum Recipe\n\nSalt, sugar, and sour plums.\n", "text/markdown")},
        data={"why": "Archive this stray recipe."},
    )

    assert upload.status_code == 200
    payload = upload.json()
    assert payload["graph_space_id"] == INBOX_GRAPH_SPACE_ID
    assert payload["routing_suggestion"]["status"] == "pending"
    assert payload["routing_suggestion"]["confidence"] == 0.52
    assert payload["routing_suggestion"]["payload"]["target_space_id"] == DEFAULT_GRAPH_SPACE_ID


def test_api_source_route_moves_material_between_spaces(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    created = client.post(
        "/api/spaces",
        json={
            "name": "Research Decisions",
            "purpose": "Research decisions, screenshots, and project judgment.",
        },
    )
    upload = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Note\n\nScreenshot routing note.\n", "text/markdown")},
        data={"route_mode": "inbox", "why": "This belongs with research decisions."},
    )
    source_id = upload.json()["source_id"]

    moved = client.post(
        f"/api/sources/{source_id}/route",
        json={"space_id": created.json()["id"], "reason": "User moved from graph workspace."},
    )

    assert created.status_code == 200
    assert upload.status_code == 200
    assert moved.status_code == 200
    assert moved.json()["detail"]["graph_space_id"] == created.json()["id"]
    target_sources = client.get(f"/api/spaces/{created.json()['id']}/sources")
    assert [source["id"] for source in target_sources.json()] == [source_id]
