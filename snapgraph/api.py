from __future__ import annotations

import json
import hashlib
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .answer import (
    ANSWER_CONCLUSION,
    answer_question,
    clean_answer_glyphs,
    ensure_retrieval_diagnostics,
    render_answer,
    save_answer,
)
from .answer_quality import build_answer_quality_pack
from .config import (
    load_config,
    save_config,
    validate_api_key_env_name,
    LLMConfig,
    SnapGraphConfig,
)
from .demo_data import load_demo_dataset, DEMO_QUESTIONS
from .decision_layers import (
    build_collect_decision_layers,
    build_recall_decision_layers,
)
from .focus import focus_graph_for_payload, focus_graph_from_retrieval
from .graph_evidence import build_graph_evidence_pack
from .graph_store import (
    create_graph_theme,
    create_manual_edge,
    create_user_thought,
    graph_diagnostics,
    graph_for_space,
    graph_insights,
    list_graph_themes,
    load_graph,
    load_graph_layout,
    save_graph_layout,
    update_graph_edge,
    update_graph_theme,
)
from .ingest import ingest_source, review_ai_inference, update_cognitive_context, update_source_title
from .linting import lint_workspace
from .llm import MockLLM
from .llm_providers import provider_metadata, resolve_llm_with_metadata
from .models import AnswerResult, DEFAULT_GRAPH_SPACE_ID, INBOX_GRAPH_SPACE_ID
from .report import write_graph_report
from .retrieval import retrieve_for_question
from .recall_projection import build_recall_result_projection
from .recall_history_insights import build_recall_history_insights
from .source_traceability import build_source_traceability_audit
from .spaces import (
    accept_suggestion,
    create_graph_space,
    create_route_suggestion,
    get_suggestion,
    list_graph_spaces,
    list_suggestions,
    move_source_to_space,
    reject_suggestion,
    update_graph_space,
)
from .trust_center import (
    batch_review,
    get_review_detail,
    list_open_loops,
    list_review_items,
    trust_diagnostics,
    trust_summary,
    update_open_loop_state,
)
from .wiki import question_pages, source_pages
from .workspace_health import build_workspace_health_pack
from .workspace_governance import build_workspace_governance_report
from .workspace import Workspace, create_workspace, get_workspace


STATIC_DIR = Path(__file__).resolve().parent / "static"
app = FastAPI(title="SnapGraph API", version="0.1.0")


def _workspace() -> Workspace:
    ws = get_workspace()
    create_workspace(workspace=ws)
    return ws


def _resolve_llm_or_503(workspace: Workspace):
    try:
        return resolve_llm_with_metadata(workspace)
    except RuntimeError as exc:
        metadata = provider_metadata(workspace, provider_error=str(exc))
        raise HTTPException(status_code=503, detail=metadata.as_dict()) from exc


def _raise_provider_runtime_error(
    workspace: Workspace,
    metadata: dict,
    exc: Exception,
) -> None:
    if metadata.get("configured_provider") == "mock":
        raise exc
    error_metadata = provider_metadata(
        workspace,
        provider_used=metadata.get("provider_used"),
        provider_error=str(exc),
    ).as_dict()
    raise HTTPException(status_code=502, detail=error_metadata) from exc


def _thought_history_root() -> Path:
    return Path(
        os.environ.get(
            "SNAPGRAPH_THOUGHT_HISTORY_DIR",
            "/Users/apple/Documents/软件体系结构大作业/data/user/workspace/chat",
        )
    )


def _thought_history_payload(root: Path, *, limit: int) -> dict:
    if not root.exists():
        return {
            "source_path": str(root),
            "items": [],
            "summary": {
                "turns": 0,
                "thinking_events": 0,
                "tool_events": 0,
                "content_events": 0,
            },
            "notice": "没有找到参考项目的历史对话记录。",
        }
    event_files = list(root.rglob("events.jsonl"))
    event_files.sort(
        key=lambda path: (
            0 if "deep_solve" in path.parts else 1,
            -path.stat().st_mtime,
        )
    )
    items = [_summarize_thought_events(path, root) for path in event_files[:limit]]
    items = [item for item in items if item]
    return {
        "source_path": str(root),
        "items": items,
        "summary": {
            "turns": len(items),
            "thinking_events": sum(item["thinking_steps"] for item in items),
            "tool_events": sum(item["tool_events"] for item in items),
            "content_events": sum(item["content_events"] for item in items),
        },
        "notice": "Thought 只显示阶段摘要，不展示模型内部草稿。",
    }


def _summarize_thought_events(path: Path, root: Path) -> dict | None:
    counts: dict[str, int] = {}
    stages: list[str] = []
    content_parts: list[str] = []
    turn_id = path.parent.name
    session_id = ""
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        event_type = str(event.get("type") or "").strip()
        if not event_type:
            continue
        counts[event_type] = counts.get(event_type, 0) + 1
        if event_type == "session":
            metadata = event.get("metadata") or {}
            turn_id = str(metadata.get("turn_id") or turn_id)
            session_id = str(metadata.get("session_id") or session_id)
        if event_type == "stage_start":
            stage = _thought_stage_label(str(event.get("stage") or ""))
            if stage and stage not in stages:
                stages.append(stage)
        if event_type == "progress":
            metadata = event.get("metadata") or {}
            stage = _thought_stage_label(str(event.get("stage") or metadata.get("phase") or ""))
            if stage and stage not in stages:
                stages.append(stage)
        if event_type == "content":
            content = str(event.get("content") or "").strip()
            if content:
                content_parts.append(content)

    if not counts:
        return None
    surface = _thought_surface_label(path)
    thinking_steps = counts.get("thinking", 0)
    tool_events = counts.get("tool_call", 0) + counts.get("tool_result", 0)
    content_events = counts.get("content", 0)
    stage_flow = stages[:4] or ["回答"]
    answer_preview = _compact_preview(" ".join(content_parts), limit=120)
    title = _thought_title(surface, answer_preview, turn_id)
    thought_lines = [
        f"{surface} 走过 {' → '.join(stage_flow)}。",
        f"记录到 {thinking_steps} 个 thought 片段、{tool_events} 个工具事件；这里显示摘要。",
    ]
    if answer_preview:
        thought_lines.append(f"输出预览：{answer_preview}")
    return {
        "id": turn_id,
        "turn_id": turn_id,
        "session_id": session_id,
        "surface": surface,
        "title": title,
        "relative_path": str(path.relative_to(root)),
        "stage_flow": stage_flow,
        "event_count": sum(counts.values()),
        "thinking_steps": thinking_steps,
        "tool_events": tool_events,
        "content_events": content_events,
        "answer_preview": answer_preview,
        "thought_lines": thought_lines,
    }


def _thought_surface_label(path: Path) -> str:
    if "deep_solve" in path.parts:
        return "Solve"
    if "deep_question" in path.parts:
        return "Question"
    if "research" in path.parts:
        return "Research"
    return "Chat"


def _thought_stage_label(stage: str) -> str:
    labels = {
        "planning": "Plan",
        "reasoning": "Reason",
        "responding": "Respond",
        "exploring": "Explore",
        "writing": "Write",
        "quizzing": "Quiz",
    }
    return labels.get(stage.strip().lower(), stage.strip())


def _thought_title(surface: str, preview: str, turn_id: str) -> str:
    if preview:
        heading = re.sub(r"^#+\s*", "", preview).strip()
        return f"{surface} · {heading[:34]}"
    return f"{surface} · {turn_id}"


