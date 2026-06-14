from pathlib import Path

from snapgraph.models import (
    AnswerResult,
    CognitiveContext,
    IngestResult,
    RetrievedContext,
    RetrievalDiagnostics,
    RetrievalResult,
    Source,
    SourcePage,
)
from snapgraph.decision_layers import (
    build_collect_decision_layers,
    build_recall_decision_layers,
    build_trust_detail_decision_layers,
    build_trust_queue_decision_layers,
)


def _retrieval_result() -> RetrievalResult:
    contexts = [
        RetrievedContext(
            source_id="src_user",
            source_page="wiki/sources/src_user.md",
            title="User anchor",
            why_saved="The user explicitly saved this because it shaped the product decision.",
            why_saved_status="user-stated",
            related_project="SnapGraph",
            open_loops=["Confirm whether this still blocks launch."],
            future_recall_questions=["Why did this direction matter?"],
            graph_space_id="default",
            space_name="Main memory",
            source_excerpt="A user-stated note about product direction.",
        ),
        RetrievedContext(
            source_id="src_ai",
            source_page="wiki/sources/src_ai.md",
            title="AI inferred context",
            why_saved="AI-inferred: The note may relate to trust review.",
            why_saved_status="AI-inferred",
            related_project="SnapGraph",
            open_loops=[],
            future_recall_questions=[],
            graph_space_id="default",
            space_name="Main memory",
            source_excerpt="An inferred note about trust review.",
        ),
    ]
    diagnostics = RetrievalDiagnostics(
        keyword_hits=3,
        graph_node_hits=2,
        expanded_nodes=5,
        source_pages_used=2,
        pinned_contexts=1,
        user_stated_contexts=1,
        ai_inferred_contexts=1,
        top_candidate_reasons=[
            "User anchor: current batch context",
            "AI inferred context: keyword density 3/80",
        ],
        graph_expansion_truncated=False,
    )
    return RetrievalResult(
        question="Why did this direction matter?",
        contexts=contexts,
        graph_paths=[
            "User anchor -> triggered_thought -> SnapGraph product decision",
            "AI inferred context -> mentions -> Trust review",
        ],
        diagnostics=diagnostics,
    )


def test_build_recall_decision_layers_includes_boundary_and_next_step() -> None:
    result = AnswerResult(
        question="Why did this direction matter?",
        text="# Answer\n\nThe saved reason points back to the product decision.",
        retrieval=_retrieval_result(),
    )

    payload = build_recall_decision_layers(
        result,
        provider_metadata={"fallback_used": False, "provider_used": "mock"},
        space_id="default",
    )

    assert payload["summary"]["answer_boundary"] == "mixed"
    assert payload["summary"]["primary_source_id"] == "src_user"
    assert payload["evidence_health"]["local_evidence_count"] == 2
    assert payload["evidence_health"]["graph_path_count"] == 2
    assert payload["answer_boundary"]["user_stated_count"] == 1
    assert payload["answer_boundary"]["ai_inferred_count"] == 1
    assert payload["next_actions"][0]["kind"] in {"open_source", "review_ai_inference", "continue_open_loop"}
    assert [step["id"] for step in payload["user_path"]] == ["collect", "review", "act"]
    assert payload["user_path"][1]["current"] is True
    assert payload["diagnostic_trace"]["space_id"] == "default"


def test_build_recall_decision_layers_handles_no_local_evidence() -> None:
    diagnostics = RetrievalDiagnostics(
        keyword_hits=0,
        graph_node_hits=0,
        expanded_nodes=0,
        source_pages_used=0,
        pinned_contexts=0,
        user_stated_contexts=0,
        ai_inferred_contexts=0,
        top_candidate_reasons=[],
        graph_expansion_truncated=False,
    )
    result = AnswerResult(
        question="Unknown question",
        text="# Answer\n\nNo evidence.",
        retrieval=RetrievalResult(
            question="Unknown question",
            contexts=[],
            graph_paths=[],
            diagnostics=diagnostics,
        ),
    )

    payload = build_recall_decision_layers(
        result,
        provider_metadata={"fallback_used": True, "provider_error": "missing key"},
        space_id="all",
    )

    assert payload["summary"]["answer_boundary"] == "unsupported"
    assert payload["evidence_health"]["status"] == "needs_collection"
    assert payload["answer_boundary"]["provider_fallback"] is True
    assert payload["next_actions"][0]["kind"] == "collect_evidence"
    assert any(item["severity"] == "high" for item in payload["risk_flags"])


