from __future__ import annotations

import hashlib
import json
import re
import sqlite3

from .graph_store import load_graph
from .models import LintResult
from .wiki import question_pages, source_pages
from .workspace import Workspace, required_workspace_paths


REQUIRED_SECTIONS = [
    "## Objective Summary",
    "## Cognitive Context",
    "## Evidence",
]

REQUIRED_QUESTION_SECTIONS = [
    "## Question",
    "## Answer",
    "## Evidence Source Pages",
    "## 检索诊断",
]

REQUIRED_REPORT_SECTIONS = [
    "## 语料概览",
    "## 置信度与审计轨迹",
    "## 关键枢纽",
    "## Open Loops",
    "## 已保存问题",
    "## 值得复查的图谱路径",
    "## 建议的后续问题",
    "## 检查摘要",
]

VALID_CONTEXT_STATUSES = {"user-stated", "user-guided", "AI-inferred", "unknown"}


def lint_workspace(workspace: Workspace) -> LintResult:
    errors: list[str] = []
    warnings: list[str] = []

    for path in required_workspace_paths(workspace):
        if not path.exists():
            errors.append(f"Missing required path: {path}")

    if errors:
        return _result(errors, warnings)

    index_text = workspace.index_path.read_text(encoding="utf-8")
    _check_index_links(workspace, index_text, warnings)
    log_events = _parse_log_events(workspace, warnings)
    page_source_ids: set[str] = set()
    for page_path in source_pages(workspace):
        page_text = page_path.read_text(encoding="utf-8")
        source_id = _check_source_page(
            workspace,
            page_path,
            page_text,
            index_text,
            log_events,
            errors,
            warnings,
        )
        if source_id:
            page_source_ids.add(source_id)

    for page_path in question_pages(workspace):
        _check_question_page(
            workspace,
            page_path,
            page_path.read_text(encoding="utf-8"),
            index_text,
            log_events,
            warnings,
        )

    report_path = workspace.wiki_dir / "graph_report.md"
    if report_path.exists():
        _check_report_page(
            workspace,
            report_path,
            report_path.read_text(encoding="utf-8"),
            index_text,
            log_events,
            warnings,
        )

    _check_database_sources(workspace, page_source_ids, index_text, warnings)
    _check_duplicate_content_hashes(workspace, warnings)
    _check_graph(workspace, errors, warnings)

    return _result(errors, warnings)


def _check_source_page(
    workspace: Workspace,
    page_path,
    page_text: str,
    index_text: str,
    log_events: list[dict],
    errors: list[str],
    warnings: list[str],
) -> str | None:
    if not page_text.startswith("---\n"):
        warnings.append(f"{page_path.name} has no frontmatter")

    for section in REQUIRED_SECTIONS:
        if section not in page_text:
            warnings.append(f"{page_path.name} missing section: {section}")

    index_relative = page_path.relative_to(workspace.index_path.parent).as_posix()
    if index_relative not in index_text:
        warnings.append(f"{page_path.name} is not listed in index.md")

    raw_path_value = _frontmatter_value(page_text, "raw_path") or _frontmatter_value(
        page_text,
        "source_path",
    )
    content_hash = _frontmatter_value(page_text, "content_hash")
    if raw_path_value:
        raw_path = workspace.path / raw_path_value
        if not raw_path.exists():
            errors.append(f"{page_path.name} points to missing raw source: {raw_path}")
        elif content_hash:
            actual_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            if actual_hash != content_hash:
                errors.append(f"{page_path.name} content_hash does not match raw source")
    else:
        warnings.append(f"{page_path.name} has no raw_path frontmatter")

    source_id = _frontmatter_value(page_text, "id")
    if not source_id:
        warnings.append(f"{page_path.name} has no id frontmatter")
        return None

    if not _source_exists_in_db(workspace, source_id):
        warnings.append(f"{page_path.name} is missing from SQLite sources table")

    if not _cognitive_context_exists_in_db(workspace, source_id):
        warnings.append(f"{page_path.name} is missing from SQLite cognitive_contexts table")
    else:
        _check_cognitive_context_against_page(workspace, source_id, page_text, warnings)

    status = _context_status(page_text)
    if status is None:
        warnings.append(f"{page_path.name} has no Cognitive Context status")
    elif status not in VALID_CONTEXT_STATUSES:
        warnings.append(f"{page_path.name} has invalid Cognitive Context status: {status}")

    if status == "AI-inferred" and "AI-inferred" not in page_text:
        warnings.append(f"{page_path.name} AI-inferred context is not visibly labeled")

    if "## Supportive Signals" not in page_text:
        warnings.append(f"{page_path.name} has no future recall questions")

    relative_page = workspace.relative_to_workspace(page_path)
    if not _has_ingest_log_event(log_events, source_id, relative_page):
        warnings.append(f"{page_path.name} has no parseable ingest event in log.md")

    return source_id