def _compact_preview(text: str, *, limit: int) -> str:
    cleaned = re.sub(r"```[\s\S]*?```", " ", text)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


@app.on_event("startup")
def _startup() -> None:
    create_workspace(workspace=get_workspace())


# ── Workspace ──

@app.get("/api/workspace")
def api_workspace():
    ws = _workspace()
    diag = graph_diagnostics(ws)
    lint = lint_workspace(ws)
    with sqlite3.connect(ws.sqlite_path) as conn:
        source_count = conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        status_rows = conn.execute(
            "SELECT why_saved_status, COUNT(*) FROM cognitive_contexts GROUP BY why_saved_status"
        ).fetchall()
    context_status = {row[0]: row[1] for row in status_rows}
    top_hubs = [{"label": label, "degree": d} for label, d in diag.top_hubs]
    insights = graph_insights(ws)
    spaces = list_graph_spaces(ws)
    payload = {
        "sources": source_count,
        "saved_questions": len(question_pages(ws)),
        "nodes": diag.node_count,
        "edges": diag.edge_count,
        "lint_status": lint.status,
        "lint_errors": lint.errors,
        "lint_warnings": lint.warnings,
        "context_status": context_status,
        "node_types": diag.node_types,
        "top_hubs": top_hubs,
        "orphans": diag.orphans,
        "insights": insights,
        "workspace_path": str(ws.path),
        "provider": provider_metadata(ws).as_dict(),
        "spaces": spaces,
    }
    payload["workspace_health"] = build_workspace_health_pack(
        source_count=source_count,
        saved_questions=payload["saved_questions"],
        node_count=diag.node_count,
        edge_count=diag.edge_count,
        lint_status=lint.status,
        lint_errors=lint.errors,
        lint_warnings=lint.warnings,
        context_status=context_status,
        node_types=diag.node_types,
        top_hubs=top_hubs,
        orphans=diag.orphans,
        spaces=spaces,
        insights=insights,
    )
    payload["traceability_audit"] = build_source_traceability_audit(ws)
    return payload


# ── Graph spaces ──

@app.get("/api/spaces")
def api_spaces():
    return {"spaces": list_graph_spaces(_workspace())}


