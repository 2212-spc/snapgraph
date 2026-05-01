from __future__ import annotations

import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .graph_store import upsert_duplicate_edges, upsert_ingest_graph
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

    page = write_source_page(
        workspace,
        source,
        cognitive_context,
        llm.key_details(effective_text),
    )
    add_source_to_index(workspace, page)
    upsert_ingest_graph(workspace, source, cognitive_context)
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
    if why is not None:
        why_saved = why
        status = "user-stated"
        confidence = 1.0
    else:
        why_saved = llm.infer_why_saved(source.title, text)
        status = "AI-inferred"
        confidence = 0.6

    open_loops = llm.open_loops(text)
    future_recall_questions = llm.future_recall_questions(source.title, text)
    return CognitiveContext(
        source_id=source.id,
        why_saved=why_saved,
        why_saved_status=status,
        related_project=llm.related_project(text),
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
