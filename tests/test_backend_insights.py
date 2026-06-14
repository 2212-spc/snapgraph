from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app


def test_workspace_payload_includes_product_health_pack(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/workspace")

    assert response.status_code == 200
    payload = response.json()
    health = payload["workspace_health"]
    assert health["summary"]["source_count"] == payload["sources"]
    assert health["summary"]["node_count"] == payload["nodes"]
    assert health["readiness"]["label"] in {"empty", "collecting", "usable", "healthy", "needs_attention"}
    assert health["next_actions"]
    assert health["information_pressure"]["default_visible_sections"] <= 4


def test_graph_payload_includes_evidence_quality_pack(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/graph?space_id=all")

    assert response.status_code == 200
    payload = response.json()
    pack = payload["graph_evidence"]
    assert pack["summary"]["node_count"] == payload["node_count"]
    assert pack["summary"]["edge_count"] == payload["edge_count"]
    assert pack["evidence_routes"]
    assert "source_coverage" in pack
    assert pack["display_policy"]["collapse_low_value_edges"] is True


def test_recall_history_payload_includes_history_insights(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    client.post(
        "/api/ask",
        json={
            "question": "鎴戜负浠€涔堣浠?LLM Wiki 寮€濮嬶紵",
            "mode": "auto",
            "depth": "quick",
            "save": False,
        },
    )

    response = client.get("/api/recall-history?limit=5")

    assert response.status_code == 200
    payload = response.json()
    insights = payload["history_insights"]
    assert insights["summary"]["total"] == payload["summary"]["total"]
    assert insights["conversation_patterns"]["mode_counts"]
    assert insights["reuse_candidates"]
    assert insights["display_policy"]["max_visible_history"] <= 8
