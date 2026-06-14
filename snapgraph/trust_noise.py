from __future__ import annotations

from collections import Counter
from typing import Any


RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
STATUS_ORDER = {"unreviewed": 0, "deferred": 1, "rewritten": 2, "confirmed": 3, "rejected": 4}


def build_trust_noise_pack(
    items: list[dict[str, Any]],
    summary: dict[str, Any],
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = [_normalize_item(item) for item in items]
    lanes = _lanes(normalized)
    pressure = _pressure(normalized, lanes)
    visible_ids = _visible_source_ids(lanes, pressure)
    return {
        "summary": {
            "total": int(summary.get("total") or len(items)),
            "visible_count": len(visible_ids),
            "collapsed_count": max(0, len(normalized) - len(visible_ids)),
            "pressure_level": pressure["level"],
            "attention_score": pressure["score"],
            "filter_count": len(filters or {}),
            "immediate_count": lanes["immediate"]["count"],
            "next_count": lanes["next"]["count"],
            "monitor_count": lanes["monitor"]["count"],
        },
        "lanes": lanes,
        "focus_order": _focus_order(lanes),
        "attention_budget": pressure,
        "progressive_disclosure": _progressive_disclosure(normalized, lanes, pressure),
        "microcopy": _microcopy(lanes, pressure),
        "plain_language": _plain_language(lanes, pressure),
        "display_policy": _display_policy(normalized, pressure),
    }


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    trust_signals = item.get("trust_signals") if isinstance(item.get("trust_signals"), dict) else {}
    why_saved_status = str(item.get("why_saved_status") or "unknown")
    review_status = str(item.get("review_status") or "unreviewed")
    return {
        "source_id": str(item.get("source_id") or ""),
        "title": str(item.get("title") or ""),
        "why_saved_status": why_saved_status,
        "review_status": review_status,
        "risk_level": str(item.get("risk_level") or "low"),
        "recommended_action": str(item.get("recommended_action") or "monitor"),
        "confidence": _float(item.get("confidence")),
        "evidence_count": _int(item.get("evidence_count")),
        "topic_count": len(item.get("topic_refs") or []),
        "open_loop_count": _int(trust_signals.get("open_loop_count"), fallback=len(item.get("open_loops") or [])),
        "future_question_count": len(item.get("future_recall_questions") or []),
        "has_open_loops": bool(item.get("has_open_loops") or trust_signals.get("has_open_loops")),
        "needs_review": bool(item.get("needs_review"))
        or (why_saved_status == "AI-inferred" and review_status in {"unreviewed", "deferred"}),
        "risk_reasons": [str(reason) for reason in item.get("risk_reasons") or []],
        "imported_at": str(item.get("imported_at") or ""),
    }


def _lanes(items: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = {
        "immediate": [],
        "next": [],
        "monitor": [],
        "collapsed": [],
    }
    for item in items:
        lane = _lane_for_item(item)
        grouped[lane].append(item)
    for lane_items in grouped.values():
        lane_items.sort(key=_item_sort_key)
    return {
        "immediate": _lane_payload("immediate", "Needs decision", grouped["immediate"], 1),
        "next": _lane_payload("next", "Useful next", grouped["next"], 2),
        "monitor": _lane_payload("monitor", "Monitor", grouped["monitor"], 3),
        "collapsed": _lane_payload("collapsed", "Keep folded", grouped["collapsed"], 4),
    }


def _lane_for_item(item: dict[str, Any]) -> str:
    risk = item["risk_level"]
    status = item["review_status"]
    if item["needs_review"] and risk in {"critical", "high"}:
        return "immediate"
    if status == "deferred" or (item["has_open_loops"] and risk in {"critical", "high", "medium"}):
        return "next"
    if status in {"confirmed", "rewritten"} and risk == "low":
        return "collapsed"
    if status == "rejected":
        return "collapsed"
    if item["needs_review"]:
        return "next"
    return "monitor"


def _lane_payload(lane_id: str, label: str, items: list[dict[str, Any]], priority: int) -> dict[str, Any]:
    visible_limit = 3 if lane_id == "immediate" else 2 if lane_id == "next" else 1
    if lane_id == "collapsed":
        visible_limit = 0
    return {
        "id": lane_id,
        "label": label,
        "priority": priority,
        "count": len(items),
        "visible_source_ids": [item["source_id"] for item in items[:visible_limit]],
        "collapsed_source_ids": [item["source_id"] for item in items[visible_limit:]],
        "top_items": [_item_preview(item) for item in items[:visible_limit or 3]],
        "reasons": _lane_reasons(lane_id, items),
        "default_collapsed": lane_id in {"monitor", "collapsed"} or not items,
    }


def _pressure(items: list[dict[str, Any]], lanes: dict[str, Any]) -> dict[str, Any]:
    score = 0
    score += lanes["immediate"]["count"] * 30
    score += lanes["next"]["count"] * 14
    score += sum(8 for item in items if item["risk_level"] == "critical")
    score += sum(5 for item in items if item["risk_level"] == "high")
    score += min(sum(item["open_loop_count"] for item in items), 8) * 2
    if len(items) > 12:
        score += 12
    score = max(0, min(100, score))
    if not items:
        level = "empty"
    elif score >= 70:
        level = "high"
    elif score >= 35:
        level = "medium"
    else:
        level = "low"
    return {
        "score": score,
        "level": level,
        "recommended_visible_items": _recommended_visible_items(level, lanes),
        "recommended_visible_lanes": _recommended_visible_lanes(level, lanes),
        "reason": _pressure_reason(level, lanes, len(items)),
    }


def _visible_source_ids(lanes: dict[str, Any], pressure: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for lane_id in ["immediate", "next", "monitor"]:
        ids.extend(lanes[lane_id]["visible_source_ids"])
    return ids[: pressure["recommended_visible_items"]]


def _focus_order(lanes: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for lane_id in ["immediate", "next", "monitor", "collapsed"]:
        lane = lanes[lane_id]
        rows.append(
            {
                "lane_id": lane_id,
                "label": lane["label"],
                "count": lane["count"],
                "priority": lane["priority"],
                "start_collapsed": lane["default_collapsed"],
            }
        )
    return rows


def _progressive_disclosure(
    items: list[dict[str, Any]],
    lanes: dict[str, Any],
    pressure: dict[str, Any],
) -> dict[str, Any]:
    status_counts = Counter(item["review_status"] for item in items)
    boundary_counts = Counter(item["why_saved_status"] for item in items)
    return {
        "first_screen": {
            "show_counts": True,
            "show_first_lane": lanes["immediate"]["count"] > 0,
            "show_next_lane": lanes["next"]["count"] > 0 and pressure["level"] != "high",
            "hide_completed": status_counts.get("confirmed", 0) + status_counts.get("rewritten", 0),
        },
        "expandable_sections": [
            {
                "id": "reviewed",
                "label": "Reviewed context",
                "count": status_counts.get("confirmed", 0) + status_counts.get("rewritten", 0),
                "default_collapsed": True,
            },
            {
                "id": "ai_inferred",
                "label": "AI-inferred reasons",
                "count": boundary_counts.get("AI-inferred", 0),
                "default_collapsed": boundary_counts.get("AI-inferred", 0) > lanes["immediate"]["count"],
            },
            {
                "id": "open_loops",
                "label": "Open loops",
                "count": sum(item["open_loop_count"] for item in items),
                "default_collapsed": pressure["level"] == "high",
            },
        ],
        "empty_state": not items,
    }


def _microcopy(lanes: dict[str, Any], pressure: dict[str, Any]) -> dict[str, Any]:
    if pressure["level"] == "empty":
        headline = "No trust item matches the current filter."
        subline = "Clear filters or capture more material."
    elif lanes["immediate"]["count"]:
        headline = f"{lanes['immediate']['count']} item(s) need a trust decision first."
        subline = "Review the highest-risk AI-inferred reasons before scanning everything."
    elif lanes["next"]["count"]:
        headline = f"{lanes['next']['count']} useful next item(s) are ready."
        subline = "Start with open loops or deferred decisions, then fold the rest."
    else:
        headline = "Trust queue is mostly quiet."
        subline = "Keep reviewed and low-risk context collapsed by default."
    return {
        "headline": headline,
        "subline": subline,
        "empty": "No trust work is visible under these filters.",
        "collapsed": "Lower-pressure context is still available below the fold.",
    }


def _plain_language(lanes: dict[str, Any], pressure: dict[str, Any]) -> dict[str, Any]:
    return {
        "headline": _microcopy(lanes, pressure)["headline"],
        "why_compact": "Users should see the next trust decision before the full audit trail.",
        "what_is_hidden": _hidden_copy(lanes),
        "how_to_continue": _continue_copy(lanes),
    }


def _display_policy(items: list[dict[str, Any]], pressure: dict[str, Any]) -> dict[str, Any]:
    return {
        "default_visible_lanes": min(3, pressure["recommended_visible_lanes"]),
        "default_visible_items": min(len(items), pressure["recommended_visible_items"]),
        "collapse_resolved_items": True,
        "collapse_low_risk_items": True,
        "collapse_empty_lanes": True,
        "show_lane_counts": True,
        "reason": pressure["reason"],
    }


def _item_preview(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": item["source_id"],
        "title": item["title"],
        "risk_level": item["risk_level"],
        "review_status": item["review_status"],
        "recommended_action": item["recommended_action"],
        "reason": _item_reason(item),
    }


def _item_reason(item: dict[str, Any]) -> str:
    if item["risk_reasons"]:
        return item["risk_reasons"][0]
    if item["needs_review"]:
        return "AI-inferred reason still needs review."
    if item["has_open_loops"]:
        return "Open loop is attached."
    return "Low-pressure context."


def _lane_reasons(lane_id: str, items: list[dict[str, Any]]) -> list[str]:
    if not items:
        return ["No items in this lane."]
    if lane_id == "immediate":
        return ["High-risk AI-inferred or low-confidence context should stay visible."]
    if lane_id == "next":
        return ["Deferred decisions and open loops are useful after urgent review."]
    if lane_id == "monitor":
        return ["Context is available but does not need first-screen attention."]
    return ["Resolved, rejected, or low-risk items should stay folded."]


def _item_sort_key(item: dict[str, Any]) -> tuple:
    return (
        RISK_ORDER.get(item["risk_level"], 9),
        STATUS_ORDER.get(item["review_status"], 9),
        0 if item["needs_review"] else 1,
        -item["open_loop_count"],
        item["title"],
    )


def _recommended_visible_items(level: str, lanes: dict[str, Any]) -> int:
    if level == "empty":
        return 0
    if level == "high":
        return min(4, max(1, lanes["immediate"]["count"]))
    if level == "medium":
        return 5
    return 6


def _recommended_visible_lanes(level: str, lanes: dict[str, Any]) -> int:
    if level == "empty":
        return 1
    if level == "high":
        return 2
    if lanes["monitor"]["count"]:
        return 3
    return 2


def _pressure_reason(level: str, lanes: dict[str, Any], total: int) -> str:
    if level == "empty":
        return "No queue items are visible."
    if level == "high":
        return f"{lanes['immediate']['count']} immediate item(s) out of {total} total create high attention pressure."
    if level == "medium":
        return "There is trust work to do, but it can be grouped into compact lanes."
    return "Most trust items can stay folded while preserving access."


def _hidden_copy(lanes: dict[str, Any]) -> str:
    hidden = lanes["collapsed"]["count"] + len(lanes["monitor"]["collapsed_source_ids"])
    if hidden:
        return f"{hidden} low-pressure item(s) are folded."
    return "No important item is hidden by default."


def _continue_copy(lanes: dict[str, Any]) -> str:
    if lanes["immediate"]["count"]:
        return "Start with the first immediate item."
    if lanes["next"]["count"]:
        return "Continue with the next open loop or deferred decision."
    return "Use filters only when you need a specific source."


def _int(value: Any, *, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _float(value: Any, *, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback
