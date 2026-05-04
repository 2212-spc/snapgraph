from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone

from .models import (
    DEFAULT_GRAPH_SPACE_ID,
    CognitiveContext,
    GraphDiagnostics,
    GraphEdge,
    GraphNode,
    Source,
)
from .workspace import Workspace


def upsert_ingest_graph(
    workspace: Workspace,
    source: Source,
    context: CognitiveContext,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes, edges = build_ingest_graph(source, context, space_id=source.graph_space_id)
    graph = load_graph(workspace)
    graph["nodes"] = _upsert_items(graph.get("nodes", []), nodes)
    graph["edges"] = _upsert_items(graph.get("edges", []), edges)
    save_graph(workspace, graph)
    _save_sqlite(workspace, nodes, edges)
    return nodes, edges


def upsert_duplicate_edges(
    workspace: Workspace,
    source: Source,
    duplicate_source_ids: list[str],
) -> list[GraphEdge]:
    edges = [
        GraphEdge(
            id=_edge_id(f"source_{source.id}", f"source_{duplicate_id}", "related_to"),
            source=f"source_{source.id}",
            target=f"source_{duplicate_id}",
            relation="related_to",
            evidence_source_id=source.id,
            confidence=1.0,
            graph_space_id=source.graph_space_id,
            status="confirmed",
        )
        for duplicate_id in duplicate_source_ids
    ]
    if not edges:
        return []

    graph = load_graph(workspace)
    graph["edges"] = _upsert_items(graph.get("edges", []), edges)
    save_graph(workspace, graph)
    _save_sqlite(workspace, [], edges)
    return edges


def build_ingest_graph(
    source: Source,
    context: CognitiveContext,
    space_id: str | None = None,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    graph_space_id = space_id or source.graph_space_id or DEFAULT_GRAPH_SPACE_ID
    source_node = GraphNode(
        id=f"source_{source.id}",
        type="source",
        label=source.title,
        properties={
            "source_id": source.id,
            "raw_path": source.path,
            "content_hash": source.content_hash,
        },
        graph_space_id=graph_space_id,
        status="confirmed",
    )
    thought_node = GraphNode(
        id=f"thought_{source.id}",
        type="thought",
        label=_short_label(context.why_saved),
        properties={
            "source_id": source.id,
            "why_saved_status": context.why_saved_status,
            "confidence": context.confidence,
        },
        graph_space_id=graph_space_id,
        status="confirmed",
    )
    nodes = [source_node, thought_node]
    edges = [
        GraphEdge(
            id=_edge_id(source_node.id, thought_node.id, "triggered_thought"),
            source=source_node.id,
            target=thought_node.id,
            relation="triggered_thought",
            evidence_source_id=source.id,
            confidence=context.confidence,
            graph_space_id=graph_space_id,
            status="confirmed",
        ),
        GraphEdge(
            id=_edge_id(source_node.id, thought_node.id, "evidence_for"),
            source=source_node.id,
            target=thought_node.id,
            relation="evidence_for",
            evidence_source_id=source.id,
            confidence=1.0,
            graph_space_id=graph_space_id,
            status="confirmed",
        ),
    ]

    for index, question in enumerate(context.future_recall_questions, start=1):
        question_node = GraphNode(
            id=f"question_{source.id}_{index}",
            type="question",
            label=question,
            properties={"source_id": source.id},
            graph_space_id=graph_space_id,
            status="proposed",
        )
        nodes.append(question_node)
        edges.append(
            GraphEdge(
                id=_edge_id(source_node.id, question_node.id, "follow_up"),
                source=source_node.id,
                target=question_node.id,
                relation="follow_up",
                evidence_source_id=source.id,
                confidence=0.9,
                graph_space_id=graph_space_id,
                status="proposed",
            )
        )

    for index, open_loop in enumerate(context.open_loops, start=1):
        task_node = GraphNode(
            id=f"task_{source.id}_{index}",
            type="task",
            label=open_loop,
            properties={"source_id": source.id},
            graph_space_id=graph_space_id,
            status="proposed",
        )
        nodes.append(task_node)
        edges.append(
            GraphEdge(
                id=_edge_id(source_node.id, task_node.id, "follow_up"),
                source=source_node.id,
                target=task_node.id,
                relation="follow_up",
                evidence_source_id=source.id,
                confidence=0.8,
                graph_space_id=graph_space_id,
                status="proposed",
            )
        )

    if context.related_project:
        project_node = GraphNode(
            id=f"project_{_slug(graph_space_id)}_{_slug(context.related_project)}",
            type="project",
            label=context.related_project,
            properties={},
            graph_space_id=graph_space_id,
            status="proposed",
        )
        nodes.append(project_node)
        edges.extend(
            [
                GraphEdge(
                    id=_edge_id(thought_node.id, project_node.id, "belongs_to"),
                    source=thought_node.id,
                    target=project_node.id,
                    relation="belongs_to",
                    evidence_source_id=source.id,
                    confidence=0.8,
                    graph_space_id=graph_space_id,
                    status="proposed",
                ),
                GraphEdge(
                    id=_edge_id(source_node.id, project_node.id, "evidence_for"),
                    source=source_node.id,
                    target=project_node.id,
                    relation="evidence_for",
                    evidence_source_id=source.id,
                    confidence=0.7,
                    graph_space_id=graph_space_id,
                    status="proposed",
                ),
            ]
        )

    return nodes, edges


def load_graph(workspace: Workspace) -> dict:
    if not workspace.graph_path.exists():
        return {"nodes": [], "edges": []}
    graph = json.loads(workspace.graph_path.read_text(encoding="utf-8"))
    return {
        "nodes": graph.get("nodes", []),
        "edges": graph.get("edges", []),
    }


def graph_for_space(workspace: Workspace, space_id: str | None) -> dict:
    graph = load_graph(workspace)
    if not space_id or space_id == "all":
        return graph

    nodes = [
        node
        for node in graph.get("nodes", [])
        if node.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID) == space_id
    ]
    node_ids = {node.get("id") for node in nodes}
    edges = [
        edge
        for edge in graph.get("edges", [])
        if edge.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID) == space_id
        and edge.get("source") in node_ids
        and edge.get("target") in node_ids
    ]
    return {"nodes": nodes, "edges": edges}


