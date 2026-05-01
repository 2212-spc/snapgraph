from __future__ import annotations

import json
import sqlite3

from .graph_store import graph_for_space
from .models import DEFAULT_GRAPH_SPACE_ID, RetrievedContext, RetrievalResult
from .retrieval import retrieve_for_question
from .workspace import Workspace


MAX_FOCUS_NODES = 18
MAX_EVIDENCE_CARDS = 5


def focus_graph_for_payload(workspace: Workspace, payload: dict) -> dict:
    space_id = str(payload.get("space_id") or "all")
    question = str(payload.get("question") or "").strip()
    source_id = str(payload.get("source_id") or "").strip()
    node_id = str(payload.get("node_id") or "").strip()

    if question:
        retrieval = retrieve_for_question(workspace, question, space_id=space_id)
        return focus_graph_from_retrieval(workspace, retrieval, space_id=space_id)
    if source_id:
        contexts = _contexts_for_sources(workspace, [source_id], space_id=space_id)
        return _build_focus_graph(
            workspace,
            contexts=contexts,
            center={"kind": "source", "label": contexts[0].title if contexts else source_id},
            space_id=space_id,
        )
    if node_id:
        source_id = _source_id_for_node(workspace, node_id, space_id=space_id)
        contexts = _contexts_for_sources(workspace, [source_id], space_id=space_id) if source_id else []
        return _build_focus_graph(
            workspace,
            contexts=contexts,
            center={"kind": "node", "label": node_id},
            space_id=space_id,
        )
    return _empty_focus_graph(center={"kind": "none", "label": ""}, space_id=space_id)


def focus_graph_from_retrieval(
    workspace: Workspace,
    retrieval: RetrievalResult,
    *,
    space_id: str | None,
) -> dict:
    return _build_focus_graph(
        workspace,
        contexts=_rank_contexts(retrieval.contexts),
        center={"kind": "question", "label": retrieval.question},
        space_id=space_id or "all",
    )


def _build_focus_graph(
    workspace: Workspace,
    *,
    contexts: list[RetrievedContext],
    center: dict,
    space_id: str,
) -> dict:
    if not contexts:
        return _empty_focus_graph(center=center, space_id=space_id)

    graph = graph_for_space(workspace, space_id)
    node_by_id = {node.get("id"): dict(node) for node in graph.get("nodes", [])}
    selected_source_ids = [context.source_id for context in contexts[:MAX_EVIDENCE_CARDS]]
    selected_node_ids: list[str] = []
    selected_edges: list[dict] = []

    for source_id in selected_source_ids:
        source_node_id = f"source_{source_id}"
        _append_unique(selected_node_ids, source_node_id)
        source_edges = [
            edge
            for edge in graph.get("edges", [])
            if edge.get("evidence_source_id") == source_id
            and (edge.get("source") == source_node_id or edge.get("target") == source_node_id)
        ]
        source_edges = _rank_edges(source_edges)[:3]
        for edge in source_edges:
            selected_edges.append(dict(edge))
            _append_unique(selected_node_ids, edge.get("source"))
            _append_unique(selected_node_ids, edge.get("target"))

    compact_node_ids_ordered = sorted(
        (node_id for node_id in selected_node_ids if node_id in node_by_id),
        key=lambda node_id: (_node_order(node_by_id[node_id]), selected_node_ids.index(node_id)),
    )[:MAX_FOCUS_NODES]
    compact_nodes = [_focus_node(node_by_id[node_id]) for node_id in compact_node_ids_ordered]
    compact_node_ids = {node["id"] for node in compact_nodes}
    compact_edges = [
        _focus_edge(edge)
        for edge in selected_edges
        if edge.get("source") in compact_node_ids and edge.get("target") in compact_node_ids
    ]

    evidence_cards = _evidence_cards(contexts[:MAX_EVIDENCE_CARDS])
    open_loops = [
        loop
        for card in evidence_cards
        for loop in card["open_loops"]
        if loop and loop != "None"
    ][:5]
    return {
        "center": center,
        "space_id": space_id,
        "nodes": compact_nodes,
        "edges": compact_edges,
        "evidence_cards": evidence_cards,
        "open_loops": open_loops,
        "confidence_summary": _confidence_summary(contexts),
    }


def _empty_focus_graph(center: dict, space_id: str) -> dict:
    return {
        "center": center,
        "space_id": space_id,
        "nodes": [],
        "edges": [],
        "evidence_cards": [],
        "open_loops": [],
        "confidence_summary": {
            "source_count": 0,
            "user_stated": 0,
            "ai_inferred": 0,
            "confidence_label": "low",
        },
    }


def _rank_contexts(contexts: list[RetrievedContext]) -> list[RetrievedContext]:
    return sorted(
        contexts,
        key=lambda context: (
            context.why_saved_status != "user-stated",
            not any(loop and loop != "None" for loop in context.open_loops),
            context.title,
        ),
    )


