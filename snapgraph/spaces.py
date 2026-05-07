from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone

from .graph_store import load_graph, save_graph
from .models import DEFAULT_GRAPH_SPACE_ID, INBOX_GRAPH_SPACE_ID
from .wiki import append_log_event
from .workspace import Workspace, create_workspace


def list_graph_spaces(workspace: Workspace) -> list[dict]:
    create_workspace(workspace)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT id, name, description, purpose, color, status, created_at, updated_at
            FROM graph_spaces
            ORDER BY
                CASE id
                    WHEN ? THEN 0
                    WHEN ? THEN 1
                    ELSE 2
                END,
                updated_at DESC,
                name ASC
            """,
            (INBOX_GRAPH_SPACE_ID, DEFAULT_GRAPH_SPACE_ID),
        ).fetchall()
        source_counts = _counts_by_space(conn, "sources")
        node_counts = _counts_by_space(conn, "nodes")
        edge_counts = _counts_by_space(conn, "edges")
        suggestion_counts = {
            row[0]: row[1]
            for row in conn.execute(
                """
                SELECT graph_space_id, COUNT(*)
                FROM suggestions
                WHERE status = 'pending'
                GROUP BY graph_space_id
                """
            ).fetchall()
        }

    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "purpose": row[3],
            "color": row[4],
            "status": row[5],
            "created_at": row[6],
            "updated_at": row[7],
            "source_count": source_counts.get(row[0], 0),
            "node_count": node_counts.get(row[0], 0),
            "edge_count": edge_counts.get(row[0], 0),
            "pending_suggestions": suggestion_counts.get(row[0], 0),
        }
        for row in rows
    ]


def create_graph_space(
    workspace: Workspace,
    *,
    name: str,
    description: str = "",
    purpose: str = "",
    color: str = "#315ea8",
) -> dict:
    create_workspace(workspace)
    cleaned_name = " ".join(name.strip().split())
    if not cleaned_name:
        raise ValueError("Space name is required")
    space_id = _unique_space_id(workspace, cleaned_name)
    now = _now()
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO graph_spaces (
                id, name, description, purpose, color, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (
                space_id,
                cleaned_name,
                description.strip(),
                purpose.strip(),
                color.strip() or "#315ea8",
                now,
                now,
            ),
        )
    return get_graph_space(workspace, space_id)


def update_graph_space(workspace: Workspace, space_id: str, updates: dict) -> dict:
    create_workspace(workspace)
    allowed = {"name", "description", "purpose", "color", "status"}
    assignments = []
    values = []
    for key in allowed:
        if key in updates:
            assignments.append(f"{key} = ?")
            values.append(str(updates[key]).strip())
    if not assignments:
        return get_graph_space(workspace, space_id)
    assignments.append("updated_at = ?")
    values.append(_now())
    values.append(space_id)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        result = conn.execute(
            f"UPDATE graph_spaces SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        if result.rowcount == 0:
            raise KeyError(space_id)
    return get_graph_space(workspace, space_id)


def get_graph_space(workspace: Workspace, space_id: str) -> dict:
    rows = list_graph_spaces(workspace)
    for row in rows:
        if row["id"] == space_id:
            return row
    raise KeyError(space_id)


def upsert_material(
    workspace: Workspace,
    *,
    source_id: str,
    graph_space_id: str,
    routing_status: str = "placed",
    routing_reason: str = "",
) -> None:
    create_workspace(workspace)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO materials (
                id, source_id, graph_space_id, routing_status, routing_reason, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_id) DO UPDATE SET
                graph_space_id = excluded.graph_space_id,
                routing_status = excluded.routing_status,
                routing_reason = excluded.routing_reason
            """,
            (
                f"mat_{source_id}",
                source_id,
                graph_space_id,
                routing_status,
                routing_reason,
                _now(),
            ),
        )


def create_route_suggestion(workspace: Workspace, source_id: str) -> dict:
    create_workspace(workspace)
    profile = _source_profile(workspace, source_id)
    spaces = [space for space in list_graph_spaces(workspace) if space["status"] == "active"]
    target, alternatives, confidence, reason = _choose_target_space(profile, spaces)
    suggestion_id = _suggestion_id(source_id, target["id"], reason)
    payload = {
        "source_id": source_id,
        "current_space_id": profile["graph_space_id"],
        "target_space_id": target["id"],
        "target_space_name": target["name"],
        "alternatives": alternatives,
    }
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO suggestions (
                id, graph_space_id, kind, payload_json, reason, confidence, status, created_at
            ) VALUES (?, ?, 'route_material', ?, ?, ?, 'pending', ?)
            """,
            (
                suggestion_id,
                target["id"],
                json.dumps(payload, ensure_ascii=False),
                reason,
                confidence,
                _now(),
            ),
        )
        conn.execute(
            """
            UPDATE materials
            SET routing_status = 'suggested', routing_reason = ?
            WHERE source_id = ?
            """,
            (reason, source_id),
        )
    return get_suggestion(workspace, suggestion_id)


def list_suggestions(
    workspace: Workspace,
    *,
    status: str | None = None,
    space_id: str | None = None,
) -> list[dict]:
    create_workspace(workspace)
    clauses = []
    values: list[str] = []
    if status:
        clauses.append("status = ?")
        values.append(status)
    if space_id and space_id != "all":
        clauses.append("graph_space_id = ?")
        values.append(space_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            f"""
            SELECT id, graph_space_id, kind, payload_json, reason, confidence, status, created_at
            FROM suggestions
            {where}
            ORDER BY created_at DESC
            """,
            values,
        ).fetchall()
    return [_suggestion_from_row(row) for row in rows]


def get_suggestion(workspace: Workspace, suggestion_id: str) -> dict:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT id, graph_space_id, kind, payload_json, reason, confidence, status, created_at
            FROM suggestions
            WHERE id = ?
            """,
            (suggestion_id,),
        ).fetchone()
    if not row:
        raise KeyError(suggestion_id)
    return _suggestion_from_row(row)