def save_graph(workspace: Workspace, graph: dict) -> None:
    workspace.graph_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_graph_layout(workspace: Workspace, view_id: str) -> dict:
    """Return saved node positions for a graph view without changing graph facts."""
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT node_id, x, y, locked, graph_space_id, updated_at
            FROM graph_layouts
            WHERE view_id = ?
            ORDER BY node_id ASC
            """,
            (view_id,),
        ).fetchall()
    return {
        "view_id": view_id,
        "positions": [
            {
                "node_id": row[0],
                "x": float(row[1]),
                "y": float(row[2]),
                "locked": bool(row[3]),
                "graph_space_id": row[4],
                "updated_at": row[5],
            }
            for row in rows
        ],
    }


def save_graph_layout(
    workspace: Workspace,
    *,
    view_id: str,
    graph_space_id: str,
    positions: list[dict],
) -> dict:
    """Persist user-arranged node coordinates for a single graph view."""
    now = _now()
    saved = 0
    with sqlite3.connect(workspace.sqlite_path) as conn:
        for position in positions:
            node_id = str(position.get("node_id", "")).strip()
            if not node_id:
                continue
            x_value = float(position.get("x", 0))
            y_value = float(position.get("y", 0))
            locked = 1 if bool(position.get("locked", False)) else 0
            row_id = _layout_id(view_id, node_id)
            conn.execute(
                """
                INSERT INTO graph_layouts (
                    id, view_id, graph_space_id, node_id, x, y, locked,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(view_id, node_id) DO UPDATE SET
                    graph_space_id = excluded.graph_space_id,
                    x = excluded.x,
                    y = excluded.y,
                    locked = excluded.locked,
                    updated_at = excluded.updated_at
                """,
                (
                    row_id,
                    view_id,
                    graph_space_id,
                    node_id,
                    x_value,
                    y_value,
                    locked,
                    now,
                    now,
                ),
            )
            saved += 1
    return {"view_id": view_id, "saved": saved}


def create_manual_edge(
    workspace: Workspace,
    *,
    source: str,
    target: str,
    relation: str,
    reason: str,
    graph_space_id: str,
) -> dict:
    """Create a user-confirmed graph edge and record the feedback reason."""
    source_id = source.strip()
    target_id = target.strip()
    relation_name = relation.strip() or "related_to"
    reason_text = " ".join(reason.strip().split())
    if not source_id or not target_id:
        raise ValueError("source and target are required")
    if source_id == target_id:
        raise ValueError("source and target must be different")
    if not reason_text:
        raise ValueError("reason is required")

    graph = load_graph(workspace)
    node_ids = {node.get("id") for node in graph.get("nodes", [])}
    if source_id not in node_ids or target_id not in node_ids:
        raise KeyError("source or target node not found")

    edge = {
        "id": _edge_id(source_id, target_id, relation_name),
        "source": source_id,
        "target": target_id,
        "relation": relation_name,
        "evidence_source_id": _edge_evidence_source_id(graph, source_id, target_id),
        "confidence": 1.0,
        "graph_space_id": graph_space_id,
        "status": "confirmed",
        "evidence_kind": "manual",
        "explanation": reason_text,
        "origin": "user",
    }
    graph["edges"] = _upsert_dict_items(graph.get("edges", []), [edge])
    save_graph(workspace, graph)
    _save_sqlite_edge_dict(workspace, edge)
    _record_graph_feedback(
        workspace,
        kind="connect",
        graph_space_id=graph_space_id,
        source_node_id=source_id,
        target_node_id=target_id,
        edge_id=edge["id"],
        reason=reason_text,
    )
    return edge


def update_graph_edge(
    workspace: Workspace,
    edge_id: str,
    *,
    status: str,
    reason: str = "",
) -> dict:
    """Update a graph edge review status and store the user's reason."""
    allowed_statuses = {"confirmed", "proposed", "rejected", "weakened", "hidden"}
    status_value = status.strip()
    if status_value not in allowed_statuses:
        raise ValueError(f"Unsupported edge status: {status}")

    graph = load_graph(workspace)
    for edge in graph.get("edges", []):
        if edge.get("id") != edge_id:
            continue
        edge["status"] = status_value
        reason_text = " ".join(reason.strip().split())
        if reason_text:
            edge[f"{status_value}_reason"] = reason_text
        save_graph(workspace, graph)
        _save_sqlite_edge_dict(workspace, edge)
        _record_graph_feedback(
            workspace,
            kind=status_value,
            graph_space_id=edge.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID),
            source_node_id=edge.get("source"),
            target_node_id=edge.get("target"),
            edge_id=edge_id,
            reason=reason_text,
        )
        return edge
    raise KeyError(edge_id)


