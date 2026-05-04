from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .graph_store import get_related_links, replace_source_graph, upsert_duplicate_edges
from .llm import LLMProvider, MockLLM
from .models import INBOX_GRAPH_SPACE_ID, CognitiveContext, IngestResult, Source
from .parsers import parse_source
from .spaces import create_route_suggestion, upsert_material
from .wiki import add_source_to_index, append_log_event, write_source_page
from .workspace import Workspace, create_workspace


def ingest_source(
    workspace: Workspace,
    path: Path,
    why: str | None = None,
    llm: LLMProvider | None = None,
    space_id: str | None = None,
) -> IngestResult:
    create_workspace(workspace)
    graph_space_id = space_id or INBOX_GRAPH_SPACE_ID
    parsed = parse_source(path)
    llm = llm or MockLLM()

    effective_text = parsed.text
    if not effective_text and parsed.source_type == "screenshot":
        effective_text = llm.describe_image(parsed.path)

    imported_at = datetime.now(timezone.utc).isoformat()
    source_id = _source_id(imported_at, parsed.content_hash)
    duplicate_source_ids = _duplicate_source_ids(workspace, parsed.content_hash)
    raw_path = _copy_to_raw(workspace, parsed.path, source_id)
    relative_raw_path = workspace.relative_to_workspace(raw_path)

    summary = llm.summarize(effective_text)
    source = Source(
        id=source_id,
        path=relative_raw_path,
        type=parsed.source_type,
        imported_at=imported_at,
        content_hash=parsed.content_hash,
        title=parsed.title,
        original_filename=parsed.path.name,
        summary=summary,
        graph_space_id=graph_space_id,
    )
    _save_source(workspace, source)
    upsert_material(
        workspace,
        source_id=source.id,
        graph_space_id=graph_space_id,
        routing_status="placed" if space_id else "inbox",
        routing_reason="User selected a graph space." if space_id else "Captured into Inbox.",
    )

    cognitive_context = _build_cognitive_context(source, effective_text, why, llm)
    _save_cognitive_context(workspace, cognitive_context)

    replace_source_graph(workspace, source, cognitive_context)
    page = write_source_page(
        workspace,
        source,
        cognitive_context,
        llm.key_details(effective_text),
        get_related_links(workspace, source.id),
    )
    add_source_to_index(workspace, page)
    upsert_duplicate_edges(workspace, source, duplicate_source_ids)
    routing_suggestion_id = None
    if graph_space_id == INBOX_GRAPH_SPACE_ID:
        routing_suggestion_id = create_route_suggestion(workspace, source.id)["id"]
    append_log_event(
        workspace,
        operation="ingest",
        source_id=source.id,
        touched_pages=[
            relative_raw_path,
            page.relative_page_path,
            workspace.relative_to_workspace(workspace.index_path),
            workspace.relative_to_workspace(workspace.log_path),
            workspace.relative_to_workspace(workspace.graph_path),
            workspace.relative_to_workspace(workspace.sqlite_path),
        ],
    )
    return IngestResult(
        source=source,
        cognitive_context=cognitive_context,
        raw_path=raw_path,
        page=page,
        warnings=[
            f"duplicate content_hash also seen in {duplicate_id}"
            for duplicate_id in duplicate_source_ids
        ],
        routing_suggestion_id=routing_suggestion_id,
    )


def _source_id(imported_at: str, content_hash: str) -> str:
    compact_time = (
        imported_at.replace("-", "")
        .replace(":", "")
        .replace("+", "")
        .replace(".", "")
    )
    return f"src_{compact_time[:20]}_{content_hash[:8]}"


def _copy_to_raw(workspace: Workspace, source_path: Path, source_id: str) -> Path:
    target = workspace.raw_dir / _raw_subdir_for_suffix(source_path.suffix) / f"{source_id}_{source_path.name}"
    shutil.copy2(source_path, target)
    return target


def _raw_subdir_for_suffix(suffix: str) -> str:
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    text_suffixes = {".md", ".markdown", ".txt"}
    suffix_lower = suffix.lower()
    if suffix_lower in text_suffixes:
        return "notes"
    if suffix_lower in image_suffixes:
        return "screenshots"
    if suffix_lower == ".pdf":
        return "pdfs"
    if suffix_lower in {".html", ".htm"}:
        return "webpages"
    return "docs"


def _duplicate_source_ids(workspace: Workspace, content_hash: str) -> list[str]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            "SELECT id FROM sources WHERE content_hash = ? ORDER BY imported_at ASC",
            (content_hash,),
        ).fetchall()
    return [row[0] for row in rows]


def _save_source(workspace: Workspace, source: Source) -> None:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO sources (
                id, path, type, imported_at, content_hash, title, original_filename,
                summary, graph_space_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.id,
                source.path,
                source.type,
                source.imported_at,
                source.content_hash,
                source.title,
                source.original_filename,
                source.summary,
                source.graph_space_id,
            ),
        )


