import json
import sqlite3
from pathlib import Path

from snapgraph.config import load_config, validate_api_key_env_name
from snapgraph.ingest import ingest_source
from snapgraph.retrieval import _query_terms, retrieve_for_question
from snapgraph.workspace import Workspace, create_workspace


class FakeLLMProvider:
    def summarize(self, text: str) -> str:
        return "fake summary"

    def key_details(self, text: str) -> list[str]:
        return ["fake detail"]

    def infer_why_saved(self, title: str, text: str) -> str:
        return "fake inferred why"

    def open_loops(self, text: str) -> list[str]:
        return ["fake open loop"]

    def future_recall_questions(self, title: str, text: str) -> list[str]:
        return ["fake recall question"]

    def related_project(self, text: str) -> str | None:
        return "Fake Project"


def test_fake_llm_provider_can_drive_ingest(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text("# Note\n\nbody", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = ingest_source(workspace, source_path, llm=FakeLLMProvider())

    assert result.source.summary == "fake summary"
    assert result.cognitive_context.why_saved == "fake inferred why"
    assert result.cognitive_context.related_project == "Fake Project"


def test_config_aliases_affect_query(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    workspace.config_path.write_text(
        json.dumps(
            {
                "workspace_version": 1,
                "retrieval": {
                    "aliases": {"自定义": ["customterm"]},
                    "title_weight": 3,
                    "keyword_weight": 1,
                    "graph_node_weight": 2,
                    "graph_edge_weight": 1,
                    "max_expanded_nodes": 40,
                    "max_source_pages": 8,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    source_path = tmp_path / "note.md"
    source_path.write_text("# Note\n\ncustomterm evidence", encoding="utf-8")
    ingest_source(workspace, source_path)

    retrieval = retrieve_for_question(workspace, "自定义")

    assert retrieval.contexts
    assert retrieval.contexts[0].title == "Note"


def test_legacy_config_falls_back_to_defaults(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    workspace.config_path.write_text("workspace_version: 1\n", encoding="utf-8")

    config = load_config(workspace)

    assert config.workspace_version == 1
    assert "截图" in config.retrieval.aliases


def test_query_terms_include_single_letter_and_digit() -> None:
    terms = _query_terms("A 1", {})

    assert "a" in terms
    assert "1" in terms


def test_sqlite_uses_wal_mode(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)

    with sqlite3.connect(workspace.sqlite_path) as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert journal_mode == "wal"


def test_api_key_env_validation_rejects_secret_values() -> None:
    assert validate_api_key_env_name("SNAPGRAPH_LLM_API_KEY") == "SNAPGRAPH_LLM_API_KEY"

    try:
        validate_api_key_env_name("sk-should-not-be-stored")
    except ValueError as exc:
        assert "not an API key" in str(exc)
    else:
        raise AssertionError("Expected API key shaped value to be rejected")