def create_user_thought(
    workspace: Workspace,
    *,
    graph_space_id: str,
    node_ids: list[str],
    label: str,
    reason: str,
) -> dict:
    """Create a user-stated thought node that synthesizes selected graph nodes."""
    selected_ids = [node_id.strip() for node_id in node_ids if node_id.strip()]
    selected_ids = sorted(set(selected_ids))
    label_text = " ".join(label.strip().split())
    reason_text = " ".join(reason.strip().split())
    if len(selected_ids) < 2:
        raise ValueError("At least two nodes are required")
    if not label_text:
        raise ValueError("label is required")
    if not reason_text:
        raise ValueError("reason is required")

    graph = load_graph(workspace)
    existing_node_ids = {node.get("id") for node in graph.get("nodes", [])}
    missing = [node_id for node_id in selected_ids if node_id not in existing_node_ids]
    if missing:
        raise KeyError(f"Unknown node ids: {', '.join(missing)}")

    thought_id = _user_thought_id(graph_space_id, label_text, selected_ids, reason_text)
    thought_node = GraphNode(
        id=thought_id,
        type="thought",
        label=label_text,
        properties={
            "trust_status": "user-stated",
            "origin": "user",
            "reason": reason_text,
            "member_node_ids": selected_ids,
            "confidence": 1.0,
        },
        graph_space_id=graph_space_id,
        status="confirmed",
    )
    edges = [
        {
            "id": _edge_id(node_id, thought_id, "supports"),
            "source": node_id,
            "target": thought_id,
            "relation": "supports",
            "evidence_source_id": _node_source_id(graph, node_id),
            "confidence": 1.0,
            "graph_space_id": graph_space_id,
            "status": "confirmed",
            "evidence_kind": "user-stated",
            "explanation": reason_text,
            "origin": "user",
        }
        for node_id in selected_ids
    ]
    graph["nodes"] = _upsert_items(graph.get("nodes", []), [thought_node])
    graph["edges"] = _upsert_dict_items(graph.get("edges", []), edges)
    save_graph(workspace, graph)
    _save_sqlite(workspace, [thought_node], [])
    for edge in edges:
        _save_sqlite_edge_dict(workspace, edge)
    _record_graph_feedback(
        workspace,
        kind="synthesize",
        graph_space_id=graph_space_id,
        source_node_id=selected_ids[0],
        target_node_id=thought_id,
        edge_id=None,
        reason=reason_text,
    )
    return {"thought_node": asdict(thought_node), "edges_created": len(edges)}


