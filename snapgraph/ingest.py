from __future__ import annotations

import json
import re
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .graph_store import get_related_links, replace_source_graph, upsert_duplicate_edges
from .llm import LLMProvider, MockLLM
from .models import (
    INBOX_GRAPH_SPACE_ID,
    CognitiveContext,
    IngestResult,
    Source,
    SourcePage,
)
from .parsers import parse_source
from .spaces import create_route_suggestion, upsert_material
from .wiki import add_source_to_index, append_log_event, write_source_page
from .workspace import Workspace, create_workspace

DedupeScope = Literal["space", "workspace"]


def ingest_source(
    workspace: Workspace,
    path: Path,
    why: str | None = None,
    llm: LLMProvider | None = None,
    space_id: str | None = None,
    dedupe_scope: DedupeScope = "space",
) -> IngestResult:
    create_workspace(workspace)
    graph_space_id = space_id or INBOX_GRAPH_SPACE_ID
    parsed = parse_source(path)

    existing_source = _existing_source_for_content(
        workspace,
        content_hash=parsed.content_hash,
        graph_space_id=graph_space_id,
        dedupe_scope=dedupe_scope,
    )
    if existing_source is not None:
        return _deduplicated_ingest_result(workspace, existing_source)

    llm = llm or MockLLM()

    effective_text = parsed.text
    if not effective_text and parsed.source_type == "screenshot":
        effective_text = llm.describe_image(parsed.path)
    memory_title = _source_title_for_ingest(
        parsed_title=parsed.title,
        source_path=parsed.path,
        source_type=parsed.source_type,
        text=effective_text,
        why=why,
        llm=llm,
    )

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
        title=memory_title,
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


def _deduplicated_ingest_result(
    workspace: Workspace,
    existing_source: Source,
) -> IngestResult:
    """Return the existing persisted source for an exact duplicate ingest."""
    cognitive_context = load_cognitive_context(workspace, existing_source.id)
    page = _source_page_for_source(workspace, existing_source)
    raw_path = workspace.path / existing_source.path
    append_log_event(
        workspace,
        operation="ingest_deduplicated",
        source_id=existing_source.id,
        touched_pages=[
            existing_source.path,
            page.relative_page_path,
            workspace.relative_to_workspace(workspace.log_path),
        ],
    )
    return IngestResult(
        source=existing_source,
        cognitive_context=cognitive_context,
        raw_path=raw_path,
        page=page,
        warnings=[
            (
                "duplicate content_hash already exists in "
                f"{existing_source.graph_space_id} as {existing_source.id}; "
                "reused existing source"
            )
        ],
        deduplicated=True,
    )


def _existing_source_for_content(
    workspace: Workspace,
    *,
    content_hash: str,
    graph_space_id: str,
    dedupe_scope: DedupeScope,
) -> Source | None:
    """Find the canonical source for an exact content duplicate."""
    if dedupe_scope not in ("space", "workspace"):
        raise ValueError("dedupe_scope must be space or workspace")

    if dedupe_scope == "space":
        where_clause = "WHERE content_hash = ? AND graph_space_id = ?"
        params: tuple[str, ...] = (content_hash, graph_space_id)
    else:
        where_clause = "WHERE content_hash = ?"
        params = (content_hash,)

    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            f"""
            SELECT
                id, path, type, imported_at, content_hash, title, original_filename,
                summary, graph_space_id
            FROM sources
            {where_clause}
            ORDER BY imported_at ASC, id ASC
            LIMIT 1
            """,
            params,
        ).fetchone()
    return _source_from_row(row) if row is not None else None


def _source_page_for_source(workspace: Workspace, source: Source) -> SourcePage:
    """Build the source page handle for an existing source row."""
    page_path = workspace.wiki_dir / "sources" / f"{source.id}.md"
    return SourcePage(
        source=source,
        relative_page_path=workspace.relative_to_workspace(page_path),
        absolute_page_path=page_path,
    )


def update_source_title(
    workspace: Workspace,
    source_id: str,
    title: str,
) -> Source:
    """Persist a user-edited source title and rewrite derived views."""
    # Load the source/context pair that owns the receipt title.
    source = load_source(workspace, source_id)
    context = load_cognitive_context(workspace, source_id)
    next_title = _clean_manual_title(title)
    if not next_title:
        raise ValueError("title cannot be empty")

    # Save the canonical title, then regenerate graph/wiki projections from it.
    updated_source = Source(
        id=source.id,
        path=source.path,
        type=source.type,
        imported_at=source.imported_at,
        content_hash=source.content_hash,
        title=next_title,
        original_filename=source.original_filename,
        summary=source.summary,
        graph_space_id=source.graph_space_id,
    )
    _save_source(workspace, updated_source)
    replace_source_graph(workspace, updated_source, context)
    duplicate_source_ids = [
        duplicate_id
        for duplicate_id in _duplicate_source_ids(workspace, source.content_hash)
        if duplicate_id != source.id
    ]
    upsert_duplicate_edges(workspace, updated_source, duplicate_source_ids)
    page = write_source_page(
        workspace,
        updated_source,
        context,
        _key_details_for_source(workspace, updated_source),
        get_related_links(workspace, updated_source.id),
    )
    add_source_to_index(workspace, page)
    append_log_event(
        workspace,
        operation="title_update",
        source_id=source_id,
        touched_pages=[
            page.relative_page_path,
            workspace.relative_to_workspace(workspace.index_path),
            workspace.relative_to_workspace(workspace.graph_path),
            workspace.relative_to_workspace(workspace.sqlite_path),
            workspace.relative_to_workspace(workspace.log_path),
        ],
    )
    return updated_source


