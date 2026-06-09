from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from .models import AnswerResult, DEFAULT_GRAPH_SPACE_ID
from .workspace import Workspace


@dataclass(frozen=True)
class Topic:
    id: str
    title: str
    summary: str
    space_id: str
    pinned_source_ids: list[str]
    open_loops: list[str]
    confirmed_judgments: list[str]
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class TopicTurn:
    id: str
    topic_id: str
    question: str
    answer: str
    evidence_source_ids: list[str]
    graph_paths: list[str]
    created_at: str


def create_topic(
    workspace: Workspace,
    title: str | None = None,
    initial_question: str | None = None,
    space_id: str | None = None,
) -> dict:
    now = _now()
    seed = (title or initial_question or "New topic").strip()
    topic_id = _topic_id(now, seed)
    topic_title = (title or _short_title(initial_question or "New topic")).strip()
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO topics (
                id, title, summary, space_id, pinned_source_ids_json,
                open_loops_json, confirmed_judgments_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, '[]', '[]', '[]', ?, ?)
            """,
            (
                topic_id,
                topic_title,
                _initial_summary(initial_question),
                space_id or "all",
                now,
                now,
            ),
        )
    return get_topic_payload(workspace, topic_id)


def list_topics(workspace: Workspace) -> list[dict]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT
                t.id, t.title, t.summary, t.space_id, t.pinned_source_ids_json,
                t.open_loops_json, t.confirmed_judgments_json, t.created_at, t.updated_at,
                COUNT(tt.id) AS turn_count
            FROM topics t
            LEFT JOIN topic_turns tt ON tt.topic_id = t.id
            GROUP BY t.id
            ORDER BY t.updated_at DESC
            """
        ).fetchall()
    return [
        {
            **_topic_from_row(row[:9]).__dict__,
            "turn_count": int(row[9] or 0),
        }
        for row in rows
    ]


def get_topic_payload(workspace: Workspace, topic_id: str) -> dict:
    topic = get_topic(workspace, topic_id)
    turns = list_topic_turns(workspace, topic_id)
    return {
        "topic": topic.__dict__,
        "turns": [turn.__dict__ for turn in turns],
        "state": topic_state(workspace, topic, turns),
    }


