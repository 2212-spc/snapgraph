from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .models import AnswerResult, CognitiveContext, QuestionPage, Source, SourcePage
from .workspace import Workspace


SOURCE_MARKER = "<!-- snapgraph:sources -->"
QUESTION_MARKER = "<!-- snapgraph:questions -->"
REPORT_MARKER = "<!-- snapgraph:reports -->"


def render_source_page(
    source: Source,
    cognitive_context: CognitiveContext,
    key_details: list[str],
    related_links: dict[str, list[tuple[str, str]]] | None = None,
) -> str:
    details = "\n".join(f"- {detail}" for detail in key_details)
    open_loops = _render_list(cognitive_context.open_loops)
    recall_questions = _render_list(cognitive_context.future_recall_questions)
    related_project = cognitive_context.related_project or ""
    related_projects = _render_list([related_project] if related_project else [])

    links = related_links or {}
    graph_projects = _render_links(links.get("projects", []))
    graph_sources = _render_links(links.get("sources", []))
    graph_questions = _render_links(links.get("questions", []))
    graph_tasks = _render_links(links.get("tasks", []))

    return f"""---
id: {source.id}
title: {source.title}
type: {source.type}
created_at: {source.imported_at}
imported_at: {source.imported_at}
source_path: {source.path}
raw_path: {source.path}
original_filename: {source.original_filename}
content_hash: {source.content_hash}
graph_space_id: {source.graph_space_id}
---
# Source: {source.title}

## Objective Summary
{source.summary or "No summary available."}

## Key Details
{details}

## Cognitive Context
- Why this may have been saved: {cognitive_context.why_saved}
- Status: {cognitive_context.why_saved_status}
- Related project: {related_project}
- Open loops:
{open_loops}
- Importance: {cognitive_context.importance}
- Confidence: {cognitive_context.confidence:.2f}

## Supportive Signals
- Future recall questions:
{recall_questions}

## Links
- Related people:
  - None
- Related concepts:
  - None
- Related projects:
{_merge_link_sections(related_projects, graph_projects)}
- Related questions:
{_merge_link_sections(recall_questions, graph_questions)}
- Related tasks:
{_merge_link_sections(open_loops, graph_tasks)}
- Related sources:
{graph_sources}

## Evidence
- Original source: `{source.path}`
- Original filename: `{source.original_filename}`
- Content hash: `{source.content_hash}`
"""


def write_source_page(
    workspace: Workspace,
    source: Source,
    cognitive_context: CognitiveContext,
    key_details: list[str],
    related_links: dict[str, list[tuple[str, str]]] | None = None,
) -> SourcePage:
    page_path = workspace.wiki_dir / "sources" / f"{source.id}.md"
    page_path.write_text(
        render_source_page(source, cognitive_context, key_details, related_links),
        encoding="utf-8",
    )
    return SourcePage(
        source=source,
        relative_page_path=workspace.relative_to_workspace(page_path),
        absolute_page_path=page_path,
    )


def add_source_to_index(workspace: Workspace, page: SourcePage) -> None:
    target = markdown_link_target(workspace.index_path, page.absolute_page_path)
    line = f"- [{page.source.title}]({target}) - `{page.source.id}`\n"
    current = workspace.index_path.read_text(encoding="utf-8")
    if line in current:
        return
    if SOURCE_MARKER in current:
        updated = current.replace(SOURCE_MARKER, f"{SOURCE_MARKER}\n{line}", 1)
    else:
        updated = current.rstrip() + "\n" + line
    workspace.index_path.write_text(updated, encoding="utf-8")


def render_question_page(
    workspace: Workspace,
    page_path: Path,
    question_id: str,
    created_at: str,
    answer: AnswerResult,
) -> str:
    evidence_lines = _render_evidence_source_links(workspace, page_path, answer)
    graph_paths = answer.retrieval.graph_paths or ["None."]
    return f"""---
id: {question_id}
type: question
created_at: {created_at}
question_hash: {_hash_text(answer.question)}
answer_hash: {_hash_text(answer.text)}
evidence_source_ids: {json.dumps([context.source_id for context in answer.retrieval.contexts], ensure_ascii=False)}
---
# Saved Question: {_short_title(answer.question)}

## Question
{answer.question}

## Answer
{answer.text}

## Evidence Source Pages
{evidence_lines}

## Saved Graph Paths
```text
{chr(10).join(graph_paths)}
```
"""


