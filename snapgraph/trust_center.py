from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass

from .models import DEFAULT_GRAPH_SPACE_ID
from .workspace import Workspace


OPEN_LOOP_STATES = {"active", "next", "resolved", "dismissed"}
REVIEW_RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


@dataclass(frozen=True)
class _SourceProjection:
    source_id: str
    title: str
    source_type: str
    imported_at: str
    summary: str
    graph_space_id: str
    space_name: str
    why_saved: str
    why_saved_status: str
    related_project: str
    open_loops: list[str]
    future_recall_questions: list[str]
    importance: str
    confidence: float
    review_status: str
    review_note: str
    reviewed_at: str


def list_review_items(workspace: Workspace, filters: dict | None = None) -> dict:
    """Return a normalized review queue plus aggregate counts."""
    filter_values = _normalize_filters(filters)
    evidence_counts = _evidence_counts(workspace)
    topic_refs = _topic_refs_by_source(workspace)
    items = [
        _review_item(row, evidence_counts.get(row.source_id, 0), topic_refs.get(row.source_id, []))
        for row in _source_rows(workspace)
    ]
    items = [_item for _item in items if _matches_filters(_item, filter_values)]
    items.sort(key=_review_sort_key)
    return {
        "items": items,
        "summary": _summary(items),
        "filters": filter_values,
    }


def get_review_detail(workspace: Workspace, source_id: str) -> dict:
    """Return one review item with source traceability and trust operations history."""
    payload = list_review_items(workspace, {"source_id": source_id})
    if not payload["items"]:
        raise KeyError(source_id)
    item = payload["items"][0]
    open_loops = [
        loop for loop in list_open_loops(workspace)["items"]
        if source_id in loop.get("source_ids", [])
    ]
    return {
        "item": item,
        "evidence_paths": _evidence_paths(workspace, source_id),
        "history": _history_rows(workspace, source_id),
        "open_loops": open_loops,
        "source_map": _source_map_summary(workspace, source_id),
    }


def trust_summary(workspace: Workspace) -> dict:
    """Return deterministic aggregate counts derived from the current queue."""
    return list_review_items(workspace)["summary"]


def trust_diagnostics(workspace: Workspace) -> dict:
    """Return deterministic diagnostics for queue, history, and open loops."""
    review_payload = list_review_items(workspace)
    items = review_payload["items"]
    open_loop_payload = list_open_loops(workspace)
    current_loop_ids = {item["loop_id"] for item in open_loop_payload["items"]}
    lifecycle_ids = _stored_loop_ids(workspace)
    orphan_lifecycle_ids = sorted(lifecycle_ids - current_loop_ids)
    history_count = _history_count(workspace)
    ai_unreviewed = sum(
        1
        for item in items
        if item["why_saved_status"] == "AI-inferred" and item["review_status"] == "unreviewed"
    )
    risk_counts = Counter(item["risk_level"] for item in items)
    warnings = []
    if ai_unreviewed:
        warnings.append(f"{ai_unreviewed} AI-inferred contexts still need review.")
    if orphan_lifecycle_ids:
        warnings.append(f"{len(orphan_lifecycle_ids)} open-loop lifecycle records no longer match current sources.")
    return {
        "queue_total": len(items),
        "ai_inferred_unreviewed": ai_unreviewed,
        "critical_count": risk_counts.get("critical", 0),
        "high_count": risk_counts.get("high", 0),
        "deferred_count": sum(1 for item in items if item["review_status"] == "deferred"),
        "rejected_count": sum(1 for item in items if item["review_status"] == "rejected"),
        "history_count": history_count,
        "open_loop_total": len(open_loop_payload["items"]),
        "open_loop_states": open_loop_payload["summary"]["by_state"],
        "orphan_lifecycle_ids": orphan_lifecycle_ids,
        "warnings": warnings,
    }


def list_open_loops(workspace: Workspace, state: str | None = None) -> dict:
    """Materialize source and topic open loops with persisted lifecycle state."""
    state_filter = (state or "").strip()
    loop_states = _loop_state_map(workspace)
    source_items = _source_rows(workspace)
    source_by_id = {item.source_id: item for item in source_items}
    evidence_counts = _evidence_counts(workspace)
    topic_refs = _topic_refs_by_source(workspace)
    source_loops = []
    for source in source_items:
        risk = _risk_level(source)
        for index, text in enumerate(source.open_loops):
            loop_id = _loop_id("source", source.source_id, index, text)
            lifecycle = loop_states.get(loop_id, {})
            item = {
                "loop_id": loop_id,
                "origin": "source",
                "text": text,
                "state": lifecycle.get("state", "active"),
                "note": lifecycle.get("note", ""),
                "updated_at": lifecycle.get("updated_at", ""),
                "source_ids": [source.source_id],
                "source_titles": [source.title],
                "risk_level": risk,
                "review_status_summary": {source.review_status: 1},
                "evidence_count": evidence_counts.get(source.source_id, 0),
                "topic_ids": [ref["topic_id"] for ref in topic_refs.get(source.source_id, [])],
            }
            source_loops.append(item)
    topic_loops = _topic_open_loops(workspace, loop_states, source_by_id)
    items = source_loops + topic_loops
    if state_filter:
        items = [item for item in items if item["state"] == state_filter]
    items.sort(key=lambda item: (item["state"] != "next", REVIEW_RISK_ORDER.get(item["risk_level"], 9), item["text"]))
    return {
        "items": items,
        "summary": _open_loop_summary(items),
    }


