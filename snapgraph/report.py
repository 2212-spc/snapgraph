from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .graph_store import graph_diagnostics, graph_insights, load_graph
from .linting import lint_workspace
from .models import is_ai_inferred_status
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
            f"# 认知图谱报告（{today}）",
            "",
            "## 语料概览",
            f"- 材料数：{len(sources)}",
            f"- 已保存问题数：{len(saved_questions)}",
            f"- 节点数：{diagnostics.node_count}",
            f"- 边数：{diagnostics.edge_count}",
            f"- 检查状态：{lint.status}",
            "",
            "## 认知上下文分布",
            *_bullet_lines(_status_summary(status_counts)),
            "",
            "## 置信度与审计轨迹",
            *_bullet_lines(audit_lines),
            "",
            "## 项目簇",
            *_bullet_lines(_project_cluster_lines(insights)),
            "",
            "## 高价值复查路径",
            *_bullet_lines(_high_value_path_lines(insights)),
            "",
            "## 认知缺口",
            *_bullet_lines(_cognitive_gap_lines(insights)),
            "",
            "## 诚实审计说明",
            *_bullet_lines(_honest_audit_lines(insights)),
            "",
            "## 关键枢纽",
            *_bullet_lines([f"{label}：{degree} 条边" for label, degree in diagnostics.top_hubs]),
            "",
            "## Open Loops",
            *_bullet_lines(open_loops[:10]),
            "",
            "## 已保存问题",
            *_bullet_lines(saved_questions[:10]),
            "",
            "## 值得复查的图谱路径",
            "```text",
            *graph_paths[:10],
            "```",
            "",
            "## 建议的后续问题",
            *_bullet_lines(future_questions[:8]),
            "",
            "## 检查摘要",
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
    return sorted(dict.fromkeys(loops)) or ["未发现 open loop。"]


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
                    f"{question} - 来自 {source_link}，{_status_label(context['why_saved_status'])}，置信度 {context['confidence']:.2f}"
                )
    return sorted(dict.fromkeys(questions)) or [
        "先导入材料或保存回答，再生成更好的回忆问题。"
    ]


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
                f"{source_label} -> 触发理由 [{_status_label(status)}, {confidence:.2f}] -> {thought_label} -> 归属项目 -> {project_label}"
            )
        else:
            paths.append(
                f"{source_label} -> 触发理由 [{_status_label(status)}, {confidence:.2f}] -> {thought_label}"
            )
    return sorted(dict.fromkeys(paths)) or ["暂时还没有可复查的图谱路径。"]


def _status_summary(status_counts: dict[str, int]) -> list[str]:
    if not status_counts:
        return ["未发现认知上下文。"]
    return [f"{_status_label(status)}：{count}" for status, count in sorted(status_counts.items())]


def _project_cluster_lines(insights: dict) -> list[str]:
    clusters = insights.get("project_clusters", [])
    if not clusters:
        return ["暂时还没有项目簇。"]
    lines = []
    for cluster in clusters[:8]:
        lines.append(
            f"{cluster['project']}：{cluster['source_count']} 份材料，"
            f"{cluster['user_stated']} 份用户确认，{cluster['ai_inferred']} 份 AI 推断，"
            f"平均置信度 {cluster['average_confidence']:.2f}"
        )
    return lines


def _high_value_path_lines(insights: dict) -> list[str]:
    paths = insights.get("high_value_review_paths", [])
    if not paths:
        return ["暂时还没有高价值复查路径。"]
    return [
        (
            f"{path['path']} [{_status_label(path['status'])}，置信度 {path['confidence']:.2f}] "
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
        gaps.append(f"复查这些低置信度的 AI 推断记忆：{titles}")
    if unassigned:
        titles = ", ".join(item["title"] for item in unassigned[:5])
        gaps.append(f"为这些未归类材料补充项目或问题归属：{titles}")
    if not gaps:
        gaps.append("未发现明显的认知缺口。")
    return gaps


def _honest_audit_lines(insights: dict) -> list[str]:
    lines = []
    for item in insights.get("low_confidence_contexts", [])[:5]:
        lines.append(
            f"{item['title']}：AI 推断，置信度 {item['confidence']:.2f}；"
            "建议请用户确认或改写这条保存理由。"
        )
    for item in insights.get("bridge_sources", [])[:5]:
        lines.append(
            f"{item['title']}：{_status_label(item['status'])}，置信度 {item['confidence']:.2f}；"
            f"{item['why']}"
        )
    return lines or ["所有展示出的记忆路径都带有状态和置信度。"]


def _audit_trail(
    workspace: Workspace,
    report_path: Path,
    contexts: list[dict],
) -> list[str]:
    if not contexts:
        return ["未发现认知上下文。"]
    average_confidence = sum(context["confidence"] for context in contexts) / len(contexts)
    lines = [f"平均置信度：{average_confidence:.2f}"]
    lines.extend(
        (
            f"{_source_link(workspace, report_path, context)} - "
            f"{_status_label(context['why_saved_status'])}，置信度 {context['confidence']:.2f}，"
            f"证据 `{context['source_id']}`"
        )
        for context in contexts
    )
    low_confidence = [
        context
        for context in contexts
        if is_ai_inferred_status(context["why_saved_status"]) and context["confidence"] < 0.7
    ]
    if low_confidence:
        lines.append(
            "需要复查的低置信度 AI 推断上下文："
            + ", ".join(context["title"] for context in low_confidence[:5])
        )
    return lines


def _source_link(workspace: Workspace, report_path: Path, context: dict) -> str:
    source_path = workspace.wiki_dir / "sources" / f"{context['source_id']}.md"
    return f"[{context['title']}]({markdown_link_target(report_path, source_path)})"


def _lint_summary(lint) -> list[str]:
    lines = [f"状态：{lint.status}"]
    lines.extend(f"错误：{error}" for error in lint.errors)
    lines.extend(f"警告：{warning}" for warning in lint.warnings)
    return lines


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- 无"]


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


def _status_label(status: str) -> str:
    mapping = {
        "user-stated": "用户确认",
        "user-guided": "用户引导",
        "AI-inferred": "AI 推断",
        "unknown": "未知",
    }
    return mapping.get(status, status)
