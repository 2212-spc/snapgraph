from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


def build_graph_evidence_pack(graph: dict[str, Any], *, space_id: str | None = "all") -> dict[str, Any]:
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])
    node_by_id = {str(node.get("id")): node for node in nodes}
    routes = _evidence_routes(nodes, edges, node_by_id)
    coverage = _source_coverage(nodes, edges)
    integrity = _integrity(nodes, edges, node_by_id)
    return {
        "summary": {
            "space_id": space_id or "all",
            "node_count": len(nodes),
            "edge_count": len(edges),
            "source_node_count": sum(1 for node in nodes if node.get("type") == "source"),
            "evidence_route_count": len(routes),
            "quality_label": _quality_label(nodes, edges, routes, integrity),
        },
        "evidence_routes": routes[:12],
        "source_coverage": coverage,
        "integrity": integrity,
        "relation_profile": _relation_profile(edges),
        "node_profile": _node_profile(nodes),
        "repair_plan": _repair_plan(coverage, integrity, routes),
        "display_policy": {
            "collapse_low_value_edges": True,
            "max_visible_routes": 4,
            "max_visible_orphans": 5,
            "show_quality_before_canvas": True,
            "reason": "Graph quality should explain evidence value without forcing visual graph inspection.",
        },
    }


def _evidence_routes(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    node_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        outgoing[str(edge.get("source"))].append(edge)
        incoming[str(edge.get("target"))].append(edge)
    routes = []
    for node in nodes:
        if node.get("type") != "source":
            continue
        source_id = str(node.get("id"))
        first_edges = outgoing.get(source_id, []) + incoming.get(source_id, [])
        route_edges = []
        targets = []
        for edge in first_edges:
            other_id = edge.get("target") if edge.get("source") == source_id else edge.get("source")
            other = node_by_id.get(str(other_id), {})
            route_edges.append(edge)
            targets.append(other)
        routes.append(
            {
                "source_node_id": source_id,
                "source_label": node.get("label", source_id),
                "route_strength": _route_strength(route_edges, targets),
                "relations": sorted({str(edge.get("relation") or "unknown") for edge in route_edges}),
                "target_labels": [target.get("label", target.get("id", "")) for target in targets[:5]],
                "has_thought": any(target.get("type") == "thought" for target in targets),
                "has_project": any(target.get("type") == "project" for target in targets),
                "has_task": any(target.get("type") == "task" for target in targets),
                "default_collapsed": len(route_edges) > 3,
            }
        )
    routes.sort(key=lambda item: (-item["route_strength"]["score"], item["source_label"]))
    return routes


def _source_coverage(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    source_nodes = [node for node in nodes if node.get("type") == "source"]
    linked_sources = set()
    evidence_sources = set()
    for edge in edges:
        if edge.get("source", "").startswith("source_"):
            linked_sources.add(edge.get("source"))
        if edge.get("target", "").startswith("source_"):
            linked_sources.add(edge.get("target"))
        if edge.get("evidence_source_id"):
            evidence_sources.add(edge.get("evidence_source_id"))
    source_ids = {node.get("id") for node in source_nodes}
    unlinked = sorted(source_ids - linked_sources)
    coverage = 0 if not source_ids else round((len(source_ids) - len(unlinked)) / len(source_ids) * 100)
    return {
        "source_total": len(source_nodes),
        "linked_source_count": len(source_ids) - len(unlinked),
        "unlinked_source_ids": unlinked[:20],
        "evidence_source_count": len(evidence_sources),
        "coverage_percent": coverage,
        "plain_language": _coverage_copy(coverage, len(unlinked)),
    }


def _integrity(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    node_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    broken_edges = []
    linked = set()
    duplicate_node_labels = []
    seen_labels = set()
    for node in nodes:
        label_key = (node.get("type", ""), node.get("label", ""))
        if label_key in seen_labels:
            duplicate_node_labels.append({"type": label_key[0], "label": label_key[1]})
        seen_labels.add(label_key)
    for edge in edges:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        if source not in node_by_id or target not in node_by_id:
            broken_edges.append(edge.get("id", ""))
        else:
            linked.add(source)
            linked.add(target)
    orphans = [
        {
            "node_id": str(node.get("id")),
            "label": node.get("label", ""),
            "type": node.get("type", "unknown"),
        }
        for node in nodes
        if str(node.get("id")) not in linked
    ]
    return {
        "broken_edge_ids": broken_edges,
        "orphan_nodes": orphans[:30],
        "duplicate_node_labels": duplicate_node_labels[:30],
        "has_integrity_issue": bool(broken_edges or orphans or duplicate_node_labels),
        "plain_language": _integrity_copy(broken_edges, orphans, duplicate_node_labels),
    }


def _relation_profile(edges: list[dict[str, Any]]) -> dict[str, Any]:
    relation_counts = Counter(str(edge.get("relation") or "unknown") for edge in edges)
    status_counts = Counter(str(edge.get("status") or "confirmed") for edge in edges)
    confidence_bands = Counter(_confidence_band(float(edge.get("confidence") or 0)) for edge in edges)
    return {
        "relation_counts": dict(relation_counts),
        "status_counts": dict(status_counts),
        "confidence_bands": dict(confidence_bands),
        "dominant_relation": relation_counts.most_common(1)[0][0] if relation_counts else "",
    }


def _node_profile(nodes: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts = Counter(str(node.get("type") or "unknown") for node in nodes)
    status_counts = Counter(str(node.get("status") or "confirmed") for node in nodes)
    return {
        "type_counts": dict(type_counts),
        "status_counts": dict(status_counts),
        "dominant_type": type_counts.most_common(1)[0][0] if type_counts else "",
    }


def _repair_plan(
    coverage: dict[str, Any],
    integrity: dict[str, Any],
    routes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    plan = []
    if integrity["broken_edge_ids"]:
        plan.append(_action("fix_broken_edges", "Fix broken graph edges", f"{len(integrity['broken_edge_ids'])} edge(s) point to missing nodes.", 1))
    if coverage["unlinked_source_ids"]:
        plan.append(_action("connect_sources", "Connect unlinked sources", f"{len(coverage['unlinked_source_ids'])} source node(s) lack evidence routes.", 2))
    weak_routes = [route for route in routes if route["route_strength"]["label"] in {"weak", "thin"}]
    if weak_routes:
        plan.append(_action("review_weak_routes", "Review weak evidence routes", f"{len(weak_routes)} source route(s) are weak or thin.", 3))
    if integrity["duplicate_node_labels"]:
        plan.append(_action("merge_duplicate_labels", "Inspect duplicate labels", f"{len(integrity['duplicate_node_labels'])} duplicate label(s) exist.", 4))
    if not plan:
        plan.append(_action("use_graph", "Use graph evidence", "Graph evidence is available for recall and trust review.", 1))
    return plan


def _route_strength(edges: list[dict[str, Any]], targets: list[dict[str, Any]]) -> dict[str, Any]:
    score = 0
    score += min(len(edges), 5) * 12
    score += 15 if any(target.get("type") == "thought" for target in targets) else 0
    score += 10 if any(target.get("type") == "project" for target in targets) else 0
    score += 6 if any(target.get("type") == "task" for target in targets) else 0
    score += sum(int(float(edge.get("confidence") or 0) * 5) for edge in edges[:5])
    score = max(0, min(100, score))
    if score >= 70:
        label = "strong"
    elif score >= 45:
        label = "usable"
    elif score >= 20:
        label = "thin"
    else:
        label = "weak"
    return {
        "score": score,
        "label": label,
        "edge_count": len(edges),
    }


def _quality_label(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    integrity: dict[str, Any],
) -> str:
    if not nodes:
        return "empty"
    if integrity["broken_edge_ids"]:
        return "broken"
    strong_routes = sum(1 for route in routes if route["route_strength"]["label"] in {"strong", "usable"})
    if strong_routes >= max(1, len(routes) // 2):
        return "evidence_ready"
    if edges:
        return "forming"
    return "thin"


def _confidence_band(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.55:
        return "medium"
    if confidence > 0:
        return "low"
    return "unknown"


def _action(action_id: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": action_id,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


def _coverage_copy(percent: int, unlinked: int) -> str:
    if percent == 100:
        return "All source nodes have at least one graph connection."
    if unlinked:
        return f"{unlinked} source node(s) still need graph connections."
    return "Source coverage is still forming."


def _integrity_copy(
    broken_edges: list[str],
    orphans: list[dict[str, Any]],
    duplicates: list[dict[str, Any]],
) -> str:
    if broken_edges:
        return f"{len(broken_edges)} broken edge(s) need repair."
    if orphans:
        return f"{len(orphans)} orphan node(s) should stay collapsed by default."
    if duplicates:
        return f"{len(duplicates)} duplicate node label(s) should be reviewed."
    return "No major graph integrity issue detected."
