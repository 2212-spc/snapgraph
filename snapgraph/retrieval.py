from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from .config import load_config
from .graph_store import graph_for_space, load_graph
from .models import (
    DEFAULT_GRAPH_SPACE_ID,
    RetrievedContext,
    RetrievalDiagnostics,
    RetrievalResult,
    is_ai_inferred_status,
    is_user_guided_status,
)
from .workspace import Workspace


MIN_RETRIEVAL_SCORE = 0.001
QUERY_STOPWORDS = {
    "我",
    "刚才",
    "之前",
    "当时",
    "那份",
    "这份",
    "那张",
    "这个",
    "那个",
    "找回",
    "寻找",
    "记得",
    "觉得",
    "真正",
    "容易",
    "关系",
    "是什",
    "有什",
    "么关",
    "的是",
    "请",
    "不要",
    "什么",
    "为什么",
    "这个",
    "现在",
    "应该",
    "问题",
    "需要",
}


def retrieve_for_question(
    workspace: Workspace,
    question: str,
    space_id: str | None = None,
) -> RetrievalResult:
    retrieval_config = load_config(workspace).retrieval
    terms = _query_terms(question, retrieval_config.aliases)
    keyword_scores, candidate_reasons = _keyword_source_scores(
        workspace,
        terms,
        retrieval_config.title_weight,
        retrieval_config.keyword_weight,
    )
    keyword_scores = _filter_scores_to_space(workspace, keyword_scores, space_id)
    candidate_reasons = {
        source_id: reasons
        for source_id, reasons in candidate_reasons.items()
        if source_id in keyword_scores
    }
    try:
        graph = graph_for_space(workspace, space_id) if space_id else load_graph(workspace)
    except json.JSONDecodeError:
        graph = {"nodes": [], "edges": []}
    node_by_id = {node["id"]: node for node in graph.get("nodes", [])}
    matched_node_ids = _matched_graph_nodes(node_by_id, terms)
    expanded_node_ids, graph_expansion_truncated = _expand_one_hop(
        graph.get("edges", []),
        matched_node_ids,
        retrieval_config.max_expanded_nodes,
    )
    source_scores = dict(keyword_scores)
    graph_node_source_ids = _source_ids_from_nodes(node_by_id, expanded_node_ids)
    graph_edge_source_ids = _source_ids_from_edges(graph.get("edges", []), matched_node_ids)
    _add_scores(source_scores, graph_node_source_ids, retrieval_config.graph_node_weight)
    _add_scores(source_scores, graph_edge_source_ids, retrieval_config.graph_edge_weight)
    _add_reasons(candidate_reasons, graph_node_source_ids, "near matched graph node")
    _add_reasons(candidate_reasons, graph_edge_source_ids, "evidence edge from matched graph node")
    source_scores = _significant_scores(source_scores)
    candidate_reasons = {
        source_id: reasons
        for source_id, reasons in candidate_reasons.items()
        if source_id in source_scores
    }

    contexts = _load_contexts(
        workspace,
        source_scores,
        retrieval_config.max_source_pages,
        space_id=space_id,
        terms=terms,
    )
    graph_paths = _graph_paths(graph, node_by_id, matched_node_ids, expanded_node_ids)
    diagnostics = RetrievalDiagnostics(
        keyword_hits=len(keyword_scores),
        graph_node_hits=len(matched_node_ids),
        expanded_nodes=len(expanded_node_ids),
        source_pages_used=len(contexts),
        user_stated_contexts=sum(
            1 for context in contexts if is_user_guided_status(context.why_saved_status)
        ),
        ai_inferred_contexts=sum(
            1 for context in contexts if is_ai_inferred_status(context.why_saved_status)
        ),
        top_candidate_reasons=[
            f"{context.title}: {', '.join(candidate_reasons.get(context.source_id, ['matched']))}"
            for context in contexts[:3]
        ],
        graph_expansion_truncated=graph_expansion_truncated,
    )
    return RetrievalResult(
        question=question,
        contexts=contexts,
        graph_paths=graph_paths,
        diagnostics=diagnostics,
    )


def _query_terms(question: str, aliases: dict[str, list[str]] | None = None) -> list[str]:
    aliases = aliases or {}
    lowered = question.lower()
    terms = re.findall(r"[a-z0-9]+[a-z0-9_-]*|[\u4e00-\u9fff]+", lowered)
    expanded = list(terms)
    for term in terms:
        expanded.extend(aliases.get(term, []))
    for term in list(expanded):
        if re.search(r"[\u4e00-\u9fff]", term) and len(term) >= 3:
            for i in range(len(term) - 1):
                expanded.append(term[i:i + 2])
    for alias_key, alias_values in aliases.items():
        if alias_key in question:
            expanded.extend(alias_values)
    return sorted(
        {
            term.strip().lower()
            for term in expanded
            if term.strip() and term.strip().lower() not in QUERY_STOPWORDS
        }
    )


