from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .graph_store import graph_diagnostics, graph_insights, load_graph
from .linting import lint_workspace
from .wiki import add_report_to_index, append_log_event, markdown_link_target, question_pages
from .workspace import Workspace


@dataclass(frozen=True)
class GraphReportResult:
    relative_page_path: str
    absolute_page_path: Path
    text: str


def write_graph_report(workspace: Workspace) -> GraphReportResult:
    report_path = workspace.wiki_dir / "graph_report.md"
    text = render_graph_report(workspace)
    report_path.write_text(text, encoding="utf-8")
    relative_path = workspace.relative_to_workspace(report_path)
    add_report_to_index(workspace, relative_path)
    append_log_event(
        workspace,
        operation="report",
        source_id=None,
        touched_pages=[
            relative_path,
            workspace.relative_to_workspace(workspace.index_path),
            workspace.relative_to_workspace(workspace.log_path),
        ],
    )
    return GraphReportResult(
        relative_page_path=relative_path,
        absolute_page_path=report_path,
        text=text,
    )


def render_graph_report(workspace: Workspace) -> str:
    today = date.today().isoformat()
    report_path = workspace.wiki_dir / "graph_report.md"
    sources = _source_rows(workspace)
    contexts = _context_rows(workspace)
    graph = load_graph(workspace)
    diagnostics = graph_diagnostics(workspace)
    insights = graph_insights(workspace)
    lint = lint_workspace(workspace)
    saved_questions = _saved_questions(workspace)
    open_loops = _open_loops(contexts)
    future_questions = _future_questions(workspace, report_path, contexts)
    graph_paths = _graph_paths_worth_reviewing(workspace, report_path, graph, contexts)
    audit_lines = _audit_trail(workspace, report_path, contexts)

    status_counts: dict[str, int] = {}
    for context in contexts:
        status = context["why_saved_status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    return "\n".join(
        [
            f"# Cognitive Graph Report ({today})",
            "",
            "## Corpus Summary",
            f"- Sources: {len(sources)}",
            f"- Saved questions: {len(saved_questions)}",
            f"- Nodes: {diagnostics.node_count}",
            f"- Edges: {diagnostics.edge_count}",
            f"- Lint status: {lint.status}",
            "",
            "## Cognitive Context Mix",
            *_bullet_lines(_status_summary(status_counts)),
            "",
            "## Confidence & Audit Trail",
            *_bullet_lines(audit_lines),
            "",
            "## Project Clusters",
            *_bullet_lines(_project_cluster_lines(insights)),
            "",
            "## High-Value Review Paths",
            *_bullet_lines(_high_value_path_lines(insights)),
            "",
            "## Cognitive Gaps",
            *_bullet_lines(_cognitive_gap_lines(insights)),
            "",
            "## Honest Audit Trail",
            *_bullet_lines(_honest_audit_lines(insights)),
            "",
            "## Top Hubs",
            *_bullet_lines([f"{label}: {degree} edges" for label, degree in diagnostics.top_hubs]),
            "",
            "## Open Loops",
            *_bullet_lines(open_loops[:10]),
            "",
            "## Saved Questions",
            *_bullet_lines(saved_questions[:10]),
            "",
            "## Graph Paths Worth Reviewing",
            "```text",
            *graph_paths[:10],
            "```",
            "",
            "## Suggested Next Questions",
            *_bullet_lines(future_questions[:8]),
            "",
            "## Lint Summary",
            *_bullet_lines(_lint_summary(lint)),
        ]
    )


def _source_rows(workspace: Workspace) -> list[dict]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT id, title, type, imported_at
            FROM sources
            ORDER BY imported_at ASC
            """
        ).fetchall()
    return [
        {"id": row[0], "title": row[1], "type": row[2], "imported_at": row[3]}
        for row in rows
    ]


def _context_rows(workspace: Workspace) -> list[dict]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT
                c.source_id,
                s.title,
                c.why_saved_status,
                c.open_loops_json,
                c.future_recall_questions_json,
                c.confidence
            FROM cognitive_contexts c
            JOIN sources s ON s.id = c.source_id
            ORDER BY s.title ASC
            """
        ).fetchall()
    return [
        {
            "source_id": row[0],
            "title": row[1],
            "why_saved_status": row[2],
            "open_loops": _loads_list(row[3]),
            "future_recall_questions": _loads_list(row[4]),
            "confidence": float(row[5]),
        }
        for row in rows
    ]


def _saved_questions(workspace: Workspace) -> list[str]:
    questions: list[str] = []
    for page_path in question_pages(workspace):
        text = page_path.read_text(encoding="utf-8")
        question = _section_text(text, "## Question")
        questions.append(question or page_path.stem)
    return questions


def _open_loops(contexts: list[dict]) -> list[str]:
    loops = [
        loop
        for context in contexts
        for loop in context["open_loops"]
        if loop and loop != "None"
    ]
    return sorted(dict.fromkeys(loops)) or ["No open loops found."]


def _future_questions(
    workspace: Workspace,
    report_path: Path,
    contexts: list[dict],
) -> list[str]:
    questions = []
    for context in contexts:
        source_link = _source_link(workspace, report_path, context)
        for question in context["future_recall_questions"]:
            if question and question != "None":
                questions.append(
                    f"{question} — from {source_link}, {context['why_saved_status']}, confidence {context['confidence']:.2f}"
                )
    return sorted(dict.fromkeys(questions)) or ["Ingest sources or save answers to generate better recall questions."]


