from __future__ import annotations

from dataclasses import asdict
from typing import Any, Iterable

from .collect_quality import build_collect_quality_pack
from .models import AnswerResult, IngestResult, RetrievedContext, RetrievalResult
from .recall_strategy import build_recall_strategy_pack
from .trust_workflow import build_trust_workflow_pack


RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
STATUS_ORDER = {
    "unreviewed": 0,
    "deferred": 1,
    "rewritten": 2,
    "confirmed": 3,
    "rejected": 4,
}
BOUNDARY_ORDER = {"AI-inferred": 0, "unknown": 1, "user-stated": 2, "user-guided": 3}


def build_recall_decision_layers(
    result: AnswerResult,
    provider_metadata: dict[str, Any] | None = None,
    space_id: str = "all",
) -> dict[str, Any]:
    """Build a compact decision layer for an answer without changing answer text."""
    metadata = provider_metadata or {}
    retrieval = result.retrieval
    contexts = retrieval.contexts
    primary = contexts[0] if contexts else None
    boundary = _recall_boundary(contexts, metadata)
    evidence_health = _recall_evidence_health(retrieval)
    risk_flags = _recall_risk_flags(retrieval, metadata)
    answer_boundary = _recall_answer_boundary(contexts, metadata)
    next_actions = _recall_next_actions(retrieval, metadata, space_id)
    user_path = _recall_user_path(retrieval, evidence_health, answer_boundary, next_actions)
    return {
        "summary": {
            "question": result.question,
            "space_id": space_id,
            "answer_boundary": boundary,
            "primary_source_id": primary.source_id if primary else "",
            "primary_title": primary.title if primary else "",
            "confidence_label": _recall_confidence_label(evidence_health, answer_boundary, metadata),
            "can_answer_as_memory": boundary in {"user_supported", "mixed"} and not metadata.get("fallback_used"),
            "quiet_copy": _recall_quiet_copy(boundary, evidence_health, answer_boundary),
        },
        "evidence_health": evidence_health,
        "answer_boundary": answer_boundary,
        "risk_flags": risk_flags,
        "next_actions": next_actions,
        "user_path": user_path,
        "strategy_pack": build_recall_strategy_pack(retrieval, space_id=space_id),
        "diagnostic_trace": {
            "space_id": space_id,
            "provider": metadata.get("provider_used") or metadata.get("configured_provider") or "",
            "fallback_used": bool(metadata.get("fallback_used")),
            "fallback_error": str(metadata.get("provider_error") or ""),
            "retrieval": asdict(retrieval.diagnostics),
            "context_source_ids": [context.source_id for context in contexts],
            "graph_paths": retrieval.graph_paths[:8],
        },
    }