def _source_rows(workspace: Workspace) -> list[_SourceProjection]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.title,
                s.type,
                s.imported_at,
                COALESCE(s.summary, ''),
                COALESCE(s.graph_space_id, ?),
                COALESCE(gs.name, 'Default'),
                COALESCE(c.why_saved, ''),
                COALESCE(c.why_saved_status, 'unknown'),
                COALESCE(c.related_project, ''),
                COALESCE(c.open_loops_json, '[]'),
                COALESCE(c.future_recall_questions_json, '[]'),
                COALESCE(c.importance, ''),
                COALESCE(c.confidence, 0),
                COALESCE(c.review_status, 'unreviewed'),
                COALESCE(c.review_note, ''),
                COALESCE(c.reviewed_at, '')
            FROM sources s
            LEFT JOIN cognitive_contexts c ON c.source_id = s.id
            LEFT JOIN graph_spaces gs ON gs.id = s.graph_space_id
            ORDER BY s.imported_at DESC
            """,
            [DEFAULT_GRAPH_SPACE_ID],
        ).fetchall()
    return [
        _SourceProjection(
            source_id=row[0],
            title=row[1],
            source_type=row[2],
            imported_at=row[3],
            summary=row[4] or "",
            graph_space_id=row[5] or DEFAULT_GRAPH_SPACE_ID,
            space_name=row[6] or "Default",
            why_saved=row[7] or "",
            why_saved_status=row[8] or "unknown",
            related_project=row[9] or "",
            open_loops=_loads_json_list(row[10]),
            future_recall_questions=_loads_json_list(row[11]),
            importance=row[12] or "",
            confidence=float(row[13] or 0.0),
            review_status=row[14] or "unreviewed",
            review_note=row[15] or "",
            reviewed_at=row[16] or "",
        )
        for row in rows
    ]


def _review_item(source: _SourceProjection, evidence_count: int, topic_refs: list[dict]) -> dict:
    risk = _risk_level(source, evidence_count=evidence_count)
    return {
        "source_id": source.source_id,
        "title": source.title,
        "type": source.source_type,
        "imported_at": source.imported_at,
        "summary": source.summary,
        "graph_space_id": source.graph_space_id,
        "space_name": source.space_name,
        "why_saved": source.why_saved,
        "why_saved_status": source.why_saved_status,
        "related_project": source.related_project,
        "open_loops": source.open_loops,
        "future_recall_questions": source.future_recall_questions,
        "importance": source.importance,
        "confidence": source.confidence,
        "review_status": source.review_status,
        "review_note": source.review_note,
        "reviewed_at": source.reviewed_at,
        "risk_level": risk,
        "recommended_action": _recommended_action(source, risk),
        "evidence_count": evidence_count,
        "topic_refs": topic_refs,
        "has_open_loops": bool(source.open_loops),
        "needs_review": source.why_saved_status == "AI-inferred" and source.review_status in {"unreviewed", "deferred"},
    }


def _risk_level(source: _SourceProjection, evidence_count: int = 0) -> str:
    if source.why_saved_status == "AI-inferred" and source.review_status == "unreviewed" and source.confidence < 0.55:
        return "critical"
    if source.why_saved_status == "AI-inferred" and source.review_status == "unreviewed":
        return "high"
    if source.review_status == "deferred" or source.open_loops:
        return "medium"
    if source.why_saved_status == "AI-inferred" and evidence_count == 0:
        return "medium"
    return "low"


def _recommended_action(source: _SourceProjection, risk: str) -> str:
    if source.review_status == "deferred":
        return "resume_review"
    if source.review_status == "rejected":
        return "inspect_rejection"
    if source.why_saved_status == "AI-inferred" and source.review_status == "unreviewed":
        return "review_ai_inference"
    if source.open_loops and risk in {"critical", "high", "medium"}:
        return "inspect_open_loops"
    return "monitor"


def _matches_filters(item: dict, filters: dict) -> bool:
    if filters.get("source_id") and item["source_id"] != filters["source_id"]:
        return False
    if filters.get("status") and item["review_status"] != filters["status"]:
        return False
    if filters.get("risk") and item["risk_level"] != filters["risk"]:
        return False
    if filters.get("space_id") and filters["space_id"] != "all" and item["graph_space_id"] != filters["space_id"]:
        return False
    if filters.get("inferred") == "ai" and item["why_saved_status"] != "AI-inferred":
        return False
    if filters.get("inferred") == "user" and item["why_saved_status"] == "AI-inferred":
        return False
    if filters.get("has_open_loops") is True and not item["has_open_loops"]:
        return False
    if filters.get("has_open_loops") is False and item["has_open_loops"]:
        return False
    query = filters.get("q", "")
    if query:
        haystack = " ".join(
            [
                item["title"],
                item["summary"],
                item["why_saved"],
                item["related_project"],
                " ".join(item["open_loops"]),
                " ".join(item["future_recall_questions"]),
            ]
        ).lower()
        return query.lower() in haystack
    return True


def _normalize_filters(filters: dict | None) -> dict:
    raw = filters or {}
    normalized = {
        "source_id": str(raw.get("source_id") or "").strip(),
        "status": str(raw.get("status") or "").strip(),
        "risk": str(raw.get("risk") or "").strip(),
        "space_id": str(raw.get("space_id") or "").strip(),
        "q": str(raw.get("q") or "").strip(),
        "inferred": str(raw.get("inferred") or "").strip(),
        "has_open_loops": raw.get("has_open_loops"),
    }
    return {key: value for key, value in normalized.items() if value not in {"", None}}


def _review_sort_key(item: dict) -> tuple:
    needs_review = 0 if item["needs_review"] else 1
    risk_order = REVIEW_RISK_ORDER.get(item["risk_level"], 9)
    status_order = 0 if item["review_status"] in {"unreviewed", "deferred"} else 1
    return (needs_review, risk_order, status_order, item["imported_at"])


def _summary(items: list[dict]) -> dict:
    risk_counts = Counter(item["risk_level"] for item in items)
    status_counts = Counter(item["review_status"] for item in items)
    return {
        "total": len(items),
        "critical": risk_counts.get("critical", 0),
        "high": risk_counts.get("high", 0),
        "medium": risk_counts.get("medium", 0),
        "low": risk_counts.get("low", 0),
        "unreviewed": status_counts.get("unreviewed", 0),
        "confirmed": status_counts.get("confirmed", 0),
        "rewritten": status_counts.get("rewritten", 0),
        "rejected": status_counts.get("rejected", 0),
        "deferred": status_counts.get("deferred", 0),
        "ai_inferred": sum(1 for item in items if item["why_saved_status"] == "AI-inferred"),
        "user_stated": sum(1 for item in items if item["why_saved_status"] == "user-stated"),
        "open_loop_items": sum(1 for item in items if item["has_open_loops"]),
    }


def _evidence_counts(workspace: Workspace) -> dict[str, int]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT evidence_source_id, COUNT(*)
            FROM edges
            WHERE evidence_source_id IS NOT NULL AND evidence_source_id != ''
            GROUP BY evidence_source_id
            """
        ).fetchall()
    return {row[0]: int(row[1]) for row in rows}


