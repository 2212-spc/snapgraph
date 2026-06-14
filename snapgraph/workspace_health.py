from __future__ import annotations

from collections import Counter
from typing import Any


def build_workspace_health_pack(
    *,
    source_count: int,
    saved_questions: int,
    node_count: int,
    edge_count: int,
    lint_status: str,
    lint_errors: list[str],
    lint_warnings: list[str],
    context_status: dict[str, int],
    node_types: dict[str, int],
    top_hubs: list[dict[str, Any]],
    orphans: list[str],
    spaces: list[dict[str, Any]],
    insights: dict[str, Any],
) -> dict[str, Any]:
    summary = _summary(
        source_count=source_count,
        saved_questions=saved_questions,
        node_count=node_count,
        edge_count=edge_count,
        lint_status=lint_status,
        context_status=context_status,
    )
    readiness = _readiness(summary, lint_errors, lint_warnings, orphans, spaces, insights)
    pressure = _information_pressure(summary, lint_warnings, orphans, spaces)
    next_actions = _next_actions(readiness, summary, lint_errors, lint_warnings, orphans, spaces)
    return {
        "summary": summary,
        "readiness": readiness,
        "information_pressure": pressure,
        "next_actions": next_actions,
        "space_health": _space_health(spaces),
        "graph_health": _graph_health(node_count, edge_count, node_types, top_hubs, orphans),
        "trust_health": _trust_health(context_status, insights),
        "display_policy": {
            "show_summary_first": True,
            "default_visible_sections": pressure["default_visible_sections"],
            "collapse_diagnostics": True,
            "collapse_low_priority_spaces": True,
            "reason": "Workspace health should guide the next action without making the dashboard heavier.",
        },
    }


def _summary(
    *,
    source_count: int,
    saved_questions: int,
    node_count: int,
    edge_count: int,
    lint_status: str,
    context_status: dict[str, int],
) -> dict[str, Any]:
    user_stated = context_status.get("user-stated", 0) + context_status.get("user-guided", 0)
    ai_inferred = context_status.get("AI-inferred", 0)
    unknown = context_status.get("unknown", 0)
    return {
        "source_count": source_count,
        "saved_questions": saved_questions,
        "node_count": node_count,
        "edge_count": edge_count,
        "lint_status": lint_status,
        "user_stated_contexts": user_stated,
        "ai_inferred_contexts": ai_inferred,
        "unknown_contexts": unknown,
        "context_total": sum(context_status.values()),
        "graph_density": round(edge_count / max(node_count, 1), 3),
    }


def _readiness(
    summary: dict[str, Any],
    lint_errors: list[str],
    lint_warnings: list[str],
    orphans: list[str],
    spaces: list[dict[str, Any]],
    insights: dict[str, Any],
) -> dict[str, Any]:
    score = 0
    score += min(summary["source_count"], 10) * 5
    score += min(summary["saved_questions"], 6) * 4
    score += min(summary["user_stated_contexts"], 8) * 6
    score += min(summary["edge_count"], 20) * 2
    score -= len(lint_errors) * 25
    score -= min(len(lint_warnings), 10) * 3
    score -= min(len(orphans), 10) * 2
    if any(space.get("pending_suggestions", 0) for space in spaces):
        score -= 4
    if insights.get("high_value_review_paths"):
        score += 8
    score = max(0, min(100, score))
    if summary["source_count"] == 0:
        label = "empty"
    elif lint_errors:
        label = "needs_attention"
    elif score >= 75:
        label = "healthy"
    elif score >= 45:
        label = "usable"
    else:
        label = "collecting"
    return {
        "score": score,
        "label": label,
        "can_answer_from_memory": label in {"usable", "healthy"},
        "needs_trust_review": summary["ai_inferred_contexts"] > summary["user_stated_contexts"],
        "reason": _readiness_reason(label, summary, lint_errors, lint_warnings),
    }


def _information_pressure(
    summary: dict[str, Any],
    lint_warnings: list[str],
    orphans: list[str],
    spaces: list[dict[str, Any]],
) -> dict[str, Any]:
    pending_suggestions = sum(int(space.get("pending_suggestions") or 0) for space in spaces)
    warning_pressure = len(lint_warnings) + len(orphans) + pending_suggestions
    if warning_pressure >= 12 or summary["source_count"] >= 30:
        pressure = "high"
        visible = 3
    elif warning_pressure or summary["source_count"] >= 8:
        pressure = "medium"
        visible = 4
    else:
        pressure = "low"
        visible = 4
    return {
        "pressure": pressure,
        "default_visible_sections": visible,
        "warning_pressure": warning_pressure,
        "pending_suggestions": pending_suggestions,
        "collapse_after": visible,
        "plain_language": _pressure_copy(pressure, warning_pressure),
    }