def write_question_page(workspace: Workspace, answer: AnswerResult) -> QuestionPage:
    created_at = datetime.now(timezone.utc).isoformat()
    question_id = _question_id(created_at, answer.question)
    page_path = workspace.wiki_dir / "questions" / f"{question_id}.md"
    page_path.write_text(
        render_question_page(workspace, page_path, question_id, created_at, answer),
        encoding="utf-8",
    )
    page = QuestionPage(
        id=question_id,
        question=answer.question,
        relative_page_path=workspace.relative_to_workspace(page_path),
        absolute_page_path=page_path,
    )
    add_question_to_index(workspace, page)
    append_log_event(
        workspace,
        operation="ask_save",
        source_id=None,
        touched_pages=[
            page.relative_page_path,
            workspace.relative_to_workspace(workspace.index_path),
            workspace.relative_to_workspace(workspace.log_path),
        ],
    )
    return page


def add_question_to_index(workspace: Workspace, page: QuestionPage) -> None:
    target = markdown_link_target(workspace.index_path, page.absolute_page_path)
    line = f"- [{_short_title(page.question)}]({target}) - `{page.id}`\n"
    current = workspace.index_path.read_text(encoding="utf-8")
    if line in current:
        return
    if QUESTION_MARKER in current:
        updated = current.replace(QUESTION_MARKER, f"{QUESTION_MARKER}\n{line}", 1)
    else:
        updated = current.rstrip() + "\n" + line
    workspace.index_path.write_text(updated, encoding="utf-8")


def add_report_to_index(workspace: Workspace, relative_page_path: str) -> None:
    report_path = workspace.path / relative_page_path
    target = markdown_link_target(workspace.index_path, report_path)
    line = f"- [Cognitive Graph Report]({target})\n"
    current = workspace.index_path.read_text(encoding="utf-8")
    if line in current:
        return
    if REPORT_MARKER in current:
        updated = current.replace(REPORT_MARKER, f"{REPORT_MARKER}\n{line}", 1)
    else:
        updated = current.rstrip() + "\n\n## Reports\n" + REPORT_MARKER + "\n" + line
    workspace.index_path.write_text(updated, encoding="utf-8")


def append_log_event(
    workspace: Workspace,
    operation: str,
    source_id: str | None,
    touched_pages: list[str],
) -> None:
    timestamp = datetime.now(timezone.utc).isoformat()
    event = {
        "timestamp": timestamp,
        "operation": operation,
        "source_id": source_id,
        "touched_pages": touched_pages,
    }
    with workspace.log_path.open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n## {timestamp} {operation}"
            + (f" {source_id}" if source_id else "")
            + "\n\n```json\n"
            + json.dumps(event, ensure_ascii=False, indent=2)
            + "\n```\n"
        )


def source_pages(workspace: Workspace) -> list[Path]:
    return sorted((workspace.wiki_dir / "sources").glob("*.md"))


def question_pages(workspace: Workspace) -> list[Path]:
    return sorted((workspace.wiki_dir / "questions").glob("*.md"))


def _render_list(items: list[str]) -> str:
    if not items:
        return "  - None"
    return "\n".join(f"  - {item}" for item in items)


def _render_links(links: list[tuple[str, str]]) -> str:
    if not links:
        return "  - None"
    return "\n".join(f"  - [{label}]({path})" for label, path in links)


def _merge_link_sections(from_context: str, from_graph: str) -> str:
    if from_graph != "  - None":
        return from_graph
    return from_context


def markdown_link_target(from_page: Path, target_page: Path) -> str:
    return os.path.relpath(target_page, start=from_page.parent).replace(os.sep, "/")


def _render_evidence_source_links(
    workspace: Workspace,
    page_path: Path,
    answer: AnswerResult,
) -> str:
    if not answer.retrieval.contexts:
        return "- None"
    return "\n".join(
        (
            f"- [{context.title}]({markdown_link_target(page_path, workspace.path / context.source_page)}) "
            f"- `{context.source_id}` ({context.why_saved_status})"
        )
        for context in answer.retrieval.contexts
    )


def _question_id(created_at: str, question: str) -> str:
    compact_time = (
        created_at.replace("-", "")
        .replace(":", "")
        .replace("+", "")
        .replace(".", "")
    )
    return f"q_{compact_time[:20]}_{_hash_text(question)[:8]}"


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _short_title(text: str) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= 80:
        return cleaned or "Untitled question"
    return cleaned[:77].rstrip() + "..."