@app.post("/api/spaces")
def api_spaces_create(payload: dict):
    ws = _workspace()
    try:
        space = create_graph_space(
            ws,
            name=payload.get("name", ""),
            description=payload.get("description", ""),
            purpose=payload.get("purpose", ""),
            color=payload.get("color", "#315ea8"),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return space


@app.patch("/api/spaces/{space_id}")
def api_spaces_update(space_id: str, payload: dict):
    try:
        return update_graph_space(_workspace(), space_id, payload)
    except KeyError as exc:
        raise HTTPException(404, "Space not found") from exc


@app.get("/api/spaces/{space_id}/graph")
def api_space_graph(space_id: str):
    return _graph_payload(_workspace(), space_id)


@app.get("/api/spaces/{space_id}/sources")
def api_space_sources(space_id: str):
    return _sources_payload(_workspace(), space_id)


@app.post("/api/suggestions/route")
def api_suggestions_route(payload: dict):
    source_id = str(payload.get("source_id", "")).strip()
    if not source_id:
        raise HTTPException(400, "source_id is required")
    try:
        return create_route_suggestion(_workspace(), source_id)
    except KeyError as exc:
        raise HTTPException(404, "Source not found") from exc


@app.get("/api/suggestions")
def api_suggestions(status: str | None = None, space_id: str | None = None):
    return {
        "suggestions": list_suggestions(
            _workspace(),
            status=status,
            space_id=space_id,
        )
    }


@app.post("/api/suggestions/{suggestion_id}/accept")
def api_suggestions_accept(suggestion_id: str):
    try:
        return accept_suggestion(_workspace(), suggestion_id)
    except KeyError as exc:
        raise HTTPException(404, "Suggestion not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/suggestions/{suggestion_id}/reject")
def api_suggestions_reject(suggestion_id: str):
    try:
        return reject_suggestion(_workspace(), suggestion_id)
    except KeyError as exc:
        raise HTTPException(404, "Suggestion not found") from exc


# ── Sources ──

@app.get("/api/sources")
def api_sources(space_id: str | None = None):
    return _sources_payload(_workspace(), space_id)


def _sources_payload(ws: Workspace, space_id: str | None = None):
    space_filter = "" if not space_id or space_id == "all" else "WHERE s.graph_space_id = ?"
    params = [] if not space_filter else [space_id]
    with sqlite3.connect(ws.sqlite_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                s.id,
                s.title,
                s.type,
                s.imported_at,
                s.original_filename,
                s.summary,
                s.graph_space_id,
                COALESCE(gs.name, 'Default'),
                c.why_saved,
                c.why_saved_status,
                c.related_project,
                c.open_loops_json,
                c.future_recall_questions_json,
                c.confidence,
                COALESCE(c.review_status, 'unreviewed'),
                COALESCE(c.review_note, ''),
                COALESCE(c.reviewed_at, ''),
                COALESCE(m.routing_status, ''),
                COALESCE(m.routing_reason, '')
            FROM sources s
            LEFT JOIN cognitive_contexts c ON c.source_id = s.id
            LEFT JOIN graph_spaces gs ON gs.id = s.graph_space_id
            LEFT JOIN materials m ON m.source_id = s.id
            {space_filter}
            ORDER BY s.imported_at DESC
            """,
            params,
        ).fetchall()
    sources = []
    for row in rows:
        page_path = ws.wiki_dir / "sources" / f"{row[0]}.md"
        sources.append({
            "id": row[0],
            "title": row[1],
            "type": row[2],
            "imported_at": row[3],
            "original_filename": row[4],
            "summary": row[5] or "",
            "graph_space_id": row[6] or DEFAULT_GRAPH_SPACE_ID,
            "space_name": row[7] or "Default",
            "why_saved": row[8] or "",
            "why_saved_status": row[9] or "unknown",
            "related_project": row[10] or "",
            "open_loops": _loads_json_list(row[11]),
            "future_recall_questions": _loads_json_list(row[12]),
            "confidence": row[13] if row[13] is not None else 0.0,
            "review_status": row[14] or "unreviewed",
            "review_note": row[15] or "",
            "reviewed_at": row[16] or "",
            "routing_status": row[17] or "",
            "routing_reason": row[18] or "",
            "path": ws.relative_to_workspace(page_path),
        })
    return sources


@app.get("/api/sources/{source_id}")
def api_source_detail(source_id: str):
    ws = _workspace()
    page_path = ws.wiki_dir / "sources" / f"{source_id}.md"
    if not page_path.exists():
        raise HTTPException(404, "Source not found")
    detail = next((source for source in api_sources("all") if source["id"] == source_id), None)
    return {
        "markdown": page_path.read_text(encoding="utf-8"),
        "detail": detail or {},
    }


@app.patch("/api/sources/{source_id}/context")
def api_source_context_update(source_id: str, payload: dict):
    try:
        update_cognitive_context(
            _workspace(),
            source_id,
            why_saved=payload.get("why_saved"),
            related_project=payload.get("related_project"),
            open_loops=payload.get("open_loops"),
            future_recall_questions=payload.get("future_recall_questions"),
            confirm=bool(payload.get("confirm")),
        )
    except KeyError as exc:
        raise HTTPException(404, "Source not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    detail = next((source for source in api_sources("all") if source["id"] == source_id), None)
    return {"detail": detail or {}}


@app.patch("/api/sources/{source_id}/title")
def api_source_title_update(source_id: str, payload: dict):
    """Update the user-visible title for a captured source."""
    try:
        update_source_title(_workspace(), source_id, str(payload.get("title", "")))
    except KeyError as exc:
        raise HTTPException(404, "Source not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    detail = next((source for source in api_sources("all") if source["id"] == source_id), None)
    return {"detail": detail or {}}


@app.patch("/api/sources/{source_id}/review")
def api_source_review_update(source_id: str, payload: dict):
    """Persist a user review decision for an AI-inferred context."""
    try:
        review_ai_inference(
            _workspace(),
            source_id,
            review_status=str(payload.get("review_status", "")),
            review_note=str(payload.get("review_note", "")),
            why_saved=payload.get("why_saved"),
        )
    except KeyError as exc:
        raise HTTPException(404, "Source not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    detail = next((source for source in api_sources("all") if source["id"] == source_id), None)
    return {"detail": detail or {}}


# 鈹€鈹€ Trust operations 鈹€鈹€

@app.get("/api/trust/review")
def api_trust_review(
    status: str = "",
    risk: str = "",
    space_id: str = "",
    q: str = "",
    inferred: str = "",
    has_open_loops: bool | None = None,
):
    return list_review_items(
        _workspace(),
        {
            "status": status,
            "risk": risk,
            "space_id": space_id,
            "q": q,
            "inferred": inferred,
            "has_open_loops": has_open_loops,
        },
    )


@app.post("/api/trust/review/batch")
def api_trust_review_batch(payload: dict):
    try:
        return batch_review(
            _workspace(),
            source_ids=payload.get("source_ids") or [],
            action=str(payload.get("action") or ""),
            note=str(payload.get("note") or ""),
            rewrites=payload.get("rewrites") or {},
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/trust/review/{source_id}")
def api_trust_review_detail(source_id: str):
    try:
        return get_review_detail(_workspace(), source_id)
    except KeyError as exc:
        raise HTTPException(404, "Source not found") from exc


@app.get("/api/trust/summary")
def api_trust_summary():
    return trust_summary(_workspace())


@app.get("/api/trust/diagnostics")
def api_trust_diagnostics():
    return trust_diagnostics(_workspace())


@app.get("/api/trust/open-loops")
def api_trust_open_loops(state: str = ""):
    return list_open_loops(_workspace(), state=state or None)


@app.get("/api/governance/report")
def api_governance_report():
    return build_workspace_governance_report(_workspace())


@app.patch("/api/trust/open-loops/{loop_id}")
def api_trust_open_loop_update(loop_id: str, payload: dict):
    try:
        return update_open_loop_state(
            _workspace(),
            loop_id,
            state=str(payload.get("state") or ""),
            note=str(payload.get("note") or ""),
        )
    except KeyError as exc:
        raise HTTPException(404, "Open loop not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/ingest")
def api_ingest(
    file: UploadFile = File(...),
    why: str = Form(""),
    space_id: str = Form(""),
    route_mode: str = Form("auto"),
):
    ws = _workspace()
    suffix = Path(file.filename or "untitled.md").suffix.lower()
    if suffix not in {".gif", ".htm", ".html", ".jpeg", ".jpg", ".markdown", ".md", ".pdf", ".png", ".txt", ".webp"}:
        raise HTTPException(400, f"Unsupported file type: {suffix}")
    route_mode = (route_mode or "auto").strip().lower()
    if route_mode not in {"auto", "manual", "inbox"}:
        raise HTTPException(400, "route_mode must be auto, manual, or inbox")
    if route_mode == "manual" and not space_id.strip():
        raise HTTPException(400, "space_id is required when route_mode is manual")
    ingest_space_id = space_id.strip() if route_mode == "manual" else INBOX_GRAPH_SPACE_ID
    with tempfile.TemporaryDirectory() as tmpdir:
        source_path = Path(tmpdir) / (file.filename or "untitled")
        source_path.write_bytes(file.file.read())
        llm, metadata = _resolve_ingest_llm(ws)
        try:
            result = ingest_source(
                ws,
                source_path,
                why=why or None,
                llm=llm,
                space_id=ingest_space_id,
                dedupe_scope="workspace" if route_mode == "auto" else "space",
            )
        except Exception as exc:
            _raise_provider_runtime_error(ws, metadata.as_dict(), exc)
    routing_suggestion = (
        get_suggestion(ws, result.routing_suggestion_id)
        if result.routing_suggestion_id
        else None
    )
    if route_mode == "auto" and _should_auto_accept_route(routing_suggestion):
        routing_suggestion = accept_suggestion(ws, routing_suggestion["id"])
    source_detail = next((source for source in api_sources("all") if source["id"] == result.source.id), {})
    return {
        "source_id": result.source.id,
        "title": source_detail.get("title", result.source.title),
        "type": source_detail.get("type", result.source.type),
        "summary": source_detail.get("summary", result.source.summary),
        "status": result.cognitive_context.why_saved_status,
        "wiki_page": result.page.relative_page_path,
        "graph_space_id": source_detail.get("graph_space_id", result.source.graph_space_id),
        "space_name": source_detail.get("space_name", ""),
        "routing_suggestion_id": result.routing_suggestion_id,
        "warnings": result.warnings,
        "deduplicated": result.deduplicated,
        "provider": metadata.as_dict(),
        "focus_graph": focus_graph_for_payload(
            ws,
            {"source_id": result.source.id, "space_id": source_detail.get("graph_space_id", result.source.graph_space_id)},
        ),
        "routing_suggestion": routing_suggestion,
        "decision_layers": build_collect_decision_layers(
            result,
            source_detail=source_detail,
            routing_suggestion=routing_suggestion,
            route_mode=route_mode,
            provider_metadata=metadata.as_dict(),
        ),
    }


def _should_auto_accept_route(suggestion: dict | None) -> bool:
    if not suggestion or suggestion.get("status") != "pending":
        return False
    payload = suggestion.get("payload") or {}
    target_space_id = payload.get("target_space_id")
    confidence = float(suggestion.get("confidence") or 0)
    if target_space_id == DEFAULT_GRAPH_SPACE_ID and confidence <= 0.52:
        return False
    return confidence >= 0.62


@app.post("/api/sources/{source_id}/route")
def api_source_route(source_id: str, payload: dict):
    space_id = str(payload.get("space_id") or "").strip()
    if not space_id:
        raise HTTPException(400, "space_id is required")
    reason = str(payload.get("reason") or "User moved from graph workspace.").strip()
    try:
        move_source_to_space(_workspace(), source_id, space_id, reason=reason)
    except KeyError as exc:
        raise HTTPException(404, "Source or space not found") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    detail = next((source for source in api_sources("all") if source["id"] == source_id), None)
    return {"detail": detail or {}}


def _resolve_ingest_llm(workspace: Workspace):
    try:
        return resolve_llm_with_metadata(workspace)
    except RuntimeError as exc:
        return MockLLM(), provider_metadata(
            workspace,
            provider_used="mock",
            fallback_used=True,
            provider_error=str(exc),
        )


# ── Graph ──

@app.get("/api/graph")
def api_graph(space_id: str = DEFAULT_GRAPH_SPACE_ID):
    return _graph_payload(_workspace(), space_id)


@app.get("/api/graph/layout")
def api_graph_layout(view_id: str):
    return load_graph_layout(_workspace(), view_id)


@app.patch("/api/graph/layout")
def api_graph_layout_save(payload: dict):
    view_id = str(payload.get("view_id", "")).strip()
    if not view_id:
        raise HTTPException(400, "view_id is required")
    try:
        return save_graph_layout(
            _workspace(),
            view_id=view_id,
            graph_space_id=str(payload.get("graph_space_id") or DEFAULT_GRAPH_SPACE_ID),
            positions=list(payload.get("positions") or []),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/graph/edges")
def api_graph_edge_create(payload: dict):
    try:
        edge = create_manual_edge(
            _workspace(),
            source=str(payload.get("source", "")),
            target=str(payload.get("target", "")),
            relation=str(payload.get("relation") or "related_to"),
            reason=str(payload.get("reason", "")),
            graph_space_id=str(payload.get("graph_space_id") or DEFAULT_GRAPH_SPACE_ID),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    return {"edge": edge}


@app.patch("/api/graph/edges/{edge_id}")
def api_graph_edge_update(edge_id: str, payload: dict):
    try:
        edge = update_graph_edge(
            _workspace(),
            edge_id,
            status=str(payload.get("status", "")),
            reason=str(payload.get("reason", "")),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "Edge not found") from exc
    return {"edge": edge}


@app.post("/api/graph/thoughts")
def api_graph_thought_create(payload: dict):
    try:
        return create_user_thought(
            _workspace(),
            graph_space_id=str(payload.get("graph_space_id") or DEFAULT_GRAPH_SPACE_ID),
            node_ids=[str(node_id) for node_id in payload.get("node_ids", [])],
            label=str(payload.get("label", "")),
            reason=str(payload.get("reason", "")),
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/graph/themes")
def api_graph_themes(space_id: str | None = None):
    return {"themes": list_graph_themes(_workspace(), space_id)}


@app.post("/api/graph/themes")
def api_graph_theme_create(payload: dict):
    try:
        return create_graph_theme(
            _workspace(),
            graph_space_id=str(payload.get("graph_space_id") or DEFAULT_GRAPH_SPACE_ID),
            label=str(payload.get("label", "")),
            member_node_ids=[str(node_id) for node_id in payload.get("member_node_ids", [])],
            reason=str(payload.get("reason", "")),
            description=str(payload.get("description", "")),
            origin=str(payload.get("origin") or "user"),
            status=str(payload.get("status") or "confirmed"),
            confidence=float(payload.get("confidence", 1.0)),
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.patch("/api/graph/themes/{theme_id}")
def api_graph_theme_update(theme_id: str, payload: dict):
    try:
        return update_graph_theme(_workspace(), theme_id, payload)
    except (TypeError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, "Theme not found") from exc


# ── Focus graph ──

@app.post("/api/focus")
def api_focus(payload: dict):
    ws = _workspace()
    question = str(payload.get("question") or "").strip()
    if not question:
        return focus_graph_for_payload(ws, payload)

    space_id = str(payload.get("space_id") or "all")
    mode = str(payload.get("mode") or "auto")
    depth = str(payload.get("depth") or "quick")
    recall_metadata = _recall_turn_metadata(payload)
    retrieval = retrieve_for_question(
        ws,
        question,
        space_id=space_id,
        context_source_ids=_payload_context_source_ids(payload),
    )
    focus = focus_graph_from_retrieval(ws, retrieval, space_id=space_id)
    if _safe_recall_depth(depth) == "deep":
        focus["thought"] = _public_thought_payload(
            question,
            retrieval,
            previous_turns=recall_metadata["previous_turns"],
            status="done",
        )
    if _safe_recall_mode(mode) == "files":
        _record_recall_history(
            ws,
            question=question,
            mode=mode,
            depth=depth,
            space_id=space_id,
            **recall_metadata,
            response={
                "text": "",
                "contexts": _contexts_payload(ws, retrieval),
                "local_files": _local_files_payload(ws, retrieval),
                "thought": focus.get("thought") or {},
            },
        )
    return focus


# ── Ask ──

@app.post("/api/ask")
def api_ask(payload: dict):
    question = payload.get("question", "").strip()
    save = payload.get("save", False)
    mode = str(payload.get("mode") or "auto")
    depth = str(payload.get("depth") or "quick")
    if not question:
        raise HTTPException(400, "Question is required")
    space_id = str(payload.get("space_id") or "all")
    context_source_ids = _payload_context_source_ids(payload)
    recall_metadata = _recall_turn_metadata(payload)
    ws = _workspace()
    retrieval = retrieve_for_question(
        ws,
        question,
        space_id=space_id,
        context_source_ids=context_source_ids,
    )
    if retrieval.contexts:
        try:
            llm, metadata = resolve_llm_with_metadata(ws)
            metadata_dict = metadata.as_dict()
        except RuntimeError as exc:
            llm = None
            metadata_dict = provider_metadata(
                ws,
                provider_used="none",
                fallback_used=True,
                provider_error=str(exc),
            ).as_dict()
    else:
        llm = None
        metadata_dict = provider_metadata(ws, provider_used="none").as_dict()
    try:
        result = answer_question(
            ws,
            question,
            llm=llm,
            space_id=space_id,
            retrieval=retrieval,
        )
    except Exception as exc:
        if llm is not None:
            metadata_dict = provider_metadata(
                ws,
                provider_used=metadata_dict.get("provider_used"),
                fallback_used=True,
                provider_error=str(exc),
            ).as_dict()
            result = answer_question(
                ws,
                question,
                llm=None,
                space_id=space_id,
                retrieval=retrieval,
            )
        else:
            _raise_provider_runtime_error(ws, metadata_dict, exc)
    response = _ask_response_payload(
        ws,
        result,
        metadata_dict,
        space_id,
        thought=_public_thought_payload(
            result.question,
            result.retrieval,
            previous_turns=recall_metadata["previous_turns"],
        ) if _safe_recall_depth(depth) == "deep" else None,
    )
    _record_recall_history(
        ws,
        question=question,
        mode=mode,
        depth=depth,
        space_id=space_id,
        **recall_metadata,
        response=response,
    )
    if save:
        page = save_answer(ws, result)
        response["saved_page"] = page.relative_page_path
    return response


@app.post("/api/ask/stream")
def api_ask_stream(payload: dict):
    question = payload.get("question", "").strip()
    save = payload.get("save", False)
    depth = str(payload.get("depth") or "quick")
    mode = str(payload.get("mode") or "auto")
    if not question:
        raise HTTPException(400, "Question is required")
    space_id = str(payload.get("space_id") or "all")
    context_source_ids = _payload_context_source_ids(payload)
    recall_metadata = _recall_turn_metadata(payload)

    def generate():
        ws = _workspace()
        retrieval = retrieve_for_question(
            ws,
            question,
            space_id=space_id,
            context_source_ids=context_source_ids,
        )
        focus_graph = focus_graph_from_retrieval(ws, retrieval, space_id=space_id)
        yield _sse(
            "stage",
            {
                "id": "evidence",
                "label": "找本地证据",
                "status": "done",
                "detail": f"找到 {len(retrieval.contexts)} 条相关材料",
            },
        )
        yield _sse(
            "focus",
            {
                "contexts": _contexts_payload(ws, retrieval),
                "graph_paths": retrieval.graph_paths,
                "diagnostics": asdict(retrieval.diagnostics),
                "focus_graph": focus_graph,
            },
        )

        thought_payload = None
        if not retrieval.contexts:
            if _safe_recall_depth(depth) == "deep":
                thought_payload = _public_thought_payload(
                    question,
                    retrieval,
                    previous_turns=recall_metadata["previous_turns"],
                    status="done",
                )
                yield from _stream_public_thought(thought_payload)
            result = answer_question(ws, question, llm=None, space_id=space_id, retrieval=retrieval)
            response = _ask_response_payload(
                ws,
                result,
                provider_metadata(ws, provider_used="none").as_dict(),
                space_id,
                thought=thought_payload,
            )
            _record_recall_history(
                ws,
                question=question,
                mode=mode,
                depth=depth,
                space_id=space_id,
                **recall_metadata,
                response=response,
            )
            if save:
                page = save_answer(ws, result)
                response["saved_page"] = page.relative_page_path
            yield _sse("final", response)
            return

        yield _sse(
            "stage",
            {
                "id": "read",
                "label": "读用户原话",
                "status": "done",
                "detail": f"{retrieval.diagnostics.user_stated_contexts} 条 user-stated",
            },
        )
        yield _sse(
            "stage",
            {
                "id": "connect",
                "label": "检查图谱连接",
                "status": "done",
                "detail": f"{len(retrieval.graph_paths)} 条连接路径",
            },
        )
        if _safe_recall_depth(depth) == "deep":
            thought_payload = _public_thought_payload(
                question,
                retrieval,
                previous_turns=recall_metadata["previous_turns"],
                status="done",
            )
            yield from _stream_public_thought(thought_payload)
        yield _sse(
            "stage",
            {
                "id": "write",
                "label": "生成 AI 回复",
                "status": "active",
                "detail": _provider_action_label(provider_metadata(ws).as_dict()),
            },
        )

        try:
            llm, metadata = resolve_llm_with_metadata(ws)
            metadata_dict = metadata.as_dict()
            context_dicts = _context_dicts(retrieval)
            if hasattr(llm, "stream_recall_reply"):
                reply_chunks: list[str] = []
                for chunk in llm.stream_recall_reply(question, context_dicts, retrieval.graph_paths):
                    reply_chunks.append(chunk)
                    yield _sse("chunk", {"text": chunk})
                ai_reply = clean_answer_glyphs("".join(reply_chunks).strip())
                final_text = render_answer(retrieval, question=question)
                if ai_reply:
                    final_text = _replace_markdown_section(final_text, ANSWER_CONCLUSION, ai_reply)
                final_text = ensure_retrieval_diagnostics(final_text, retrieval)
                result = AnswerResult(question=question, text=final_text, retrieval=retrieval)
            else:
                result = answer_question(ws, question, llm=llm, space_id=space_id, retrieval=retrieval)
        except Exception as exc:
            metadata_dict = provider_metadata(
                ws,
                provider_used="none",
                fallback_used=True,
                provider_error=str(exc),
            ).as_dict()
            yield _sse(
                "stage",
                {
                    "id": "write",
                    "label": "生成 AI 回复",
                    "status": "error",
                    "detail": "模型暂时不可用，保留本地证据",
                },
            )
            result = answer_question(ws, question, llm=None, space_id=space_id, retrieval=retrieval)

        response = _ask_response_payload(ws, result, metadata_dict, space_id, thought=thought_payload)
        _record_recall_history(
            ws,
            question=question,
            mode=mode,
            depth=depth,
            space_id=space_id,
            **recall_metadata,
            response=response,
        )
        if save:
            page = save_answer(ws, result)
            response["saved_page"] = page.relative_page_path
        yield _sse("stage", {"id": "write", "label": "生成 AI 回复", "status": "done", "detail": "回答已完成"})
        yield _sse("final", response)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/open-local")
def api_open_local(payload: dict):
    ws = _workspace()
    source_id = str(payload.get("source_id") or "").strip()
    target = str(payload.get("target") or payload.get("open_target") or "raw").strip()
    if source_id:
        local_file = _local_file_for_source(ws, source_id)
        if not local_file:
            raise HTTPException(404, "Source not found")
        relative_path = local_file["path"] if target == "source_page" else local_file["raw_path"]
    else:
        relative_path = str(payload.get("path") or "").strip()
    path = _workspace_file_path(ws, relative_path)
    _open_path(path)
    return {
        "opened_path": ws.relative_to_workspace(path),
        "absolute_path": str(path),
    }


# ── Report ──

@app.get("/api/report")
def api_report():
    ws = _workspace()
    report_path = ws.wiki_dir / "graph_report.md"
    if not report_path.exists():
        raise HTTPException(404, "Report not generated yet")
    return {"markdown": report_path.read_text(encoding="utf-8")}


@app.post("/api/report/generate")
def api_report_generate():
    ws = _workspace()
    report = write_graph_report(ws)
    return {"path": report.relative_page_path, "markdown": report.text}


# ── Lint ──

@app.get("/api/lint")
def api_lint():
    ws = _workspace()
    lint = lint_workspace(ws)
    return {"status": lint.status, "errors": lint.errors, "warnings": lint.warnings}


# ── Questions ──

@app.get("/api/questions")
def api_questions():
    ws = _workspace()
    questions = []
    for page_path in question_pages(ws):
        text = page_path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        questions.append({
            "id": fm.get("id", page_path.stem),
            "question": _section_text(text, "## Question"),
            "path": ws.relative_to_workspace(page_path),
            "evidence_source_ids": json.loads(fm.get("evidence_source_ids", "[]")),
        })
    return questions


@app.get("/api/questions/{question_id}")
def api_question_detail(question_id: str):
    ws = _workspace()
    page_path = ws.wiki_dir / "questions" / f"{question_id}.md"
    if not page_path.exists():
        raise HTTPException(404, "Question not found")
    text = page_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    answer = _markdown_section(text, "## Answer", ["## Evidence Source Pages", "## Saved Graph Paths"])
    return {
        "id": fm.get("id", question_id),
        "question": _section_text(text, "## Question"),
        "answer": _clean_markdown_text(answer),
        "answer_heading": "Answer",
        "markdown": text,
        "path": ws.relative_to_workspace(page_path),
        "evidence_source_ids": json.loads(fm.get("evidence_source_ids", "[]")),
    }


# ── Demo ──

@app.post("/api/demo/load")
def api_demo_load(payload: dict | None = Body(default=None)):
    ws = _workspace()
    use_provider = bool((payload or {}).get("use_provider"))
    if use_provider:
        llm, metadata = _resolve_llm_or_503(ws)
    else:
        llm = MockLLM()
        metadata = provider_metadata(ws, provider_used="mock")
    result = load_demo_dataset(ws, llm=llm)
    return {
        "ingested": result.ingested,
        "skipped": result.skipped,
        "saved_answers": result.saved_answers,
        "report": result.report_path,
        "provider": metadata.as_dict(),
    }


@app.get("/api/thought-history")
def api_thought_history(limit: int = 4):
    root = _thought_history_root()
    if limit < 1:
        limit = 1
    limit = min(limit, 8)
    return _thought_history_payload(root, limit=limit)


@app.get("/api/recall-history")
def api_recall_history(limit: int = 12, thread_id: str = ""):
    if limit < 1:
        limit = 1
    thread_id = thread_id.strip()
    return _recall_history_payload(_workspace(), limit=min(limit, 50 if thread_id else 24), thread_id=thread_id)


# ── Config ──

@app.get("/api/config")
def api_config_get():
    ws = _workspace()
    config = load_config(ws)
    metadata = provider_metadata(ws).as_dict()
    return {
        "provider": config.llm.provider,
        "model": config.llm.model,
        "api_key_env": config.llm.api_key_env,
        "has_api_key": bool(os.environ.get(config.llm.api_key_env or "SNAPGRAPH_LLM_API_KEY", "")),
        "provider_ready": metadata["provider_ready"],
        "provider_error": metadata["provider_error"],
        "runtime": metadata,
    }


@app.put("/api/config")
def api_config_put(payload: dict):
    ws = _workspace()
    config = load_config(ws)
    provider = payload.get("provider", config.llm.provider)
    if provider not in ("mock", "deepseek", "anthropic", "qwen"):
        raise HTTPException(400, f"Unknown provider: {provider}")
    api_key_env = payload.get("api_key_env", config.llm.api_key_env)
    try:
        api_key_env = validate_api_key_env_name(api_key_env)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    updated = SnapGraphConfig(
        workspace_version=config.workspace_version,
        llm=LLMConfig(
            provider=provider,
            model=payload.get("model", config.llm.model),
            api_key_env=api_key_env,
        ),
        retrieval=config.retrieval,
    )
    save_config(ws, updated)
    return {"provider": provider, "runtime": provider_metadata(ws).as_dict()}


# ── Demo questions ──

@app.get("/api/demo/questions")
def api_demo_questions():
    return {"questions": DEMO_QUESTIONS}


# ── Helpers ──

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _provider_action_label(metadata: dict) -> str:
    provider = metadata.get("provider_used") or metadata.get("configured_provider") or "mock"
    model = metadata.get("model_used") or ""
    if provider == "mock":
        return "MockLLM 正在按本地证据组织回答。"
    label = f"{provider} · {model}" if model else str(provider)
    return f"{label} 正在组织回答。"


def _record_recall_history(
    ws: Workspace,
    *,
    question: str,
    mode: str,
    depth: str,
    space_id: str,
    thread_id: str = "",
    turn_id: str = "",
    turn_index: int = 0,
    previous_turns: list[dict] | None = None,
    response: dict,
) -> None:
    context_source_ids = [
        str(context.get("source_id"))
        for context in response.get("contexts", [])
        if context.get("source_id")
    ]
    history_id = turn_id or _recall_history_id(question, space_id)
    now = _now_iso()
    answer_text = _preserve_answer_markdown(str(response.get("text") or ""))
    answer_preview = _compact_preview(answer_text, limit=180)
    thought = response.get("thought") or {}
    thought_summary = str(thought.get("summary") or "").strip()
    sanitized_previous_turns = _sanitize_previous_turns(previous_turns or [])
    with sqlite3.connect(ws.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO recall_history (
                id,
                thread_id,
                turn_id,
                turn_index,
                question,
                mode,
                depth,
                space_id,
                previous_turns_json,
                context_source_ids_json,
                answer_text,
                answer_preview,
                thought_summary,
                thought_json,
                context_count,
                local_file_count,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                thread_id = excluded.thread_id,
                turn_id = excluded.turn_id,
                turn_index = excluded.turn_index,
                question = excluded.question,
                mode = excluded.mode,
                depth = excluded.depth,
                space_id = excluded.space_id,
                previous_turns_json = excluded.previous_turns_json,
                context_source_ids_json = excluded.context_source_ids_json,
                answer_text = excluded.answer_text,
                answer_preview = excluded.answer_preview,
                thought_summary = excluded.thought_summary,
                thought_json = excluded.thought_json,
                context_count = excluded.context_count,
                local_file_count = excluded.local_file_count,
                updated_at = excluded.updated_at
            """,
            (
                history_id,
                thread_id,
                turn_id,
                int(turn_index or 0),
                question,
                _safe_recall_mode(mode),
                _safe_recall_depth(depth),
                space_id or "all",
                json.dumps(sanitized_previous_turns, ensure_ascii=False),
                json.dumps(context_source_ids, ensure_ascii=False),
                answer_text,
                answer_preview,
                thought_summary,
                json.dumps(thought, ensure_ascii=False),
                len(response.get("contexts", [])),
                len(response.get("local_files", [])),
                now,
                now,
            ),
        )


def _recall_history_payload(ws: Workspace, *, limit: int, thread_id: str = "") -> dict:
    with sqlite3.connect(ws.sqlite_path) as conn:
        where = "WHERE thread_id = ? OR id = ?" if thread_id else ""
        params: tuple[object, ...] = (thread_id, thread_id) if thread_id else ()
        total = int(conn.execute(f"SELECT COUNT(*) FROM recall_history {where}", params).fetchone()[0])
        rows = conn.execute(
            f"""
            SELECT
                id,
                thread_id,
                turn_id,
                turn_index,
                question,
                mode,
                depth,
                space_id,
                previous_turns_json,
                context_source_ids_json,
                answer_text,
                answer_preview,
                thought_summary,
                thought_json,
                context_count,
                local_file_count,
                created_at,
                updated_at
            FROM recall_history
            {where}
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (*params, limit),
        ).fetchall()
    items = [
        {
            "id": row[0],
            "thread_id": row[1],
            "turn_id": row[2],
            "turn_index": row[3],
            "question": row[4],
            "mode": row[5],
            "depth": row[6],
            "space_id": row[7],
            "previous_turns": _loads_json_object_list(row[8]),
            "context_source_ids": _loads_json_list(row[9]),
            "answer_text": row[10],
            "answer_preview": row[11],
            "thought_summary": row[12],
            "thought": _loads_json_dict(row[13]),
            "context_count": row[14],
            "local_file_count": row[15],
            "created_at": row[16],
            "updated_at": row[17],
        }
        for row in rows
    ]
    summary = {
        "total": total,
        "returned": len(rows),
    }
    return {
        "items": items,
        "summary": summary,
        "history_insights": build_recall_history_insights(items, summary),
    }


def _recall_history_id(question: str, space_id: str) -> str:
    digest = hashlib.sha1(f"{space_id or 'all'}\n{question.strip()}".encode("utf-8")).hexdigest()[:14]
    return f"recall_{digest}"


def _recall_turn_metadata(payload: dict) -> dict:
    turn_index = payload.get("turn_index") or 0
    try:
        turn_index_int = int(turn_index)
    except (TypeError, ValueError):
        turn_index_int = 0
    return {
        "thread_id": str(payload.get("thread_id") or "").strip(),
        "turn_id": str(payload.get("turn_id") or "").strip(),
        "turn_index": max(0, turn_index_int),
        "previous_turns": _payload_previous_turns(payload),
    }


def _payload_previous_turns(payload: dict) -> list[dict]:
    return _sanitize_previous_turns(payload.get("previous_turns") or [])


def _sanitize_previous_turns(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []
    turns: list[dict] = []
    for item in raw[-8:]:
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or "").strip()
        if not question:
            continue
        turns.append({
            "question": _compact_inline(question, 160),
            "answer_preview": _compact_inline(str(item.get("answer_preview") or item.get("answer") or ""), 240),
            "mode": _safe_recall_mode(str(item.get("mode") or "auto")),
            "depth": _safe_recall_depth(str(item.get("depth") or "quick")),
        })
    return turns


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_recall_mode(mode: str) -> str:
    return mode if mode in {"auto", "files", "answer"} else "auto"


def _safe_recall_depth(depth: str) -> str:
    return depth if depth in {"quick", "deep"} else "quick"


def _context_dicts(retrieval) -> list[dict]:
    return [
        {
            "source_id": context.source_id,
            "source_page": context.source_page,
            "title": context.title,
            "why_saved": context.why_saved,
            "why_saved_status": context.why_saved_status,
            "related_project": context.related_project,
            "open_loops": context.open_loops,
            "future_recall_questions": context.future_recall_questions,
            "graph_space_id": context.graph_space_id,
            "space_name": context.space_name,
            "source_excerpt": context.source_excerpt,
        }
        for context in retrieval.contexts
    ]


def _public_thought_payload(
    question: str,
    retrieval,
    *,
    previous_turns: list[dict] | None = None,
    status: str = "done",
) -> dict:
    contexts = retrieval.contexts
    user_count = retrieval.diagnostics.user_stated_contexts
    ai_count = retrieval.diagnostics.ai_inferred_contexts
    evidence_titles = _dedupe_texts([context.title for context in contexts])[:4]
    primary_title = evidence_titles[0] if evidence_titles else ""
    sanitized_previous_turns = _sanitize_previous_turns(previous_turns or [])
    stage_flow = ["Plan", "Retrieve", "Think", "Verify", "Finish"]
    trace_events: list[dict] = []

    def add_trace(label: str, phase: str, trace_role: str, text: str) -> None:
        trace_events.append(
            _public_thought_trace_event(
                index=len(trace_events) + 1,
                label=label,
                phase=phase,
                trace_role=trace_role,
                text=text,
                status=status,
            )
        )

    add_trace(
        "Plan",
        "planning",
        "plan",
        f"把“{_compact_inline(question, 42)}”拆成要恢复的记忆对象、可用证据、回答边界三部分。",
    )
    if sanitized_previous_turns:
        add_trace(
            "Context",
            "planning",
            "thought",
            f"沿用同一窗口前 {len(sanitized_previous_turns)} 轮摘要，只读取问题和公开回答摘要，不读取隐藏草稿。",
        )
    if contexts:
        evidence_label = "、".join(evidence_titles[:3])
        add_trace(
            "Retrieve",
            "retrieval",
            "retrieve",
            f"从本地图谱召回 {len(contexts)} 条材料，优先检查 {evidence_label}。",
        )
        add_trace(
            "Think",
            "reasoning",
            "thought",
            "把召回材料按“用户明确说过 / AI 推断 / 只来自正文命中”分层，先用高信任材料支撑结论。",
        )
        if user_count:
            add_trace(
                "Think",
                "reasoning",
                "thought",
                f"{user_count} 条带有用户写过的保存理由，可以当作更靠前的判断依据。",
            )
        if ai_count:
            add_trace(
                "Verify",
                "verification",
                "thought",
                f"{ai_count} 条是 AI 猜的理由，只能作为线索，不能当成你的原话。",
            )
        if retrieval.graph_paths:
            add_trace(
                "Verify",
                "verification",
                "thought",
                f"用 {len(retrieval.graph_paths)} 条连接路径检查材料之间是否互相支撑，避免只凭一个片段下结论。",
            )
    else:
        add_trace("Retrieve", "retrieval", "retrieve", "这次没有找到可靠本地材料，所以答案会先说明低置信度。")
        add_trace("Think", "reasoning", "thought", "没有证据时只整理问题本身，不补写你当时的真实动机。")
        add_trace("Verify", "verification", "thought", "没有证据时不会替你编造当时为什么保存。")
    add_trace("Finish", "answering", "response", "先给结论，再把证据边界、AI 推断和下一步分开写。")
    lines = [f"{event['label']}：{event['text']}" for event in trace_events]
    summary = (
        f"本轮按 Plan → Retrieve → Verify 先看 {primary_title}，再回答。"
        if primary_title
        else "本轮按 Plan → Retrieve → Verify 运行，但没有可靠材料，先说明边界再回答。"
    )
    return {
        "id": "current-recall-thought",
        "title": "Thought",
        "status": status,
        "question": question,
        "summary": summary,
        "lines": lines,
        "trace_events": trace_events,
        "stage_flow": stage_flow,
        "evidence_titles": evidence_titles,
        "notice": "这是后端 solve 模式的公开推理轨迹；不展示模型私有草稿。",
    }


def _public_thought_trace_event(
    *,
    index: int,
    label: str,
    phase: str,
    trace_role: str,
    text: str,
    status: str,
) -> dict:
    return {
        "trace_id": f"recall-{phase}-{index}",
        "phase": phase,
        "label": label,
        "trace_role": trace_role,
        "call_kind": "llm_reasoning",
        "trace_kind": "llm_output" if status == "done" else "llm_chunk",
        "call_state": "complete" if status == "done" else "running",
        "index": index,
        "text": text,
    }


def _thought_trace_events_for_stream(thought_payload: dict) -> list[dict]:
    trace_events = thought_payload.get("trace_events")
    if isinstance(trace_events, list) and trace_events:
        return [
            {
                **event,
                "text": str(event.get("text") or ""),
            }
            for event in trace_events
            if isinstance(event, dict) and str(event.get("text") or "").strip()
        ]
    events = []
    for index, line in enumerate(thought_payload.get("lines", []), start=1):
        text = str(line or "")
        match = re.match(r"^([^：:]{1,24})[：:]\s*(.+)$", text)
        label = match.group(1) if match else "Think"
        body = match.group(2) if match else text
        events.append(
            _public_thought_trace_event(
                index=index,
                label=label,
                phase="reasoning",
                trace_role="thought",
                text=body,
                status="done",
            )
        )
    return events


def _split_public_thought_text(text: str, chunk_size: int = 18) -> list[str]:
    cleaned = str(text or "")
    if len(cleaned) <= chunk_size:
        return [cleaned] if cleaned else []
    chunks: list[str] = []
    buffer = ""
    for char in cleaned:
        buffer += char
        if len(buffer) >= chunk_size and char in "，。；、,!?！？ ":
            chunks.append(buffer)
            buffer = ""
        elif len(buffer) >= chunk_size * 2:
            chunks.append(buffer)
            buffer = ""
    if buffer:
        chunks.append(buffer)
    return chunks


def _thought_stream_delay() -> float:
    raw = os.environ.get("SNAPGRAPH_THOUGHT_STREAM_DELAY", "0.012")
    try:
        return max(0.0, min(float(raw), 0.2))
    except ValueError:
        return 0.012


def _stream_public_thought(thought_payload: dict):
    trace_events = _thought_trace_events_for_stream(thought_payload)
    thinking_payload = {
        **thought_payload,
        "status": "thinking",
        "lines": [],
        "trace_events": [],
    }
    yield _sse("thought", thinking_payload)
    delay = _thought_stream_delay()
    for event in trace_events:
        for chunk in _split_public_thought_text(str(event.get("text") or "")):
            yield _sse(
                "thought_delta",
                {
                    **event,
                    "id": thought_payload.get("id") or "current-recall-thought",
                    "text": chunk,
                    "status": "thinking",
                    "trace_kind": "llm_chunk",
                    "call_state": "running",
                },
            )
            if delay:
                import time

                time.sleep(delay)
    done_events = [
        {
            **event,
            "trace_kind": "llm_output",
            "call_state": "complete",
        }
        for event in trace_events
    ]
    done_lines = [f"{event['label']}：{event['text']}" for event in done_events]
    yield _sse(
        "thought",
        {**thought_payload, "status": "done", "lines": done_lines, "trace_events": done_events},
    )


def _dedupe_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            result.append(text)
            seen.add(text)
    return result


def _compact_inline(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _payload_context_source_ids(payload: dict) -> list[str]:
    raw = payload.get("context_source_ids") or payload.get("batch_source_ids") or []
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def _contexts_payload(ws: Workspace, retrieval) -> list[dict]:
    confidence_by_source = _context_confidence_by_source(ws)
    return [
        {
            "source_id": context.source_id,
            "title": context.title,
            "why_saved": context.why_saved,
            "why_saved_status": context.why_saved_status,
            "related_project": context.related_project,
            "open_loops": context.open_loops,
            "future_recall_questions": context.future_recall_questions,
            "confidence": confidence_by_source.get(context.source_id, 0.0),
            "graph_space_id": context.graph_space_id,
            "space_name": context.space_name,
            "source_excerpt": context.source_excerpt,
        }
        for context in retrieval.contexts
    ]


def _local_files_payload(ws: Workspace, retrieval) -> list[dict]:
    files = []
    for context in retrieval.contexts:
        local_file = _local_file_for_source(ws, context.source_id)
        if not local_file:
            continue
        reason = _local_file_reason(context)
        files.append({
            **local_file,
            "why_saved": context.why_saved,
            "why_saved_status": context.why_saved_status or "unknown",
            "space_name": context.space_name,
            "source_excerpt": context.source_excerpt,
            "match_reason": reason,
        })
    return files


def _local_file_for_source(ws: Workspace, source_id: str) -> dict | None:
    with sqlite3.connect(ws.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT id, title, path
            FROM sources
            WHERE id = ?
            """,
            (source_id,),
        ).fetchone()
    if row is None:
        return None
    source_page = f"wiki/sources/{row[0]}.md"
    raw_path = row[2] or ""
    return {
        "source_id": row[0],
        "title": row[1],
        "path": source_page,
        "raw_path": raw_path,
        "open_target": "raw" if raw_path else "source_page",
    }


def _local_file_reason(context) -> str:
    if context.why_saved_status == "user-stated" and context.why_saved:
        return "命中了你保存时写下的理由。"
    if context.why_saved_status == "AI-inferred":
        return "命中了系统推断出的关联，需要你确认。"
    if context.source_excerpt:
        return "命中了材料正文里的相关片段。"
    return "命中了本地图谱里的相关材料。"


def _workspace_file_path(ws: Workspace, relative_path: str) -> Path:
    if not relative_path:
        raise HTTPException(400, "path is required")
    root = ws.path.resolve()
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise HTTPException(400, "Path must stay inside the workspace") from exc
    if not path.exists():
        raise HTTPException(404, "Local file not found")
    return path


def _open_path(path: Path) -> None:
    if sys.platform == "darwin":
        command = ["open", str(path)]
    elif sys.platform.startswith("win"):
        command = ["cmd", "/c", "start", "", str(path)]
    else:
        command = ["xdg-open", str(path)]
    subprocess.Popen(command)


def _ask_response_payload(
    ws: Workspace,
    result: AnswerResult,
    metadata_dict: dict,
    space_id: str,
    *,
    thought: dict | None = None,
) -> dict:
    thought_payload = thought or _public_thought_payload(result.question, result.retrieval)
    return {
        "question": result.question,
        "text": result.text,
        "provider": metadata_dict,
        "space_id": space_id,
        "contexts": _contexts_payload(ws, result.retrieval),
        "local_files": _local_files_payload(ws, result.retrieval),
        "graph_paths": result.retrieval.graph_paths,
        "diagnostics": asdict(result.retrieval.diagnostics),
        "thought": thought_payload,
        "focus_graph": focus_graph_from_retrieval(
            ws,
            result.retrieval,
            space_id=space_id,
        ),
        "recall_projection": build_recall_result_projection(
            result,
            provider_metadata=metadata_dict,
            space_id=space_id,
        ),
        "decision_layers": build_recall_decision_layers(
            result,
            provider_metadata=metadata_dict,
            space_id=space_id,
        ),
        "answer_quality": build_answer_quality_pack(
            result,
            provider_metadata=metadata_dict,
            space_id=space_id,
        ),
    }


def _replace_markdown_section(text: str, heading: str, body: str) -> str:
    start = text.find(heading)
    if start < 0:
        return "\n".join([text.rstrip(), "", heading, body.strip()]).rstrip()
    body_start = start + len(heading)
    next_match = text.find("\n## ", body_start)
    replacement = f"{heading}\n{body.strip()}\n"
    if next_match < 0:
        return f"{text[:start].rstrip()}\n{replacement}".rstrip()
    return f"{text[:start].rstrip()}\n{replacement}{text[next_match:].lstrip()}".rstrip()


def _parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) < 3:
        return {}
    fm: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