def _next_actions(
    readiness: dict[str, Any],
    summary: dict[str, Any],
    lint_errors: list[str],
    lint_warnings: list[str],
    orphans: list[str],
    spaces: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    actions = []
    if readiness["label"] == "empty":
        actions.append(_action("load_demo", "Load demo data", "Start with demo material to understand the workflow.", 1))
    if lint_errors:
        actions.append(_action("fix_lint_errors", "Fix workspace errors", lint_errors[0], 1))
    if summary["ai_inferred_contexts"] > 0:
        actions.append(
            _action(
                "review_ai_context",
                "Review AI-inferred reasons",
                f"{summary['ai_inferred_contexts']} saved reason(s) still need a user boundary decision.",
                2,
            )
        )
    pending = sum(int(space.get("pending_suggestions") or 0) for space in spaces)
    if pending:
        actions.append(_action("route_materials", "Route captured material", f"{pending} route suggestion(s) are pending.", 3))
    if orphans:
        actions.append(_action("inspect_graph_orphans", "Inspect graph orphans", f"{len(orphans)} graph node(s) are not connected.", 4))
    if lint_warnings and not lint_errors:
        actions.append(_action("inspect_warnings", "Inspect warnings", lint_warnings[0], 5))
    if not actions:
        actions.append(_action("ask_memory", "Ask from memory", "The workspace is ready enough for recall.", 1))
    return sorted(actions, key=lambda item: item["priority"])[:6]


def _space_health(spaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for space in spaces:
        source_count = int(space.get("source_count") or 0)
        pending = int(space.get("pending_suggestions") or 0)
        edge_count = int(space.get("edge_count") or 0)
        if source_count == 0 and pending == 0:
            label = "quiet"
        elif pending:
            label = "needs_routing"
        elif edge_count >= source_count:
            label = "connected"
        else:
            label = "thin"
        rows.append(
            {
                "space_id": space.get("id", ""),
                "name": space.get("name", ""),
                "label": label,
                "source_count": source_count,
                "edge_count": edge_count,
                "pending_suggestions": pending,
                "default_collapsed": label == "quiet",
            }
        )
    return rows


def _graph_health(
    node_count: int,
    edge_count: int,
    node_types: dict[str, int],
    top_hubs: list[dict[str, Any]],
    orphans: list[str],
) -> dict[str, Any]:
    density = round(edge_count / max(node_count, 1), 3)
    if node_count == 0:
        label = "empty"
    elif orphans and density < 0.7:
        label = "fragmented"
    elif density >= 1:
        label = "connected"
    else:
        label = "forming"
    return {
        "label": label,
        "density": density,
        "node_types": node_types,
        "top_hubs": top_hubs[:5],
        "orphan_count": len(orphans),
        "plain_language": _graph_health_copy(label, density, len(orphans)),
    }


def _trust_health(context_status: dict[str, int], insights: dict[str, Any]) -> dict[str, Any]:
    counts = Counter(context_status)
    ai = counts.get("AI-inferred", 0)
    user = counts.get("user-stated", 0) + counts.get("user-guided", 0)
    high_value_paths = len(insights.get("high_value_review_paths") or [])
    if ai > user:
        label = "review_needed"
    elif high_value_paths:
        label = "review_available"
    elif user:
        label = "anchored"
    else:
        label = "thin"
    return {
        "label": label,
        "ai_inferred": ai,
        "user_stated": user,
        "high_value_review_paths": high_value_paths,
        "plain_language": _trust_health_copy(label, ai, user),
    }


def _action(action_id: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": action_id,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


def _readiness_reason(
    label: str,
    summary: dict[str, Any],
    lint_errors: list[str],
    lint_warnings: list[str],
) -> str:
    if label == "empty":
        return "No saved sources exist yet."
    if lint_errors:
        return f"{len(lint_errors)} workspace error(s) should be fixed first."
    if label == "healthy":
        return "Sources, user-stated context, and graph edges are available."
    if lint_warnings:
        return f"Usable, with {len(lint_warnings)} warning(s) kept in diagnostics."
    return f"{summary['source_count']} source(s) are available and the graph is still forming."


def _pressure_copy(pressure: str, warning_pressure: int) -> str:
    if pressure == "high":
        return "Show fewer sections by default; diagnostics are available but should stay collapsed."
    if pressure == "medium":
        return f"{warning_pressure} signal(s) need attention, but the dashboard can stay compact."
    return "The workspace can show a concise overview without hiding critical issues."


def _graph_health_copy(label: str, density: float, orphan_count: int) -> str:
    if label == "empty":
        return "No graph facts exist yet."
    if label == "fragmented":
        return f"The graph has {orphan_count} orphan node(s) and density {density}."
    if label == "connected":
        return "The graph has enough edges to support evidence paths."
    return "The graph is forming and should keep evidence routes visible."


def _trust_health_copy(label: str, ai: int, user: int) -> str:
    if label == "review_needed":
        return f"{ai} AI-inferred reason(s) outweigh {user} user-stated anchor(s)."
    if label == "review_available":
        return "There are high-value review paths available."
    if label == "anchored":
        return "User-stated anchors are available for recall."
    return "Trust context is still thin."