def list_graph_themes(workspace: Workspace, space_id: str | None = None) -> list[dict]:
    """Return graph themes, optionally scoped to one graph space."""
    where = ""
    params: list[str] = []
    if space_id and space_id != "all":
        where = "WHERE graph_space_id = ?"
        params.append(space_id)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            f"""
            SELECT id, graph_space_id, label, description, member_node_ids_json,
                   origin, status, confidence, reason, created_at, updated_at
            FROM graph_themes
            {where}
            ORDER BY updated_at DESC, label ASC
            """,
            params,
        ).fetchall()
    return [_theme_from_row(row) for row in rows]


def create_graph_theme(
    workspace: Workspace,
    *,
    graph_space_id: str,
    label: str,
    member_node_ids: list[str],
    reason: str = "",
    description: str = "",
    origin: str = "user",
    status: str = "confirmed",
    confidence: float = 1.0,
) -> dict:
    """Create a graph theme that groups nodes without rewriting graph facts."""
    label_text = " ".join(label.strip().split())
    members = sorted({node_id.strip() for node_id in member_node_ids if node_id.strip()})
    if not label_text:
        raise ValueError("label is required")
    if not members:
        raise ValueError("member_node_ids are required")

    now = _now()
    theme_id = _theme_id(graph_space_id, label_text, members)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO graph_themes (
                id, graph_space_id, label, description, member_node_ids_json,
                origin, status, confidence, reason, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                label = excluded.label,
                description = excluded.description,
                member_node_ids_json = excluded.member_node_ids_json,
                origin = excluded.origin,
                status = excluded.status,
                confidence = excluded.confidence,
                reason = excluded.reason,
                updated_at = excluded.updated_at
            """,
            (
                theme_id,
                graph_space_id,
                label_text,
                description.strip(),
                json.dumps(members, ensure_ascii=False),
                origin.strip() or "user",
                status.strip() or "confirmed",
                float(confidence),
                reason.strip(),
                now,
                now,
            ),
        )
    return next(theme for theme in list_graph_themes(workspace, graph_space_id) if theme["id"] == theme_id)


def update_graph_theme(workspace: Workspace, theme_id: str, updates: dict) -> dict:
    """Update review fields for a graph theme."""
    allowed = {"label", "description", "origin", "status", "confidence", "reason"}
    assignments = []
    values: list[str | float] = []
    for key in allowed:
        if key in updates:
            assignments.append(f"{key} = ?")
            value = float(updates[key]) if key == "confidence" else str(updates[key]).strip()
            values.append(value)
    if "member_node_ids" in updates:
        assignments.append("member_node_ids_json = ?")
        members = [str(node_id).strip() for node_id in updates["member_node_ids"] if str(node_id).strip()]
        values.append(json.dumps(sorted(set(members)), ensure_ascii=False))
    if not assignments:
        themes = [theme for theme in list_graph_themes(workspace) if theme["id"] == theme_id]
        if not themes:
            raise KeyError(theme_id)
        return themes[0]
    assignments.append("updated_at = ?")
    values.append(_now())
    values.append(theme_id)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        result = conn.execute(
            f"UPDATE graph_themes SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        if result.rowcount == 0:
            raise KeyError(theme_id)
    return next(theme for theme in list_graph_themes(workspace) if theme["id"] == theme_id)


def graph_diagnostics(workspace: Workspace) -> GraphDiagnostics:
    graph = load_graph(workspace)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_by_id = {node["id"]: node for node in nodes}
    degrees = {node_id: 0 for node_id in node_by_id}
    warnings: list[str] = []

    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_by_id or target not in node_by_id:
            warnings.append(f"Broken edge {edge.get('id')}: {source} -> {target}")
            continue
        degrees[source] += 1
        degrees[target] += 1

    node_types: dict[str, int] = {}
    for node in nodes:
        node_types[node.get("type", "unknown")] = (
            node_types.get(node.get("type", "unknown"), 0) + 1
        )

    top_hubs = sorted(
        ((node_by_id[node_id]["label"], degree) for node_id, degree in degrees.items()),
        key=lambda item: item[1],
        reverse=True,
    )[:5]
    orphans = [node_by_id[node_id]["label"] for node_id, degree in degrees.items() if degree == 0]
    return GraphDiagnostics(
        node_count=len(nodes),
        edge_count=len(edges),
        node_types=node_types,
        top_hubs=top_hubs,
        orphans=orphans,
        warnings=warnings,
    )


def graph_insights(workspace: Workspace) -> dict:
    """Return human-facing cognitive graph insights for the demo UI and report."""
    contexts = _insight_context_rows(workspace)
    graph = _load_graph_safely(workspace)
    return {
        "project_clusters": _project_clusters(contexts),
        "bridge_sources": _bridge_sources(contexts, graph),
        "open_loop_hotspots": _open_loop_hotspots(contexts),
        "low_confidence_contexts": _low_confidence_contexts(contexts),
        "unassigned_sources": _unassigned_sources(contexts),
        "high_value_review_paths": _high_value_review_paths(contexts),
    }


def _upsert_items(existing: list[dict], new_items: list[GraphNode] | list[GraphEdge]) -> list[dict]:
    merged = {item["id"]: item for item in existing}
    for item in new_items:
        merged[item.id] = asdict(item)
    return sorted(merged.values(), key=lambda item: item["id"])


def _upsert_dict_items(existing: list[dict], new_items: list[dict]) -> list[dict]:
    merged = {item["id"]: item for item in existing}
    for item in new_items:
        merged[item["id"]] = item
    return sorted(merged.values(), key=lambda item: item["id"])


def _save_sqlite(
    workspace: Workspace,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
) -> None:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        for node in nodes:
            conn.execute(
                """
                INSERT OR REPLACE INTO nodes (
                    id, type, label, properties_json, graph_space_id, status
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.type,
                    node.label,
                    json.dumps(node.properties, ensure_ascii=False),
                    node.graph_space_id,
                    node.status,
                ),
            )
        for edge in edges:
            conn.execute(
                """
                INSERT OR REPLACE INTO edges (
                    id, source, target, relation, evidence_source_id, confidence,
                    graph_space_id, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge.id,
                    edge.source,
                    edge.target,
                    edge.relation,
                    edge.evidence_source_id,
                    edge.confidence,
                    edge.graph_space_id,
                    edge.status,
                ),
            )


def _save_sqlite_edge_dict(workspace: Workspace, edge: dict) -> None:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO edges (
                id, source, target, relation, evidence_source_id, confidence,
                graph_space_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                edge["id"],
                edge["source"],
                edge["target"],
                edge["relation"],
                edge.get("evidence_source_id"),
                float(edge.get("confidence", 0)),
                edge.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID),
                edge.get("status", "confirmed"),
            ),
        )


def _edge_id(source: str, target: str, relation: str) -> str:
    digest = hashlib.sha1(f"{source}|{target}|{relation}".encode("utf-8")).hexdigest()
    return f"edge_{digest[:12]}"


def _layout_id(view_id: str, node_id: str) -> str:
    digest = hashlib.sha1(f"{view_id}|{node_id}".encode("utf-8")).hexdigest()
    return f"layout_{digest[:16]}"


def _user_thought_id(
    graph_space_id: str,
    label: str,
    node_ids: list[str],
    reason: str,
) -> str:
    payload = f"{graph_space_id}|{label}|{'|'.join(node_ids)}|{reason}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"thought_user_{digest[:12]}"


def _theme_id(graph_space_id: str, label: str, node_ids: list[str]) -> str:
    payload = f"{graph_space_id}|{label}|{'|'.join(node_ids)}"
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"theme_{digest[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _node_source_id(graph: dict, node_id: str) -> str | None:
    for node in graph.get("nodes", []):
        if node.get("id") == node_id:
            value = node.get("properties", {}).get("source_id")
            return str(value) if value else None
    return None


def _edge_evidence_source_id(graph: dict, source: str, target: str) -> str | None:
    return _node_source_id(graph, source) or _node_source_id(graph, target)


def _record_graph_feedback(
    workspace: Workspace,
    *,
    kind: str,
    graph_space_id: str,
    source_node_id: str | None,
    target_node_id: str | None,
    edge_id: str | None,
    reason: str,
) -> None:
    now = _now()
    payload = f"{kind}|{graph_space_id}|{source_node_id}|{target_node_id}|{edge_id}|{reason}|{now}"
    feedback_id = f"feedback_{hashlib.sha1(payload.encode('utf-8')).hexdigest()[:16]}"
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO graph_feedback (
                id, kind, graph_space_id, source_node_id, target_node_id,
                edge_id, reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                kind,
                graph_space_id,
                source_node_id,
                target_node_id,
                edge_id,
                reason,
                now,
            ),
        )


def _theme_from_row(row: tuple) -> dict:
    return {
        "id": row[0],
        "graph_space_id": row[1],
        "label": row[2],
        "description": row[3],
        "member_node_ids": _loads_list(row[4]),
        "origin": row[5],
        "status": row[6],
        "confidence": float(row[7]),
        "reason": row[8],
        "created_at": row[9],
        "updated_at": row[10],
    }


def _short_label(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= 120:
        return cleaned
    candidate = cleaned[:120]
    for separator, minimum_index in (
        (". ", 4),
        ("。", 4),
        ("; ", 20),
        ("；", 20),
        (", ", 40),
        ("，", 40),
        (" ", 40),
    ):
        index = candidate.rfind(separator)
        if index >= minimum_index:
            return candidate[: index + len(separator)].strip()
    return candidate.strip()


def get_related_links(
    workspace: Workspace,
    source_id: str,
) -> dict[str, list[tuple[str, str]]]:
    graph = load_graph(workspace)
    node_by_id = {node["id"]: node for node in graph.get("nodes", [])}
    source_node_id = f"source_{source_id}"
    if source_node_id not in node_by_id:
        return {}

    connected_node_ids: set[str] = set()
    for edge in graph.get("edges", []):
        src = edge.get("source")
        tgt = edge.get("target")
        if src == source_node_id and tgt:
            connected_node_ids.add(tgt)
        elif tgt == source_node_id and src:
            connected_node_ids.add(src)

    links: dict[str, list[tuple[str, str]]] = {}
    for node_id in sorted(connected_node_ids):
        node = node_by_id.get(node_id, {})
        node_type = node.get("type", "")
        label = node.get("label", "")
        if node_type in ("thought", "source"):
            continue
        links.setdefault(f"{node_type}s", []).append((label, f"wiki/{node_type}s/{node_id}.md"))
    return links


def _load_graph_safely(workspace: Workspace) -> dict:
    try:
        return load_graph(workspace)
    except json.JSONDecodeError:
        return {"nodes": [], "edges": []}


def _insight_context_rows(workspace: Workspace) -> list[dict]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.title,
                s.path,
                s.summary,
                c.why_saved,
                c.why_saved_status,
                c.related_project,
                c.open_loops_json,
                c.future_recall_questions_json,
                c.confidence
            FROM sources s
            JOIN cognitive_contexts c ON c.source_id = s.id
            ORDER BY s.imported_at ASC
            """
        ).fetchall()
    return [
        {
            "source_id": row[0],
            "title": row[1],
            "raw_path": row[2],
            "summary": row[3] or "",
            "why_saved": row[4],
            "why_saved_status": row[5],
            "related_project": row[6] or "",
            "open_loops": _loads_list(row[7]),
            "future_recall_questions": _loads_list(row[8]),
            "confidence": float(row[9]),
        }
        for row in rows
    ]


