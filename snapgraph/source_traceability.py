from __future__ import annotations

from collections import Counter, defaultdict
import json
import sqlite3
from typing import Any

from .models import DEFAULT_GRAPH_SPACE_ID
from .workspace import Workspace


def build_source_traceability_audit(workspace: Workspace) -> dict[str, Any]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        sources = conn.execute(
            """
            SELECT id, title, path, type, imported_at, graph_space_id
            FROM sources
            ORDER BY imported_at ASC
            """
        ).fetchall()
        contexts = conn.execute(
            """
            SELECT source_id, why_saved_status, review_status, confidence,
                   related_project, open_loops_json, future_recall_questions_json
            FROM cognitive_contexts
            """
        ).fetchall()
        nodes = conn.execute(
            """
            SELECT id, type, label, graph_space_id, status, properties_json
            FROM nodes
            """
        ).fetchall()
        edges = conn.execute(
            """
            SELECT id, source, target, relation, evidence_source_id, graph_space_id, status, confidence
            FROM edges
            """
        ).fetchall()
        recall_rows = conn.execute(
            """
            SELECT id, context_source_ids_json, thread_id, question, mode, depth, space_id
            FROM recall_history
            """
        ).fetchall()

    source_rows = [
        {
            "source_id": row[0],
            "title": row[1],
            "path": row[2],
            "type": row[3],
            "imported_at": row[4],
            "graph_space_id": row[5] or DEFAULT_GRAPH_SPACE_ID,
        }
        for row in sources
    ]
    context_map = {
        row[0]: {
            "why_saved_status": row[1],
            "review_status": row[2],
            "confidence": float(row[3]),
            "related_project": row[4] or "",
            "open_loops": _loads_list(row[5]),
            "future_recall_questions": _loads_list(row[6]),
        }
        for row in contexts
    }
    node_by_source = _source_node_map(nodes)
    edges_by_source = _edges_by_evidence(edges)
    recall_by_source = _recall_source_map(recall_rows)
    source_items = []
    for source in source_rows:
        context = context_map.get(source["source_id"], {})
        source_items.append(
            {
                **source,
                **context,
                "has_context": bool(context),
                "has_source_node": source["source_id"] in node_by_source,
                "source_node_count": node_by_source.get(source["source_id"], 0),
                "graph_edge_count": edges_by_source.get(source["source_id"], 0),
                "recall_count": recall_by_source.get(source["source_id"], 0),
                "traceability_score": _traceability_score(source, context, node_by_source, edges_by_source, recall_by_source),
            }
        )

    coverage = _coverage(source_items)
    gaps = _gaps(source_items)
    trails = _trails(source_items)
    risk = _risk_register(source_items, coverage, gaps)
    traceability_label = _traceability_label(coverage, risk, source_items)
    return {
        "summary": {
            "source_count": len(source_items),
            "tracked_count": sum(1 for item in source_items if item["has_context"]),
            "node_linked_count": sum(1 for item in source_items if item["has_source_node"]),
            "edge_linked_count": sum(1 for item in source_items if item["graph_edge_count"] > 0),
            "recall_linked_count": sum(1 for item in source_items if item["recall_count"] > 0),
            "traceability_label": traceability_label,
            "plain_language": _summary_copy(traceability_label, coverage, risk),
        },
        "sources": source_items[:20],
        "coverage": coverage,
        "gaps": gaps,
        "trails": trails,
        "risk_register": risk,
        "display_policy": {
            "default_visible_sources": min(6, len(source_items)),
            "collapse_complete_sources": True,
            "collapse_sources_with_full_coverage": True,
            "collapse_sources_without_gaps": True,
            "reason": "Traceability should help the next review step without exposing every row at once.",
        },
    }