def _check_question_page(
    workspace: Workspace,
    page_path,
    page_text: str,
    index_text: str,
    log_events: list[dict],
    warnings: list[str],
) -> None:
    if not page_text.startswith("---\n"):
        warnings.append(f"{page_path.name} has no frontmatter")

    for section in REQUIRED_QUESTION_SECTIONS:
        if section not in page_text:
            warnings.append(f"{page_path.name} missing section: {section}")

    relative_page = workspace.relative_to_workspace(page_path)
    index_relative = page_path.relative_to(workspace.index_path.parent).as_posix()
    if index_relative not in index_text:
        warnings.append(f"{page_path.name} is not listed in index.md")

    question_id = _frontmatter_value(page_text, "id")
    if not question_id:
        warnings.append(f"{page_path.name} has no id frontmatter")

    evidence_source_ids = _frontmatter_value(page_text, "evidence_source_ids")
    if not evidence_source_ids:
        warnings.append(f"{page_path.name} has no evidence_source_ids frontmatter")
    elif evidence_source_ids == "[]":
        warnings.append(f"{page_path.name} has no evidence sources")

    if not _has_ask_save_log_event(log_events, relative_page):
        warnings.append(f"{page_path.name} has no parseable ask_save event in log.md")

    for target in _page_links(page_text):
        if target.startswith(("http://", "https://", "#")):
            continue
        if not _markdown_link_exists(page_path, target):
            warnings.append(f"{page_path.name} has dead evidence link: {target}")


def _check_report_page(
    workspace: Workspace,
    page_path,
    page_text: str,
    index_text: str,
    log_events: list[dict],
    warnings: list[str],
) -> None:
    for section in REQUIRED_REPORT_SECTIONS:
        if section not in page_text:
            warnings.append(f"{page_path.name} missing section: {section}")

    index_relative = page_path.relative_to(workspace.index_path.parent).as_posix()
    if index_relative not in index_text:
        warnings.append(f"{page_path.name} is not listed in index.md")

    relative_page = workspace.relative_to_workspace(page_path)
    if not _has_report_log_event(log_events, relative_page):
        warnings.append(f"{page_path.name} has no parseable report event in log.md")

    for target in _page_links(page_text):
        if target.startswith(("http://", "https://", "#")):
            continue
        if not _markdown_link_exists(page_path, target):
            warnings.append(f"{page_path.name} has dead link: {target}")


def _source_exists_in_db(workspace: Workspace, source_id: str) -> bool:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM sources WHERE id = ? LIMIT 1",
            (source_id,),
        ).fetchone()
    return row is not None


def _cognitive_context_exists_in_db(workspace: Workspace, source_id: str) -> bool:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM cognitive_contexts WHERE source_id = ? LIMIT 1",
            (source_id,),
        ).fetchone()
    return row is not None