def _section_text(text: str, heading: str) -> str:
    if heading not in text:
        return ""
    tail = text.split(heading, 1)[1].lstrip()
    if "\n## " in tail:
        tail = tail.split("\n## ", 1)[0]
    return " ".join(tail.strip().split())


def _markdown_section(text: str, heading: str, stop_headings: list[str]) -> str:
    if heading not in text:
        return ""
    tail = text.split(heading, 1)[1].lstrip()
    stops = [tail.find(stop) for stop in stop_headings if stop in tail]
    if stops:
        tail = tail[: min(stops)]
    return tail.strip()


def _clean_markdown_text(text: str) -> str:
    return " ".join(
        line.strip()
        for line in text.replace("# Answer", "").splitlines()
        if line.strip()
    ).strip()


def _preserve_answer_markdown(text: str) -> str:
    return re.sub(
        r"\n{3,}",
        "\n\n",
        text.replace("\r\n", "\n").replace("# Answer", "# 回答").strip(),
    )


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


def _loads_json_object_list(value: str | None) -> list[dict]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [item for item in loaded if isinstance(item, dict)]


def _loads_json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _context_confidence_by_source(workspace: Workspace) -> dict[str, float]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            "SELECT source_id, confidence FROM cognitive_contexts"
        ).fetchall()
    return {row[0]: float(row[1]) for row in rows}