def get_topic(workspace: Workspace, topic_id: str) -> Topic:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT id, title, summary, space_id, pinned_source_ids_json,
                   open_loops_json, confirmed_judgments_json, created_at, updated_at
            FROM topics
            WHERE id = ?
            """,
            (topic_id,),
        ).fetchone()
    if row is None:
        raise KeyError(topic_id)
    return _topic_from_row(row)


def list_topic_turns(workspace: Workspace, topic_id: str) -> list[TopicTurn]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            """
            SELECT id, topic_id, question, answer, evidence_source_ids_json,
                   graph_paths_json, created_at
            FROM topic_turns
            WHERE topic_id = ?
            ORDER BY created_at ASC
            """,
            (topic_id,),
        ).fetchall()
    return [_turn_from_row(row) for row in rows]


def update_topic(workspace: Workspace, topic_id: str, payload: dict) -> dict:
    topic = get_topic(workspace, topic_id)
    title = str(payload.get("title", topic.title)).strip() or topic.title
    pinned = payload.get("pinned_source_ids", topic.pinned_source_ids)
    open_loops = payload.get("open_loops", topic.open_loops)
    judgments = payload.get("confirmed_judgments", topic.confirmed_judgments)
    now = _now()
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            UPDATE topics
            SET title = ?, pinned_source_ids_json = ?, open_loops_json = ?,
                confirmed_judgments_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                title,
                _json_list(pinned),
                _json_list(open_loops),
                _json_list(judgments),
                now,
                topic_id,
            ),
        )
    write_topic_page(workspace, topic_id)
    return get_topic_payload(workspace, topic_id)


def add_topic_turn(workspace: Workspace, topic_id: str, result: AnswerResult) -> dict:
    topic = get_topic(workspace, topic_id)
    turns = list_topic_turns(workspace, topic_id)
    now = _now()
    turn_id = _turn_id(now, result.question)
    evidence_source_ids = [context.source_id for context in result.retrieval.contexts]
    graph_paths = result.retrieval.graph_paths
    summary = _updated_summary(topic, turns, result)
    open_loops = _merge_unique(
        topic.open_loops,
        [
            item
            for context in result.retrieval.contexts
            for item in context.open_loops
            if item and item != "None"
        ],
    )
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            """
            INSERT INTO topic_turns (
                id, topic_id, question, answer, evidence_source_ids_json,
                graph_paths_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                turn_id,
                topic_id,
                result.question,
                result.text,
                _json_list(evidence_source_ids),
                _json_list(graph_paths),
                now,
            ),
        )
        conn.execute(
            """
            UPDATE topics
            SET summary = ?, open_loops_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (summary, _json_list(open_loops), now, topic_id),
        )
    write_topic_page(workspace, topic_id)
    return get_topic_payload(workspace, topic_id)


def topic_context_query(topic: Topic, question: str) -> str:
    parts = [question.strip()]
    if topic.summary.strip():
        parts.append(f"Topic summary: {topic.summary.strip()}")
    if topic.open_loops:
        parts.append("Open loops: " + "; ".join(topic.open_loops[:5]))
    if topic.confirmed_judgments:
        parts.append("User-confirmed judgments: " + "; ".join(topic.confirmed_judgments[:5]))
    return "\n".join(part for part in parts if part)


def topic_state(workspace: Workspace, topic: Topic, turns: list[TopicTurn] | None = None) -> dict:
    turns = turns if turns is not None else list_topic_turns(workspace, topic.id)
    evidence_source_ids = _merge_unique(
        topic.pinned_source_ids,
        [source_id for turn in turns for source_id in turn.evidence_source_ids],
    )
    evidence = _source_cards(workspace, evidence_source_ids)
    return {
        "topic_id": topic.id,
        "title": topic.title,
        "summary": topic.summary,
        "space_id": topic.space_id,
        "pinned_source_ids": topic.pinned_source_ids,
        "evidence_source_ids": evidence_source_ids,
        "open_loops": topic.open_loops,
        "confirmed_judgments": topic.confirmed_judgments,
        "evidence": evidence,
        "user_stated_count": sum(1 for item in evidence if item.get("why_saved_status") == "user-stated"),
        "ai_inferred_count": sum(1 for item in evidence if item.get("why_saved_status") != "user-stated"),
        "turn_count": len(turns),
    }


def write_topic_page(workspace: Workspace, topic_id: str) -> str:
    topic = get_topic(workspace, topic_id)
    turns = list_topic_turns(workspace, topic_id)
    state = topic_state(workspace, topic, turns)
    page_path = workspace.wiki_dir / "topics" / f"{topic.id}.md"
    evidence_lines = []
    for source in state["evidence"]:
        source_path = workspace.wiki_dir / "sources" / f"{source['source_id']}.md"
        target = _rel_link(page_path, source_path)
        evidence_lines.append(
            f"- [{source['title']}]({target}) - `{source['source_id']}` ({source['why_saved_status']})"
        )
    if not evidence_lines:
        evidence_lines = ["- None"]
    turn_lines = []
    for index, turn in enumerate(turns, start=1):
        turn_lines.extend(
            [
                f"### Turn {index}: {turn.question}",
                "",
                turn.answer,
                "",
                "Evidence source ids: "
                + json.dumps(turn.evidence_source_ids, ensure_ascii=False),
                "",
            ]
        )
    if not turn_lines:
        turn_lines = ["No turns yet.", ""]
    page_path.write_text(
        "\n".join(
            [
                "---",
                f"id: {topic.id}",
                "type: topic",
                f"title: {topic.title}",
                f"space_id: {topic.space_id}",
                f"created_at: {topic.created_at}",
                f"updated_at: {topic.updated_at}",
                "---",
                f"# Topic: {topic.title}",
                "",
                "## Topic State",
                topic.summary or "No summary yet.",
                "",
                "## Confirmed Judgments",
                _render_list(topic.confirmed_judgments),
                "",
                "## Open Loops",
                _render_list(topic.open_loops),
                "",
                "## Evidence Sources",
                "\n".join(evidence_lines),
                "",
                "## Turns",
                "\n".join(turn_lines).rstrip(),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return workspace.relative_to_workspace(page_path)


def _topic_from_row(row) -> Topic:
    return Topic(
        id=row[0],
        title=row[1] or "",
        summary=row[2] or "",
        space_id=row[3] or "all",
        pinned_source_ids=_loads_list(row[4]),
        open_loops=_loads_list(row[5]),
        confirmed_judgments=_loads_list(row[6]),
        created_at=row[7],
        updated_at=row[8],
    )


def _turn_from_row(row) -> TopicTurn:
    return TopicTurn(
        id=row[0],
        topic_id=row[1],
        question=row[2],
        answer=row[3],
        evidence_source_ids=_loads_list(row[4]),
        graph_paths=_loads_list(row[5]),
        created_at=row[6],
    )


def _source_cards(workspace: Workspace, source_ids: list[str]) -> list[dict]:
    if not source_ids:
        return []
    placeholders = ",".join("?" for _ in source_ids)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            f"""
            SELECT s.id, s.title, s.summary, c.why_saved, c.why_saved_status,
                   c.related_project, c.open_loops_json, c.confidence
            FROM sources s
            LEFT JOIN cognitive_contexts c ON c.source_id = s.id
            WHERE s.id IN ({placeholders})
            """,
            source_ids,
        ).fetchall()
    by_id = {
        row[0]: {
            "source_id": row[0],
            "title": row[1] or row[0],
            "summary": row[2] or "",
            "why_saved": row[3] or "",
            "why_saved_status": row[4] or "unknown",
            "related_project": row[5] or "",
            "open_loops": _loads_list(row[6]),
            "confidence": float(row[7]) if row[7] is not None else 0.0,
        }
        for row in rows
    }
    return [by_id[source_id] for source_id in source_ids if source_id in by_id]


def _updated_summary(topic: Topic, turns: list[TopicTurn], result: AnswerResult) -> str:
    first_question = turns[0].question if turns else result.question
    latest = result.question
    evidence_titles = [context.title for context in result.retrieval.contexts[:3]]
    pieces = [f"主题围绕：{_compact(first_question, 80)}"]
    if latest != first_question:
        pieces.append(f"最近追问：{_compact(latest, 80)}")
    if evidence_titles:
        pieces.append("当前证据集中在：" + " / ".join(_compact(title, 36) for title in evidence_titles))
    if topic.confirmed_judgments:
        pieces.append("用户确认判断：" + "；".join(topic.confirmed_judgments[:2]))
    return "。".join(pieces)[:600]


def _initial_summary(initial_question: str | None) -> str:
    if not initial_question:
        return ""
    return f"主题从这个问题开始：{_compact(initial_question, 120)}"


def _topic_id(created_at: str, seed: str) -> str:
    import hashlib

    digest = hashlib.sha1(f"{created_at}|{seed}".encode("utf-8")).hexdigest()
    return f"topic_{digest[:12]}"


def _turn_id(created_at: str, question: str) -> str:
    import hashlib

    digest = hashlib.sha1(f"{created_at}|{question}".encode("utf-8")).hexdigest()
    return f"turn_{digest[:12]}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_title(text: str) -> str:
    cleaned = " ".join((text or "").split())
    return _compact(cleaned, 42) or "New topic"


def _compact(text: str, limit: int) -> str:
    cleaned = " ".join((text or "").split())
    return cleaned if len(cleaned) <= limit else cleaned[: limit - 1] + "…"


def _json_list(value) -> str:
    if not isinstance(value, list):
        value = []
    return json.dumps([str(item) for item in value if str(item).strip()], ensure_ascii=False)


def _loads_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        loaded = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return [str(item) for item in loaded]


def _merge_unique(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for group in groups:
        for item in group:
            cleaned = str(item).strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
    return result


def _render_list(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {item}" for item in items)


def _rel_link(from_page, target_page) -> str:
    import os

    return os.path.relpath(target_page, start=from_page.parent).replace(os.sep, "/")