def _check_database_sources(
    workspace: Workspace,
    page_source_ids: set[str],
    index_text: str,
    warnings: list[str],
) -> None:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute("SELECT id FROM sources").fetchall()

    for (source_id,) in rows:
        page_path = workspace.wiki_dir / "sources" / f"{source_id}.md"
        index_relative = page_path.relative_to(workspace.index_path.parent).as_posix()
        if source_id not in page_source_ids:
            warnings.append(f"SQLite source {source_id} has no source page")
        elif index_relative not in index_text:
            warnings.append(f"SQLite source {source_id} is not linked from index.md")


def _check_index_links(
    workspace: Workspace,
    index_text: str,
    warnings: list[str],
) -> None:
    for match in re.finditer(r"\]\((?P<target>[^)]+)\)", index_text):
        target = match.group("target")
        if target.startswith(("http://", "https://", "#")):
            continue
        if not _markdown_link_exists(workspace.index_path, target):
            warnings.append(f"index.md has dead link: {target}")


def _check_duplicate_content_hashes(workspace: Workspace, warnings: list[str]) -> None:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT content_hash, GROUP_CONCAT(id)
            FROM sources
            GROUP BY content_hash
            HAVING COUNT(*) > 1
            """
        ).fetchall()
    for content_hash, source_ids in rows:
        warnings.append(f"duplicate content hash {content_hash}: {source_ids}")


def _check_cognitive_context_against_page(
    workspace: Workspace,
    source_id: str,
    page_text: str,
    warnings: list[str],
) -> None:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT why_saved, why_saved_status
            FROM cognitive_contexts
            WHERE source_id = ?
            """,
            (source_id,),
        ).fetchone()
    if row is None:
        return
    why_saved, why_saved_status = row
    if why_saved_status in {"user-stated", "user-guided"} and why_saved not in page_text:
        warnings.append(f"{source_id} user-stated why_saved is not preserved in source page")


def _check_graph(
    workspace: Workspace,
    errors: list[str],
    warnings: list[str],
) -> None:
    try:
        graph = load_graph(workspace)
    except json.JSONDecodeError:
        errors.append("graph.json is not valid JSON")
        return

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    node_ids = {node.get("id") for node in nodes}
    edge_ids = {edge.get("id") for edge in edges}
    seen_labels: set[tuple[str, str]] = set()
    duplicate_labels: set[tuple[str, str]] = set()

    for node in nodes:
        key = (node.get("type", ""), node.get("label", ""))
        if key in seen_labels:
            duplicate_labels.add(key)
        seen_labels.add(key)

    for node_type, label in sorted(duplicate_labels):
        warnings.append(f"duplicate graph node label: {node_type}:{label}")

    connected_node_ids: set[str] = set()
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids or target not in node_ids:
            warnings.append(f"broken graph edge: {edge.get('id')}")
            continue
        connected_node_ids.add(source)
        connected_node_ids.add(target)

    for node in nodes:
        node_id = node.get("id")
        if node_id not in connected_node_ids:
            warnings.append(f"orphan graph node: {node.get('label')}")

    with sqlite3.connect(workspace.sqlite_path) as conn:
        source_rows = conn.execute("SELECT id FROM sources").fetchall()
        sqlite_nodes = {
            row[0]: {
                "id": row[0],
                "type": row[1],
                "label": row[2],
                "properties": json.loads(row[3]),
            }
            for row in conn.execute(
                "SELECT id, type, label, properties_json FROM nodes"
            ).fetchall()
        }
        sqlite_edges = {
            row[0]: {
                "id": row[0],
                "source": row[1],
                "target": row[2],
                "relation": row[3],
                "evidence_source_id": row[4],
                "confidence": row[5],
            }
            for row in conn.execute(
                """
                SELECT id, source, target, relation, evidence_source_id, confidence
                FROM edges
                """
            ).fetchall()
        }

    if source_rows and not nodes and not edges:
        warnings.append("graph.json is empty but sources exist")

    for (source_id,) in source_rows:
        source_node_id = f"source_{source_id}"
        if source_node_id not in node_ids:
            warnings.append(f"source {source_id} has no source node in graph.json")
        if not any(
            edge.get("source") == source_node_id or edge.get("target") == source_node_id
            for edge in edges
        ):
            warnings.append(f"source {source_id} has no graph edges")

    if node_ids != set(sqlite_nodes):
        warnings.append("graph.json nodes do not match SQLite nodes table")
    if edge_ids != set(sqlite_edges):
        warnings.append("graph.json edges do not match SQLite edges table")

    for node in nodes:
        node_id = node.get("id")
        sqlite_node = sqlite_nodes.get(node_id)
        if sqlite_node and _normalized_node(node) != sqlite_node:
            warnings.append(f"graph node differs from SQLite: {node_id}")

    for edge in edges:
        edge_id = edge.get("id")
        sqlite_edge = sqlite_edges.get(edge_id)
        if sqlite_edge and _normalized_edge(edge) != sqlite_edge:
            warnings.append(f"graph edge differs from SQLite: {edge_id}")