def _graph_payload(ws: Workspace, space_id: str | None = DEFAULT_GRAPH_SPACE_ID):
    graph = graph_for_space(ws, space_id)
    node_types: dict[str, int] = {}
    for node in graph.get("nodes", []):
        node_type = node.get("type", "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1
    return {
        "space_id": space_id or "all",
        "nodes": graph.get("nodes", []),
        "edges": graph.get("edges", []),
        "node_count": len(graph.get("nodes", [])),
        "edge_count": len(graph.get("edges", [])),
        "node_types": node_types,
        "top_hubs": _top_hubs(graph),
        "orphans": _orphans(graph),
        "insights": graph_insights(ws),
        "graph_evidence": build_graph_evidence_pack(graph, space_id=space_id),
    }


def _top_hubs(graph: dict) -> list[dict]:
    node_by_id = {node.get("id"): node for node in graph.get("nodes", [])}
    degrees = {node_id: 0 for node_id in node_by_id}
    for edge in graph.get("edges", []):
        if edge.get("source") in degrees:
            degrees[edge.get("source")] += 1
        if edge.get("target") in degrees:
            degrees[edge.get("target")] += 1
    return [
        {"label": node_by_id[node_id].get("label", node_id), "degree": degree}
        for node_id, degree in sorted(degrees.items(), key=lambda item: item[1], reverse=True)[:5]
    ]


def _orphans(graph: dict) -> list[str]:
    node_by_id = {node.get("id"): node for node in graph.get("nodes", [])}
    linked = set()
    for edge in graph.get("edges", []):
        linked.add(edge.get("source"))
        linked.add(edge.get("target"))
    return [
        node.get("label", node_id)
        for node_id, node in node_by_id.items()
        if node_id not in linked
    ]


# Mount static files AFTER all API routes
if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
