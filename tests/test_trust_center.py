from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app


def test_trust_review_queue_prioritizes_unreviewed_ai_context(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/trust/review")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["summary"]["total"] == len(payload["items"])
    assert any(item["why_saved_status"] == "AI-inferred" for item in payload["items"])
    assert payload["items"][0]["risk_level"] in {"critical", "high", "medium", "low"}
    assert "recommended_action" in payload["items"][0]


def test_trust_review_queue_exposes_session_decision_fields(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    payload = client.get("/api/trust/review").json()
    item = payload["items"][0]

    assert item["risk_reasons"]
    assert item["review_focus"]["headline"]
    assert item["review_focus"]["primary_action"]
    assert item["trust_signals"]["evidence_count"] == item["evidence_count"]
    assert item["trust_signals"]["has_open_loops"] == item["has_open_loops"]
    assert item["trust_signals"]["topic_count"] == len(item["topic_refs"])
    assert item["decision_options"]
    assert {option["action"] for option in item["decision_options"]} == {
        "confirmed",
        "rewritten",
        "rejected",
        "deferred",
    }
    assert any(option["requires_rewrite"] for option in item["decision_options"])


def test_trust_review_detail_exposes_traceability(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    queue = client.get("/api/trust/review").json()
    source_id = queue["items"][0]["source_id"]

    response = client.get(f"/api/trust/review/{source_id}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["item"]["source_id"] == source_id
    assert "evidence_paths" in detail
    assert "history" in detail
    assert "open_loops" in detail


def test_trust_diagnostics_reports_counts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/trust/diagnostics")

    assert response.status_code == 200
    diagnostics = response.json()
    assert diagnostics["queue_total"] >= 1
    assert "ai_inferred_unreviewed" in diagnostics
    assert "open_loop_total" in diagnostics
    assert "warnings" in diagnostics


def test_trust_batch_confirm_writes_history(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    item = next(
        item
        for item in client.get("/api/trust/review").json()["items"]
        if item["why_saved_status"] == "AI-inferred"
    )

    response = client.post(
        "/api/trust/review/batch",
        json={"source_ids": [item["source_id"]], "action": "confirmed", "note": "User confirmed."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated_count"] == 1
    detail = client.get(f"/api/trust/review/{item['source_id']}").json()
    assert detail["item"]["review_status"] == "confirmed"
    assert detail["history"][0]["action"] == "confirmed"


def test_trust_batch_rewrite_requires_replacement_text(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    source_id = client.get("/api/trust/review").json()["items"][0]["source_id"]

    response = client.post(
        "/api/trust/review/batch",
        json={"source_ids": [source_id], "action": "rewritten", "note": "Missing rewrite map."},
    )

    assert response.status_code == 400
    assert "rewrite" in response.json()["detail"].lower()


def test_trust_open_loop_list_materializes_source_traceability(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/trust/open-loops")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["summary"]["total"] == len(payload["items"])
    first = payload["items"][0]
    assert first["loop_id"]
    assert first["state"] == "active"
    assert first["source_ids"]
    assert first["source_titles"]
    assert first["risk_level"] in {"critical", "high", "medium", "low"}


def test_trust_open_loops_can_be_marked_next(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    loops = client.get("/api/trust/open-loops").json()["items"]
    assert loops

    response = client.patch(
        f"/api/trust/open-loops/{loops[0]['loop_id']}",
        json={"state": "next", "note": "Work this next."},
    )

    assert response.status_code == 200
    updated = response.json()["item"]
    assert updated["state"] == "next"
    assert updated["note"] == "Work this next."


def test_trust_open_loop_rejects_invalid_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    loop_id = client.get("/api/trust/open-loops").json()["items"][0]["loop_id"]

    response = client.patch(
        f"/api/trust/open-loops/{loop_id}",
        json={"state": "blocked", "note": "Not supported."},
    )

    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()