def _build_cognitive_context(
    source: Source,
    text: str,
    why: str | None,
    llm: LLMProvider,
) -> CognitiveContext:
    hint = (why or "").strip()
    effective_text = text
    if hint:
        effective_text = f"{text}\n\nUser hint: {hint}".strip()
        why_saved = llm.infer_why_saved(source.title, effective_text)
        status = "user-guided"
        confidence = 0.85
    else:
        why_saved = llm.infer_why_saved(source.title, effective_text)
        status = "AI-inferred"
        confidence = 0.6

    open_loops = llm.open_loops(effective_text)
    future_recall_questions = llm.future_recall_questions(source.title, effective_text)
    return CognitiveContext(
        source_id=source.id,
        why_saved=why_saved,
        why_saved_status=status,
        related_project=llm.related_project(effective_text),
        open_loops=open_loops,
        future_recall_questions=future_recall_questions,
        importance="medium",
        confidence=confidence,
    )


def _save_cognitive_context(
    workspace: Workspace,
    cognitive_context: CognitiveContext,
) -> None:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO cognitive_contexts (
                source_id,
                why_saved,
                why_saved_status,
                related_project,
                open_loops_json,
                future_recall_questions_json,
                importance,
                confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                cognitive_context.source_id,
                cognitive_context.why_saved,
                cognitive_context.why_saved_status,
                cognitive_context.related_project,
                json.dumps(cognitive_context.open_loops, ensure_ascii=False),
                json.dumps(
                    cognitive_context.future_recall_questions,
                    ensure_ascii=False,
                ),
                cognitive_context.importance,
                cognitive_context.confidence,
            ),
        )


def load_source(workspace: Workspace, source_id: str) -> Source:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT
                id, path, type, imported_at, content_hash, title, original_filename,
                summary, graph_space_id
            FROM sources
            WHERE id = ?
            """,
            (source_id,),
        ).fetchone()
    if row is None:
        raise KeyError(source_id)
    return Source(
        id=row[0],
        path=row[1],
        type=row[2],
        imported_at=row[3],
        content_hash=row[4],
        title=row[5],
        original_filename=row[6],
        summary=row[7],
        graph_space_id=row[8],
    )


def load_cognitive_context(workspace: Workspace, source_id: str) -> CognitiveContext:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT
                source_id,
                why_saved,
                why_saved_status,
                related_project,
                open_loops_json,
                future_recall_questions_json,
                importance,
                confidence
            FROM cognitive_contexts
            WHERE source_id = ?
            """,
            (source_id,),
        ).fetchone()
    if row is None:
        raise KeyError(source_id)
    return CognitiveContext(
        source_id=row[0],
        why_saved=row[1],
        why_saved_status=row[2],
        related_project=row[3],
        open_loops=json.loads(row[4]),
        future_recall_questions=json.loads(row[5]),
        importance=row[6],
        confidence=float(row[7]),
    )


def update_cognitive_context(
    workspace: Workspace,
    source_id: str,
    *,
    why_saved: str | None = None,
    related_project: str | None = None,
    open_loops: list[str] | None = None,
    future_recall_questions: list[str] | None = None,
    confirm: bool = False,
) -> CognitiveContext:
    source = load_source(workspace, source_id)
    existing = load_cognitive_context(workspace, source_id)
    next_context = CognitiveContext(
        source_id=source_id,
        why_saved=(why_saved if why_saved is not None else existing.why_saved).strip(),
        why_saved_status="user-stated" if confirm else existing.why_saved_status,
        related_project=(
            related_project.strip() if related_project is not None else existing.related_project
        ),
        open_loops=_clean_list(open_loops if open_loops is not None else existing.open_loops),
        future_recall_questions=_clean_list(
            future_recall_questions
            if future_recall_questions is not None
            else existing.future_recall_questions
        ),
        importance=existing.importance,
        confidence=1.0 if confirm else existing.confidence,
    )
    if not next_context.why_saved:
        raise ValueError("why_saved cannot be empty")
    _save_cognitive_context(workspace, next_context)
    replace_source_graph(workspace, source, next_context)
    page = write_source_page(
        workspace,
        source,
        next_context,
        _key_details_for_source(workspace, source),
        get_related_links(workspace, source.id),
    )
    append_log_event(
        workspace,
        operation="context_update",
        source_id=source_id,
        touched_pages=[
            page.relative_page_path,
            workspace.relative_to_workspace(workspace.graph_path),
            workspace.relative_to_workspace(workspace.sqlite_path),
            workspace.relative_to_workspace(workspace.log_path),
        ],
    )
    return next_context


def _key_details_for_source(workspace: Workspace, source: Source) -> list[str]:
    raw_path = workspace.path / source.path
    parsed = parse_source(raw_path)
    llm = MockLLM()
    text = parsed.text
    if not text and source.type == "screenshot":
        text = llm.describe_image(raw_path)
    return llm.key_details(text)


def _clean_list(items: list[str]) -> list[str]:
    cleaned = []
    for item in items:
        value = str(item).strip()
        if value:
            cleaned.append(value)
    return cleaned
