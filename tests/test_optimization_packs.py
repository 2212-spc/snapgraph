from pathlib import Path

from snapgraph.collect_quality import build_collect_quality_pack
from snapgraph.models import (
    CognitiveContext,
    IngestResult,
    RetrievedContext,
    RetrievalDiagnostics,
    RetrievalResult,
    Source,
    SourcePage,
)
from snapgraph.recall_strategy import build_recall_strategy_pack
from snapgraph.trust_workflow import build_trust_workflow_pack


def _context(
    source_id: str,
    *,
    status: str,
    title: str = "Source",
    loops: list[str] | None = None,
    questions: list[str] | None = None,
) -> RetrievedContext:
    return RetrievedContext(
        source_id=source_id,
        source_page=f"wiki/sources/{source_id}.md",
        title=title,
        why_saved=(
            "The user saved this as a direct decision anchor."
            if status == "user-stated"
            else "AI-inferred: This may explain the old decision."
        ),
        why_saved_status=status,
        related_project="SnapGraph",
        open_loops=loops or [],
        future_recall_questions=questions or [],
        graph_space_id="default",
        space_name="Main memory",
        source_excerpt="This note discusses memory, evidence, and design decisions.",
    )


def test_recall_strategy_pack_scores_readiness_and_query_followups() -> None:
    retrieval = RetrievalResult(
        question="Why did the memory workflow matter?",
        contexts=[
            _context(
                "src_user",
                status="user-stated",
                title="Workflow decision",
                loops=["Check whether the launch scope still excludes collaboration."],
                questions=["Why did we exclude collaboration?"],
            ),
            _context("src_ai", status="AI-inferred", title="Trust note"),
        ],
        graph_paths=[
            "Workflow decision -> triggered_thought -> Product scope",
            "Trust note -> mentions -> AI boundary",
        ],
        diagnostics=RetrievalDiagnostics(
            keyword_hits=5,
            graph_node_hits=3,
            expanded_nodes=6,
            source_pages_used=2,
            pinned_contexts=0,
            user_stated_contexts=1,
            ai_inferred_contexts=1,
            top_candidate_reasons=["Workflow decision: title matched workflow"],
            graph_expansion_truncated=False,
        ),
    )

    pack = build_recall_strategy_pack(retrieval, space_id="default")

    assert pack["readiness"]["score"] >= 70
    assert pack["readiness"]["label"] in {"ready", "review_first"}
    assert pack["evidence_matrix"]["coverage"]["user_stated"] == 1
    assert pack["query_plan"]["follow_up_questions"]
    assert pack["source_roles"][0]["role"] == "primary_anchor"
    assert pack["failure_modes"][0]["id"] != "no_local_evidence"


def test_recall_strategy_pack_handles_empty_retrieval() -> None:
    retrieval = RetrievalResult(
        question="What did I decide about pricing?",
        contexts=[],
        graph_paths=[],
        diagnostics=RetrievalDiagnostics(
            keyword_hits=0,
            graph_node_hits=0,
            expanded_nodes=0,
            source_pages_used=0,
            pinned_contexts=0,
            user_stated_contexts=0,
            ai_inferred_contexts=0,
            top_candidate_reasons=[],
            graph_expansion_truncated=False,
        ),
    )

    pack = build_recall_strategy_pack(retrieval, space_id="all")

    assert pack["readiness"]["label"] == "needs_collection"
    assert pack["query_plan"]["rewrite_suggestions"]
    assert pack["failure_modes"][0]["id"] == "no_local_evidence"
    assert pack["source_roles"] == []


def test_collect_quality_pack_audits_capture_and_route(tmp_path: Path) -> None:
    source = Source(
        id="src_collect",
        path="raw/notes/src_collect.md",
        type="markdown",
        imported_at="2026-06-14T00:00:00+00:00",
        content_hash="abc123",
        title="Memory workflow note",
        original_filename="workflow.md",
        summary="A note about memory workflow evidence.",
        graph_space_id="inbox",
    )
    context = CognitiveContext(
        source_id="src_collect",
        why_saved="AI-inferred: This probably belongs to the product workflow.",
        why_saved_status="AI-inferred",
        related_project="SnapGraph",
        open_loops=["Decide whether this belongs in launch scope."],
        future_recall_questions=["Why did this workflow matter?"],
        importance="medium",
        confidence=0.58,
    )
    result = IngestResult(
        source=source,
        cognitive_context=context,
        raw_path=tmp_path / "raw" / "notes" / "src_collect.md",
        page=SourcePage(
            source=source,
            relative_page_path="wiki/sources/src_collect.md",
            absolute_page_path=tmp_path / "wiki" / "sources" / "src_collect.md",
        ),
        warnings=[],
        routing_suggestion_id="sug_1",
        deduplicated=False,
    )

    pack = build_collect_quality_pack(
        result,
        route_mode="auto",
        routing_suggestion={
            "id": "sug_1",
            "status": "pending",
            "confidence": 0.64,
            "reason": "Matched workflow space.",
            "payload": {"target_space_id": "default", "target_space_name": "Main memory"},
        },
        provider_metadata={"provider_used": "mock", "fallback_used": False},
    )

    assert pack["capture_audit"]["boundary"] == "AI-inferred"
    assert pack["capture_audit"]["quality_label"] in {"usable", "thin", "needs_review"}
    assert pack["routing_audit"]["needs_user_choice"] is True
    assert pack["traceability_audit"]["source_id"] == "src_collect"
    assert pack["repair_plan"][0]["action"] in {"confirm_reason", "accept_route", "ask_from_capture"}


def test_trust_workflow_pack_builds_lanes_and_decision_script() -> None:
    items = [
        {
            "source_id": "src_a",
            "title": "AI decision note",
            "risk_level": "critical",
            "review_status": "unreviewed",
            "why_saved_status": "AI-inferred",
            "confidence": 0.4,
            "evidence_count": 1,
            "has_open_loops": True,
            "open_loops": ["Resolve launch scope."],
            "future_recall_questions": ["What did this affect?"],
        },
        {
            "source_id": "src_b",
            "title": "Confirmed source",
            "risk_level": "low",
            "review_status": "confirmed",
            "why_saved_status": "user-stated",
            "confidence": 1.0,
            "evidence_count": 4,
            "has_open_loops": False,
            "open_loops": [],
            "future_recall_questions": [],
        },
    ]

    pack = build_trust_workflow_pack(items, filters={"risk": "", "status": ""})

    assert pack["work_modes"][0]["id"] == "focus"
    assert pack["review_lanes"][0]["id"] == "decision_required"
    assert pack["decision_script"][0]["step"] == "orient"
    assert pack["bulk_plan"]["safe_source_ids"] == ["src_b"]
    assert pack["queue_health"]["pressure"] in {"high", "medium", "low", "empty"}