def accept_suggestion(workspace: Workspace, suggestion_id: str) -> dict:
    suggestion = get_suggestion(workspace, suggestion_id)
    if suggestion["status"] != "pending":
        return suggestion
    if suggestion["kind"] == "route_material":
        payload = suggestion["payload"]
        move_source_to_space(
            workspace,
            payload["source_id"],
            payload["target_space_id"],
            reason=suggestion["reason"],
        )
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            "UPDATE suggestions SET status = 'accepted' WHERE id = ?",
            (suggestion_id,),
        )
    return get_suggestion(workspace, suggestion_id)


def reject_suggestion(workspace: Workspace, suggestion_id: str) -> dict:
    suggestion = get_suggestion(workspace, suggestion_id)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            "UPDATE suggestions SET status = 'rejected' WHERE id = ?",
            (suggestion_id,),
        )
        if suggestion["kind"] == "route_material":
            conn.execute(
                """
                UPDATE materials
                SET routing_status = 'rejected', routing_reason = ?
                WHERE source_id = ?
                """,
                (suggestion["reason"], suggestion["payload"].get("source_id")),
            )
    return get_suggestion(workspace, suggestion_id)


def move_source_to_space(
    workspace: Workspace,
    source_id: str,
    space_id: str,
    *,
    reason: str = "",
) -> None:
    create_workspace(workspace)
    get_graph_space(workspace, space_id)
    content_hash, _current_space_id = _source_route_profile(workspace, source_id)
    duplicate_source_id = _duplicate_source_id_in_space(
        workspace,
        content_hash=content_hash,
        graph_space_id=space_id,
        excluded_source_id=source_id,
    )
    if duplicate_source_id is not None:
        raise ValueError(
            "duplicate content_hash already exists in target space as "
            f"{duplicate_source_id}"
        )

    graph = load_graph(workspace)
    node_ids_to_move = _source_node_ids(graph, source_id)
    for node in graph.get("nodes", []):
        if node.get("id") in node_ids_to_move:
            node["graph_space_id"] = space_id
    for edge in graph.get("edges", []):
        if edge.get("evidence_source_id") == source_id:
            edge["graph_space_id"] = space_id
    save_graph(workspace, graph)

    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            "UPDATE sources SET graph_space_id = ? WHERE id = ?",
            (space_id, source_id),
        )
        conn.executemany(
            "UPDATE nodes SET graph_space_id = ? WHERE id = ?",
            [(space_id, node_id) for node_id in node_ids_to_move],
        )
        conn.execute(
            "UPDATE edges SET graph_space_id = ? WHERE evidence_source_id = ?",
            (space_id, source_id),
        )
    upsert_material(
        workspace,
        source_id=source_id,
        graph_space_id=space_id,
        routing_status="placed",
        routing_reason=reason,
    )
    append_log_event(
        workspace,
        operation="space_route_accept",
        source_id=source_id,
        touched_pages=[
            workspace.relative_to_workspace(workspace.graph_path),
            workspace.relative_to_workspace(workspace.sqlite_path),
        ],
    )


def _source_route_profile(workspace: Workspace, source_id: str) -> tuple[str, str]:
    """Return the content hash and current graph space for a source being routed."""
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT content_hash, graph_space_id
            FROM sources
            WHERE id = ?
            """,
            (source_id,),
        ).fetchone()
    if row is None:
        raise KeyError(source_id)
    return row[0], row[1] or DEFAULT_GRAPH_SPACE_ID


def _duplicate_source_id_in_space(
    workspace: Workspace,
    *,
    content_hash: str,
    graph_space_id: str,
    excluded_source_id: str,
) -> str | None:
    """Find another source with the same exact content in the target space."""
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT id
            FROM sources
            WHERE content_hash = ?
              AND graph_space_id = ?
              AND id != ?
            ORDER BY imported_at ASC, id ASC
            LIMIT 1
            """,
            (content_hash, graph_space_id, excluded_source_id),
        ).fetchone()
    return row[0] if row else None


