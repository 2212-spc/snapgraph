from pathlib import Path

from snapgraph.answer import answer_question, save_answer
from snapgraph.ingest import ingest_source
from snapgraph.linting import lint_workspace
from snapgraph.report import write_graph_report
from snapgraph.workspace import Workspace, create_workspace


def test_lint_clean_workspace_is_ok(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)

    result = lint_workspace(workspace)

    assert result.status == "OK"
    assert result.errors == []
    assert result.warnings == []


def test_lint_reports_missing_raw_source(tmp_path: Path) -> None:
    source_path = tmp_path / "note.txt"
    source_path.write_text("A small note.", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest = ingest_source(workspace, source_path)
    ingest.raw_path.unlink()

    result = lint_workspace(workspace)

    assert result.status == "ERROR"
    assert any("missing raw source" in error for error in result.errors)


def test_lint_reports_source_page_missing_from_index(tmp_path: Path) -> None:
    source_path = tmp_path / "note.txt"
    source_path.write_text("A small note.", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest = ingest_source(workspace, source_path)
    workspace.index_path.write_text("# SnapGraph Index\n", encoding="utf-8")

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any(ingest.page.absolute_page_path.name in warning for warning in result.warnings)
    assert any("not listed in index.md" in warning for warning in result.warnings)


def test_lint_reports_missing_cognitive_context_row(tmp_path: Path) -> None:
    import sqlite3

    source_path = tmp_path / "note.txt"
    source_path.write_text("A small note.", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest = ingest_source(workspace, source_path)
    with sqlite3.connect(workspace.sqlite_path) as conn:
        conn.execute(
            "DELETE FROM cognitive_contexts WHERE source_id = ?",
            (ingest.source.id,),
        )

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any("cognitive_contexts" in warning for warning in result.warnings)


def test_lint_reports_graph_json_sqlite_node_value_mismatch(tmp_path: Path) -> None:
    import json

    source_path = tmp_path / "note.txt"
    source_path.write_text("SnapGraph note.", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest_source(workspace, source_path)

    graph = json.loads(workspace.graph_path.read_text(encoding="utf-8"))
    graph["nodes"][0]["label"] = "CORRUPTED LABEL"
    workspace.graph_path.write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any("graph node differs from SQLite" in warning for warning in result.warnings)


def test_lint_reports_duplicate_content_hash(tmp_path: Path) -> None:
    source_path = tmp_path / "note.txt"
    source_path.write_text("same", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest_source(workspace, source_path)
    ingest_source(workspace, source_path)

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any("duplicate content hash" in warning for warning in result.warnings)


def test_lint_reports_dead_index_link(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    workspace.index_path.write_text(
        "# SnapGraph Index\n\n- [Missing](sources/missing.md)\n",
        encoding="utf-8",
    )

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any("dead link" in warning for warning in result.warnings)


def test_lint_reports_invalid_graph_json(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    workspace.graph_path.write_text("", encoding="utf-8")

    result = lint_workspace(workspace)

    assert result.status == "ERROR"
    assert any("not valid JSON" in error for error in result.errors)


def test_lint_reports_question_page_missing_from_index(tmp_path: Path) -> None:
    source_path = tmp_path / "note.txt"
    source_path.write_text("LLM Wiki note.", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest_source(workspace, source_path)
    page = save_answer(workspace, answer_question(workspace, "LLM Wiki"))
    workspace.index_path.write_text("# SnapGraph Index\n", encoding="utf-8")

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any(page.absolute_page_path.name in warning for warning in result.warnings)
    assert any("not listed in index.md" in warning for warning in result.warnings)


def test_lint_reports_question_page_missing_diagnostics(tmp_path: Path) -> None:
    source_path = tmp_path / "note.txt"
    source_path.write_text("LLM Wiki note.", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest_source(workspace, source_path)
    page = save_answer(workspace, answer_question(workspace, "LLM Wiki"))
    page_text = page.absolute_page_path.read_text(encoding="utf-8")
    page.absolute_page_path.write_text(
        page_text.replace("## 检索诊断", "## Missing Diagnostics"),
        encoding="utf-8",
    )

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any("missing section: ## 检索诊断" in warning for warning in result.warnings)


def test_lint_reports_question_page_dead_evidence_link(tmp_path: Path) -> None:
    source_path = tmp_path / "note.txt"
    source_path.write_text("LLM Wiki note.", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest_source(workspace, source_path)
    page = save_answer(workspace, answer_question(workspace, "LLM Wiki"))
    page_text = page.absolute_page_path.read_text(encoding="utf-8")
    page.absolute_page_path.write_text(
        page_text.replace("../sources/", "../sources/missing/"),
        encoding="utf-8",
    )

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any("dead evidence link" in warning for warning in result.warnings)


def test_lint_reports_question_page_without_evidence_sources(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    page = save_answer(workspace, answer_question(workspace, "unmatched question"))

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any(page.absolute_page_path.name in warning for warning in result.warnings)
    assert any("has no evidence sources" in warning for warning in result.warnings)


def test_lint_reports_graph_report_missing_from_index(tmp_path: Path) -> None:
    source_path = tmp_path / "note.txt"
    source_path.write_text("LLM Wiki note.", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    ingest_source(workspace, source_path)
    write_graph_report(workspace)
    workspace.index_path.write_text("# SnapGraph Index\n", encoding="utf-8")

    result = lint_workspace(workspace)

    assert result.status == "WARN"
    assert any("graph_report.md is not listed in index.md" in warning for warning in result.warnings)