def _source_id(imported_at: str, content_hash: str) -> str:
    compact_time = (
        imported_at.replace("-", "")
        .replace(":", "")
        .replace("+", "")
        .replace(".", "")
    )
    return f"src_{compact_time[:20]}_{content_hash[:8]}"


def _source_title_for_ingest(
    *,
    parsed_title: str,
    source_path: Path,
    source_type: str,
    text: str,
    why: str | None,
    llm: LLMProvider,
) -> str:
    """Choose the persisted title for a newly ingested source."""
    if not _should_generate_memory_title(source_path, source_type):
        return _clean_manual_title(parsed_title) or source_path.stem

    # Free-form UI captures are named capture-*.md; their parser title is often
    # just the first pasted line, so ask the provider for a receipt label.
    title_generator = getattr(llm, "memory_title", None)
    generated = (
        title_generator(text, why)
        if callable(title_generator)
        else _fallback_memory_title(text, why, parsed_title)
    )
    cleaned = _clean_generated_title(generated)
    if cleaned and not _is_redundant_title(cleaned, parsed_title, why):
        return cleaned
    return _fallback_memory_title(text, why, parsed_title)


def _should_generate_memory_title(source_path: Path, source_type: str) -> bool:
    """Return whether a source should receive an AI memory title."""
    return source_type in {"markdown", "text"} and source_path.stem.startswith("capture-")


def _fallback_memory_title(
    text: str,
    why: str | None,
    parsed_title: str,
) -> str:
    """Build a deterministic title when the provider returns a weak label."""
    reason = _short_phrase(why or "", 28)
    content = _short_phrase(_first_capture_content_line(text), 28)
    if reason and content:
        return _clean_generated_title(f"{reason}：{content}") or parsed_title
    if reason:
        return _clean_generated_title(reason) or parsed_title
    if content:
        return _clean_generated_title(content) or parsed_title
    return _clean_manual_title(parsed_title) or "新的材料"


def _clean_generated_title(title: str) -> str:
    """Normalize provider-generated receipt titles."""
    cleaned = _clean_manual_title(title)
    cleaned = re.sub(r"^(?:保存为|标题|记忆标题)\s*[:：]\s*", "", cleaned)
    cleaned = cleaned.strip(" \t\r\n\"'“”‘’`")
    if len(cleaned) <= 48:
        return cleaned
    return cleaned[:48].rstrip("，。；、:： ")


def _clean_manual_title(title: str) -> str:
    """Normalize user-entered source titles."""
    return re.sub(r"\s+", " ", str(title or "")).strip()


def _is_redundant_title(title: str, parsed_title: str, why: str | None) -> bool:
    """Return whether a generated title still looks like the old first-line title."""
    comparable_title = _comparable_title(title)
    comparable_parsed = _comparable_title(parsed_title)
    if not comparable_title or not comparable_parsed:
        return False
    if comparable_title == comparable_parsed:
        return True
    if (why or "").strip():
        return False
    return comparable_title.startswith(comparable_parsed) and len(
        comparable_title
    ) <= len(comparable_parsed) + 12


def _first_capture_content_line(text: str) -> str:
    """Return the first non-heading content line from a browser capture."""
    body_lines: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.startswith("#") and not body_lines:
            continue
        normalized = cleaned.lstrip("#").strip()
        if normalized:
            body_lines.append(normalized)
    return body_lines[0] if body_lines else ""


def _short_phrase(text: str, limit: int) -> str:
    """Return a compact single-line phrase."""
    cleaned = _clean_manual_title(text)
    cleaned = re.sub(r"^(?:我保存它是因为|我保存这个是因为|因为|为了)\s*", "", cleaned)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip("，。；、:： ")


def _comparable_title(title: str) -> str:
    """Return a punctuation-insensitive representation for title comparison."""
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", title.lower())


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
            INSERT INTO sources (
                id, path, type, imported_at, content_hash, title, original_filename,
                summary, graph_space_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                path = excluded.path,
                type = excluded.type,
                imported_at = excluded.imported_at,
                content_hash = excluded.content_hash,
                title = excluded.title,
                original_filename = excluded.original_filename,
                summary = excluded.summary,
                graph_space_id = excluded.graph_space_id
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
        effective_text = f"{text}\n\nUser-stated saved reason: {hint}".strip()
        why_saved = hint
        status = "user-stated"
        confidence = 1.0
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
    return _source_from_row(row)


def _source_from_row(row: tuple) -> Source:
    """Convert a SQLite source row into a Source model."""
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
    duplicate_source_ids = [
        duplicate_id
        for duplicate_id in _duplicate_source_ids(workspace, source.content_hash)
        if duplicate_id != source.id
    ]
    upsert_duplicate_edges(workspace, source, duplicate_source_ids)
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