def _keyword_source_scores(
    workspace: Workspace,
    terms: list[str],
    title_weight: float,
    keyword_weight: float,
) -> tuple[dict[str, float], dict[str, list[str]]]:
    source_scores: dict[str, float] = {}
    candidate_reasons: dict[str, list[str]] = {}
    for page_path in sorted((workspace.wiki_dir / "sources").glob("*.md")):
        page_text = page_path.read_text(encoding="utf-8").lower()
        source_title = _source_title(page_text)
        title_matches = [term for term in terms if term in source_title]
        term_count = max(1, len(re.findall(r"[a-z0-9]+[a-z0-9_-]*|[\u4e00-\u9fff]", page_text)))
        occurrences = sum(page_text.count(term) for term in terms)
        score = (title_weight if title_matches else 0.0) + (
            keyword_weight * occurrences / term_count
        )
        source_id = _frontmatter_value(page_path, "id")
        if source_id and score > 0:
            source_scores[source_id] = score
            reasons = []
            if title_matches:
                reasons.append(f"title matched {', '.join(title_matches[:3])}")
            if occurrences:
                reasons.append(f"keyword density {occurrences}/{term_count}")
            candidate_reasons[source_id] = reasons
    return source_scores, candidate_reasons


def _matched_graph_nodes(node_by_id: dict[str, dict], terms: list[str]) -> set[str]:
    matched: set[str] = set()
    for node_id, node in node_by_id.items():
        label = node.get("label", "").lower()
        if any(term in label for term in terms):
            matched.add(node_id)
    return matched


def _expand_one_hop(
    edges: list[dict],
    matched_node_ids: set[str],
    max_expanded_nodes: int,
) -> tuple[set[str], bool]:
    expanded = set(matched_node_ids)
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source in matched_node_ids and target:
            expanded.add(target)
        if target in matched_node_ids and source:
            expanded.add(source)
        if len(expanded) >= max_expanded_nodes:
            return set(sorted(expanded)[:max_expanded_nodes]), True
    return expanded, False


def _source_ids_from_nodes(
    node_by_id: dict[str, dict],
    node_ids: set[str],
) -> set[str]:
    source_ids: set[str] = set()
    for node_id in node_ids:
        node = node_by_id.get(node_id, {})
        properties = node.get("properties", {})
        source_id = properties.get("source_id")
        if source_id:
            source_ids.add(source_id)
    return source_ids


def _source_ids_from_edges(edges: list[dict], matched_node_ids: set[str]) -> set[str]:
    source_ids: set[str] = set()
    for edge in edges:
        if edge.get("source") in matched_node_ids or edge.get("target") in matched_node_ids:
            evidence_source_id = edge.get("evidence_source_id")
            if evidence_source_id:
                source_ids.add(evidence_source_id)
    return source_ids


def _add_scores(source_scores: dict[str, float], source_ids: set[str], score: float) -> None:
    for source_id in source_ids:
        source_scores[source_id] = source_scores.get(source_id, 0) + score


def _add_reasons(
    candidate_reasons: dict[str, list[str]],
    source_ids: set[str],
    reason: str,
) -> None:
    for source_id in source_ids:
        candidate_reasons.setdefault(source_id, [])
        if reason not in candidate_reasons[source_id]:
            candidate_reasons[source_id].append(reason)


def _filter_scores_to_space(
    workspace: Workspace,
    source_scores: dict[str, float],
    space_id: str | None,
) -> dict[str, float]:
    if not source_scores or not space_id or space_id == "all":
        return source_scores
    source_ids = set(source_scores)
    placeholders = ",".join("?" for _ in source_ids)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            f"""
            SELECT id
            FROM sources
            WHERE graph_space_id = ? AND id IN ({placeholders})
            """,
            [space_id, *sorted(source_ids)],
        ).fetchall()
    allowed = {row[0] for row in rows}
    return {source_id: score for source_id, score in source_scores.items() if source_id in allowed}


def _significant_scores(source_scores: dict[str, float]) -> dict[str, float]:
    return {
        source_id: score
        for source_id, score in source_scores.items()
        if score >= MIN_RETRIEVAL_SCORE
    }


