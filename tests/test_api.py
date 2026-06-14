import json
from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app


def test_api_thought_history_summarizes_reference_events_without_raw_thinking(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "chat"
    events_path = root / "deep_solve" / "bot-alpha" / "turn_001" / "events.jsonl"
    events_path.parent.mkdir(parents=True)
    events = [
        {"type": "session", "metadata": {"turn_id": "turn_001", "session_id": "session_a"}},
        {"type": "stage_start", "stage": "planning"},
        {"type": "thinking", "content": "SECRET RAW THOUGHT DRAFT should never be returned"},
        {"type": "progress", "stage": "reasoning"},
        {"type": "tool_call", "name": "search"},
        {"type": "tool_result", "name": "search"},
        {"type": "content", "content": "最终回答：使用接口适配器隔离复杂度。"},
    ]
    events_path.write_text("\n".join(json.dumps(event, ensure_ascii=False) for event in events), encoding="utf-8")
    monkeypatch.setenv("SNAPGRAPH_THOUGHT_HISTORY_DIR", str(root))
    client = TestClient(app)

    response = client.get("/api/thought-history?limit=2")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["turns"] == 1
    assert payload["summary"]["thinking_events"] == 1
    assert payload["summary"]["tool_events"] == 2
    assert payload["items"][0]["surface"] == "Solve"
    assert payload["items"][0]["stage_flow"] == ["Plan", "Reason"]
    assert "最终回答" in payload["items"][0]["answer_preview"]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "SECRET RAW THOUGHT DRAFT" not in serialized
    assert "内部草稿" in payload["notice"]


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
    assert any(source["why_saved_status"] == "user-stated" for source in sources)

    insights = graph_response.json()["insights"]
    assert insights["project_clusters"]
    assert insights["open_loop_hotspots"]
    assert insights["high_value_review_paths"]

    questions = questions_response.json()
    assert questions
    question_detail = client.get(f"/api/questions/{questions[0]['id']}")
    assert question_detail.status_code == 200
    detail = question_detail.json()
    assert "## Question" in detail["markdown"]
    assert detail["answer"]
    assert detail["answer_heading"] == "Answer"


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


def test_api_ask_uses_recall_emergence_section_contract(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.post(
        "/api/ask",
        json={"question": "我之前为什么觉得截图不是核心？", "save": False},
    )

    assert response.status_code == 200
    payload = response.json()
    text = payload["text"]
    for heading in [
        "## 结论",
        "## 找回的原话",
        "## 相关材料",
        "## 连接路径",
        "## AI 探索回应",
        "## 涌现洞见",
        "## 下一步",
        "## 检索诊断",
    ]:
        assert heading in text
    assert text.index("## 结论") < text.index("## 找回的原话")


    projection = payload["recall_projection"]
    assert projection["judgment"]["summary"]
    assert projection["evidence_ladder"]
    assert projection["trust_debt"]["level"] in {"low", "medium", "high"}
    assert projection["actions"]
    assert projection["write_back_preview"]["source_ids"]


def test_api_ask_exposes_clickable_local_files(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.post(
        "/api/ask",
        json={"question": "我为什么要从 LLM Wiki 开始？", "save": False},
    )

    assert response.status_code == 200
    local_files = response.json()["local_files"]
    assert local_files
    first = local_files[0]
    assert first["source_id"]
    assert first["title"]
    assert first["path"].startswith("wiki/sources/")
    assert first["raw_path"].startswith("raw/")
    assert first["open_target"] in {"raw", "source_page"}
    assert first["why_saved_status"] in {"user-stated", "AI-inferred", "unknown"}


def test_api_open_local_file_is_workspace_scoped(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    opened: list[list[str]] = []
    client = TestClient(app)
    client.post("/api/demo/load")
    ask_response = client.post(
        "/api/ask",
        json={"question": "我为什么要从 LLM Wiki 开始？", "save": False},
    )
    local_file = ask_response.json()["local_files"][0]

    def fake_popen(command: list[str]) -> object:
        opened.append(command)
        return object()

    monkeypatch.setattr("snapgraph.api.subprocess.Popen", fake_popen)
    open_response = client.post(
        "/api/open-local",
        json={"source_id": local_file["source_id"], "target": "raw"},
    )
    outside_response = client.post(
        "/api/open-local",
        json={"path": "../outside.md"},
    )

    assert open_response.status_code == 200
    assert open_response.json()["opened_path"].startswith("raw/")
    assert opened
    assert outside_response.status_code == 400


def test_api_ask_accepts_current_batch_context_source_ids(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post(
        "/api/ingest",
        files={"file": ("old-noise.md", b"# Old noise\n\narchitecture memory evidence graph retrieval " * 100, "text/markdown")},
        data={"why": "Older global background, not the current upload batch."},
    )
    first = client.post(
        "/api/ingest",
        files={"file": ("batch-receipt.md", b"# Batch receipt\n\nThe current batch needs a receipt and follow-up action.", "text/markdown")},
        data={"why": "This batch tests upload receipt."},
    ).json()
    second = client.post(
        "/api/ingest",
        files={"file": ("batch-evidence.md", b"# Batch evidence\n\nThe answer should lead with a conclusion and then evidence.", "text/markdown")},
        data={"why": "This batch tests answer-first evidence."},
    ).json()

    response = client.post(
        "/api/ask",
        json={
            "question": "结合刚才上传的这批材料，我们下一步应该完善什么？",
            "space_id": "all",
            "save": False,
            "context_source_ids": [first["source_id"], second["source_id"]],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [context["source_id"] for context in payload["contexts"][:2]] == [
        first["source_id"],
        second["source_id"],
    ]
    assert payload["diagnostics"]["pinned_contexts"] == 2
    assert "current batch context" in " ".join(payload["diagnostics"]["top_candidate_reasons"])


def test_api_ask_stream_accepts_current_batch_context_source_ids(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    first = client.post(
        "/api/ingest",
        files={"file": ("stream-batch-a.md", b"# Stream batch A\n\nCurrent batch stream evidence.", "text/markdown")},
        data={"why": "This stream batch source should be pinned."},
    ).json()
    second = client.post(
        "/api/ingest",
        files={"file": ("stream-batch-b.md", b"# Stream batch B\n\nCurrent batch stream conclusion.", "text/markdown")},
        data={"why": "This stream batch source should also be pinned."},
    ).json()

    response = client.post(
        "/api/ask/stream",
        json={
            "question": "结合刚才上传的这批材料，总结一下。",
            "space_id": "all",
            "save": False,
            "context_source_ids": [first["source_id"], second["source_id"]],
        },
    )

    assert response.status_code == 200
    body = response.text
    assert "event: focus" in body
    assert '"pinned_contexts": 2' in body
    assert "Stream batch A" in body
    assert "Stream batch B" in body


def test_api_ask_stream_deep_records_recall_history(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.post(
        "/api/ask/stream",
        json={
            "question": "我为什么要从 LLM Wiki 开始？",
            "space_id": "all",
            "depth": "deep",
            "mode": "auto",
            "thread_id": "thread-a",
            "turn_id": "turn-a",
            "turn_index": 2,
            "previous_turns": [
                {
                    "question": "上一轮问了什么？",
                    "answer_preview": "上一轮的答案摘要",
                    "mode": "auto",
                    "depth": "quick",
                }
            ],
            "save": False,
        },
    )

    assert response.status_code == 200
    body = response.text
    assert "event: thought" in body
    assert '"stage_flow"' in body
    assert "event: final" in body
    assert '"thought"' in body

    history_response = client.get("/api/recall-history?limit=5")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["summary"]["total"] >= 1
    first = history["items"][0]
    assert first["question"] == "我为什么要从 LLM Wiki 开始？"
    assert first["mode"] == "auto"
    assert first["depth"] == "deep"
    assert first["space_id"] == "all"
    assert first["thread_id"] == "thread-a"
    assert first["turn_id"] == "turn-a"
    assert first["turn_index"] == 2
    assert first["answer_text"]
    assert "\n## " in first["answer_text"]
    assert "# 回答 ##" not in first["answer_text"]
    assert first["thought"]
    assert first["thought"]["stage_flow"][:2] == ["Plan", "Retrieve"]
    assert "Think" in first["thought"]["stage_flow"]
    assert "Finish" in first["thought"]["stage_flow"]
    assert first["previous_turns"][0]["question"] == "上一轮问了什么？"
    assert first["context_count"] >= 1
    assert first["thought_summary"]


def test_api_recall_history_filters_multiple_turns_by_thread(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    first_response = client.post(
        "/api/ask/stream",
        json={
            "question": "第一轮为什么从 LLM Wiki 开始？",
            "space_id": "all",
            "mode": "auto",
            "depth": "quick",
            "thread_id": "thread-restore",
            "turn_id": "turn-restore-1",
            "turn_index": 1,
            "save": False,
        },
    )
    second_response = client.post(
        "/api/ask/stream",
        json={
            "question": "第二轮它和普通搜索区别是什么？",
            "space_id": "all",
            "mode": "auto",
            "depth": "deep",
            "thread_id": "thread-restore",
            "turn_id": "turn-restore-2",
            "turn_index": 2,
            "previous_turns": [
                {
                    "question": "第一轮为什么从 LLM Wiki 开始？",
                    "answer_preview": "第一轮公开回答摘要",
                    "mode": "auto",
                    "depth": "quick",
                }
            ],
            "save": False,
        },
    )
    other_response = client.post(
        "/api/ask/stream",
        json={
            "question": "其他线程的问题",
            "space_id": "all",
            "mode": "answer",
            "depth": "quick",
            "thread_id": "thread-other",
            "turn_id": "turn-other-1",
            "turn_index": 1,
            "save": False,
        },
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert other_response.status_code == 200

    history_response = client.get("/api/recall-history?thread_id=thread-restore&limit=10")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history["summary"]["total"] == 2
    assert {item["thread_id"] for item in history["items"]} == {"thread-restore"}
    assert {item["turn_id"] for item in history["items"]} == {"turn-restore-1", "turn-restore-2"}
    second = next(item for item in history["items"] if item["turn_id"] == "turn-restore-2")
    assert second["turn_index"] == 2
    assert second["previous_turns"][0]["question"] == "第一轮为什么从 LLM Wiki 开始？"
    assert second["answer_text"]
    assert second["thought"]


def test_api_ask_stream_deep_records_history_without_contexts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/ask/stream",
        json={
            "question": "完全不存在的材料 zzz-snapgraph-no-context",
            "space_id": "all",
            "depth": "deep",
            "mode": "auto",
            "save": False,
        },
    )

    assert response.status_code == 200
    body = response.text
    assert "event: thought" in body
    assert "event: final" in body

    history_response = client.get("/api/recall-history?limit=5")
    assert history_response.status_code == 200
    first = history_response.json()["items"][0]
    assert first["question"] == "完全不存在的材料 zzz-snapgraph-no-context"
    assert first["mode"] == "auto"
    assert first["depth"] == "deep"
    assert first["context_count"] == 0
    assert first["local_file_count"] == 0
    assert first["thought_summary"]


def test_api_ask_stream_emits_agent_stages_and_final_answer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.post(
        "/api/ask/stream",
        json={"question": "我为什么要从 LLM Wiki 开始？", "save": False},
    )

    assert response.status_code == 200
    body = response.text
    assert "event: stage" in body
    assert '"id": "evidence"' in body
    assert '"id": "write"' in body
    assert "event: final" in body
    assert "## AI 探索回应" in body


    assert '"recall_projection"' in body


def test_api_ask_stream_emits_current_public_thought_before_answer_in_deep_mode(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.post(
        "/api/ask/stream",
        json={"question": "我为什么要从 LLM Wiki 开始？", "depth": "deep", "save": False},
    )

    assert response.status_code == 200
    body = response.text
    assert "event: thought" in body
    assert body.count("event: thought_delta") >= 3
    assert body.index('"id": "connect"') < body.index("event: thought")
    assert body.index('"status": "thinking"') < body.index("event: thought_delta")
    first_delta = body.index("event: thought_delta")
    assert '"trace_role": "thought"' in body
    assert '"call_kind": "llm_reasoning"' in body
    assert '"trace_kind": "llm_chunk"' in body
    assert '"call_state": "running"' in body
    assert '"trace_events": []' in body[:first_delta]
    thought_done = body.index('"status": "done"', first_delta)
    assert '"trace_kind": "llm_output"' in body[thought_done:]
    assert '"call_state": "complete"' in body[thought_done:]
    write_stage = body.index('"id": "write"', thought_done)
    assert first_delta < thought_done
    assert thought_done < write_stage
    assert write_stage < body.index("event: final")
    assert '"title": "Thought"' in body
    assert "我为什么要从 LLM Wiki 开始？" in body
    assert "LLM Wiki Note" in body
    assert "隐藏草稿" not in body


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


def test_api_config_accepts_qwen_multimodal_provider(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SNAPGRAPH_LLM_API_KEY", "test-key")
    client = TestClient(app)

    response = client.put(
        "/api/config",
        json={"provider": "qwen", "model": "qwen3-vl-plus", "api_key_env": "SNAPGRAPH_LLM_API_KEY"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "qwen"
    assert payload["runtime"]["provider_used"] == "qwen"
    assert payload["runtime"]["model_used"] == "qwen3-vl-plus"


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


def test_api_keeps_local_evidence_when_real_provider_key_is_missing_for_evidence(
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
    assert response.status_code == 200
    payload = response.json()
    assert "## 找回的原话" in payload["text"]
    assert payload["contexts"]
    assert payload["provider"]["configured_provider"] == "deepseek"
    assert payload["provider"]["provider_ready"] is False
    assert payload["provider"]["fallback_used"] is True


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


def test_api_can_update_source_title(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    upload = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Old Title\n\nMemory receipt draft.\n", "text/markdown")},
    )
    source_id = upload.json()["source_id"]

    response = client.patch(
        f"/api/sources/{source_id}/title",
        json={"title": "用户确认后的保存名"},
    )

    assert response.status_code == 200
    detail = response.json()["detail"]
    assert detail["title"] == "用户确认后的保存名"


def test_api_can_review_ai_inferred_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    upload = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# AI Draft\n\nThis source needs review.\n", "text/markdown")},
    )
    source_id = upload.json()["source_id"]

    response = client.patch(
        f"/api/sources/{source_id}/review",
        json={
            "review_status": "confirmed",
            "review_note": "用户确认：这个推断符合当时的保存意图。",
        },
    )

    assert response.status_code == 200
    detail = response.json()["detail"]
    assert detail["why_saved_status"] == "user-stated"
    assert detail["review_status"] == "confirmed"
    assert detail["review_note"] == "用户确认：这个推断符合当时的保存意图。"
    assert detail["reviewed_at"]


def test_api_can_rewrite_and_reject_ai_inferred_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    upload = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Rewrite Me\n\nThis source needs a human reason.\n", "text/markdown")},
    )
    source_id = upload.json()["source_id"]

    rewrite = client.patch(
        f"/api/sources/{source_id}/review",
        json={
            "review_status": "rewritten",
            "why_saved": "我保存它是因为它能提醒我修正 AI 推断。",
            "review_note": "改写为用户原话。",
        },
    )

    assert rewrite.status_code == 200
    rewritten_detail = rewrite.json()["detail"]
    assert rewritten_detail["why_saved_status"] == "user-stated"
    assert rewritten_detail["why_saved"] == "我保存它是因为它能提醒我修正 AI 推断。"
    assert rewritten_detail["review_status"] == "rewritten"

    reject = client.patch(
        f"/api/sources/{source_id}/review",
        json={"review_status": "rejected", "review_note": "这个推断不是我的真实意图。"},
    )

    assert reject.status_code == 200
    rejected_detail = reject.json()["detail"]
    assert rejected_detail["review_status"] == "rejected"
    assert rejected_detail["review_note"] == "这个推断不是我的真实意图。"


def test_api_rejects_invalid_review_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    upload = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Bad Review\n\nInvalid review status.\n", "text/markdown")},
    )
    source_id = upload.json()["source_id"]

    response = client.patch(
        f"/api/sources/{source_id}/review",
        json={"review_status": "made-up"},
    )

    assert response.status_code == 400


def test_api_ingest_reuses_exact_duplicate_in_same_manual_space(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    first = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Same\n\nExact duplicate.\n", "text/markdown")},
        data={"route_mode": "manual", "space_id": "default"},
    )
    second = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Same\n\nExact duplicate.\n", "text/markdown")},
        data={"route_mode": "manual", "space_id": "default"},
    )
    sources = client.get("/api/spaces/default/sources")
    graph = client.get("/api/spaces/default/graph")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["deduplicated"] is True
    assert second.json()["source_id"] == first.json()["source_id"]
    assert len(sources.json()) == 1
    assert not any(edge["relation"] == "related_to" for edge in graph.json()["edges"])


def test_api_ingest_accepts_pdf_as_capture_shell(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/ingest",
        files={"file": ("paper.pdf", b"%PDF-1.4\n% placeholder\n", "application/pdf")},
        data={"why": "This PDF might close the agent memory question."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "pdf"
    assert payload["status"] == "user-stated"


def test_api_ingest_falls_back_to_mock_when_provider_key_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SNAPGRAPH_LLM_API_KEY", raising=False)
    client = TestClient(app)
    client.put("/api/config", json={"provider": "deepseek", "api_key_env": "SNAPGRAPH_LLM_API_KEY"})

    response = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Note\n\nA local capture should still work.\n", "text/markdown")},
        data={"why": "This must be preserved even without a provider key."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "user-stated"
    assert payload["provider"]["provider_used"] == "mock"
    assert payload["provider"]["fallback_used"] is True


def test_api_ask_falls_back_to_local_answer_when_provider_key_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SNAPGRAPH_LLM_API_KEY", raising=False)
    client = TestClient(app)
    config = client.put(
        "/api/config",
        json={
            "provider": "qwen",
            "model": "qwen3-vl-plus",
            "api_key_env": "SNAPGRAPH_LLM_API_KEY",
        },
    )
    upload = client.post(
        "/api/ingest",
        files={"file": ("note.md", b"# Screenshot note\n\nScreenshots are only capture inputs.\n", "text/markdown")},
        data={"why": "Screenshots are not the core; recall is the core."},
    )
    answer = client.post(
        "/api/ask",
        json={"question": "我之前为什么觉得截图不是核心？", "space_id": "all"},
    )

    assert config.status_code == 200
    assert upload.status_code == 200
    assert answer.status_code == 200
    payload = answer.json()
    assert "## 找回的原话" in payload["text"]
    assert "Screenshots are not the core" in payload["text"]
    assert payload["provider"]["fallback_used"] is True
