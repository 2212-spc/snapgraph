from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import deque

from .focus import focus_graph_for_payload
from .graph_store import graph_for_space, _short_label
from .models import DEFAULT_GRAPH_SPACE_ID
from .workspace import Workspace


def source_map_graph(workspace: Workspace, space_id: str | None) -> dict:
    """Return source-level graph: only source nodes + synthetic cross-source edges."""
    graph = graph_for_space(workspace, space_id)
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])

    # Filter to source nodes only
    source_nodes = [node for node in nodes if node.get("type") == "source"]
    node_by_id = {node.get("id"): node for node in nodes}

    # Build source_id -> thought node mapping
    source_to_thought: dict[str, dict] = {}
    source_to_task_nodes: dict[str, list[dict]] = {}
    for node in nodes:
        props = node.get("properties", {})
        source_id = props.get("source_id", "")
        if not source_id:
            continue
        if node.get("type") == "thought":
            source_to_thought[source_id] = node
        elif node.get("type") == "task":
            source_to_task_nodes.setdefault(source_id, []).append(node)

    # Build thought_id -> project connections
    thought_to_projects: dict[str, list[str]] = {}
    for edge in edges:
        if edge.get("relation") == "belongs_to" and edge.get("status") != "hidden":
            source = edge.get("source", "")
            target = edge.get("target", "")
            if source.startswith("thought_"):
                thought_to_projects.setdefault(source, []).append(target)

    # Enrich source nodes with metadata from SQLite
    source_details = _source_detail_map(workspace, space_id)
    enriched_sources: list[dict] = []
    for source_node in source_nodes:
        source_id = source_node.get("properties", {}).get("source_id", "")
        detail = source_details.get(source_id, {})
        thought_node = source_to_thought.get(source_id, {})
        tasks = source_to_task_nodes.get(source_id, [])
        thought_id = thought_node.get("id", "")

        project_name = None
        if thought_id and thought_id in thought_to_projects:
            project_ids = thought_to_projects[thought_id]
            project_labels = [
                node_by_id.get(pid, {}).get("label", pid) for pid in project_ids
            ]
            project_name = project_labels[0] if project_labels else None

        enriched_sources.append({
            "node": source_node,
            "source_detail": {
                "id": detail.get("id", source_id),
                "title": detail.get("title", source_node.get("label", "")),
                "summary": detail.get("summary", ""),
                "why_saved": detail.get("why_saved", ""),
                "why_saved_status": detail.get("why_saved_status", "unknown"),
                "confidence": detail.get("confidence", 0.0),
                "related_project": detail.get("related_project", ""),
                "open_loops": detail.get("open_loops", []),
                "space_name": detail.get("space_name", "Default"),
            },
            "thought_count": 1 if thought_node else 0,
            "task_count": len(tasks),
            "thought_label_snippet": _short_label(thought_node.get("label", ""))[:80] if thought_node else "",
            "project_name": project_name,
        })

    # Compute synthetic edges between source nodes
    synthetic_edges = _compute_synthetic_edges(
        enriched_sources, source_to_thought, thought_to_projects, edges, node_by_id
    )

    return {
        "space_id": space_id or "all",
        "sources": enriched_sources,
        "synthetic_edges": synthetic_edges,
    }


def expand_source(workspace: Workspace, source_id: str, space_id: str | None) -> dict:
    """Return the local subgraph for a single source."""
    focus = focus_graph_for_payload(
        workspace,
        {"source_id": source_id, "space_id": space_id or "all"},
    )
    return {"nodes": focus.get("nodes", []), "edges": focus.get("edges", [])}