def _coverage(items: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(items)
    with_context = sum(1 for item in items if item["has_context"])
    with_node = sum(1 for item in items if item["has_source_node"])
    with_edge = sum(1 for item in items if item["graph_edge_count"] > 0)
    with_recall = sum(1 for item in items if item["recall_count"] > 0)
    ai_only = sum(1 for item in items if item.get("why_saved_status") == "AI-inferred" and not item["has_context"])
    user_stated = sum(1 for item in items if item.get("why_saved_status") == "user-stated")
    return {
        "total": total,
        "context_coverage_percent": _percent(with_context, total),
        "node_coverage_percent": _percent(with_node, total),
        "edge_coverage_percent": _percent(with_edge, total),
        "recall_coverage_percent": _percent(with_recall, total),
        "ai_only_count": ai_only,
        "user_stated_count": user_stated,
        "source_only_count": sum(1 for item in items if not item["has_context"] and item["graph_edge_count"] == 0),
        "plain_language": _coverage_copy(total, with_context, with_edge, with_recall),
    }


def _gaps(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    no_context = [item for item in items if not item["has_context"]]
    no_edges = [item for item in items if item["graph_edge_count"] == 0]
    no_recall = [item for item in items if item["recall_count"] == 0]
    if no_context:
        gaps.append(_gap("missing_context", "Missing cognitive context", f"{len(no_context)} source(s) have no why-saved context.", 1))
    if no_edges:
        gaps.append(_gap("missing_graph_edges", "Missing graph edges", f"{len(no_edges)} source(s) are not connected to graph edges.", 2))
    if no_recall:
        gaps.append(_gap("missing_recall", "Missing recall usage", f"{len(no_recall)} source(s) have not been reused in recall history.", 3))
    if not gaps:
        gaps.append(_gap("traceable", "Traceability is healthy", "Every source has enough traceability to be reviewed.", 1))
    return gaps


def _trails(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for item in sorted(items, key=lambda row: (-row["traceability_score"], row["title"])):
        rows.append(
            {
                "source_id": item["source_id"],
                "title": item["title"],
                "score": item["traceability_score"],
                "signal": _trail_signal(item),
                "default_collapsed": item["traceability_score"] < 65,
                "open_loop_count": len(item.get("open_loops") or []),
                "future_question_count": len(item.get("future_recall_questions") or []),
            }
        )
    return rows[:12]


def _risk_register(items: list[dict[str, Any]], coverage: dict[str, Any], gaps: list[dict[str, Any]]) -> dict[str, Any]:
    risks = []
    if coverage["ai_only_count"]:
        risks.append(_risk("ai_only", "high", "AI-only sources", f"{coverage['ai_only_count']} source(s) are AI-inferred without context.", 1))
    if coverage["source_only_count"]:
        risks.append(_risk("source_only", "medium", "Source-only records", f"{coverage['source_only_count']} source(s) still lack graph or context coverage.", 2))
    if len(gaps) > 2:
        risks.append(_risk("multi_gap", "medium", "Multiple traceability gaps", "Several traceability layers are incomplete.", 3))
    return {
        "risk_count": len(risks),
        "risks": risks,
        "highest_severity": _highest_severity(risks),
        "plain_language": _risk_copy(risks),
    }


def _traceability_score(
    source: dict[str, Any],
    context: dict[str, Any],
    node_by_source: dict[str, int],
    edges_by_source: dict[str, int],
    recall_by_source: dict[str, int],
) -> int:
    score = 0
    if context:
        score += 25
    if node_by_source.get(source["source_id"], 0):
        score += 20
    if edges_by_source.get(source["source_id"], 0):
        score += 25
    if recall_by_source.get(source["source_id"], 0):
        score += 15
    if context.get("why_saved_status") == "user-stated":
        score += 10
    if context.get("why_saved_status") == "AI-inferred":
        score -= 4
    if context.get("open_loops"):
        score += min(len(context.get("open_loops") or []), 3) * 2
    if context.get("future_recall_questions"):
        score += min(len(context.get("future_recall_questions") or []), 3) * 2
    return max(0, min(100, score))


def _source_node_map(nodes: list[tuple[Any, ...]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in nodes:
        node_id = str(row[0])
        properties = _loads_dict(row[5])
        source_id = str(properties.get("source_id") or node_id.removeprefix("source_"))
        if source_id:
            counts[source_id] += 1
    return dict(counts)


def _edges_by_evidence(edges: list[tuple[Any, ...]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in edges:
        evidence_source_id = str(row[4] or "")
        if evidence_source_id:
            counts[evidence_source_id] += 1
    return dict(counts)


def _recall_source_map(recall_rows: list[tuple[Any, ...]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in recall_rows:
        source_ids = _loads_list(row[1])
        for source_id in source_ids:
            counts[source_id] += 1
    return dict(counts)


def _trail_signal(item: dict[str, Any]) -> str:
    if item["graph_edge_count"] and item["recall_count"]:
        return "source, graph, and recall are aligned"
    if item["graph_edge_count"]:
        return "graph evidence is available"
    if item["has_context"]:
        return "context exists but graph coverage is thin"
    return "no traceability trail yet"


def _traceability_label(coverage: dict[str, Any], risk: dict[str, Any], items: list[dict[str, Any]]) -> str:
    if not items:
        return "empty"
    if risk["highest_severity"] in {"critical", "high"}:
        return "thin"
    if coverage["context_coverage_percent"] >= 85 and coverage["edge_coverage_percent"] >= 70 and coverage["recall_coverage_percent"] >= 50:
        return "auditable"
    if coverage["context_coverage_percent"] >= 60 and coverage["edge_coverage_percent"] >= 35:
        return "traceable"
    return "forming"


def _summary_copy(label: str, coverage: dict[str, Any], risk: dict[str, Any]) -> str:
    if label == "empty":
        return "No source traceability exists yet."
    if label == "auditable":
        return "Sources, graph edges, and recall trails are ready for review."
    if risk["risk_count"]:
        return f"Traceability is usable, but {risk['risk_count']} risk(s) remain."
    return f"Context coverage is {coverage['context_coverage_percent']} percent."


def _coverage_copy(total: int, with_context: int, with_edge: int, with_recall: int) -> str:
    if total == 0:
        return "No sources are loaded."
    return f"{with_context}/{total} sources have context, {with_edge}/{total} have graph edges, {with_recall}/{total} appear in recall."


def _risk_copy(risks: list[dict[str, Any]]) -> str:
    if not risks:
        return "No major traceability risk detected."
    return f"{len(risks)} traceability risk(s) should stay visible."


def _gap(gap_id: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": gap_id,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


def _risk(risk_id: str, severity: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": risk_id,
        "severity": severity,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


def _percent(part: int, total: int) -> int:
    if total <= 0:
        return 0
    return round(part / total * 100)


def _highest_severity(risks: list[dict[str, Any]]) -> str:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    if not risks:
        return "none"
    return min((risk["severity"] for risk in risks), key=lambda severity: order.get(severity, 9))


def _loads_list(value: Any) -> list[str]:
    try:
        loaded = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded if str(item)]


def _loads_dict(value: Any) -> dict[str, Any]:
    try:
        loaded = json.loads(value or "{}")
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}
