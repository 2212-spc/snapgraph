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