def _load_contexts(
    workspace: Workspace,
    source_scores: dict[str, float],
    max_source_pages: int,
    *,
    space_id: str | None = None,
    terms: list[str] | None = None,
) -> list[RetrievedContext]:
    if not source_scores:
        return []
    source_ids = set(source_scores)
    placeholders = ",".join("?" for _ in source_ids)
    query = f"""
        SELECT
            s.id,
            s.title,
            s.type,
            s.imported_at,
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
    params: list[str] = sorted(source_ids)
    if space_id and space_id != "all":
        query += " AND s.graph_space_id = ?"
        params.append(space_id)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(query, params).fetchall()

    contexts = []
    index_text = workspace.index_path.read_text(encoding="utf-8")
    for row in rows:
        (
            source_id,
            title,
            source_type,
            imported_at,
            why_saved,
            why_saved_status,
            related_project,
            open_loops_json,
            future_recall_questions_json,
            graph_space_id,
            space_name,
        ) = row
        page_path = workspace.wiki_dir / "sources" / f"{source_id}.md"
        relative_page = workspace.relative_to_workspace(page_path)
        index_page = page_path.relative_to(workspace.index_path.parent).as_posix()
        if (
            not page_path.exists()
            or (relative_page not in index_text and index_page not in index_text)
        ):
            continue
        context = RetrievedContext(
                source_id=source_id,
                source_page=relative_page,
                title=title,
                why_saved=why_saved,
                why_saved_status=why_saved_status,
                related_project=related_project,
                open_loops=json.loads(open_loops_json),
                future_recall_questions=json.loads(future_recall_questions_json),
                graph_space_id=graph_space_id or DEFAULT_GRAPH_SPACE_ID,
                space_name=space_name or "Default",
                source_excerpt=_source_excerpt(page_path),
            )
        contexts.append((context, source_type or "", imported_at or ""))
    terms = terms or []
    ranked = sorted(
        contexts,
        key=lambda item: (
            -_ranking_score(item[0], source_scores.get(item[0].source_id, 0), item[1], item[2], terms),
            -_imported_at_number(item[2]),
            item[0].title,
        )
    )
    return [context for context, _source_type, _imported_at in ranked[:max_source_pages]]


def _ranking_score(
    context: RetrievedContext,
    base_score: float,
    source_type: str,
    imported_at: str,
    terms: list[str],
) -> float:
    score = min(base_score, 1.6)
    searchable = " ".join(
        [
            context.title,
            context.why_saved,
            context.related_project or "",
            context.source_excerpt,
            " ".join(context.open_loops),
            " ".join(context.future_recall_questions),
        ]
    ).lower()
    if is_user_guided_status(context.why_saved_status):
        score += 0.9
    elif is_ai_inferred_status(context.why_saved_status):
        score -= 0.45
    if source_type and source_type.lower() in terms:
        score += 1.0
    if source_type == "pdf" and "pdf" in terms:
        score += 1.0
    if source_type == "pdf" and (
        "不会解析 pdf 正文" in searchable
        or "没有从这份 pdf 中提取到可用正文" in searchable
    ):
        score -= 0.9
    if any(term and term in context.title.lower() for term in terms):
        score += 0.75
    score += min(0.45, 0.04 * sum(searchable.count(term) for term in terms if term))
    return score


def _imported_at_number(imported_at: str) -> int:
    digits = re.sub(r"\D", "", imported_at)[:14]
    return int(digits or "0")


def _graph_paths(
    graph: dict,
    node_by_id: dict[str, dict],
    matched_node_ids: set[str],
    expanded_node_ids: set[str],
) -> list[str]:
    source_paths = _source_to_project_paths(graph, node_by_id, expanded_node_ids)
    if source_paths:
        return source_paths[:8]

    paths = []
    for edge in graph.get("edges", []):
        source = edge.get("source")
        target = edge.get("target")
        if source not in expanded_node_ids or target not in expanded_node_ids:
            continue
        if source not in matched_node_ids and target not in matched_node_ids:
            continue
        source_label = node_by_id.get(source, {}).get("label", source)
        target_label = node_by_id.get(target, {}).get("label", target)
        paths.append(f"{source_label} -[{edge.get('relation')}]-> {target_label}")
    return sorted(dict.fromkeys(paths))[:8]


def _source_to_project_paths(
    graph: dict,
    node_by_id: dict[str, dict],
    expanded_node_ids: set[str],
) -> list[str]:
    triggered = {
        edge.get("source"): edge.get("target")
        for edge in graph.get("edges", [])
        if edge.get("relation") == "triggered_thought"
    }
    belongs_to = {
        edge.get("source"): edge.get("target")
        for edge in graph.get("edges", [])
        if edge.get("relation") == "belongs_to"
    }
    follow_ups: dict[str, list[str]] = {}
    for edge in graph.get("edges", []):
        if edge.get("relation") == "follow_up":
            follow_ups.setdefault(edge.get("source"), []).append(edge.get("target"))

    paths = []
    for source_id, thought_id in triggered.items():
        if source_id not in expanded_node_ids and thought_id not in expanded_node_ids:
            continue
        source_label = node_by_id.get(source_id, {}).get("label", source_id)
        thought_label = node_by_id.get(thought_id, {}).get("label", thought_id)
        project_id = belongs_to.get(thought_id)
        if project_id:
            project_label = node_by_id.get(project_id, {}).get("label", project_id)
            paths.append(
                f"{source_label} -> triggered_thought -> {thought_label} -> belongs_to -> {project_label}"
            )
        for follow_up_id in follow_ups.get(source_id, [])[:1]:
            follow_up_label = node_by_id.get(follow_up_id, {}).get("label", follow_up_id)
            paths.append(f"{source_label} -> follow_up -> {follow_up_label}")

    return sorted(dict.fromkeys(paths))


def _frontmatter_value(page_path: Path, key: str) -> str | None:
    text = page_path.read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(key)}: (?P<value>.+)$", text, re.MULTILINE)
    return match.group("value").strip() if match else None


def _source_title(page_text: str) -> str:
    match = re.search(r"^# source: (?P<title>.+)$", page_text, re.MULTILINE)
    return match.group("title").strip().lower() if match else ""


def _source_excerpt(page_path: Path) -> str:
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