def _evidence_paths(workspace: Workspace, source_id: str) -> list[dict]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT
                e.id,
                e.source,
                COALESCE(ns.label, e.source),
                e.target,
                COALESCE(nt.label, e.target),
                e.relation,
                e.confidence,
                COALESCE(e.status, 'confirmed')
            FROM edges e
            LEFT JOIN nodes ns ON ns.id = e.source
            LEFT JOIN nodes nt ON nt.id = e.target
            WHERE e.evidence_source_id = ?
            ORDER BY e.confidence DESC, e.id
            """,
            [source_id],
        ).fetchall()
    return [
        {
            "edge_id": row[0],
            "source_node_id": row[1],
            "source_label": row[2],
            "target_node_id": row[3],
            "target_label": row[4],
            "relation": row[5],
            "confidence": row[6],
            "status": row[7],
            "path": f"{row[2]} --{row[5]}--> {row[4]}",
        }
        for row in rows
    ]


def _history_rows(workspace: Workspace, source_id: str) -> list[dict]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT
                id,
                source_id,
                action,
                previous_status,
                next_status,
                note,
                previous_why_saved,
                next_why_saved,
                created_at
            FROM trust_review_history
            WHERE source_id = ?
            ORDER BY created_at DESC
            """,
            [source_id],
        ).fetchall()
    return [
        {
            "id": row[0],
            "source_id": row[1],
            "action": row[2],
            "previous_status": row[3],
            "next_status": row[4],
            "note": row[5],
            "previous_why_saved": row[6],
            "next_why_saved": row[7],
            "created_at": row[8],
        }
        for row in rows
    ]