def _graph_paths_worth_reviewing(
    workspace: Workspace,
    report_path: Path,
    graph: dict,
    contexts: list[dict],
) -> list[str]:
    nodes = {node["id"]: node for node in graph.get("nodes", [])}
    context_by_source_id = {context["source_id"]: context for context in contexts}
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
    paths = []
    for source_id, thought_id in triggered.items():
        source_node = nodes.get(source_id, {})
        source_key = source_node.get("properties", {}).get("source_id")
        context = context_by_source_id.get(source_key or "")
        source_label = (
            _source_link(workspace, report_path, context)
            if context
            else source_node.get("label", source_id)
        )
        thought_label = nodes.get(thought_id, {}).get("label", thought_id)
        status = context["why_saved_status"] if context else "unknown"
        confidence = context["confidence"] if context else 0.0
        project_id = belongs_to.get(thought_id)
        if project_id:
            project_label = nodes.get(project_id, {}).get("label", project_id)
            paths.append(
                f"{source_label} -> triggered_thought [{status}, {confidence:.2f}] -> {thought_label} -> belongs_to -> {project_label}"
            )
        else:
            paths.append(f"{source_label} -> triggered_thought [{status}, {confidence:.2f}] -> {thought_label}")
    return sorted(dict.fromkeys(paths)) or ["No graph paths found yet."]


def _status_summary(status_counts: dict[str, int]) -> list[str]:
    if not status_counts:
        return ["No cognitive contexts found."]
    return [f"{status}: {count}" for status, count in sorted(status_counts.items())]


def _project_cluster_lines(insights: dict) -> list[str]:
    clusters = insights.get("project_clusters", [])
    if not clusters:
        return ["No project clusters found yet."]
    lines = []
    for cluster in clusters[:8]:
        lines.append(
            f"{cluster['project']}: {cluster['source_count']} sources, "
            f"{cluster['user_stated']} user-stated, {cluster['ai_inferred']} AI-inferred, "
            f"average confidence {cluster['average_confidence']:.2f}"
        )
    return lines


def _high_value_path_lines(insights: dict) -> list[str]:
    paths = insights.get("high_value_review_paths", [])
    if not paths:
        return ["No high-value review paths found yet."]
    return [
        (
            f"{path['path']} [{path['status']}, confidence {path['confidence']:.2f}] "
            f"- {path['why']}"
        )
        for path in paths[:10]
    ]


def _cognitive_gap_lines(insights: dict) -> list[str]:
    gaps = []
    low_confidence = insights.get("low_confidence_contexts", [])
    unassigned = insights.get("unassigned_sources", [])
    if low_confidence:
        titles = ", ".join(item["title"] for item in low_confidence[:5])
        gaps.append(f"Review low-confidence AI-inferred memories: {titles}")
    if unassigned:
        titles = ", ".join(item["title"] for item in unassigned[:5])
        gaps.append(f"Assign projects or questions to unassigned sources: {titles}")
    if not gaps:
        gaps.append("No major cognitive gaps detected.")
    return gaps


def _honest_audit_lines(insights: dict) -> list[str]:
    lines = []
    for item in insights.get("low_confidence_contexts", [])[:5]:
        lines.append(
            f"{item['title']}: AI-inferred, confidence {item['confidence']:.2f}; "
            "ask the user to confirm or replace this saved reason."
        )
    for item in insights.get("bridge_sources", [])[:5]:
        lines.append(
            f"{item['title']}: {item['status']}, confidence {item['confidence']:.2f}; "
            f"{item['why']}"
        )
    return lines or ["Every displayed memory path includes status and confidence."]


def _audit_trail(
    workspace: Workspace,
    report_path: Path,
    contexts: list[dict],
) -> list[str]:
    if not contexts:
        return ["No cognitive contexts found."]
    average_confidence = sum(context["confidence"] for context in contexts) / len(contexts)
    lines = [f"Average confidence: {average_confidence:.2f}"]
    lines.extend(
        (
            f"{_source_link(workspace, report_path, context)} — "
            f"{context['why_saved_status']}, confidence {context['confidence']:.2f}, "
            f"evidence `{context['source_id']}`"
        )
        for context in contexts
    )
    low_confidence = [
        context
        for context in contexts
        if context["why_saved_status"] == "AI-inferred" and context["confidence"] < 0.7
    ]
    if low_confidence:
        lines.append(
            "Review low-confidence AI-inferred contexts: "
            + ", ".join(context["title"] for context in low_confidence[:5])
        )
    return lines


def _source_link(workspace: Workspace, report_path: Path, context: dict) -> str:
    source_path = workspace.wiki_dir / "sources" / f"{context['source_id']}.md"
    return f"[{context['title']}]({markdown_link_target(report_path, source_path)})"


def _lint_summary(lint) -> list[str]:
    lines = [f"Status: {lint.status}"]
    lines.extend(f"Error: {error}" for error in lint.errors)
    lines.extend(f"Warning: {warning}" for warning in lint.warnings)
    return lines


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- None"]


def _loads_list(raw_json: str) -> list[str]:
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _section_text(text: str, heading: str) -> str:
    if heading not in text:
        return ""
    tail = text.split(heading, 1)[1].lstrip()
    if "\n## " in tail:
        tail = tail.split("\n## ", 1)[0]
    return " ".join(tail.strip().split())
