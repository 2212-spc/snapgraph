from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import asdict
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles

from .answer import answer_question, save_answer
from .config import (
    load_config,
    save_config,
    validate_api_key_env_name,
    LLMConfig,
    SnapGraphConfig,
)
from .demo_data import load_demo_dataset, DEMO_QUESTIONS
from .focus import focus_graph_for_payload, focus_graph_from_retrieval
from .graph_store import graph_diagnostics, graph_for_space, graph_insights, load_graph
from .ingest import ingest_source, update_cognitive_context
from .linting import lint_workspace
from .llm import MockLLM
from .llm_providers import provider_metadata, resolve_llm_with_metadata
from .models import DEFAULT_GRAPH_SPACE_ID, INBOX_GRAPH_SPACE_ID
from .report import write_graph_report
from .retrieval import retrieve_for_question
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
from .wiki import question_pages, source_pages
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
    return {
        "sources": source_count,
        "saved_questions": len(question_pages(ws)),
        "nodes": diag.node_count,
        "edges": diag.edge_count,
        "lint_status": lint.status,
        "lint_errors": lint.errors,
        "lint_warnings": lint.warnings,
        "context_status": {row[0]: row[1] for row in status_rows},
        "node_types": diag.node_types,
        "top_hubs": [{"label": label, "degree": d} for label, d in diag.top_hubs],
        "orphans": diag.orphans,
        "insights": graph_insights(ws),
        "workspace_path": str(ws.path),
        "provider": provider_metadata(ws).as_dict(),
        "spaces": list_graph_spaces(ws),
    }


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
            "routing_status": row[14] or "",
            "routing_reason": row[15] or "",
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
        "provider": metadata.as_dict(),
        "focus_graph": focus_graph_for_payload(
            ws,
            {"source_id": result.source.id, "space_id": source_detail.get("graph_space_id", result.source.graph_space_id)},
        ),
        "routing_suggestion": routing_suggestion,
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


# ── Focus graph ──

@app.post("/api/focus")
def api_focus(payload: dict):
    return focus_graph_for_payload(_workspace(), payload)


# ── Ask ──

@app.post("/api/ask")
def api_ask(payload: dict):
    question = payload.get("question", "").strip()
    save = payload.get("save", False)
    if not question:
        raise HTTPException(400, "Question is required")
    space_id = str(payload.get("space_id") or "all")
    ws = _workspace()
    retrieval = retrieve_for_question(ws, question, space_id=space_id)
    if retrieval.contexts:
        llm, metadata = _resolve_llm_or_503(ws)
        metadata_dict = metadata.as_dict()
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
        _raise_provider_runtime_error(ws, metadata_dict, exc)
    confidence_by_source = _context_confidence_by_source(ws)
    response = {
        "question": result.question,
        "text": result.text,
        "provider": metadata_dict,
        "space_id": space_id,
        "contexts": [
            {
                "source_id": c.source_id,
                "title": c.title,
                "why_saved": c.why_saved,
                "why_saved_status": c.why_saved_status,
                "related_project": c.related_project,
                "open_loops": c.open_loops,
                "future_recall_questions": c.future_recall_questions,
                "confidence": confidence_by_source.get(c.source_id, 0.0),
                "graph_space_id": c.graph_space_id,
                "space_name": c.space_name,
                "source_excerpt": c.source_excerpt,
            }
            for c in result.retrieval.contexts
        ],
        "graph_paths": result.retrieval.graph_paths,
        "diagnostics": asdict(result.retrieval.diagnostics),
        "focus_graph": focus_graph_from_retrieval(
            ws,
            result.retrieval,
            space_id=space_id,
        ),
    }
    if save:
        page = save_answer(ws, result)
        response["saved_page"] = page.relative_page_path
    return response


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
    return {
        "id": fm.get("id", question_id),
        "question": _section_text(text, "## Question"),
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
