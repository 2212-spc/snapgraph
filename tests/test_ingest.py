import json
import sqlite3
from pathlib import Path

from snapgraph.ingest import ingest_source
from snapgraph.workspace import Workspace, create_workspace


def test_ingest_markdown_creates_raw_page_index_and_log(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text("# Test Note\n\nThis source matters later.\n", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)

    result = ingest_source(workspace, source_path)

    assert result.raw_path.exists()
    assert result.page.absolute_page_path.exists()

    page_text = result.page.absolute_page_path.read_text(encoding="utf-8")
    assert "## Objective Summary" in page_text
    assert "## Cognitive Context" in page_text
    assert "- Status: AI-inferred" in page_text
    assert "AI-inferred:" in page_text
    assert "raw_path:" in page_text
    assert "original_filename: note.md" in page_text
    assert "## Evidence" in page_text
    assert result.source.content_hash in page_text
    assert "- Related projects:" in page_text
    assert "- Related questions:" in page_text
    assert "- Related tasks:" in page_text

    index_text = workspace.index_path.read_text(encoding="utf-8")
    assert result.source.id in index_text
    assert f"sources/{result.source.id}.md" in index_text

    log_text = workspace.log_path.read_text(encoding="utf-8")
    assert f'"source_id": "{result.source.id}"' in log_text
    assert '"operation": "ingest"' in log_text
    assert result.page.relative_page_path in log_text


def test_ingest_preserves_user_stated_why_exactly(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text("# Test Note\n\nSnapGraph source.\n", encoding="utf-8")
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    why = "我保存它是因为它可能影响我的开题报告方法论章节。"

    result = ingest_source(workspace, source_path, why=why)

    assert result.cognitive_context.why_saved == why
    assert result.cognitive_context.why_saved_status == "user-stated"

    page_text = result.page.absolute_page_path.read_text(encoding="utf-8")
    assert f"- Why this may have been saved: {why}" in page_text
    assert "- Status: user-stated" in page_text

    with sqlite3.connect(workspace.sqlite_path) as conn:
        row = conn.execute(
            """
            SELECT why_saved, why_saved_status
            FROM cognitive_contexts
            WHERE source_id = ?
            """,
            (result.source.id,),
        ).fetchone()
    assert row == (why, "user-stated")


def test_ingest_without_why_is_ai_inferred(tmp_path: Path) -> None:
    source_path = tmp_path / "note.txt"
    source_path.write_text("A deterministic source.", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = ingest_source(workspace, source_path)

    assert result.cognitive_context.why_saved_status == "AI-inferred"
    assert result.cognitive_context.why_saved.startswith("AI-inferred:")
    assert result.cognitive_context.future_recall_questions


def test_log_event_is_parseable_json(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text("# Test Note\n\nThis source matters later.\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    result = ingest_source(workspace, source_path)
    log_text = workspace.log_path.read_text(encoding="utf-8")
    event_json = log_text.split("```json\n", 1)[1].split("\n```", 1)[0]
    event = json.loads(event_json)

    assert event["operation"] == "ingest"
    assert event["source_id"] == result.source.id
    assert result.page.relative_page_path in event["touched_pages"]


def test_ingest_rejects_unsupported_file_type(tmp_path: Path) -> None:
    source_path = tmp_path / "data.bin"
    source_path.write_bytes(b"not a supported file")
    workspace = Workspace(tmp_path)

    try:
        ingest_source(workspace, source_path)
    except ValueError as exc:
        assert "Unsupported source type" in str(exc)
    else:
        raise AssertionError("Expected unsupported type to raise ValueError")


def test_duplicate_ingest_warns_and_creates_related_edge(tmp_path: Path) -> None:
    source_path = tmp_path / "note.md"
    source_path.write_text("# Test Note\n\nSame content.\n", encoding="utf-8")
    workspace = Workspace(tmp_path)

    first = ingest_source(workspace, source_path)
    second = ingest_source(workspace, source_path)

    assert second.warnings == [
        f"duplicate content_hash also seen in {first.source.id}"
    ]
    graph = json.loads(workspace.graph_path.read_text(encoding="utf-8"))
    assert any(edge["relation"] == "related_to" for edge in graph["edges"])


def test_experimental_image_ingest_uses_mock_placeholder(tmp_path: Path) -> None:
    image_path = tmp_path / "screen.png"
    image_path.write_bytes(b"not a real png but enough for hash-based mock ingest")
    workspace = Workspace(tmp_path)

    result = ingest_source(workspace, image_path)

    assert result.source.type == "screenshot"
    assert result.raw_path.parent.name == "screenshots"
    assert "visual content not available" in (result.source.summary or "")

    page_text = result.page.absolute_page_path.read_text(encoding="utf-8")
    assert "type: screenshot" in page_text
    assert "Use a vision-enabled LLM provider" in page_text
