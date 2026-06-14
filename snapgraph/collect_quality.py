from __future__ import annotations

from typing import Any

from .models import IngestResult


def build_collect_quality_pack(
    result: IngestResult,
    *,
    route_mode: str,
    routing_suggestion: dict[str, Any] | None = None,
    provider_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build backend-only quality diagnostics for a newly captured source."""
    metadata = provider_metadata or {}
    capture = _capture_audit(result, metadata)
    routing = _routing_audit(result, route_mode, routing_suggestion)
    traceability = _traceability_audit(result)
    repair_plan = _repair_plan(result, capture, routing, traceability)
    return {
        "capture_audit": capture,
        "routing_audit": routing,
        "traceability_audit": traceability,
        "repair_plan": repair_plan,
        "receipt_contract": _receipt_contract(capture, routing, traceability),
    }


def _capture_audit(result: IngestResult, metadata: dict[str, Any]) -> dict[str, Any]:
    source = result.source
    context = result.cognitive_context
    boundary = context.why_saved_status
    reason = str(context.why_saved or "").strip()
    summary = str(source.summary or "").strip()
    score_parts = {
        "has_title": 10 if bool(source.title.strip()) else 0,
        "has_summary": 15 if bool(summary) else 0,
        "has_reason": 20 if bool(reason) else 0,
        "user_stated_reason": 20 if boundary in {"user-stated", "user-guided"} else 0,
        "future_recall": min(len(context.future_recall_questions), 3) * 5,
        "open_loop": 5 if context.open_loops else 0,
        "confidence": int(float(context.confidence or 0) * 20),
        "dedupe_penalty": -20 if result.deduplicated else 0,
        "fallback_penalty": -10 if metadata.get("fallback_used") else 0,
    }
    score = max(0, min(100, sum(score_parts.values())))
    return {
        "source_id": source.id,
        "title": source.title,
        "source_type": source.type,
        "boundary": boundary,
        "quality_score": score,
        "quality_label": _quality_label(score),
        "score_parts": score_parts,
        "has_user_reason": boundary in {"user-stated", "user-guided"},
        "has_ai_inferred_reason": boundary == "AI-inferred",
        "has_summary": bool(summary),
        "has_open_loops": bool(context.open_loops),
        "future_question_count": len(context.future_recall_questions),
        "confidence": float(context.confidence or 0),
        "deduplicated": result.deduplicated,
        "provider_used": metadata.get("provider_used") or metadata.get("configured_provider") or "",
        "provider_fallback": bool(metadata.get("fallback_used")),
        "plain_language": _capture_plain_language(boundary, score, result.deduplicated),
    }


def _routing_audit(
    result: IngestResult,
    route_mode: str,
    routing_suggestion: dict[str, Any] | None,
) -> dict[str, Any]:
    suggestion = routing_suggestion or {}
    payload = suggestion.get("payload") or {}
    confidence = float(suggestion.get("confidence") or 0)
    status = str(suggestion.get("status") or "none")
    target_id = payload.get("target_space_id") or result.source.graph_space_id
    target_name = payload.get("target_space_name") or ""
    alternatives = payload.get("alternatives") or []
    needs_user_choice = (
        route_mode == "auto"
        and status == "pending"
        and bool(result.routing_suggestion_id)
        and confidence < 0.72
    )
    return {
        "route_mode": route_mode,
        "current_space_id": result.source.graph_space_id,
        "suggestion_id": result.routing_suggestion_id or "",
        "suggestion_status": status,
        "target_space_id": target_id,
        "target_space_name": target_name,
        "confidence": confidence,
        "confidence_band": _confidence_band(confidence, status),
        "needs_user_choice": needs_user_choice,
        "reason": str(suggestion.get("reason") or ""),
        "alternatives": alternatives[:5],
        "auto_accept_candidate": route_mode == "auto" and confidence >= 0.72 and status == "pending",
        "plain_language": _routing_plain_language(route_mode, status, confidence, target_name or target_id),
    }


def _traceability_audit(result: IngestResult) -> dict[str, Any]:
    source = result.source
    raw_path = source.path
    wiki_page = result.page.relative_page_path
    warnings = list(result.warnings)
    anchors = [
        {"kind": "raw", "path": raw_path, "required": True},
        {"kind": "wiki", "path": wiki_page, "required": True},
        {"kind": "source_id", "path": source.id, "required": True},
        {"kind": "hash", "path": source.content_hash, "required": True},
    ]
    completeness = 100
    if not raw_path:
        completeness -= 25
    if not wiki_page:
        completeness -= 25
    if not source.content_hash:
        completeness -= 25
    if warnings:
        completeness -= min(len(warnings), 3) * 10
    if result.deduplicated:
        completeness -= 5
    completeness = max(0, completeness)
    return {
        "source_id": source.id,
        "raw_path": raw_path,
        "wiki_page": wiki_page,
        "content_hash": source.content_hash,
        "original_filename": source.original_filename,
        "trace_status": "deduplicated" if result.deduplicated else "captured",
        "anchors": anchors,
        "warnings": warnings,
        "completeness": completeness,
        "plain_language": _traceability_plain_language(completeness, warnings, result.deduplicated),
    }


def _repair_plan(
    result: IngestResult,
    capture: dict[str, Any],
    routing: dict[str, Any],
    traceability: dict[str, Any],
) -> list[dict[str, Any]]:
    plan = []
    if capture["boundary"] == "AI-inferred":
        plan.append(
            {
                "id": "confirm_reason",
                "action": "confirm_reason",
                "priority": 1,
                "label": "Confirm saved reason",
                "detail": "Ask the user to confirm or rewrite the AI-inferred saved reason.",
            }
        )
    if routing["needs_user_choice"]:
        plan.append(
            {
                "id": "accept_route",
                "action": "accept_route",
                "priority": 2,
                "label": "Accept or change route",
                "detail": f"Suggested target is {routing['target_space_name'] or routing['target_space_id']}.",
            }
        )
    if traceability["warnings"]:
        plan.append(
            {
                "id": "inspect_warnings",
                "action": "inspect_warnings",
                "priority": 3,
                "label": "Inspect capture warnings",
                "detail": traceability["warnings"][0],
            }
        )
    if result.deduplicated:
        plan.append(
            {
                "id": "open_existing",
                "action": "open_existing",
                "priority": 4,
                "label": "Open existing source",
                "detail": "The exact same content already existed.",
            }
        )
    plan.append(
        {
            "id": "ask_from_capture",
            "action": "ask_from_capture",
            "priority": 5,
            "label": "Ask from this capture",
            "detail": "Use the source id as context for a focused recall question.",
        }
    )
    return sorted(plan, key=lambda item: item["priority"])


def _receipt_contract(
    capture: dict[str, Any],
    routing: dict[str, Any],
    traceability: dict[str, Any],
) -> dict[str, Any]:
    return {
        "must_show": [
            "title",
            "space",
            "saved_reason_boundary",
            "primary_next_action",
        ],
        "can_collapse": [
            "raw_path",
            "content_hash",
            "routing_alternatives",
            "provider_metadata",
            "warnings",
        ],
        "summary": _receipt_summary(capture, routing, traceability),
        "default_collapsed": True,
    }


def _quality_label(score: int) -> str:
    if score >= 85:
        return "strong"
    if score >= 70:
        return "usable"
    if score >= 50:
        return "thin"
    return "needs_review"


def _confidence_band(confidence: float, status: str) -> str:
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


def _capture_plain_language(boundary: str, score: int, deduplicated: bool) -> str:
    if deduplicated:
        return "This capture reused an existing source and did not create duplicate memory."
    if boundary == "AI-inferred":
        return "The material is preserved, but the saved reason is still a model inference."
    if score >= 85:
        return "The capture has enough user context to be reused confidently."
    if score >= 70:
        return "The capture is usable and traceable."
    return "The capture needs a clearer saved reason or route before it becomes strong memory."


def _routing_plain_language(route_mode: str, status: str, confidence: float, target: str) -> str:
    if route_mode == "manual":
        return "The user chose the destination space."
    if status == "accepted":
        return f"The routing suggestion was accepted into {target}."
    if status == "pending" and confidence >= 0.72:
        return f"The system can confidently suggest {target}."
    if status == "pending":
        return f"The system suggests {target}, but the user should confirm."
    return "No route suggestion is active."


def _traceability_plain_language(completeness: int, warnings: list[str], deduplicated: bool) -> str:
    if deduplicated:
        return "Traceability points back to the existing source."
    if warnings:
        return "Traceability is preserved, but warnings should remain available."
    if completeness >= 95:
        return "Raw source, wiki page, id, and content hash are all preserved."
    return "Some traceability fields are thin and should stay inspectable."


def _receipt_summary(
    capture: dict[str, Any],
    routing: dict[str, Any],
    traceability: dict[str, Any],
) -> str:
    return (
        f"{capture['quality_label']} capture; "
        f"{routing['confidence_band']} routing; "
        f"{traceability['trace_status']} traceability."
    )