def find_path_between_sources(
    workspace: Workspace,
    source_ids: list[str],
    space_id: str | None,
) -> dict:
    """BFS shortest path through thought/project/task nodes connecting source nodes."""
    if len(source_ids) < 2:
        raise ValueError("At least two source_ids are required")

    graph = graph_for_space(workspace, space_id)
    node_by_id = {node.get("id"): node for node in graph.get("nodes", [])}

    # Build undirected adjacency (exclude hidden edges)
    adj: dict[str, list[tuple[str, dict]]] = {}
    for edge in graph.get("edges", []):
        if edge.get("status") == "hidden":
            continue
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        if src not in node_by_id or tgt not in node_by_id:
            continue
        adj.setdefault(src, []).append((tgt, edge))
        adj.setdefault(tgt, []).append((src, edge))

    source_node_ids = [f"source_{sid}" for sid in source_ids]
    for snid in source_node_ids:
        if snid not in node_by_id:
            return {
                "path_nodes": [],
                "path_edges": [],
                "path_description": f"Source node {snid} not found in graph.",
            }

    # BFS from first source, collecting paths to all targets
    start = source_node_ids[0]
    targets = set(source_node_ids[1:])
    visited: dict[str, tuple[str | None, dict | None]] = {start: (None, None)}
    queue: deque[str] = deque([start])

    while queue and targets:
        current = queue.popleft()
        for neighbor, edge in adj.get(current, []):
            if neighbor not in visited:
                visited[neighbor] = (current, edge)
                queue.append(neighbor)
                if neighbor in targets:
                    targets.discard(neighbor)
                    if not targets:
                        break

    # Collect all nodes on paths to found targets
    found_targets = [snid for snid in source_node_ids[1:] if snid in visited]
    if not found_targets:
        return {
            "path_nodes": [],
            "path_edges": [],
            "path_description": "No path found between these sources.",
        }

    path_node_ids: set[str] = set()
    path_edges: list[dict] = []
    for target in found_targets:
        current = target
        while current is not None:
            path_node_ids.add(current)
            parent, parent_edge = visited.get(current, (None, None))
            if parent_edge:
                path_edges.append(parent_edge)
            current = parent if parent else None

    # Build ordered path (start -> ... -> first found target)
    ordered_nodes: list[str] = _reconstruct_path(start, found_targets[0], visited)
    if len(found_targets) > 1:
        for i in range(len(found_targets) - 1):
            tail = _reconstruct_path(found_targets[i], found_targets[i + 1], visited)
            if tail:
                ordered_nodes.extend(tail[1:])

    path_nodes = [
        {
            "id": node_by_id[nid].get("id"),
            "type": node_by_id[nid].get("type", "unknown"),
            "label": node_by_id[nid].get("label", ""),
            "graph_space_id": node_by_id[nid].get("graph_space_id", DEFAULT_GRAPH_SPACE_ID),
            "status": node_by_id[nid].get("status", "confirmed"),
            "properties": node_by_id[nid].get("properties", {}),
        }
        for nid in ordered_nodes
        if nid in node_by_id
    ]

    # Deduplicate path edges
    path_edge_ids: set[str] = set()
    deduped_edges: list[dict] = []
    for edge in path_edges:
        eid = edge.get("id", "")
        if eid not in path_edge_ids:
            path_edge_ids.add(eid)
            deduped_edges.append({
                "id": edge.get("id"),
                "source": edge.get("source"),
                "target": edge.get("target"),
                "relation": edge.get("relation", ""),
                "evidence_source_id": edge.get("evidence_source_id"),
                "confidence": edge.get("confidence", 0),
                "graph_space_id": edge.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID),
                "status": edge.get("status", "confirmed"),
            })

    # Build description
    descriptions: list[str] = []
    for nid in ordered_nodes:
        if nid not in node_by_id:
            continue
        node = node_by_id[nid]
        ntype = node.get("type", "")
        label = _short_label(node.get("label", ""))
        if ntype == "source":
            descriptions.append(f"「{label}」")
        elif ntype == "thought":
            descriptions.append(f"想法: {label[:40]}")
        elif ntype == "task":
            descriptions.append(f"任务: {label[:40]}")
        elif ntype == "project":
            descriptions.append(f"项目: {label}")
    path_description = " → ".join(descriptions) if descriptions else "No path found."

    return {
        "path_nodes": path_nodes,
        "path_edges": deduped_edges,
        "path_description": path_description,
    }


def _reconstruct_path(
    start: str,
    end: str,
    visited: dict[str, tuple[str | None, dict | None]],
) -> list[str]:
    """Reconstruct BFS path from end back to start."""
    path: list[str] = []
    current = end
    while current is not None:
        path.append(current)
        if current == start:
            break
        parent, _ = visited.get(current, (None, None))
        current = parent if parent else None
    path.reverse()
    if path[0] != start:
        return []
    return path


