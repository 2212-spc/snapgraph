from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app
from snapgraph.answer_quality import build_answer_quality_pack
from snapgraph.models import (
    AnswerResult,
    RetrievedContext,
    RetrievalDiagnostics,
    RetrievalResult,
)
from snapgraph.trust_noise import build_trust_noise_pack


def _retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        question="How does SnapGraph preserve context?",
        contexts=[
            RetrievedContext(
                source_id="src_demo",
                source_page="wiki/sources/src_demo.md",
                title="SnapGraph memo",
                why_saved="User wanted to preserve design rationale.",
                why_saved_status="user-stated",
                related_project="SnapGraph",
                open_loops=["Decide what to review next."],
                future_recall_questions=["What design rationale mattered?"],
                graph_space_id="default",
                space_name="Default",
                source_excerpt="SnapGraph keeps source text and cognitive context together.",
            )
        ],
        graph_paths=["SnapGraph memo -> triggered_thought -> User wanted rationale"],
        diagnostics=RetrievalDiagnostics(
            keyword_hits=2,
            graph_node_hits=3,
            expanded_nodes=5,
            source_pages_used=1,
            pinned_contexts=0,
            user_stated_contexts=1,
            ai_inferred_contexts=0,
            top_candidate_reasons=["title match", "context match"],
            graph_expansion_truncated=False,
        ),
    )


def test_answer_quality_pack_scores_grounded_answer() -> None:
    result = AnswerResult(
        question="How does SnapGraph preserve context?",
        text=(
            "# Answer\n"
            "## Conclusion\n"
            "SnapGraph preserves context with source traceability.\n"
            "## Materials\n"
            "`SnapGraph memo` - wiki/sources/src_demo.md\n"
            "## Paths\n"
            "SnapGraph memo -> triggered_thought -> User wanted rationale\n"
        ),
        retrieval=_retrieval_result(),
    )

    pack = build_answer_quality_pack(result, provider_metadata={"provider_used": "mock"}, space_id="default")

    assert pack["summary"]["quality_label"] in {"strong", "usable"}
    assert pack["summary"]["groundedness_score"] >= 70
    assert pack["evidence_contract"]["has_source_context"] is True
    assert pack["risk_register"]["risk_count"] >= 0
    assert pack["display_policy"]["collapse_diagnostics"] is True


def test_api_ask_includes_answer_quality(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.post(
        "/api/ask",
        json={
            "question": "How does SnapGraph preserve LLM Wiki context?",
            "mode": "auto",
            "depth": "quick",
            "save": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    quality = payload["answer_quality"]
    assert quality["summary"]["quality_label"] in {"strong", "usable", "thin", "unsupported"}
    assert quality["evidence_contract"]["source_count"] == len(payload["contexts"])
    assert quality["display_policy"]["max_visible_reasons"] <= 5


def test_trust_noise_pack_groups_queue_by_user_pressure() -> None:
    items = [
        {
            "source_id": "a",
            "title": "AI inferred source",
            "why_saved_status": "AI-inferred",
            "review_status": "unreviewed",
            "risk_level": "high",
            "confidence": 0.42,
            "open_loop_count": 2,
            "evidence_count": 0,
            "topic_refs": [],
        },
        {
            "source_id": "b",
            "title": "Confirmed source",
            "why_saved_status": "user-stated",
            "review_status": "confirmed",
            "risk_level": "low",
            "confidence": 0.91,
            "open_loop_count": 0,
            "evidence_count": 2,
            "topic_refs": [{"topic_id": "topic_snapgraph"}],
        },
    ]
    summary = {"total": 2, "by_review_status": {"unreviewed": 1, "confirmed": 1}}

    pack = build_trust_noise_pack(items, summary, filters={})

    assert pack["summary"]["visible_count"] <= 2
    assert pack["lanes"]["immediate"]["count"] == 1
    assert pack["lanes"]["collapsed"]["count"] >= 1
    assert pack["display_policy"]["default_visible_lanes"] <= 3
    assert pack["plain_language"]["headline"]


def test_api_trust_review_includes_noise_reduction(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/trust/review")

    assert response.status_code == 200
    payload = response.json()
    pack = payload["noise_reduction"]
    assert pack["summary"]["total"] == payload["summary"]["total"]
    assert "immediate" in pack["lanes"]
    assert pack["display_policy"]["collapse_resolved_items"] is True


def test_workspace_payload_includes_traceability_audit(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    client.post(
        "/api/ask",
        json={
            "question": "How does SnapGraph connect source and thought?",
            "mode": "auto",
            "depth": "quick",
            "save": False,
        },
    )

    response = client.get("/api/workspace")

    assert response.status_code == 200
    payload = response.json()
    audit = payload["traceability_audit"]
    assert audit["summary"]["source_count"] == payload["sources"]
    assert audit["summary"]["traceability_label"] in {"empty", "thin", "forming", "traceable", "auditable"}
    assert audit["coverage"]["context_coverage_percent"] >= 0
    assert audit["display_policy"]["collapse_complete_sources"] is True


def test_governance_report_endpoint_returns_compact_backend_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/governance/report")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["report_label"] in {"empty", "collecting", "usable", "healthy", "needs_attention"}
    assert payload["sections"]
    assert payload["action_plan"]
    assert payload["display_policy"]["max_visible_sections"] <= 5
    assert payload["source_traceability"]["summary"]["source_count"] >= 1