def _project_clusters(contexts: list[dict]) -> list[dict]:
    clusters: dict[str, list[dict]] = {}
    for context in contexts:
        project = context["related_project"]
        if project:
            clusters.setdefault(project, []).append(context)

    result = []
    for project, members in clusters.items():
        open_loops = _unique(
            loop for member in members for loop in member["open_loops"] if loop != "None"
        )
        questions = _unique(
            question
            for member in members
            for question in member["future_recall_questions"]
            if question != "None"
        )
        result.append(
            {
                "project": project,
                "source_count": len(members),
                "user_stated": sum(1 for m in members if m["why_saved_status"] == "user-stated"),
                "ai_inferred": sum(1 for m in members if m["why_saved_status"] == "AI-inferred"),
                "average_confidence": round(
                    sum(m["confidence"] for m in members) / max(1, len(members)),
                    2,
                ),
                "sources": [
                    {
                        "source_id": m["source_id"],
                        "title": m["title"],
                        "status": m["why_saved_status"],
                        "why_saved": m["why_saved"],
                    }
                    for m in members
                ],
                "open_loops": open_loops[:5],
                "future_questions": questions[:5],
            }
        )
    return sorted(result, key=lambda item: (-item["source_count"], item["project"]))[:8]


def _bridge_sources(contexts: list[dict], graph: dict) -> list[dict]:
    degrees = _source_degrees(graph)
    bridges = []
    for context in contexts:
        signals = []
        if context["related_project"]:
            signals.append(f"project: {context['related_project']}")
        if any(loop != "None" for loop in context["open_loops"]):
            signals.append("open loop")
        if any(question != "None" for question in context["future_recall_questions"]):
            signals.append("future recall questions")
        degree = degrees.get(context["source_id"], 0)
        if degree >= 3:
            signals.append(f"{degree} graph links")
        if len(signals) < 2:
            continue
        bridges.append(
            {
                "source_id": context["source_id"],
                "title": context["title"],
                "status": context["why_saved_status"],
                "confidence": context["confidence"],
                "signals": signals,
                "why": f"Connects {', '.join(signals[:3])}.",
                "why_saved": context["why_saved"],
            }
        )
    return sorted(
        bridges,
        key=lambda item: (-len(item["signals"]), -item["confidence"], item["title"]),
    )[:8]