def test_build_trust_queue_decision_layers_groups_attention_and_batch_candidates() -> None:
    items = [
        {
            "source_id": "src_critical",
            "title": "Critical AI note",
            "risk_level": "critical",
            "review_status": "unreviewed",
            "why_saved_status": "AI-inferred",
            "confidence": 0.42,
            "evidence_count": 1,
            "has_open_loops": True,
            "open_loops": ["Resolve risk."],
            "future_recall_questions": ["Will this affect answers?"],
        },
        {
            "source_id": "src_low",
            "title": "Low risk user note",
            "risk_level": "low",
            "review_status": "confirmed",
            "why_saved_status": "user-stated",
            "confidence": 1.0,
            "evidence_count": 3,
            "has_open_loops": False,
            "open_loops": [],
            "future_recall_questions": [],
        },
    ]

    payload = build_trust_queue_decision_layers(
        items,
        {"total": 2, "critical": 1, "high": 0, "unreviewed": 1},
        {"risk": "", "status": ""},
    )

    assert payload["attention_budget"]["default_visible_items"] <= 4
    assert payload["priority_lanes"][0]["id"] == "must_review"
    assert payload["priority_lanes"][0]["source_ids"] == ["src_critical"]
    assert payload["batch_candidates"]["safe_to_batch_source_ids"] == ["src_low"]
    assert payload["session_script"][0]["label"]
    assert payload["filters_echo"]["risk"] == ""


def test_build_trust_detail_decision_layers_explains_single_item_review() -> None:
    detail = {
        "item": {
            "source_id": "src_critical",
            "title": "Critical AI note",
            "risk_level": "critical",
            "review_status": "unreviewed",
            "why_saved_status": "AI-inferred",
            "confidence": 0.48,
            "evidence_count": 1,
            "has_open_loops": True,
            "open_loops": ["Resolve risk."],
            "future_recall_questions": ["Will this affect answers?"],
            "why_saved": "AI-inferred: This may affect answers.",
        },
        "analysis": {
            "trust_score": {"score": 44, "label": "fragile"},
            "evidence_compression": {"summary": "One path needs review."},
        },
        "evidence_paths": [{"path": "source -> thought", "relation": "triggered_thought"}],
        "history": [],
        "open_loops": [{"loop_id": "loop_a", "state": "active", "text": "Resolve risk."}],
    }

    payload = build_trust_detail_decision_layers(detail)

    assert payload["decision_header"]["source_id"] == "src_critical"
    assert payload["decision_header"]["recommended_action"] in {"review", "rewrite", "defer"}
    assert payload["review_ladder"][0]["id"] == "read_reason"
    assert payload["rewrite_guardrails"]["should_rewrite"] is True
    assert payload["impact_preview"]["future_recall"]


def test_build_collect_decision_layers_reports_quality_and_traceability(tmp_path: Path) -> None:
    source = Source(
        id="src_collect",
        path="raw/notes/src_collect.md",
        type="markdown",
        imported_at="2026-06-14T00:00:00+00:00",
        content_hash="abc123",
        title="Collected note",
        original_filename="note.md",
        summary="A short source summary.",
        graph_space_id="inbox",
    )
    context = CognitiveContext(
        source_id="src_collect",
        why_saved="AI-inferred: This may explain the design direction.",
        why_saved_status="AI-inferred",
        related_project="SnapGraph",
        open_loops=["Decide where this belongs."],
        future_recall_questions=["Why did we save this?"],
        importance="medium",
        confidence=0.55,
    )
    page = SourcePage(
        source=source,
        relative_page_path="wiki/sources/src_collect.md",
        absolute_page_path=tmp_path / "wiki" / "sources" / "src_collect.md",
    )
    result = IngestResult(
        source=source,
        cognitive_context=context,
        raw_path=tmp_path / "raw" / "notes" / "src_collect.md",
        page=page,
        warnings=[],
        routing_suggestion_id="sug_1",
        deduplicated=False,
    )
    routing_suggestion = {
        "id": "sug_1",
        "status": "pending",
        "confidence": 0.67,
        "reason": "Matched product notes.",
        "payload": {
            "target_space_id": "default",
            "target_space_name": "Main memory",
            "alternatives": [{"space_id": "inbox", "space_name": "Inbox", "score": 0.33}],
        },
    }

    payload = build_collect_decision_layers(
        result,
        source_detail={"space_name": "Inbox"},
        routing_suggestion=routing_suggestion,
        route_mode="auto",
        provider_metadata={"provider_used": "mock", "fallback_used": False},
    )

    assert payload["capture_quality"]["source_id"] == "src_collect"
    assert payload["capture_quality"]["why_saved_boundary"] == "AI-inferred"
    assert payload["routing"]["suggested_space_name"] == "Main memory"
    assert payload["traceability"]["wiki_page"] == "wiki/sources/src_collect.md"
    assert payload["next_actions"][0]["kind"] in {"review_reason", "accept_route", "ask_from_source"}