def build_trust_queue_decision_layers(
    items: list[dict[str, Any]],
    summary: dict[str, Any] | None = None,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a queue-level layer that tells the UI what the user should do first."""
    clean_items = [dict(item) for item in items]
    summary = summary or {}
    filters = filters or {}
    ranked = sorted(clean_items, key=_trust_queue_sort_key)
    lanes = _trust_priority_lanes(ranked)
    attention = _trust_attention_budget(ranked, summary, filters)
    session_script = _trust_session_script(ranked, lanes, attention)
    batch_candidates = _trust_batch_candidates(ranked)
    route_map = _trust_route_map(lanes, ranked)
    return {
        "attention_budget": attention,
        "priority_lanes": lanes,
        "batch_candidates": batch_candidates,
        "session_script": session_script,
        "decision_routes": route_map,
        "workflow_pack": build_trust_workflow_pack(clean_items, filters=filters),
        "filters_echo": {
            "risk": str(filters.get("risk") or ""),
            "status": str(filters.get("status") or ""),
            "space_id": str(filters.get("space_id") or ""),
            "q": str(filters.get("q") or ""),
            "inferred": str(filters.get("inferred") or ""),
            "has_open_loops": filters.get("has_open_loops"),
        },
        "summary": {
            "total": int(summary.get("total") or len(clean_items)),
            "visible_now": attention["default_visible_items"],
            "hidden_by_default": max(0, len(clean_items) - attention["default_visible_items"]),
            "first_lane": lanes[0]["id"] if lanes else "empty",
            "quiet_copy": _trust_queue_quiet_copy(ranked, lanes),
        },
    }


def build_trust_detail_decision_layers(detail: dict[str, Any]) -> dict[str, Any]:
    """Build a detail-level layer around one trust item."""
    item = dict(detail.get("item") or {})
    analysis = dict(detail.get("analysis") or {})
    paths = list(detail.get("evidence_paths") or [])
    history = list(detail.get("history") or [])
    loops = list(detail.get("open_loops") or [])
    recommended = _trust_detail_recommended_action(item, analysis, paths, history, loops)
    return {
        "decision_header": {
            "source_id": item.get("source_id", ""),
            "title": item.get("title", ""),
            "risk_level": item.get("risk_level", "low"),
            "review_status": item.get("review_status", "unreviewed"),
            "why_saved_status": item.get("why_saved_status", "unknown"),
            "recommended_action": recommended,
            "one_sentence": _trust_detail_one_sentence(item, recommended),
        },
        "review_ladder": _trust_detail_review_ladder(item, analysis, paths, history, loops),
        "rewrite_guardrails": _trust_rewrite_guardrails(item, analysis, paths),
        "impact_preview": _trust_detail_impact_preview(item, analysis, loops),
        "decision_buttons": _trust_detail_decision_buttons(item, recommended),
        "collapsed_depth": _trust_detail_collapsed_depth(item, analysis, paths, history, loops),
    }


def build_collect_decision_layers(
    result: IngestResult,
    *,
    source_detail: dict[str, Any] | None = None,
    routing_suggestion: dict[str, Any] | None = None,
    route_mode: str = "auto",
    provider_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build an ingest receipt layer without changing ingestion semantics."""
    source_detail = source_detail or {}
    metadata = provider_metadata or {}
    routing = _collect_routing(result, routing_suggestion, route_mode)
    quality = _collect_quality(result, source_detail, metadata)
    traceability = _collect_traceability(result, source_detail)
    next_actions = _collect_next_actions(result, routing, quality, traceability)
    return {
        "capture_quality": quality,
        "routing": routing,
        "traceability": traceability,
        "next_actions": next_actions,
        "quality_pack": build_collect_quality_pack(
            result,
            route_mode=route_mode,
            routing_suggestion=routing_suggestion,
            provider_metadata=metadata,
        ),
        "receipt_policy": {
            "default_visible_items": 3,
            "collapse_details": True,
            "reason": "Keep the receipt short while preserving source traceability.",
            "show_to_user": ["title", "space", "why_saved_boundary", "next_action"],
            "hide_by_default": ["raw_path", "provider", "routing_alternatives"],
        },
    }


def _recall_boundary(contexts: list[RetrievedContext], metadata: dict[str, Any]) -> str:
    if not contexts:
        return "unsupported"
    user_count = sum(1 for context in contexts if context.why_saved_status in {"user-stated", "user-guided"})
    ai_count = sum(1 for context in contexts if context.why_saved_status == "AI-inferred")
    if user_count and ai_count:
        return "mixed"
    if user_count:
        return "user_supported"
    if ai_count:
        return "ai_inferred"
    if metadata.get("fallback_used"):
        return "fallback"
    return "source_supported"


def _recall_evidence_health(retrieval: RetrievalResult) -> dict[str, Any]:
    contexts = retrieval.contexts
    local_count = len(contexts)
    graph_count = len(retrieval.graph_paths)
    user_count = sum(1 for context in contexts if context.why_saved_status in {"user-stated", "user-guided"})
    ai_count = sum(1 for context in contexts if context.why_saved_status == "AI-inferred")
    pinned_count = retrieval.diagnostics.pinned_contexts
    if not local_count:
        status = "needs_collection"
    elif user_count and graph_count:
        status = "strong"
    elif local_count and graph_count:
        status = "usable"
    else:
        status = "thin"
    return {
        "status": status,
        "local_evidence_count": local_count,
        "graph_path_count": graph_count,
        "user_stated_count": user_count,
        "ai_inferred_count": ai_count,
        "pinned_context_count": pinned_count,
        "source_page_count": retrieval.diagnostics.source_pages_used,
        "keyword_hits": retrieval.diagnostics.keyword_hits,
        "graph_node_hits": retrieval.diagnostics.graph_node_hits,
        "expanded_nodes": retrieval.diagnostics.expanded_nodes,
        "truncated": retrieval.diagnostics.graph_expansion_truncated,
        "headline": _recall_evidence_headline(status, local_count, graph_count, user_count, ai_count),
    }


def _recall_answer_boundary(contexts: list[RetrievedContext], metadata: dict[str, Any]) -> dict[str, Any]:
    user_contexts = [
        context for context in contexts
        if context.why_saved_status in {"user-stated", "user-guided"}
    ]
    ai_contexts = [context for context in contexts if context.why_saved_status == "AI-inferred"]
    unknown_contexts = [
        context for context in contexts
        if context.why_saved_status not in {"user-stated", "user-guided", "AI-inferred"}
    ]
    return {
        "user_stated_count": len(user_contexts),
        "ai_inferred_count": len(ai_contexts),
        "unknown_count": len(unknown_contexts),
        "provider_fallback": bool(metadata.get("fallback_used")),
        "provider_error": str(metadata.get("provider_error") or ""),
        "trusted_source_ids": [context.source_id for context in user_contexts],
        "needs_review_source_ids": [context.source_id for context in ai_contexts + unknown_contexts],
        "plain_language": _boundary_plain_language(user_contexts, ai_contexts, unknown_contexts, metadata),
    }


def _recall_risk_flags(retrieval: RetrievalResult, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    if not retrieval.contexts:
        flags.append({
            "id": "no_local_evidence",
            "severity": "high",
            "label": "No local evidence",
            "detail": "The answer should not be treated as recovered memory until a source is saved.",
        })
    if retrieval.diagnostics.ai_inferred_contexts:
        flags.append({
            "id": "ai_inferred_contexts",
            "severity": "medium",
            "label": "AI-inferred context",
            "detail": f"{retrieval.diagnostics.ai_inferred_contexts} context item(s) need user confirmation.",
        })
    if retrieval.contexts and not retrieval.graph_paths:
        flags.append({
            "id": "missing_graph_path",
            "severity": "medium",
            "label": "No visible graph path",
            "detail": "Sources were found, but the answer has no visible evidence path.",
        })
    if retrieval.diagnostics.graph_expansion_truncated:
        flags.append({
            "id": "truncated_graph",
            "severity": "medium",
            "label": "Graph expansion truncated",
            "detail": "Nearby evidence may be missing because graph expansion stopped early.",
        })
    if metadata.get("fallback_used"):
        flags.append({
            "id": "provider_fallback",
            "severity": "medium",
            "label": "Provider fallback",
            "detail": str(metadata.get("provider_error") or "The configured provider was not used."),
        })
    return flags


def _recall_next_actions(
    retrieval: RetrievalResult,
    metadata: dict[str, Any],
    space_id: str,
) -> list[dict[str, Any]]:
    if not retrieval.contexts:
        return [
            {
                "id": "collect_evidence",
                "kind": "collect_evidence",
                "label": "Collect supporting material",
                "priority": 1,
                "source_id": "",
                "space_id": space_id,
                "detail": "Save a source or ask with a more specific old project name.",
            },
            {
                "id": "narrow_question",
                "kind": "ask_again",
                "label": "Narrow the question",
                "priority": 2,
                "source_id": "",
                "space_id": space_id,
                "detail": "Use a concrete file, project, person, decision, or saved reason.",
            },
        ]
    actions: list[dict[str, Any]] = []
    primary = retrieval.contexts[0]
    actions.append({
        "id": "open_primary_source",
        "kind": "open_source",
        "label": "Open strongest source",
        "priority": 1,
        "source_id": primary.source_id,
        "space_id": primary.graph_space_id or space_id,
        "detail": f"Start with {primary.title}.",
    })
    ai_context = next((context for context in retrieval.contexts if context.why_saved_status == "AI-inferred"), None)
    if ai_context:
        actions.append({
            "id": "review_ai_inference",
            "kind": "review_ai_inference",
            "label": "Review AI-inferred reason",
            "priority": 2,
            "source_id": ai_context.source_id,
            "space_id": ai_context.graph_space_id or space_id,
            "detail": f"Confirm whether {ai_context.title} reflects the user intent.",
        })
    open_loop = _first_open_loop(retrieval.contexts)
    if open_loop:
        actions.append({
            "id": "continue_open_loop",
            "kind": "continue_open_loop",
            "label": "Continue unresolved question",
            "priority": 3,
            "source_id": primary.source_id,
            "space_id": primary.graph_space_id or space_id,
            "detail": _compact_text(open_loop, 140),
        })
    if metadata.get("fallback_used"):
        actions.append({
            "id": "check_provider",
            "kind": "check_provider",
            "label": "Check provider",
            "priority": 4,
            "source_id": "",
            "space_id": space_id,
            "detail": "The model provider fell back; local evidence is still preserved.",
        })
    return sorted(actions, key=lambda item: item["priority"])


def _recall_user_path(
    retrieval: RetrievalResult,
    evidence_health: dict[str, Any],
    answer_boundary: dict[str, Any],
    next_actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    has_evidence = bool(retrieval.contexts)
    has_review = bool(answer_boundary["needs_review_source_ids"])
    has_next = bool(next_actions)
    current = "collect" if not has_evidence else "review" if has_review else "act"
    return [
        {
            "id": "collect",
            "label": "Recover evidence",
            "complete": has_evidence,
            "current": current == "collect",
            "detail": evidence_health["headline"],
        },
        {
            "id": "review",
            "label": "Check boundary",
            "complete": has_evidence and not has_review,
            "current": current == "review",
            "detail": answer_boundary["plain_language"],
        },
        {
            "id": "act",
            "label": "Take next step",
            "complete": False,
            "current": current == "act",
            "detail": next_actions[0]["detail"] if has_next else "No action available yet.",
        },
    ]


def _recall_confidence_label(
    evidence_health: dict[str, Any],
    answer_boundary: dict[str, Any],
    metadata: dict[str, Any],
) -> str:
    if evidence_health["status"] == "needs_collection":
        return "unsupported"
    if metadata.get("fallback_used"):
        return "local_only"
    if answer_boundary["user_stated_count"] and evidence_health["graph_path_count"]:
        return "strong"
    if answer_boundary["ai_inferred_count"]:
        return "review_first"
    return "mixed"


def _recall_quiet_copy(
    boundary: str,
    evidence_health: dict[str, Any],
    answer_boundary: dict[str, Any],
) -> str:
    if boundary == "unsupported":
        return "No local source is strong enough yet; collect or narrow the question first."
    if answer_boundary["ai_inferred_count"]:
        return "The answer has evidence, but at least one saved reason is AI-inferred."
    if evidence_health["status"] == "strong":
        return "The answer is anchored by user-stated evidence and visible graph paths."
    return "Use the result, but keep evidence details available behind expansion."


def _recall_evidence_headline(status: str, local_count: int, graph_count: int, user_count: int, ai_count: int) -> str:
    if status == "needs_collection":
        return "No local evidence found."
    if status == "strong":
        return f"{local_count} source(s), {graph_count} graph path(s), {user_count} user-stated anchor(s)."
    if ai_count:
        return f"{local_count} source(s) found; {ai_count} AI-inferred reason(s) need review."
    return f"{local_count} source(s) found; graph support is still thin."


def _boundary_plain_language(
    user_contexts: list[RetrievedContext],
    ai_contexts: list[RetrievedContext],
    unknown_contexts: list[RetrievedContext],
    metadata: dict[str, Any],
) -> str:
    if not user_contexts and not ai_contexts and not unknown_contexts:
        return "No saved source currently supports this answer."
    if user_contexts and not ai_contexts and not unknown_contexts:
        return "The answer is anchored by user-stated saved reasons."
    if ai_contexts and not user_contexts:
        return "The answer depends on AI-inferred saved reasons; ask the user before trusting it."
    if unknown_contexts:
        return "Some source boundaries are unknown and should stay visible."
    if metadata.get("fallback_used"):
        return "The model fallback changed generation, but source boundaries remain traceable."
    return "The answer mixes user-stated evidence with AI-inferred context."


def _first_open_loop(contexts: Iterable[RetrievedContext]) -> str:
    for context in contexts:
        for loop in context.open_loops:
            if loop and loop != "None":
                return loop
    return ""


def _trust_queue_sort_key(item: dict[str, Any]) -> tuple[int, int, int, float, str]:
    risk = RISK_ORDER.get(str(item.get("risk_level") or "low"), 9)
    status = STATUS_ORDER.get(str(item.get("review_status") or "unreviewed"), 9)
    boundary = BOUNDARY_ORDER.get(str(item.get("why_saved_status") or "unknown"), 9)
    confidence = -float(item.get("confidence") or 0)
    return (risk, status, boundary, confidence, str(item.get("title") or ""))


def _trust_priority_lanes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lane_specs = [
        ("must_review", "Must review", lambda item: item.get("risk_level") in {"critical", "high"} and item.get("review_status") in {"unreviewed", "deferred"}),
        ("ai_boundary", "AI-inferred boundary", lambda item: item.get("why_saved_status") == "AI-inferred" and item.get("review_status") not in {"confirmed", "rewritten", "rejected"}),
        ("open_loops", "Open loops", lambda item: bool(item.get("has_open_loops") or item.get("open_loops"))),
        ("safe_batch", "Safe batch", lambda item: _is_safe_batch_item(item)),
        ("archive", "Already decided", lambda item: item.get("review_status") in {"confirmed", "rewritten", "rejected"}),
    ]
    lanes: list[dict[str, Any]] = []
    assigned: set[str] = set()
    for lane_id, label, predicate in lane_specs:
        lane_items = []
        for item in items:
            source_id = str(item.get("source_id") or "")
            if source_id in assigned:
                continue
            if predicate(item):
                lane_items.append(item)
                assigned.add(source_id)
        lanes.append({
            "id": lane_id,
            "label": label,
            "count": len(lane_items),
            "source_ids": [str(item.get("source_id") or "") for item in lane_items],
            "headline": _lane_headline(lane_id, len(lane_items)),
            "collapsed": lane_id not in {"must_review", "ai_boundary"},
        })
    return lanes


def _trust_attention_budget(
    items: list[dict[str, Any]],
    summary: dict[str, Any],
    filters: dict[str, Any],
) -> dict[str, Any]:
    high_pressure = sum(1 for item in items if item.get("risk_level") in {"critical", "high"})
    query_active = bool(str(filters.get("q") or "").strip())
    filtered = any(
        filters.get(key) not in ("", None)
        for key in ["risk", "status", "space_id", "inferred", "has_open_loops"]
    )
    default_visible = 6 if query_active or filtered else 4
    if high_pressure >= 6:
        default_visible = 3
    return {
        "default_visible_items": min(default_visible, len(items)),
        "max_microcopy_chars": 96,
        "collapse_evidence_by_default": True,
        "collapse_resolved_by_default": True,
        "show_filter_summary": filtered or query_active,
        "pressure_level": "high" if high_pressure >= 3 else "medium" if items else "empty",
        "reason": _attention_reason(items, high_pressure, query_active, filtered),
        "summary_total": int(summary.get("total") or len(items)),
    }


def _trust_session_script(
    items: list[dict[str, Any]],
    lanes: list[dict[str, Any]],
    attention: dict[str, Any],
) -> list[dict[str, Any]]:
    first = items[0] if items else None
    script = [
        {
            "id": "orient",
            "label": "Orient",
            "complete": bool(items),
            "current": bool(items),
            "instruction": "Start with the smallest set of trust decisions.",
        },
        {
            "id": "decide",
            "label": "Decide",
            "complete": False,
            "current": bool(first),
            "instruction": _session_decide_instruction(first),
        },
        {
            "id": "compress",
            "label": "Compress",
            "complete": attention["collapse_evidence_by_default"],
            "current": False,
            "instruction": "Keep evidence collapsed unless the decision is unclear.",
        },
    ]
    if lanes and lanes[0]["count"] == 0:
        script[0]["instruction"] = "No urgent trust decision is visible in the current filter."
    return script


def _trust_batch_candidates(items: list[dict[str, Any]]) -> dict[str, Any]:
    safe = [item for item in items if _is_safe_batch_item(item)]
    needs_single = [item for item in items if not _is_safe_batch_item(item)]
    return {
        "safe_to_batch_source_ids": [str(item.get("source_id") or "") for item in safe],
        "needs_single_review_source_ids": [str(item.get("source_id") or "") for item in needs_single[:8]],
        "recommended_batch_action": "confirmed" if safe else "",
        "reason": "Low-risk confirmed or user-stated items can be handled together." if safe else "No safe batch group is available.",
    }


def _trust_route_map(lanes: list[dict[str, Any]], items: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(item.get("source_id") or ""): item for item in items}
    next_routes = []
    for lane in lanes:
        for source_id in lane["source_ids"][:3]:
            item = by_id.get(source_id, {})
            next_routes.append({
                "lane": lane["id"],
                "source_id": source_id,
                "title": item.get("title", ""),
                "action": _route_action_for_lane(lane["id"], item),
            })
    return {
        "next_routes": next_routes[:8],
        "empty_route": "Collect more material or clear filters." if not next_routes else "",
    }


def _trust_queue_quiet_copy(items: list[dict[str, Any]], lanes: list[dict[str, Any]]) -> str:
    if not items:
        return "No trust items match the current filter."
    first_lane = lanes[0] if lanes else {"count": 0}
    if first_lane["count"]:
        return "Start with the first lane, keep details collapsed, and make one trust decision at a time."
    return "The urgent lane is empty; use filters or batch handling to reduce queue pressure."


def _is_safe_batch_item(item: dict[str, Any]) -> bool:
    if item.get("risk_level") in {"critical", "high"}:
        return False
    if item.get("why_saved_status") == "AI-inferred" and item.get("review_status") == "unreviewed":
        return False
    if item.get("has_open_loops") or item.get("open_loops"):
        return False
    return True


def _lane_headline(lane_id: str, count: int) -> str:
    if lane_id == "must_review":
        return f"{count} high-risk item(s) need a focused decision."
    if lane_id == "ai_boundary":
        return f"{count} AI-inferred reason(s) need boundary checks."
    if lane_id == "open_loops":
        return f"{count} item(s) still carry unresolved questions."
    if lane_id == "safe_batch":
        return f"{count} item(s) can stay quiet or be handled together."
    return f"{count} item(s) already have decisions."


def _attention_reason(items: list[dict[str, Any]], high_pressure: int, query_active: bool, filtered: bool) -> str:
    if not items:
        return "No queue items match the current view."
    if high_pressure >= 6:
        return "Many high-risk items exist, so the default view should show fewer cards."
    if query_active or filtered:
        return "The user is searching or filtering, so a slightly larger result set is acceptable."
    return "Default view should keep the queue short and decision-oriented."


def _session_decide_instruction(item: dict[str, Any] | None) -> str:
    if not item:
        return "There is no item to decide in this view."
    if item.get("why_saved_status") == "AI-inferred":
        return "Check whether the saved reason came from the user or from the model."
    if item.get("has_open_loops"):
        return "Resolve or preserve the open loop before treating the source as stable."
    if item.get("risk_level") in {"critical", "high"}:
        return "Confirm evidence before allowing this source to influence future answers."
    return "Confirm, rewrite, reject, or defer without expanding unnecessary details."


def _route_action_for_lane(lane_id: str, item: dict[str, Any]) -> str:
    if lane_id == "must_review":
        return "open_detail"
    if lane_id == "ai_boundary":
        return "review_ai_reason"
    if lane_id == "open_loops":
        return "triage_loop"
    if lane_id == "safe_batch":
        return "batch_confirm"
    if item.get("review_status") == "rejected":
        return "keep_rejected"
    return "collapse"


def _trust_detail_recommended_action(
    item: dict[str, Any],
    analysis: dict[str, Any],
    paths: list[dict[str, Any]],
    history: list[dict[str, Any]],
    loops: list[dict[str, Any]],
) -> str:
    if item.get("review_status") == "rejected":
        return "keep_rejected"
    if item.get("why_saved_status") == "AI-inferred" and item.get("risk_level") in {"critical", "high"}:
        return "review"
    if item.get("why_saved_status") == "AI-inferred":
        return "rewrite"
    if loops or item.get("open_loops"):
        return "defer"
    trust_score = (analysis.get("trust_score") or {}).get("score")
    if isinstance(trust_score, (int, float)) and trust_score >= 70 and paths:
        return "confirm"
    if history:
        return "review_history"
    return "review"


def _trust_detail_one_sentence(item: dict[str, Any], recommended: str) -> str:
    title = item.get("title") or "This source"
    if recommended == "review":
        return f"{title} should be reviewed before future recall reuses it."
    if recommended == "rewrite":
        return f"{title} needs a user-stated reason before it becomes trusted."
    if recommended == "defer":
        return f"{title} still carries open work; defer or mark the next step."
    if recommended == "confirm":
        return f"{title} has enough support for a quick confirmation."
    if recommended == "keep_rejected":
        return f"{title} is rejected and should stay out of trusted recall."
    return f"{title} needs a small trust decision."


def _trust_detail_review_ladder(
    item: dict[str, Any],
    analysis: dict[str, Any],
    paths: list[dict[str, Any]],
    history: list[dict[str, Any]],
    loops: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reason_complete = bool(str(item.get("why_saved") or "").strip())
    evidence_complete = bool(paths or item.get("evidence_count"))
    boundary_complete = item.get("why_saved_status") in {"user-stated", "user-guided"}
    decision_complete = item.get("review_status") in {"confirmed", "rewritten", "rejected"}
    loop_complete = not (loops or item.get("open_loops"))
    ladder = [
        {
            "id": "read_reason",
            "label": "Read saved reason",
            "complete": reason_complete,
            "current": not reason_complete,
            "detail": _compact_text(str(item.get("why_saved") or "No saved reason yet."), 140),
        },
        {
            "id": "check_evidence",
            "label": "Check evidence path",
            "complete": evidence_complete,
            "current": reason_complete and not evidence_complete,
            "detail": _evidence_detail_copy(analysis, paths),
        },
        {
            "id": "confirm_boundary",
            "label": "Confirm boundary",
            "complete": boundary_complete,
            "current": reason_complete and evidence_complete and not boundary_complete,
            "detail": _boundary_detail_copy(item),
        },
        {
            "id": "handle_loops",
            "label": "Handle open loops",
            "complete": loop_complete,
            "current": reason_complete and evidence_complete and boundary_complete and not loop_complete,
            "detail": _loop_detail_copy(item, loops),
        },
        {
            "id": "record_decision",
            "label": "Record decision",
            "complete": decision_complete,
            "current": reason_complete and evidence_complete and boundary_complete and loop_complete and not decision_complete,
            "detail": f"Current status is {item.get('review_status', 'unreviewed')}.",
        },
    ]
    if not any(step["current"] for step in ladder):
        for step in ladder:
            if not step["complete"]:
                step["current"] = True
                break
    return ladder


def _trust_rewrite_guardrails(
    item: dict[str, Any],
    analysis: dict[str, Any],
    paths: list[dict[str, Any]],
) -> dict[str, Any]:
    should_rewrite = item.get("why_saved_status") == "AI-inferred" or not str(item.get("why_saved") or "").strip()
    must_keep = []
    if paths:
        must_keep.append("Keep source traceability and evidence path references.")
    if item.get("open_loops"):
        must_keep.append("Do not hide unresolved open loops in the rewrite.")
    if item.get("review_status") == "rejected":
        must_keep.append("Do not rewrite rejected context back into trusted memory without user action.")
    return {
        "should_rewrite": should_rewrite,
        "rewrite_prompt": _rewrite_prompt(item),
        "must_keep": must_keep or ["Keep the original source title and source id traceable."],
        "must_avoid": [
            "Do not claim to know the user's intention unless the user wrote it.",
            "Do not remove uncertainty from AI-inferred reasons.",
            "Do not turn weak evidence into a strong conclusion.",
        ],
        "suggested_status_after_rewrite": "rewritten" if should_rewrite else item.get("review_status", "confirmed"),
    }


def _trust_detail_impact_preview(
    item: dict[str, Any],
    analysis: dict[str, Any],
    loops: list[dict[str, Any]],
) -> dict[str, Any]:
    questions = item.get("future_recall_questions") or []
    score = (analysis.get("trust_score") or {}).get("score", 0)
    return {
        "future_recall": [
            {
                "question": question,
                "impact": "Future answers may use this decision as trust context.",
            }
            for question in questions[:4]
        ] or [{"question": "", "impact": "No explicit future recall question is attached."}],
        "open_loops": [
            {
                "loop_id": loop.get("loop_id", ""),
                "state": loop.get("state", "active"),
                "impact": "This loop remains visible until resolved or dismissed.",
            }
            for loop in loops[:4]
        ],
        "answer_quality": {
            "trust_score": score,
            "impact": "Higher trust score lets recall use this source with less explanation.",
        },
        "graph": {
            "evidence_count": int(item.get("evidence_count") or 0),
            "impact": "Graph traceability stays attached regardless of the review action.",
        },
    }


def _trust_detail_decision_buttons(item: dict[str, Any], recommended: str) -> list[dict[str, Any]]:
    actions = [
        ("confirmed", "Confirm", "Use this reason as trusted context."),
        ("rewritten", "Rewrite", "Replace AI-inferred text with user-stated wording."),
        ("rejected", "Reject", "Prevent this reason from shaping future answers."),
        ("deferred", "Defer", "Keep it visible for a later review session."),
    ]
    return [
        {
            "action": action,
            "label": label,
            "detail": detail,
            "recommended": _button_is_recommended(action, recommended),
            "requires_note": action in {"rewritten", "rejected", "deferred"},
        }
        for action, label, detail in actions
    ]


def _trust_detail_collapsed_depth(
    item: dict[str, Any],
    analysis: dict[str, Any],
    paths: list[dict[str, Any]],
    history: list[dict[str, Any]],
    loops: list[dict[str, Any]],
) -> dict[str, Any]:
    depth_count = len(paths) + len(history) + len(loops)
    if analysis.get("hidden_depth_count"):
        depth_count += int(analysis.get("hidden_depth_count") or 0)
    return {
        "hidden_item_count": depth_count,
        "default_collapsed": True,
        "expand_label": f"Show {depth_count} trace detail(s)" if depth_count else "Show trace details",
        "reason": "The detail panel should lead with the decision, not every trace record.",
    }


def _evidence_detail_copy(analysis: dict[str, Any], paths: list[dict[str, Any]]) -> str:
    evidence = analysis.get("evidence_compression") or {}
    if evidence.get("summary"):
        return str(evidence["summary"])
    if paths:
        return f"{len(paths)} evidence path(s) are available."
    return "No evidence path is attached yet."


def _boundary_detail_copy(item: dict[str, Any]) -> str:
    status = item.get("why_saved_status", "unknown")
    if status in {"user-stated", "user-guided"}:
        return "The saved reason is user-stated."
    if status == "AI-inferred":
        return "The saved reason is AI-inferred and should be confirmed or rewritten."
    return "The saved reason boundary is unknown."


def _loop_detail_copy(item: dict[str, Any], loops: list[dict[str, Any]]) -> str:
    loop_count = len(loops) if loops else len(item.get("open_loops") or [])
    if loop_count:
        return f"{loop_count} open loop(s) remain connected."
    return "No open loop remains connected."


def _rewrite_prompt(item: dict[str, Any]) -> str:
    title = item.get("title") or "this source"
    if item.get("why_saved_status") == "AI-inferred":
        return f"Rewrite the saved reason for {title} in the user's own confirmed wording."
    return f"Only rewrite {title} if the user wants a clearer saved reason."


def _button_is_recommended(action: str, recommended: str) -> bool:
    return (
        action == "confirmed" and recommended == "confirm"
        or action == "rewritten" and recommended == "rewrite"
        or action == "rejected" and recommended == "keep_rejected"
        or action == "deferred" and recommended == "defer"
        or action == "deferred" and recommended == "review_history"
    )


def _collect_quality(
    result: IngestResult,
    source_detail: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    context = result.cognitive_context
    source = result.source
    has_reason = bool(str(context.why_saved or "").strip())
    has_summary = bool(str(source.summary or source_detail.get("summary") or "").strip())
    has_open_loop = bool(context.open_loops)
    score = 40
    if has_reason:
        score += 20
    if context.why_saved_status in {"user-stated", "user-guided"}:
        score += 20
    if has_summary:
        score += 10
    if context.future_recall_questions:
        score += 5
    if has_open_loop:
        score += 5
    if result.deduplicated:
        score -= 15
    if metadata.get("fallback_used"):
        score -= 10
    score = max(0, min(100, score))
    return {
        "source_id": source.id,
        "title": source_detail.get("title", source.title),
        "source_type": source_detail.get("type", source.type),
        "quality_score": score,
        "quality_label": _quality_label(score),
        "why_saved_boundary": context.why_saved_status,
        "has_user_reason": context.why_saved_status in {"user-stated", "user-guided"},
        "has_summary": has_summary,
        "has_open_loop": has_open_loop,
        "future_question_count": len(context.future_recall_questions),
        "deduplicated": result.deduplicated,
        "provider_fallback": bool(metadata.get("fallback_used")),
        "quiet_copy": _collect_quality_copy(score, context.why_saved_status, result.deduplicated),
    }


def _collect_routing(
    result: IngestResult,
    routing_suggestion: dict[str, Any] | None,
    route_mode: str,
) -> dict[str, Any]:
    payload = (routing_suggestion or {}).get("payload") or {}
    alternatives = payload.get("alternatives") or []
    suggested_space_id = payload.get("target_space_id") or result.source.graph_space_id
    suggested_space_name = payload.get("target_space_name") or ""
    confidence = float((routing_suggestion or {}).get("confidence") or 0)
    status = str((routing_suggestion or {}).get("status") or "none")
    return {
        "route_mode": route_mode,
        "current_space_id": result.source.graph_space_id,
        "suggestion_id": result.routing_suggestion_id or "",
        "suggestion_status": status,
        "suggested_space_id": suggested_space_id,
        "suggested_space_name": suggested_space_name,
        "confidence": confidence,
        "confidence_label": _routing_confidence_label(confidence, status),
        "reason": str((routing_suggestion or {}).get("reason") or ""),
        "alternatives": alternatives[:4],
        "needs_user_choice": route_mode == "auto" and status == "pending" and confidence < 0.72,
    }


def _collect_traceability(result: IngestResult, source_detail: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": result.source.id,
        "raw_path": str(result.raw_path),
        "workspace_raw_path": result.source.path,
        "wiki_page": result.page.relative_page_path,
        "content_hash": result.source.content_hash,
        "original_filename": result.source.original_filename,
        "graph_space_id": source_detail.get("graph_space_id", result.source.graph_space_id),
        "space_name": source_detail.get("space_name", ""),
        "warnings": list(result.warnings),
        "trace_status": "deduplicated" if result.deduplicated else "captured",
    }


def _collect_next_actions(
    result: IngestResult,
    routing: dict[str, Any],
    quality: dict[str, Any],
    traceability: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if quality["why_saved_boundary"] == "AI-inferred":
        actions.append({
            "id": "review_reason",
            "kind": "review_reason",
            "label": "Review saved reason",
            "priority": 1,
            "detail": "The saved reason is AI-inferred and should be confirmed later.",
        })
    if routing["suggestion_id"] and routing["suggestion_status"] == "pending":
        actions.append({
            "id": "accept_route",
            "kind": "accept_route",
            "label": "Accept route suggestion",
            "priority": 2,
            "detail": f"Suggested space: {routing['suggested_space_name'] or routing['suggested_space_id']}.",
        })
    if result.deduplicated:
        actions.append({
            "id": "open_existing",
            "kind": "open_existing",
            "label": "Open existing source",
            "priority": 3,
            "detail": "This exact content already existed and was reused.",
        })
    actions.append({
        "id": "ask_from_source",
        "kind": "ask_from_source",
        "label": "Ask from this source",
        "priority": 4,
        "detail": f"Use {traceability['wiki_page']} as a focused context source.",
    })
    return sorted(actions, key=lambda item: item["priority"])


def _quality_label(score: int) -> str:
    if score >= 85:
        return "strong"
    if score >= 70:
        return "usable"
    if score >= 50:
        return "thin"
    return "needs_review"


def _collect_quality_copy(score: int, boundary: str, deduplicated: bool) -> str:
    if deduplicated:
        return "This capture reused an existing source; no duplicate memory was created."
    if boundary == "AI-inferred":
        return "The material was saved, but the reason is model-inferred."
    if score >= 85:
        return "The capture has a clear reason, summary, and future recall path."
    if score >= 70:
        return "The capture is usable and keeps traceability intact."
    return "The capture is preserved, but a user-stated reason would make it stronger."


def _routing_confidence_label(confidence: float, status: str) -> str:
    if status == "accepted":
        return "accepted"
    if status == "rejected":
        return "rejected"
    if confidence >= 0.75:
        return "strong"
    if confidence >= 0.55:
        return "medium"
    if confidence > 0:
        return "weak"
    return "none"


def _compact_text(value: str, limit: int) -> str:
    cleaned = " ".join(str(value or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."
