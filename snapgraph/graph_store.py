from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import asdict

from .models import (
    DEFAULT_GRAPH_SPACE_ID,
    CognitiveContext,
    GraphDiagnostics,
    GraphEdge,
    GraphNode,
    Source,
    is_ai_inferred_status,
    is_user_guided_status,
)
from .workspace import Workspace


def upsert_ingest_graph(
    workspace: Workspace,
    source: Source,
    context: CognitiveContext,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    return replace_source_graph(workspace, source, context)


def replace_source_graph(
    workspace: Workspace,
    source: Source,
    context: CognitiveContext,
) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes, edges = build_ingest_graph(source, context, space_id=source.graph_space_id)
    graph = load_graph(workspace)
    graph["nodes"] = [
        node
        for node in graph.get("nodes", [])
        if not _node_belongs_to_source(node, source.id)
    ]
    graph["edges"] = [
        edge
        for edge in graph.get("edges", [])
        if edge.get("evidence_source_id") != source.id
    ]
    graph["nodes"] = _upsert_items(graph.get("nodes", []), nodes)
    graph["edges"] = _upsert_items(graph.get("edges", []), edges)
    graph = _prune_orphan_support_nodes(graph)
    save_graph(workspace, graph)
    _rewrite_sqlite_graph(workspace, graph)
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


def _rewrite_sqlite_graph(workspace: Workspace, graph: dict) -> None:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute("DELETE FROM nodes")
        conn.execute("DELETE FROM edges")
    nodes = [_node_from_dict(node) for node in graph.get("nodes", [])]
    edges = [_edge_from_dict(edge) for edge in graph.get("edges", [])]
    _save_sqlite(workspace, nodes, edges)


def _edge_id(source: str, target: str, relation: str) -> str:
    digest = hashlib.sha1(f"{source}|{target}|{relation}".encode("utf-8")).hexdigest()
    return f"edge_{digest[:12]}"


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
                "user_stated": sum(
                    1 for m in members if is_user_guided_status(m["why_saved_status"])
                ),
                "ai_inferred": sum(
                    1 for m in members if is_ai_inferred_status(m["why_saved_status"])
                ),
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
        if is_ai_inferred_status(context["why_saved_status"]) and context["confidence"] < 0.7
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
        key=lambda item: (
            not is_user_guided_status(item["status"]),
            -item["confidence"],
            item["title"],
        ),
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


def _node_belongs_to_source(node: dict, source_id: str) -> bool:
    node_source_id = node.get("properties", {}).get("source_id")
    if node_source_id == source_id:
        return True
    prefixes = (
        f"source_{source_id}",
        f"thought_{source_id}",
        f"task_{source_id}_",
        f"question_{source_id}_",
    )
    return str(node.get("id", "")).startswith(prefixes)


def _prune_orphan_support_nodes(graph: dict) -> dict:
    removable_types = {"project", "question", "task", "thought"}
    changed = True
    nodes = list(graph.get("nodes", []))
    edges = list(graph.get("edges", []))
    while changed:
        changed = False
        linked = set()
        for edge in edges:
            linked.add(edge.get("source"))
            linked.add(edge.get("target"))
        kept_nodes = []
        removed_ids = set()
        for node in nodes:
            if node.get("type") in removable_types and node.get("id") not in linked:
                removed_ids.add(node.get("id"))
                changed = True
                continue
            kept_nodes.append(node)
        if removed_ids:
            nodes = kept_nodes
            edges = [
                edge
                for edge in edges
                if edge.get("source") not in removed_ids and edge.get("target") not in removed_ids
            ]
    return {"nodes": nodes, "edges": edges}


def _node_from_dict(node: dict) -> GraphNode:
    return GraphNode(
        id=str(node.get("id", "")),
        type=str(node.get("type", "unknown")),
        label=str(node.get("label", "")),
        properties=dict(node.get("properties", {})),
        graph_space_id=str(node.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID)),
        status=str(node.get("status", "confirmed")),
    )


def _edge_from_dict(edge: dict) -> GraphEdge:
    return GraphEdge(
        id=str(edge.get("id", "")),
        source=str(edge.get("source", "")),
        target=str(edge.get("target", "")),
        relation=str(edge.get("relation", "")),
        evidence_source_id=edge.get("evidence_source_id"),
        confidence=float(edge.get("confidence", 0)),
        graph_space_id=str(edge.get("graph_space_id", DEFAULT_GRAPH_SPACE_ID)),
        status=str(edge.get("status", "confirmed")),
    )
