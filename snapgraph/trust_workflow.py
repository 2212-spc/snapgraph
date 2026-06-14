from __future__ import annotations

from collections import Counter
from typing import Any


RISK_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
STATUS_RANK = {"unreviewed": 0, "deferred": 1, "rewritten": 2, "confirmed": 3, "rejected": 4}


def build_trust_workflow_pack(
    items: list[dict[str, Any]],
    *,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build backend workflow guidance for trust review without changing the UI."""
    filters = filters or {}
    ranked = sorted([dict(item) for item in items], key=_sort_key)
    lanes = _review_lanes(ranked)
    work_modes = _work_modes(ranked, lanes)
    decision_script = _decision_script(ranked, lanes, filters)
    bulk_plan = _bulk_plan(ranked)
    health = _queue_health(ranked, lanes, filters)
    return {
        "work_modes": work_modes,
        "review_lanes": lanes,
        "decision_script": decision_script,
        "bulk_plan": bulk_plan,
        "queue_health": health,
        "copy_contract": _copy_contract(health),
    }


def _work_modes(items: list[dict[str, Any]], lanes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = {lane["id"]: lane["count"] for lane in lanes}
    modes = [
        {
            "id": "focus",
            "label": "Focus review",
            "intent": "Handle the next risky decision first.",
            "count": counts.get("decision_required", 0),
            "recommended": counts.get("decision_required", 0) > 0,
        },
        {
            "id": "boundary",
            "label": "Boundary check",
            "intent": "Confirm AI-inferred saved reasons.",
            "count": counts.get("boundary_check", 0),
            "recommended": counts.get("decision_required", 0) == 0 and counts.get("boundary_check", 0) > 0,
        },
        {
            "id": "loops",
            "label": "Open-loop triage",
            "intent": "Turn unresolved questions into next steps or dismissals.",
            "count": counts.get("open_loop", 0),
            "recommended": counts.get("decision_required", 0) == 0 and counts.get("open_loop", 0) > 0,
        },
        {
            "id": "batch",
            "label": "Batch cleanup",
            "intent": "Quietly confirm or collapse low-risk material.",
            "count": counts.get("batch_safe", 0),
            "recommended": bool(items) and all(counts.get(key, 0) == 0 for key in ["decision_required", "boundary_check", "open_loop"]),
        },
    ]
    if not items:
        modes[0]["recommended"] = True
        modes[0]["intent"] = "No matching trust work in this filter."
    return modes


def _review_lanes(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    assigned: set[str] = set()
    specs = [
        (
            "decision_required",
            "Decision required",
            lambda item: item.get("risk_level") in {"critical", "high"} and item.get("review_status") in {"unreviewed", "deferred"},
        ),
        (
            "boundary_check",
            "AI boundary check",
            lambda item: item.get("why_saved_status") == "AI-inferred" and item.get("review_status") not in {"confirmed", "rewritten", "rejected"},
        ),
        (
            "open_loop",
            "Open-loop triage",
            lambda item: bool(item.get("has_open_loops") or item.get("open_loops")),
        ),
        (
            "batch_safe",
            "Batch-safe cleanup",
            _batch_safe,
        ),
        (
            "resolved",
            "Resolved or rejected",
            lambda item: item.get("review_status") in {"confirmed", "rewritten", "rejected"},
        ),
    ]
    lanes = []
    for lane_id, label, predicate in specs:
        lane_items = []
        for item in items:
            source_id = str(item.get("source_id") or "")
            if source_id in assigned:
                continue
            if predicate(item):
                lane_items.append(item)
                assigned.add(source_id)
        lanes.append(
            {
                "id": lane_id,
                "label": label,
                "count": len(lane_items),
                "source_ids": [str(item.get("source_id") or "") for item in lane_items],
                "recommended_visible": min(len(lane_items), 3 if lane_id == "decision_required" else 2),
                "default_collapsed": lane_id not in {"decision_required", "boundary_check"},
                "why_it_exists": _lane_reason(lane_id, len(lane_items)),
            }
        )
    return lanes


def _decision_script(
    items: list[dict[str, Any]],
    lanes: list[dict[str, Any]],
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    next_item = items[0] if items else None
    active_filter = any(value not in ("", None) for value in filters.values())
    return [
        {
            "step": "orient",
            "label": "Orient",
            "instruction": _orient_instruction(items, active_filter),
            "complete": bool(items),
            "current": bool(items),
        },
        {
            "step": "inspect_boundary",
            "label": "Check boundary",
            "instruction": _boundary_instruction(next_item),
            "complete": _boundary_complete(next_item),
            "current": bool(next_item) and not _boundary_complete(next_item),
        },
        {
            "step": "inspect_evidence",
            "label": "Check evidence",
            "instruction": _evidence_instruction(next_item),
            "complete": _evidence_complete(next_item),
            "current": bool(next_item) and _boundary_complete(next_item) and not _evidence_complete(next_item),
        },
        {
            "step": "decide",
            "label": "Decide",
            "instruction": _decision_instruction(next_item),
            "complete": _decision_complete(next_item),
            "current": bool(next_item) and _boundary_complete(next_item) and _evidence_complete(next_item) and not _decision_complete(next_item),
        },
        {
            "step": "collapse",
            "label": "Collapse detail",
            "instruction": "Keep report and diagnostics collapsed after the decision is clear.",
            "complete": True,
            "current": False,
        },
    ]


def _bulk_plan(items: list[dict[str, Any]]) -> dict[str, Any]:
    safe = [item for item in items if _batch_safe(item)]
    risky = [item for item in items if not _batch_safe(item)]
    action = "confirmed" if safe else ""
    return {
        "safe_source_ids": [str(item.get("source_id") or "") for item in safe],
        "excluded_source_ids": [str(item.get("source_id") or "") for item in risky[:10]],
        "recommended_action": action,
        "max_batch_size": min(12, len(safe)),
        "requires_note": False,
        "guardrail": _bulk_guardrail(safe, risky),
    }


def _queue_health(
    items: list[dict[str, Any]],
    lanes: list[dict[str, Any]],
    filters: dict[str, Any],
) -> dict[str, Any]:
    risk_counts = Counter(str(item.get("risk_level") or "low") for item in items)
    status_counts = Counter(str(item.get("review_status") or "unreviewed") for item in items)
    boundary_counts = Counter(str(item.get("why_saved_status") or "unknown") for item in items)
    high_pressure = risk_counts.get("critical", 0) + risk_counts.get("high", 0)
    ai_pressure = boundary_counts.get("AI-inferred", 0)
    loop_pressure = sum(1 for item in items if item.get("has_open_loops") or item.get("open_loops"))
    if not items:
        pressure = "empty"
    elif high_pressure >= 3 or ai_pressure >= 6:
        pressure = "high"
    elif high_pressure or ai_pressure or loop_pressure:
        pressure = "medium"
    else:
        pressure = "low"
    return {
        "total": len(items),
        "pressure": pressure,
        "risk_counts": dict(risk_counts),
        "status_counts": dict(status_counts),
        "boundary_counts": dict(boundary_counts),
        "active_filters": {key: value for key, value in filters.items() if value not in ("", None)},
        "visible_lane_count": sum(1 for lane in lanes if lane["count"]),
        "recommended_default_visible": _recommended_visible_count(pressure, len(items)),
        "summary": _queue_summary(pressure, high_pressure, ai_pressure, loop_pressure),
    }


def _copy_contract(health: dict[str, Any]) -> dict[str, Any]:
    return {
        "language": "zh-first",
        "max_card_reason_chars": 72 if health["pressure"] == "high" else 96,
        "max_visible_metrics": 3,
        "prefer_verbs": ["确认", "改写", "拒绝", "稍后"],
        "avoid": [
            "Do not expose full diagnostics by default.",
            "Do not ask the user to read every evidence path before the next action is clear.",
            "Do not phrase AI-inferred reasons as user intent.",
        ],
    }


def _sort_key(item: dict[str, Any]) -> tuple[int, int, int, float, str]:
    risk = RISK_RANK.get(str(item.get("risk_level") or "low"), 9)
    status = STATUS_RANK.get(str(item.get("review_status") or "unreviewed"), 9)
    boundary = 0 if item.get("why_saved_status") == "AI-inferred" else 1
    confidence = float(item.get("confidence") or 0)
    return (risk, status, boundary, -confidence, str(item.get("title") or ""))


def _batch_safe(item: dict[str, Any]) -> bool:
    if item.get("risk_level") in {"critical", "high"}:
        return False
    if item.get("review_status") in {"unreviewed", "deferred"} and item.get("why_saved_status") == "AI-inferred":
        return False
    if item.get("has_open_loops") or item.get("open_loops"):
        return False
    return True


def _lane_reason(lane_id: str, count: int) -> str:
    if lane_id == "decision_required":
        return f"{count} item(s) may affect future answer trust."
    if lane_id == "boundary_check":
        return f"{count} AI-inferred saved reason(s) need a boundary decision."
    if lane_id == "open_loop":
        return f"{count} item(s) still carry unresolved next steps."
    if lane_id == "batch_safe":
        return f"{count} item(s) can be handled without expanding detail."
    return f"{count} item(s) already have a trust decision."


def _orient_instruction(items: list[dict[str, Any]], active_filter: bool) -> str:
    if not items:
        return "No items match this view; clear filters or collect more material."
    if active_filter:
        return "Review the filtered set without exposing unrelated diagnostics."
    return "Start with the first risky item and keep the rest collapsed."


def _boundary_instruction(item: dict[str, Any] | None) -> str:
    if not item:
        return "No boundary check is needed in an empty queue."
    if item.get("why_saved_status") == "AI-inferred":
        return "Confirm whether this reason reflects the user or should be rewritten."
    if item.get("why_saved_status") in {"user-stated", "user-guided"}:
        return "Preserve the user-stated reason as the anchor."
    return "Identify whether the saved reason came from user text or model inference."


def _evidence_instruction(item: dict[str, Any] | None) -> str:
    if not item:
        return "No evidence path is available in an empty queue."
    count = int(item.get("evidence_count") or 0)
    if count:
        return f"Use {count} evidence path(s) as support; keep detailed paths collapsed."
    return "No evidence path is attached; avoid treating the reason as strong memory."


def _decision_instruction(item: dict[str, Any] | None) -> str:
    if not item:
        return "No trust decision is currently needed."
    if item.get("risk_level") in {"critical", "high"}:
        return "Make one explicit decision before moving to the next item."
    if _batch_safe(item):
        return "This item can be handled in a batch or quietly confirmed."
    return "Choose confirm, rewrite, reject, or defer based on boundary and evidence."


def _boundary_complete(item: dict[str, Any] | None) -> bool:
    if not item:
        return True
    return item.get("why_saved_status") in {"user-stated", "user-guided"} or item.get("review_status") in {"confirmed", "rewritten", "rejected"}


def _evidence_complete(item: dict[str, Any] | None) -> bool:
    if not item:
        return True
    return int(item.get("evidence_count") or 0) > 0


def _decision_complete(item: dict[str, Any] | None) -> bool:
    if not item:
        return True
    return item.get("review_status") in {"confirmed", "rewritten", "rejected"}


def _bulk_guardrail(safe: list[dict[str, Any]], risky: list[dict[str, Any]]) -> str:
    if safe and risky:
        return "Batch only the safe group; keep high-risk or AI-inferred items in single review."
    if safe:
        return "Batch group is low pressure and can stay visually quiet."
    return "No safe batch exists; review items individually."


def _recommended_visible_count(pressure: str, total: int) -> int:
    if pressure == "empty":
        return 0
    if pressure == "high":
        return min(3, total)
    if pressure == "medium":
        return min(4, total)
    return min(6, total)


def _queue_summary(pressure: str, high: int, ai: int, loops: int) -> str:
    if pressure == "empty":
        return "No trust work is visible in the current filter."
    if pressure == "high":
        return f"High pressure: {high} high-risk item(s), {ai} AI-inferred boundary item(s)."
    if pressure == "medium":
        return f"Moderate pressure: {ai} AI boundary item(s), {loops} open-loop item(s)."
    return "Low pressure: most items can stay collapsed or be handled in batches."