def _history_count(workspace: Workspace) -> int:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM trust_review_history").fetchone()[0])


def _source_map_summary(workspace: Workspace, source_id: str) -> dict:
    source_node_id = f"source_{source_id}"
    with sqlite3.connect(workspace.sqlite_path) as conn:
        source_node = conn.execute(
            "SELECT COUNT(*) FROM nodes WHERE id = ?",
            [source_node_id],
        ).fetchone()[0]
        connected_edges = conn.execute(
            """
            SELECT COUNT(*)
            FROM edges
            WHERE source = ? OR target = ? OR evidence_source_id = ?
            """,
            [source_node_id, source_node_id, source_id],
        ).fetchone()[0]
    return {
        "source_node_present": bool(source_node),
        "connected_edges": int(connected_edges),
    }


def _topic_refs_by_source(workspace: Workspace) -> dict[str, list[dict]]:
    refs: dict[str, list[dict]] = {}
    with sqlite3.connect(workspace.sqlite_path) as conn:
        topic_rows = conn.execute(
            "SELECT id, title, space_id, pinned_source_ids_json FROM topics ORDER BY updated_at DESC"
        ).fetchall()
        turn_rows = conn.execute(
            """
            SELECT tt.topic_id, t.title, t.space_id, tt.evidence_source_ids_json
            FROM topic_turns tt
            JOIN topics t ON t.id = tt.topic_id
            ORDER BY tt.created_at DESC
            """
        ).fetchall()
    for topic_id, title, space_id, pinned_json in topic_rows:
        for source_id in _loads_json_list(pinned_json):
            refs.setdefault(source_id, []).append({
                "topic_id": topic_id,
                "title": title,
                "space_id": space_id,
                "role": "pinned",
            })
    for topic_id, title, space_id, evidence_json in turn_rows:
        for source_id in _loads_json_list(evidence_json):
            candidate = {
                "topic_id": topic_id,
                "title": title,
                "space_id": space_id,
                "role": "evidence",
            }
            if candidate not in refs.setdefault(source_id, []):
                refs[source_id].append(candidate)
    return refs


def _topic_open_loops(
    workspace: Workspace,
    loop_states: dict[str, dict],
    source_by_id: dict[str, _SourceProjection],
) -> list[dict]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            "SELECT id, title, pinned_source_ids_json, open_loops_json, updated_at FROM topics ORDER BY updated_at DESC"
        ).fetchall()
    loops = []
    for topic_id, title, pinned_json, open_loops_json, updated_at in rows:
        source_ids = _loads_json_list(pinned_json)
        source_titles = [
            source_by_id[source_id].title for source_id in source_ids if source_id in source_by_id
        ]
        review_status_summary = Counter(
            source_by_id[source_id].review_status for source_id in source_ids if source_id in source_by_id
        )
        evidence_count = len(source_ids)
        risk = "medium" if source_ids else "high"
        for index, text in enumerate(_loads_json_list(open_loops_json)):
            loop_id = _loop_id("topic", topic_id, index, text)
            lifecycle = loop_states.get(loop_id, {})
            loops.append({
                "loop_id": loop_id,
                "origin": "topic",
                "text": text,
                "state": lifecycle.get("state", "active"),
                "note": lifecycle.get("note", ""),
                "updated_at": lifecycle.get("updated_at", updated_at or ""),
                "source_ids": source_ids,
                "source_titles": source_titles,
                "risk_level": risk,
                "review_status_summary": dict(review_status_summary),
                "evidence_count": evidence_count,
                "topic_ids": [topic_id],
                "topic_title": title,
            })
    return loops


def _loop_state_map(workspace: Workspace) -> dict[str, dict]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            "SELECT loop_id, state, note, updated_at FROM trust_open_loop_states"
        ).fetchall()
    return {
        row[0]: {
            "state": row[1],
            "note": row[2],
            "updated_at": row[3],
        }
        for row in rows
    }


def _stored_loop_ids(workspace: Workspace) -> set[str]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute("SELECT loop_id FROM trust_open_loop_states").fetchall()
    return {row[0] for row in rows}


def _open_loop_summary(items: list[dict]) -> dict:
    by_state = Counter(item["state"] for item in items)
    by_risk = Counter(item["risk_level"] for item in items)
    return {
        "total": len(items),
        "by_state": {state: by_state.get(state, 0) for state in sorted(OPEN_LOOP_STATES)},
        "by_risk": {risk: by_risk.get(risk, 0) for risk in REVIEW_RISK_ORDER},
    }


def _loop_id(origin: str, owner_id: str, index: int, text: str) -> str:
    return hashlib.sha256(f"{origin}:{owner_id}:{index}:{text}".encode("utf-8")).hexdigest()[:16]


def _loads_json_list(value: str | None) -> list:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [item for item in parsed if item not in {"", None}]
    return []
