from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app
from snapgraph.demo_data import DEMO_WHYS
from snapgraph.ingest import ingest_source
from snapgraph.models import DEFAULT_GRAPH_SPACE_ID
from snapgraph.topics import create_topic, get_topic_payload, update_topic
from snapgraph.workspace import Workspace, create_workspace


def _demo_workspace(tmp_path: Path) -> Workspace:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    demo_dir = Path(__file__).parents[1] / "examples" / "demo_sources"
    for source_path in sorted(demo_dir.glob("*.md"))[:3]:
        ingest_source(
            workspace,
            source_path,
            why=DEMO_WHYS.get(source_path.name),
            space_id=DEFAULT_GRAPH_SPACE_ID,
        )
    return workspace


def test_create_topic_and_update_state(tmp_path: Path) -> None:
    workspace = _demo_workspace(tmp_path)
    payload = create_topic(
        workspace,
        initial_question="How should I think about LLM Wiki?",
        space_id=DEFAULT_GRAPH_SPACE_ID,
    )

    assert payload["topic"]["id"].startswith("topic_")
    assert payload["state"]["turn_count"] == 0

    source_id = next(source["source_id"] for source in payload["state"]["evidence"]) if payload["state"]["evidence"] else ""
    updated = update_topic(
        workspace,
        payload["topic"]["id"],
        {
            "title": "LLM Wiki thread",
            "pinned_source_ids": [source_id] if source_id else [],
            "confirmed_judgments": ["User confirmed this is a research topic."],
        },
    )

    assert updated["topic"]["title"] == "LLM Wiki thread"
    assert updated["state"]["confirmed_judgments"] == ["User confirmed this is a research topic."]


def test_topic_api_continuous_turns_and_wiki_page(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    created = client.post(
        "/api/topics",
        json={"initial_question": "Why did I save LLM Wiki material?", "space_id": "all"},
    )
    assert created.status_code == 200
    topic_id = created.json()["topic"]["id"]

    first = client.post(
        f"/api/topics/{topic_id}/ask/stream",
        json={"question": "Why did I save LLM Wiki material?", "save": False},
    )
    second = client.post(
        f"/api/topics/{topic_id}/ask/stream",
        json={"question": "What should I inspect next?", "save": False},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert "event: topic" in second.text
    assert "event: final" in second.text

    detail = client.get(f"/api/topics/{topic_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert len(payload["turns"]) == 2
    assert payload["state"]["turn_count"] == 2
    assert payload["state"]["evidence_source_ids"]

    page_path = tmp_path / ".my_snapgraph" / "wiki" / "topics" / f"{topic_id}.md"
    assert page_path.exists()
    page_text = page_path.read_text(encoding="utf-8")
    assert "## Topic State" in page_text
    assert "## Evidence Sources" in page_text
    assert "## Turns" in page_text


def test_topic_api_pinned_sources_are_used_in_next_turn(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    sources = client.get("/api/sources").json()
    pinned_id = sources[0]["id"]

    created = client.post("/api/topics", json={"title": "Pinned source test"}).json()
    topic_id = created["topic"]["id"]
    patch = client.patch(
        f"/api/topics/{topic_id}",
        json={"pinned_source_ids": [pinned_id]},
    )
    assert patch.status_code == 200

    response = client.post(
        f"/api/topics/{topic_id}/ask/stream",
        json={"question": "Use the pinned source.", "save": False},
    )

    assert response.status_code == 200
    assert '"pinned_contexts": 1' in response.text
    detail = client.get(f"/api/topics/{topic_id}").json()
    assert pinned_id in detail["state"]["evidence_source_ids"]


def test_topic_api_validation_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    assert client.get("/api/topics/missing").status_code == 404
    assert client.patch("/api/topics/missing", json={}).status_code == 404
    assert client.post("/api/topics/missing/ask/stream", json={"question": "x"}).status_code == 404

    created = client.post("/api/topics", json={"title": "Empty question"}).json()
    response = client.post(
        f"/api/topics/{created['topic']['id']}/ask/stream",
        json={"question": ""},
    )
    assert response.status_code == 400
