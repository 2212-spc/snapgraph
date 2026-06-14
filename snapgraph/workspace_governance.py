from __future__ import annotations

from typing import Any

from .graph_store import graph_diagnostics, graph_for_space, graph_insights
from .models import DEFAULT_GRAPH_SPACE_ID
from .source_traceability import build_source_traceability_audit
from .trust_noise import build_trust_noise_pack
from .workspace import Workspace
from .workspace_health import build_workspace_health_pack
from .trust_center import list_review_items


def build_workspace_governance_report(workspace: Workspace) -> dict[str, Any]:
    diagnostics = graph_diagnostics(workspace)
    health = build_workspace_health_pack(
        source_count=_source_count(workspace),
        saved_questions=_saved_questions(workspace),
        node_count=diagnostics.node_count,
        edge_count=diagnostics.edge_count,
        lint_status=_lint_status(workspace),
        lint_errors=_lint_errors(workspace),
        lint_warnings=_lint_warnings(workspace),
        context_status=_context_status(workspace),
        node_types=diagnostics.node_types,
        top_hubs=[{"label": label, "degree": degree} for label, degree in diagnostics.top_hubs],
        orphans=diagnostics.orphans,
        spaces=_spaces(workspace),
        insights=graph_insights(workspace),
    )
    trust_queue = list_review_items(workspace)
    trust_noise = build_trust_noise_pack(trust_queue["items"], trust_queue["summary"], trust_queue.get("filters") or {})
    traceability = build_source_traceability_audit(workspace)
    graph = graph_for_space(workspace, DEFAULT_GRAPH_SPACE_ID)
    report_label = _report_label(health, traceability, trust_noise)
    return {
        "summary": {
            "report_label": report_label,
            "source_count": health["summary"]["source_count"],
            "node_count": health["summary"]["node_count"],
            "edge_count": health["summary"]["edge_count"],
            "traceability_label": traceability["summary"]["traceability_label"],
            "trust_pressure": trust_noise["attention_budget"]["level"],
            "plain_language": _summary_copy(report_label, health, traceability, trust_noise),
        },
        "sections": [
            {
                "id": "workspace_health",
                "label": "Workspace health",
                "count": health["summary"]["source_count"],
                "detail": health["readiness"]["reason"],
            },
            {
                "id": "traceability",
                "label": "Traceability",
                "count": traceability["summary"]["tracked_count"],
                "detail": traceability["summary"]["plain_language"],
            },
            {
                "id": "trust_noise",
                "label": "Trust noise",
                "count": trust_noise["summary"]["total"],
                "detail": trust_noise["plain_language"]["headline"],
            },
            {
                "id": "graph_evidence",
                "label": "Graph evidence",
                "count": len(graph.get("nodes", [])),
                "detail": graph_insights(workspace).get("plain_language", ""),
            },
        ],
        "action_plan": _action_plan(health, traceability, trust_noise),
        "source_traceability": traceability,
        "trust_noise": trust_noise,
        "workspace_health": health,
        "graph_summary": {
            "node_count": len(graph.get("nodes", [])),
            "edge_count": len(graph.get("edges", [])),
            "space_id": DEFAULT_GRAPH_SPACE_ID,
        },
        "display_policy": {
            "default_collapsed": True,
            "max_visible_sections": 4,
            "max_visible_actions": 4,
            "collapse_low_priority_sections": True,
            "reason": "Governance reporting should explain the current state without flooding the first screen.",
        },
    }


def _action_plan(health: dict[str, Any], traceability: dict[str, Any], trust_noise: dict[str, Any]) -> list[dict[str, Any]]:
    actions = []
    if health["readiness"]["label"] == "empty":
        actions.append(_action("load_demo", "Load demo workspace", "Populate sources so the governance report can explain real state.", 1))
    if traceability["summary"]["traceability_label"] in {"forming", "needs_attention"}:
        actions.append(_action("repair_traceability", "Repair source traceability", traceability["summary"]["plain_language"], 2))
    if trust_noise["attention_budget"]["level"] in {"medium", "high"}:
        actions.append(_action("reduce_trust_noise", "Reduce trust noise", trust_noise["plain_language"]["headline"], 3))
    if health["readiness"]["label"] != "healthy":
        actions.append(_action("review_health", "Review workspace health", health["readiness"]["reason"], 4))
    if not actions:
        actions.append(_action("keep_current_state", "Keep current state", "The workspace is already stable enough for review.", 1))
    return actions[:6]


def _report_label(health: dict[str, Any], traceability: dict[str, Any], trust_noise: dict[str, Any]) -> str:
    if health["readiness"]["label"] == "empty":
        return "empty"
    if traceability["summary"]["traceability_label"] == "needs_attention" or trust_noise["attention_budget"]["level"] == "high":
        return "needs_attention"
    if health["readiness"]["label"] == "healthy" and traceability["summary"]["traceability_label"] == "auditable":
        return "healthy"
    if health["readiness"]["label"] in {"usable", "healthy"}:
        return "usable"
    return "collecting"


def _summary_copy(report_label: str, health: dict[str, Any], traceability: dict[str, Any], trust_noise: dict[str, Any]) -> str:
    return (
        f"Workspace is {report_label}; {health['summary']['source_count']} source(s), "
        f"{traceability['summary']['traceability_label']} traceability, "
        f"{trust_noise['attention_budget']['level']} trust pressure."
    )


def _action(action_id: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": action_id,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


def _source_count(workspace: Workspace) -> int:
    import sqlite3

    with sqlite3.connect(workspace.sqlite_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0])


def _saved_questions(workspace: Workspace) -> int:
    from .wiki import question_pages

    return len(question_pages(workspace))


def _lint_status(workspace: Workspace) -> str:
    return _lint_result(workspace)["status"]


def _lint_errors(workspace: Workspace) -> list[str]:
    return _lint_result(workspace)["errors"]


def _lint_warnings(workspace: Workspace) -> list[str]:
    return _lint_result(workspace)["warnings"]


def _lint_result(workspace: Workspace) -> dict[str, Any]:
    from .linting import lint_workspace

    lint = lint_workspace(workspace)
    return {"status": lint.status, "errors": lint.errors, "warnings": lint.warnings}


def _context_status(workspace: Workspace) -> dict[str, int]:
    import sqlite3

    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            "SELECT why_saved_status, COUNT(*) FROM cognitive_contexts GROUP BY why_saved_status"
        ).fetchall()
    return {row[0]: int(row[1]) for row in rows}


def _spaces(workspace: Workspace) -> list[dict[str, Any]]:
    from .spaces import list_graph_spaces

    return list_graph_spaces(workspace)