def _source_detail_map(workspace: Workspace, space_id: str | None) -> dict[str, dict]:
    """Load source details from SQLite, keyed by source_id."""
    space_filter = "" if not space_id or space_id == "all" else "WHERE s.graph_space_id = ?"
    params = [] if not space_filter else [space_id]
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                s.id, s.title, s.summary, s.graph_space_id,
                COALESCE(gs.name, 'Default'),
                c.why_saved, c.why_saved_status, c.related_project,
                c.open_loops_json, c.confidence
            FROM sources s
            LEFT JOIN cognitive_contexts c ON c.source_id = s.id
            LEFT JOIN graph_spaces gs ON gs.id = s.graph_space_id
            {space_filter}
            """,
            params,
        ).fetchall()
    result: dict[str, dict] = {}
    for row in rows:
        result[row[0]] = {
            "id": row[0],
            "title": row[1] or "",
            "summary": row[2] or "",
            "graph_space_id": row[3] or DEFAULT_GRAPH_SPACE_ID,
            "space_name": row[4] or "Default",
            "why_saved": row[5] or "",
            "why_saved_status": row[6] or "unknown",
            "related_project": row[7] or "",
            "open_loops": _loads_json_list(row[8]),
            "confidence": float(row[9]) if row[9] is not None else 0.0,
        }
    return result


def _compute_synthetic_edges(
    enriched_sources: list[dict],
    source_to_thought: dict[str, dict],
    thought_to_projects: dict[str, list[str]],
    edges: list[dict],
    node_by_id: dict[str, dict],
) -> list[dict]:
    """Compute synthetic edges between source nodes."""
    source_ids = [
        s["node"].get("properties", {}).get("source_id", "")
        for s in enriched_sources
    ]

    # Collect thought adjacency data
    source_thought_ids: dict[str, str] = {}
    for sid, thought in source_to_thought.items():
        source_thought_ids[sid] = thought.get("id", "")

    # Rule 1: Shared project
    thought_id_to_source_id: dict[str, str] = {}
    for sid, thought in source_to_thought.items():
        thought_id_to_source_id[thought.get("id", "")] = sid

    project_to_sources: dict[str, set[str]] = {}
    for thought_id, project_ids in thought_to_projects.items():
        sid = thought_id_to_source_id.get(thought_id, "")
        if not sid:
            continue
        for pid in project_ids:
            project_to_sources.setdefault(pid, set()).add(sid)

    edge_candidates: dict[str, dict] = {}

    # Rule 1: shared project -> confidence 0.7
    for pid, sids in project_to_sources.items():
        sid_list = sorted(sids)
        for i in range(len(sid_list)):
            for j in range(i + 1, len(sid_list)):
                key = _synth_edge_key(sid_list[i], sid_list[j])
                current = edge_candidates.get(key)
                confidence = 0.7
                reason = f"共享项目: {node_by_id.get(pid, {}).get('label', pid)}"
                if not current or confidence > current.get("confidence", 0):
                    edge_candidates[key] = _make_synth_edge(
                        sid_list[i], sid_list[j], confidence, reason
                    )

    # Rule 2: Thoughts connected through one intermediate node
    # For each pair of source thoughts, check if they share a neighbor
    thought_adj: dict[str, set[str]] = {}
    for edge in edges:
        if edge.get("status") == "hidden":
            continue
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        thought_adj.setdefault(src, set()).add(tgt)
        thought_adj.setdefault(tgt, set()).add(src)

    source_id_list = sorted(source_ids)
    for i in range(len(source_id_list)):
        for j in range(i + 1, len(source_id_list)):
            sid_a = source_id_list[i]
            sid_b = source_id_list[j]
            tid_a = source_thought_ids.get(sid_a, "")
            tid_b = source_thought_ids.get(sid_b, "")
            if not tid_a or not tid_b or tid_a == tid_b:
                continue

            # Check if thoughts share a neighbor
            neighbors_a = thought_adj.get(tid_a, set())
            neighbors_b = thought_adj.get(tid_b, set())
            shared = neighbors_a & neighbors_b
            direct = tid_b in neighbors_a

            if direct or shared:
                key = _synth_edge_key(sid_a, sid_b)
                current = edge_candidates.get(key)
                confidence = 0.65 if direct else 0.5
                if direct:
                    reason = "想法直接关联"
                else:
                    shared_labels = [
                        node_by_id.get(nid, {}).get("label", nid)[:30]
                        for nid in list(shared)[:2]
                    ]
                    reason = f"想法相连: {', '.join(shared_labels)}" if shared_labels else "想法相邻"
                if not current or confidence > current.get("confidence", 0):
                    edge_candidates[key] = _make_synth_edge(
                        sid_a, sid_b, confidence, reason
                    )

    return sorted(edge_candidates.values(), key=lambda e: (-e["confidence"], e["id"]))


def _make_synth_edge(
    source_id_a: str,
    source_id_b: str,
    confidence: float,
    reason: str,
) -> dict:
    sid_a = f"source_{source_id_a}"
    sid_b = f"source_{source_id_b}"
    digest = hashlib.sha1(
        f"synth|{sid_a}|{sid_b}|{reason}".encode("utf-8")
    ).hexdigest()
    return {
        "id": f"synth_{digest[:12]}",
        "source": sid_a,
        "target": sid_b,
        "relation": "related_thoughts",
        "confidence": round(confidence, 2),
        "reason": reason,
    }


def _synth_edge_key(source_id_a: str, source_id_b: str) -> str:
    return "|".join(sorted([source_id_a, source_id_b]))


def _loads_json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded]
