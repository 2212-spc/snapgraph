from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .config import render_default_config
from .models import DEFAULT_GRAPH_SPACE_ID, INBOX_GRAPH_SPACE_ID


WORKSPACE_DIR = ".my_snapgraph"


@dataclass(frozen=True)
class Workspace:
    root: Path

    @property
    def path(self) -> Path:
        return self.root / WORKSPACE_DIR

    @property
    def raw_dir(self) -> Path:
        return self.path / "raw"

    @property
    def wiki_dir(self) -> Path:
        return self.path / "wiki"

    @property
    def memory_dir(self) -> Path:
        return self.path / "memory"

    @property
    def schema_dir(self) -> Path:
        return self.path / "schema"

    @property
    def index_path(self) -> Path:
        return self.wiki_dir / "index.md"

    @property
    def log_path(self) -> Path:
        return self.wiki_dir / "log.md"

    @property
    def graph_path(self) -> Path:
        return self.memory_dir / "graph.json"

    @property
    def sqlite_path(self) -> Path:
        return self.memory_dir / "snapgraph.sqlite"

    @property
    def config_path(self) -> Path:
        return self.path / "config.yaml"

    @property
    def schema_agents_path(self) -> Path:
        return self.schema_dir / "AGENTS.md"

    def relative_to_workspace(self, path: Path) -> str:
        return path.relative_to(self.path).as_posix()


def get_workspace(root: Path | None = None) -> Workspace:
    return Workspace((root or Path.cwd()).resolve())


def create_workspace(workspace: Workspace) -> None:
    for directory in _required_directories(workspace):
        directory.mkdir(parents=True, exist_ok=True)

    if not workspace.index_path.exists():
        workspace.index_path.write_text(_initial_index(), encoding="utf-8")

    if not workspace.log_path.exists():
        workspace.log_path.write_text(_initial_log(), encoding="utf-8")

    if not workspace.graph_path.exists():
        workspace.graph_path.write_text(
            json.dumps({"nodes": [], "edges": []}, indent=2) + "\n",
            encoding="utf-8",
        )

    if not workspace.config_path.exists():
        workspace.config_path.write_text(render_default_config(), encoding="utf-8")

    if not workspace.schema_agents_path.exists():
        workspace.schema_agents_path.write_text(_schema_agents(), encoding="utf-8")

    initialize_database(workspace)


