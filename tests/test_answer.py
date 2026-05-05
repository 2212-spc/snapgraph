from pathlib import Path
from types import SimpleNamespace

import snapgraph.parsers as parsers
from snapgraph.answer import answer_question, clean_answer_glyphs, save_answer
from snapgraph.ingest import ingest_source
from snapgraph.retrieval import retrieve_for_question
from snapgraph.workspace import Workspace, create_workspace


class BodyOnlyLLM:
    def synthesize_answer(self, question: str, contexts: list[dict], graph_paths: list[str]) -> str:
        return "# 回答\nProvider body."


def test_provider_answer_glyph_cleanup_keeps_quiet_voice() -> None:
    assert clean_answer_glyphs("✅ 下一步：继续验证。") == "下一步：继续验证。"


def test_ask_recovers_llm_wiki_context_with_graph_paths(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)

    answer = answer_question(workspace, "我为什么要从 LLM Wiki 开始？")

    assert "## 找回的原话" in answer.text
    assert "## 相关材料" in answer.text
    assert "## 连接路径" in answer.text
    assert "## AI 探索回应" in answer.text
    assert "## 涌现洞见" in answer.text
    assert "## 下一步" in answer.text
    assert "## 检索诊断" in answer.text
    assert "LLM Wiki Note" in answer.text
    assert "wiki/sources/" in answer.text
    assert "- 图节点命中：" in answer.text
    assert answer.retrieval.diagnostics.source_pages_used >= 1
    assert answer.retrieval.graph_paths
    assert any("-> triggered_thought ->" in path for path in answer.retrieval.graph_paths)
    assert "这条线索最可能连向" in answer.text
    assert "(`" in answer.text


def test_ask_handles_chinese_screenshot_query_with_aliases(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)

    answer = answer_question(workspace, "我之前为什么觉得截图不是核心，而只是入口？")

    assert "Screenshot Entry Note" in answer.text
    assert "screenshot" in answer.text.lower()
    assert answer.retrieval.diagnostics.source_pages_used >= 1
    assert answer.retrieval.graph_paths


def test_ask_no_match_is_low_confidence_and_does_not_fabricate(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)

    answer = answer_question(workspace, "unrelated quantum pineapple")

    assert "低置信度" in answer.text
    assert "我不会推断保存原因" in answer.text
    assert "## 相关材料\n无" in answer.text
    assert answer.retrieval.diagnostics.source_pages_used == 0


def test_ask_does_not_reference_deleted_source_page(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)
    source_page = next((workspace.wiki_dir / "sources").glob("*.md"))
    source_page.unlink()

    answer = answer_question(workspace, "LLM Wiki")

    assert source_page.name not in answer.text


def test_long_document_does_not_beat_short_title_match(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    long_source = tmp_path / "long_noise.md"
    long_source.write_text("needle " * 5000, encoding="utf-8")
    short_source = tmp_path / "needle_note.md"
    short_source.write_text("needle", encoding="utf-8")
    ingest_source(workspace, long_source)
    ingest_source(workspace, short_source)

    retrieval = retrieve_for_question(workspace, "needle")

    assert retrieval.contexts[0].title == "needle_note"


def test_retrieval_prioritizes_user_stated_pdf_over_ai_inferred_noise(
    tmp_path: Path,
    monkeypatch,
) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    noise = tmp_path / "wiki_core.md"
    noise.write_text(
        "# wiki的核心是什么\n\ncapture context cognitive context pdf\n",
        encoding="utf-8",
    )
    pdf = tmp_path / "agent_memory.pdf"
    pdf.write_bytes(b"%PDF-1.4\n% placeholder\n")

    monkeypatch.setattr(
        parsers.shutil,
        "which",
        lambda name: "/usr/bin/pdftotext" if name == "pdftotext" else None,
    )
    monkeypatch.setattr(
        parsers.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout="Raw storage can be found again, but the cognitive context is usually lost.",
        ),
    )

    ingest_source(workspace, noise)
    ingest_source(
        workspace,
        pdf,
        why="This PDF tests whether capture context preserves why raw storage mattered.",
    )

    retrieval = retrieve_for_question(
        workspace,
        "刚才那份 PDF 里说真正容易丢失的是什么？它和 capture context 有什么关系？",
    )

    assert retrieval.contexts[0].title == "agent_memory"
    assert retrieval.contexts[0].why_saved_status == "user-stated"


def test_graph_expansion_limit_is_reported(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)
    config = workspace.config_path.read_text(encoding="utf-8")
    workspace.config_path.write_text(
        config.replace('"max_expanded_nodes": 40', '"max_expanded_nodes": 2'),
        encoding="utf-8",
    )

    retrieval = retrieve_for_question(workspace, "SnapGraph")

    assert retrieval.diagnostics.graph_expansion_truncated is True
    assert retrieval.diagnostics.expanded_nodes <= 2


def test_ask_degrades_when_graph_json_is_invalid(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)
    workspace.graph_path.write_text("", encoding="utf-8")

    answer = answer_question(workspace, "LLM Wiki")

    assert "LLM Wiki Note" in answer.text
    assert answer.retrieval.diagnostics.graph_node_hits == 0


def test_provider_answer_still_appends_retrieval_diagnostics(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)

    answer = answer_question(workspace, "我为什么要从 LLM Wiki 开始？", llm=BodyOnlyLLM())

    assert "Provider body." in answer.text
    assert "## 检索诊断" in answer.text
    assert "- 关键词命中：" in answer.text


def test_save_answer_writes_question_page_index_and_log(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)
    answer = answer_question(workspace, "我为什么要从 LLM Wiki 开始？")

    page = save_answer(workspace, answer)

    assert page.absolute_page_path.exists()
    assert page.relative_page_path.startswith("wiki/questions/q_")

    page_text = page.absolute_page_path.read_text(encoding="utf-8")
    assert "## Question" in page_text
    assert "我为什么要从 LLM Wiki 开始？" in page_text
    assert "## Answer" in page_text
    assert "## Evidence Source Pages" in page_text
    assert "wiki/sources/" in page_text
    assert "## 检索诊断" in page_text

    index_text = workspace.index_path.read_text(encoding="utf-8")
    assert f"questions/{page.id}.md" in index_text
    assert page.id in index_text

    log_text = workspace.log_path.read_text(encoding="utf-8")
    assert '"operation": "ask_save"' in log_text
    assert page.relative_page_path in log_text


def test_save_low_confidence_answer_is_traceable(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    answer = answer_question(workspace, "unrelated quantum pineapple")

    page = save_answer(workspace, answer)
    page_text = page.absolute_page_path.read_text(encoding="utf-8")

    assert "低置信度" in page_text
    assert "## Evidence Source Pages\n- None" in page_text
    assert "## 检索诊断" in page_text


def _workspace_with_demo_sources(tmp_path: Path) -> Workspace:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    demo_dir = Path(__file__).parents[1] / "examples" / "demo_sources"
    for index, source_path in enumerate(sorted(demo_dir.glob("*.md"))):
        why = "我保存它是为了验证 SnapGraph 的认知语境和图谱召回。" if index == 0 else None
        ingest_source(workspace, source_path, why=why)
    return workspace