def _rank_edges(edges: list[dict]) -> list[dict]:
    relation_order = {
        "triggered_thought": 0,
        "belongs_to": 1,
        "follow_up": 2,
        "evidence_for": 3,
    }
    return sorted(
        edges,
        key=lambda edge: (
            relation_order.get(edge.get("relation", ""), 9),
            edge.get("target", ""),
        ),
    )


def _append_unique(items: list[str], value: str | None) -> None:
    if value and value not in items:
        items.append(value)


def _node_order(node: dict) -> int:
    return {
        "source": 0,
        "thought": 1,
        "project": 2,
        "task": 3,
        "question": 4,
    }.get(node.get("type", ""), 9)


def _focus_node(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "type": node.get("type", "unknown"),
        "label": node.get("label", ""),
        "graph_space_id": node.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID),
        "status": node.get("status", "confirmed"),
        "properties": node.get("properties", {}),
    }


def _focus_edge(edge: dict) -> dict:
    return {
        "id": edge.get("id"),
        "source": edge.get("source"),
        "target": edge.get("target"),
        "relation": edge.get("relation", ""),
        "evidence_source_id": edge.get("evidence_source_id"),
        "confidence": edge.get("confidence", 0),
        "graph_space_id": edge.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID),
        "status": edge.get("status", "confirmed"),
    }


def _evidence_cards(contexts: list[RetrievedContext]) -> list[dict]:
    return [
        {
            "source_id": context.source_id,
            "title": context.title,
            "space_id": context.graph_space_id,
            "space_name": context.space_name,
            "why_saved": context.why_saved,
            "why_saved_status": context.why_saved_status,
            "related_project": context.related_project or "",
            "open_loops": context.open_loops,
            "future_recall_questions": context.future_recall_questions,
            "source_excerpt": context.source_excerpt,
        }
        for context in contexts
    ]


def _confidence_summary(contexts: list[RetrievedContext]) -> dict:
    user_stated = sum(1 for context in contexts if context.why_saved_status == "user-stated")
    ai_inferred = sum(1 for context in contexts if context.why_saved_status == "AI-inferred")
    if user_stated >= 2:
        label = "strong"
    elif user_stated == 1:
        label = "mixed"
    else:
        label = "weak"
    return {
        "source_count": len(contexts),
        "user_stated": user_stated,
        "ai_inferred": ai_inferred,
        "confidence_label": label,
    }


def _contexts_for_sources(
    workspace: Workspace,
    source_ids: list[str],
    *,
    space_id: str,
) -> list[RetrievedContext]:
    if not source_ids:
        return []
    placeholders = ",".join("?" for _ in source_ids)
    query = f"""
        SELECT
            s.id,
            s.title,
            c.why_saved,
            c.why_saved_status,
            c.related_project,
            c.open_loops_json,
            c.future_recall_questions_json,
            s.graph_space_id,
            COALESCE(gs.name, 'Default')
        FROM sources s
        JOIN cognitive_contexts c ON c.source_id = s.id
        LEFT JOIN graph_spaces gs ON gs.id = s.graph_space_id
        WHERE s.id IN ({placeholders})
    """
    params: list[str] = list(source_ids)
    if space_id != "all":
        query += " AND s.graph_space_id = ?"
        params.append(space_id)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(query, params).fetchall()

    contexts = []
    for row in rows:
        page_path = workspace.wiki_dir / "sources" / f"{row[0]}.md"
        contexts.append(
            RetrievedContext(
                source_id=row[0],
                source_page=workspace.relative_to_workspace(page_path),
                title=row[1],
                why_saved=row[2],
                why_saved_status=row[3],
                related_project=row[4],
                open_loops=_loads_list(row[5]),
                future_recall_questions=_loads_list(row[6]),
                graph_space_id=row[7] or DEFAULT_GRAPH_SPACE_ID,
                space_name=row[8] or "Default",
                source_excerpt=_source_excerpt(page_path),
            )
        )
    return _rank_contexts(contexts)


def _source_id_for_node(workspace: Workspace, node_id: str, *, space_id: str) -> str:
    graph = graph_for_space(workspace, space_id)
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            return node.get("properties", {}).get("source_id", "")
    return ""


def _source_excerpt(page_path) -> str:
    if not page_path.exists():
        return ""
    text = page_path.read_text(encoding="utf-8")
    for heading in ("## Key Details", "## Objective Summary"):
        if heading not in text:
            continue
        tail = text.split(heading, 1)[1].lstrip()
        if "\n## " in tail:
            tail = tail.split("\n## ", 1)[0]
        cleaned = " ".join(
            line.strip().lstrip("-").strip()
            for line in tail.splitlines()
            if line.strip()
        )
        if cleaned:
            return cleaned[:420]
    return ""


def _loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded]
