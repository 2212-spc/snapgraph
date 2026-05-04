from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app


def test_api_demo_exposes_sources_questions_and_graph_insights(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    demo_response = client.post("/api/demo/load")
    sources_response = client.get("/api/sources")
    graph_response = client.get("/api/graph")
    questions_response = client.get("/api/questions")
    lint_response = client.get("/api/lint")

    assert demo_response.status_code == 200
    assert sources_response.status_code == 200
    assert graph_response.status_code == 200
    assert questions_response.status_code == 200
    assert lint_response.status_code == 200
    assert lint_response.json()["status"] == "OK"

    sources = sources_response.json()
    assert any(source["title"] == "LLM Wiki Note" for source in sources)
    assert any(source["why_saved_status"] == "user-guided" for source in sources)

    insights = graph_response.json()["insights"]
    assert insights["project_clusters"]
    assert insights["open_loop_hotspots"]
    assert insights["high_value_review_paths"]

    questions = questions_response.json()
    assert questions
    question_detail = client.get(f"/api/questions/{questions[0]['id']}")
    assert question_detail.status_code == 200
    assert "## Question" in question_detail.json()["markdown"]


def test_api_ask_save_flag_controls_question_writeback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    question_dir = tmp_path / ".my_snapgraph" / "wiki" / "questions"
    before = len(list(question_dir.glob("q_*.md")))

    no_save = client.post(
        "/api/ask",
        json={"question": "我为什么要从 LLM Wiki 开始？", "save": False},
    )
    after_no_save = len(list(question_dir.glob("q_*.md")))

    save = client.post(
        "/api/ask",
        json={"question": "我为什么要从 LLM Wiki 开始？", "save": True},
    )
    after_save = len(list(question_dir.glob("q_*.md")))

    assert no_save.status_code == 200
    assert "saved_page" not in no_save.json()
    assert after_no_save == before
    assert save.status_code == 200
    assert "saved_page" in save.json()
    assert after_save == before + 1


def test_api_reports_provider_metadata(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.post(
        "/api/ask",
        json={"question": "我为什么要从 LLM Wiki 开始？", "save": False},
    )

    assert response.status_code == 200
    provider = response.json()["provider"]
    assert provider["provider_used"] == "mock"
    assert provider["fallback_used"] is False
    assert provider["provider_error"] == ""


def test_api_rejects_api_key_in_api_key_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    response = client.put(
        "/api/config",
        json={"provider": "deepseek", "api_key_env": "sk-should-not-be-stored"},
    )

    assert response.status_code == 400
    assert "environment variable name" in response.json()["detail"]


def test_api_no_match_does_not_require_real_provider_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SNAPGRAPH_LLM_API_KEY", raising=False)
    client = TestClient(app)
    config_response = client.put(
        "/api/config",
        json={"provider": "deepseek", "api_key_env": "SNAPGRAPH_LLM_API_KEY"},
    )

    response = client.post("/api/ask", json={"question": "LLM Wiki"})

    assert config_response.status_code == 200
    assert response.status_code == 200
    assert response.json()["diagnostics"]["source_pages_used"] == 0
    assert response.json()["focus_graph"]["nodes"] == []


def test_api_fails_fast_when_real_provider_key_is_missing_for_evidence(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SNAPGRAPH_LLM_API_KEY", raising=False)
    client = TestClient(app)
    client.post("/api/demo/load")
    config_response = client.put(
        "/api/config",
        json={"provider": "deepseek", "api_key_env": "SNAPGRAPH_LLM_API_KEY"},
    )

    response = client.post("/api/ask", json={"question": "LLM Wiki"})

    assert config_response.status_code == 200
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["configured_provider"] == "deepseek"
    assert detail["provider_ready"] is False
    assert detail["fallback_used"] is False


def test_api_can_confirm_and_correct_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    upload = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Note\n\nOpen loop: keep revising.\n", "text/markdown")},
    )
    source_id = upload.json()["source_id"]

    response = client.patch(
        f"/api/sources/{source_id}/context",
        json={
            "why_saved": "This matters for the proposal narrative.",
            "related_project": "Thesis proposal",
            "open_loops": ["Rewrite the proposal framing."],
            "confirm": True,
        },
    )

    assert response.status_code == 200
    detail = response.json()["detail"]
    assert detail["why_saved_status"] == "user-stated"
    assert detail["why_saved"] == "This matters for the proposal narrative."
    assert detail["related_project"] == "Thesis proposal"
    assert detail["open_loops"] == ["Rewrite the proposal framing."]