def _normalized_node(node: dict) -> dict:
    return {
        "id": node.get("id"),
        "type": node.get("type"),
        "label": node.get("label"),
        "properties": node.get("properties", {}),
    }


def _normalized_edge(edge: dict) -> dict:
    return {
        "id": edge.get("id"),
        "source": edge.get("source"),
        "target": edge.get("target"),
        "relation": edge.get("relation"),
        "evidence_source_id": edge.get("evidence_source_id"),
        "confidence": edge.get("confidence"),
    }


def _parse_log_events(workspace: Workspace, warnings: list[str]) -> list[dict]:
    text = workspace.log_path.read_text(encoding="utf-8")
    events = []
    for match in re.finditer(r"```json\n(?P<json>.*?)\n```", text, re.DOTALL):
        try:
            event = json.loads(match.group("json"))
        except json.JSONDecodeError:
            warnings.append("log.md contains an invalid JSON event")
            continue
        if not isinstance(event, dict):
            warnings.append("log.md contains a non-object JSON event")
            continue
        for key in ("timestamp", "operation", "source_id", "touched_pages"):
            if key not in event:
                warnings.append(f"log.md event missing key: {key}")
        events.append(event)
    return events


def _has_ingest_log_event(
    log_events: list[dict],
    source_id: str,
    relative_page: str,
) -> bool:
    for event in log_events:
        touched_pages = event.get("touched_pages", [])
        if (
            event.get("operation") == "ingest"
            and event.get("source_id") == source_id
            and isinstance(touched_pages, list)
            and relative_page in touched_pages
        ):
            return True
    return False


def _has_ask_save_log_event(log_events: list[dict], relative_page: str) -> bool:
    for event in log_events:
        touched_pages = event.get("touched_pages", [])
        if (
            event.get("operation") == "ask_save"
            and isinstance(touched_pages, list)
            and relative_page in touched_pages
        ):
            return True
    return False


def _has_report_log_event(log_events: list[dict], relative_page: str) -> bool:
    for event in log_events:
        touched_pages = event.get("touched_pages", [])
        if (
            event.get("operation") == "report"
            and isinstance(touched_pages, list)
            and relative_page in touched_pages
        ):
            return True
    return False


def _page_links(page_text: str) -> list[str]:
    return [match.group("target") for match in re.finditer(r"\]\((?P<target>[^)]+)\)", page_text)]


def _markdown_link_exists(page_path, target: str) -> bool:
    return (page_path.parent / target).resolve().exists()


def _context_status(page_text: str) -> str | None:
    match = re.search(r"^- Status: (?P<status>.+)$", page_text, re.MULTILINE)
    return match.group("status").strip() if match else None


def _frontmatter_value(page_text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}: (?P<value>.+)$", page_text, re.MULTILINE)
    return match.group("value").strip() if match else None


def _result(errors: list[str], warnings: list[str]) -> LintResult:
    status = "ERROR" if errors else "WARN" if warnings else "OK"
    return LintResult(status=status, errors=errors, warnings=warnings)