def initialize_database(workspace: Workspace) -> None:
    workspace.memory_dir.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS graph_spaces (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                purpose TEXT NOT NULL DEFAULT '',
                color TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                type TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                title TEXT NOT NULL,
                original_filename TEXT NOT NULL DEFAULT '',
                summary TEXT
            )
            """
        )
        _ensure_column(conn, "sources", "original_filename", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(
            conn,
            "sources",
            "graph_space_id",
            f"TEXT NOT NULL DEFAULT '{DEFAULT_GRAPH_SPACE_ID}'",
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cognitive_contexts (
                source_id TEXT PRIMARY KEY,
                why_saved TEXT NOT NULL,
                why_saved_status TEXT NOT NULL,
                related_project TEXT,
                open_loops_json TEXT NOT NULL,
                future_recall_questions_json TEXT NOT NULL,
                importance TEXT NOT NULL,
                confidence REAL NOT NULL,
                FOREIGN KEY(source_id) REFERENCES sources(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                label TEXT NOT NULL,
                properties_json TEXT NOT NULL
            )
            """
        )
        _ensure_column(
            conn,
            "nodes",
            "graph_space_id",
            f"TEXT NOT NULL DEFAULT '{DEFAULT_GRAPH_SPACE_ID}'",
        )
        _ensure_column(conn, "nodes", "status", "TEXT NOT NULL DEFAULT 'confirmed'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation TEXT NOT NULL,
                evidence_source_id TEXT,
                confidence REAL NOT NULL
            )
            """
        )
        _ensure_column(
            conn,
            "edges",
            "graph_space_id",
            f"TEXT NOT NULL DEFAULT '{DEFAULT_GRAPH_SPACE_ID}'",
        )
        _ensure_column(conn, "edges", "status", "TEXT NOT NULL DEFAULT 'confirmed'")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS materials (
                id TEXT PRIMARY KEY,
                source_id TEXT NOT NULL UNIQUE,
                graph_space_id TEXT NOT NULL,
                routing_status TEXT NOT NULL DEFAULT 'placed',
                routing_reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS suggestions (
                id TEXT PRIMARY KEY,
                graph_space_id TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                graph_space_id TEXT NOT NULL,
                source_id TEXT,
                node_id TEXT,
                edge_id TEXT,
                quote TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        _seed_graph_spaces(conn)
        _backfill_materials(conn)
    _migrate_graph_json_spaces(workspace)


def required_workspace_paths(workspace: Workspace) -> list[Path]:
    return [
        workspace.path,
        workspace.raw_dir,
        workspace.wiki_dir,
        workspace.memory_dir,
        workspace.schema_dir,
        workspace.index_path,
        workspace.log_path,
        workspace.graph_path,
        workspace.sqlite_path,
        workspace.config_path,
        workspace.schema_agents_path,
    ]


def _required_directories(workspace: Workspace) -> list[Path]:
    raw_children = ["screenshots", "docs", "pdfs", "webpages", "notes"]
    wiki_children = [
        "sources",
        "concepts",
        "people",
        "projects",
        "thoughts",
        "tasks",
        "questions",
    ]
    return (
        [
            workspace.path,
            workspace.raw_dir,
            workspace.wiki_dir,
            workspace.memory_dir,
            workspace.schema_dir,
        ]
        + [workspace.raw_dir / child for child in raw_children]
        + [workspace.wiki_dir / child for child in wiki_children]
    )


def _ensure_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    declaration: str,
) -> None:
    existing = {
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    }
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")


def _seed_graph_spaces(conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    seeds = [
        (
            INBOX_GRAPH_SPACE_ID,
            "Inbox",
            "Unrouted captures waiting for review.",
            "Hold new material before it becomes part of a confirmed graph space.",
            "#6b7280",
        ),
        (
            DEFAULT_GRAPH_SPACE_ID,
            "Default",
            "Migrated workspace graph and general memory.",
            "Keep existing SnapGraph sources compatible with the original single-graph workflow.",
            "#315ea8",
        ),
    ]
    for space_id, name, description, purpose, color in seeds:
        conn.execute(
            """
            INSERT OR IGNORE INTO graph_spaces (
                id, name, description, purpose, color, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (space_id, name, description, purpose, color, now, now),
        )


def _backfill_materials(conn: sqlite3.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    rows = conn.execute(
        "SELECT id, graph_space_id FROM sources ORDER BY imported_at ASC"
    ).fetchall()
    for source_id, graph_space_id in rows:
        conn.execute(
            """
            INSERT OR IGNORE INTO materials (
                id, source_id, graph_space_id, routing_status, routing_reason, created_at
            ) VALUES (?, ?, ?, 'placed', 'Migrated from existing workspace source.', ?)
            """,
            (f"mat_{source_id}", source_id, graph_space_id or DEFAULT_GRAPH_SPACE_ID, now),
        )


def _migrate_graph_json_spaces(workspace: Workspace) -> None:
    if not workspace.graph_path.exists():
        return
    try:
        graph = json.loads(workspace.graph_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return

    changed = False
    for node in graph.get("nodes", []):
        if "graph_space_id" not in node:
            node["graph_space_id"] = DEFAULT_GRAPH_SPACE_ID
            changed = True
        if "status" not in node:
            node["status"] = "confirmed"
            changed = True
    for edge in graph.get("edges", []):
        if "graph_space_id" not in edge:
            edge["graph_space_id"] = DEFAULT_GRAPH_SPACE_ID
            changed = True
        if "status" not in edge:
            edge["status"] = "confirmed"
            changed = True
    if changed:
        workspace.graph_path.write_text(
            json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def _initial_index() -> str:
    return """# SnapGraph Index

This file is the content map for the generated wiki. It should stay human-readable and machine-checkable.

## Sources
<!-- snapgraph:sources -->

## Questions
<!-- snapgraph:questions -->

## Reports
<!-- snapgraph:reports -->

## Concepts
<!-- snapgraph:concepts -->
"""


def _initial_log() -> str:
    return """# SnapGraph Log

Append-only operation timeline. Each event includes a fenced JSON record so lint can parse it.
"""


def _schema_agents() -> str:
    return """# SnapGraph Workspace Agent Schema

This workspace follows the LLM Wiki pattern:

- raw sources are immutable evidence
- wiki pages are generated and maintained views
- index.md is the content map
- log.md is an append-only operation timeline
- AI-inferred cognitive context must be labeled as AI-inferred
- user-guided hints are not the same as user-stated memory
- user-stated cognitive context must be preserved exactly once confirmed
"""