def _counts_by_space(conn: sqlite3.Connection, table: str) -> dict[str, int]:
    return {
        row[0]: row[1]
        for row in conn.execute(
            f"SELECT graph_space_id, COUNT(*) FROM {table} GROUP BY graph_space_id"
        ).fetchall()
    }


def _source_profile(workspace: Workspace, source_id: str) -> dict:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT
                s.id,
                s.title,
                s.summary,
                s.graph_space_id,
                c.why_saved,
                c.related_project,
                c.open_loops_json
            FROM sources s
            LEFT JOIN cognitive_contexts c ON c.source_id = s.id
            WHERE s.id = ?
            """,
            (source_id,),
        ).fetchone()
    if not row:
        raise KeyError(source_id)
    return {
        "source_id": row[0],
        "title": row[1] or "",
        "summary": row[2] or "",
        "graph_space_id": row[3] or INBOX_GRAPH_SPACE_ID,
        "why_saved": row[4] or "",
        "related_project": row[5] or "",
        "open_loops": _loads_list(row[6]),
    }


def _choose_target_space(profile: dict, spaces: list[dict]) -> tuple[dict, list[dict], float, str]:
    searchable = " ".join(
        [
            profile["title"],
            profile["summary"],
            profile["why_saved"],
            profile["related_project"],
            " ".join(profile["open_loops"]),
        ]
    ).lower()
    scored = []
    for space in spaces:
        if space["id"] == INBOX_GRAPH_SPACE_ID:
            continue
        terms = _terms(" ".join([space["name"], space["description"], space["purpose"]]))
        score = sum(1 for term in terms if term and term in searchable)
        if profile["related_project"] and profile["related_project"].lower() in space["name"].lower():
            score += 3
        scored.append((score, space))
    scored.sort(key=lambda item: (-item[0], item[1]["name"]))
    best_score, best_space = scored[0] if scored else (0, _default_space(spaces))
    if best_score <= 0:
        best_space = _default_space(spaces)
        confidence = 0.52
        reason = "没有明显更强的空间匹配，先保留为可复查的“默认空间”建议。"
    else:
        confidence = min(0.88, 0.58 + best_score * 0.1)
        reason = (
            f"根据标题、保存理由和相关项目文本，当前更匹配“{best_space['name']}”。"
        )
    alternatives = [
        {
            "space_id": space["id"],
            "space_name": space["name"],
            "score": score,
        }
        for score, space in scored[1:4]
    ]
    return best_space, alternatives, round(confidence, 2), reason


def _default_space(spaces: list[dict]) -> dict:
    for space in spaces:
        if space["id"] == DEFAULT_GRAPH_SPACE_ID:
            return space
    return spaces[0]


def _source_node_ids(graph: dict, source_id: str) -> set[str]:
    node_by_id = {node.get("id"): node for node in graph.get("nodes", [])}
    node_ids = {
        node_id
        for node_id, node in node_by_id.items()
        if node.get("properties", {}).get("source_id") == source_id
    }
    for edge in graph.get("edges", []):
        if edge.get("evidence_source_id") != source_id:
            continue
        for endpoint in (edge.get("source"), edge.get("target")):
            endpoint_node = node_by_id.get(endpoint, {})
            endpoint_source_id = endpoint_node.get("properties", {}).get("source_id")
            if endpoint_source_id in (None, source_id):
                node_ids.add(endpoint)
    return {node_id for node_id in node_ids if node_id}


def _suggestion_from_row(row: tuple) -> dict:
    return {
        "id": row[0],
        "graph_space_id": row[1],
        "kind": row[2],
        "payload": json.loads(row[3]),
        "reason": row[4],
        "confidence": float(row[5]),
        "status": row[6],
        "created_at": row[7],
    }


def _unique_space_id(workspace: Workspace, name: str) -> str:
    base = _slug(name) or "space"
    candidate = base
    with sqlite3.connect(workspace.sqlite_path) as conn:
        existing = {
            row[0] for row in conn.execute("SELECT id FROM graph_spaces").fetchall()
        }
    if candidate not in existing:
        return candidate
    digest = hashlib.sha1(f"{name}|{_now()}".encode("utf-8")).hexdigest()[:6]
    return f"{base}_{digest}"


def _suggestion_id(source_id: str, target_space_id: str, reason: str) -> str:
    digest = hashlib.sha1(
        f"{source_id}|{target_space_id}|{reason}|{_now()}".encode("utf-8")
    ).hexdigest()
    return f"sug_{digest[:12]}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "_", value.lower()).strip("_")
    return slug[:48]


def _terms(value: str) -> set[str]:
    return {
        term.lower()
        for term in re.findall(r"[a-z0-9]+[a-z0-9_-]*|[\u4e00-\u9fff]+", value.lower())
        if len(term) >= 2
    }


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


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