def _source_degrees(graph: dict) -> dict[str, int]:
    degrees: dict[str, int] = {}
    node_to_source = {
        node.get("id"): node.get("properties", {}).get("source_id")
        for node in graph.get("nodes", [])
    }
    for edge in graph.get("edges", []):
        for endpoint in (edge.get("source"), edge.get("target")):
            source_id = node_to_source.get(endpoint)
            if source_id:
                degrees[source_id] = degrees.get(source_id, 0) + 1
    return degrees


def _open_loop_hotspots(contexts: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for context in contexts:
        for loop in context["open_loops"]:
            if not loop or loop == "None":
                continue
            key = " ".join(loop.lower().split())
            entry = grouped.setdefault(
                key,
                {
                    "open_loop": loop,
                    "count": 0,
                    "sources": [],
                },
            )
            entry["count"] += 1
            entry["sources"].append(
                {
                    "source_id": context["source_id"],
                    "title": context["title"],
                    "status": context["why_saved_status"],
                }
            )
    return sorted(grouped.values(), key=lambda item: (-item["count"], item["open_loop"]))[:10]


def _low_confidence_contexts(contexts: list[dict]) -> list[dict]:
    return [
        {
            "source_id": context["source_id"],
            "title": context["title"],
            "status": context["why_saved_status"],
            "confidence": context["confidence"],
            "why_saved": context["why_saved"],
        }
        for context in contexts
        if context["why_saved_status"] == "AI-inferred" and context["confidence"] < 0.7
    ][:10]


def _unassigned_sources(contexts: list[dict]) -> list[dict]:
    return [
        {
            "source_id": context["source_id"],
            "title": context["title"],
            "status": context["why_saved_status"],
            "why_saved": context["why_saved"],
        }
        for context in contexts
        if not context["related_project"]
    ][:10]


def _high_value_review_paths(contexts: list[dict]) -> list[dict]:
    paths = []
    for context in contexts:
        if context["related_project"]:
            paths.append(
                {
                    "source_id": context["source_id"],
                    "title": context["title"],
                    "path": (
                        f"{context['title']} -> triggered_thought -> "
                        f"{_short_label(context['why_saved'])} -> belongs_to -> "
                        f"{context['related_project']}"
                    ),
                    "status": context["why_saved_status"],
                    "confidence": context["confidence"],
                    "why": "This path explains which project the saved reason supports.",
                }
            )
        for loop in context["open_loops"][:1]:
            if loop and loop != "None":
                paths.append(
                    {
                        "source_id": context["source_id"],
                        "title": context["title"],
                        "path": f"{context['title']} -> follow_up -> {loop}",
                        "status": context["why_saved_status"],
                        "confidence": context["confidence"],
                        "why": "This path turns a saved source into a next action.",
                    }
                )
    return sorted(
        paths,
        key=lambda item: (item["status"] != "user-stated", -item["confidence"], item["title"]),
    )[:10]


def _loads_list(value: str) -> list[str]:
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded]


def _unique(items) -> list[str]:
    result = []
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _slug(label: str) -> str:
    lowered = label.lower().strip()
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", lowered).strip("_")
    if slug:
        return slug
    return hashlib.sha1(label.encode("utf-8")).hexdigest()[:12]
