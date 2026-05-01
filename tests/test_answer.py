from pathlib import Path

from snapgraph.answer import answer_question, save_answer
from snapgraph.ingest import ingest_source
from snapgraph.retrieval import retrieve_for_question
from snapgraph.workspace import Workspace, create_workspace


class BodyOnlyLLM:
    def synthesize_answer(self, question: str, contexts: list[dict], graph_paths: list[str]) -> str:
        return "# Answer\n## Direct Answer\nProvider body."


def test_ask_recovers_llm_wiki_context_with_graph_paths(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)

    answer = answer_question(workspace, "我为什么要从 LLM Wiki 开始？")

    assert "## Direct Answer" in answer.text
    assert "## Recovered Cognitive Context" in answer.text
    assert "## Evidence Sources" in answer.text
    assert "## Graph Paths" in answer.text
    assert "## Retrieval Diagnostics" in answer.text
    assert "LLM Wiki Note" in answer.text
    assert "wiki/sources/" in answer.text
    assert "- graph node hits:" in answer.text
    assert answer.retrieval.diagnostics.source_pages_used >= 1
    assert answer.retrieval.graph_paths
    assert any("-> triggered_thought ->" in path for path in answer.retrieval.graph_paths)
    assert "because it connected to" in answer.text
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

    assert "Low confidence" in answer.text
    assert "I will not infer a reason without evidence" in answer.text
    assert "Evidence Sources\nNone" in answer.text
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
    assert "## Retrieval Diagnostics" in answer.text
    assert "- keyword hits:" in answer.text


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
    assert "## Retrieval Diagnostics" in page_text

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

    assert "Low confidence" in page_text
    assert "## Evidence Source Pages\n- None" in page_text
    assert "## Retrieval Diagnostics" in page_text


def _workspace_with_demo_sources(tmp_path: Path) -> Workspace:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    demo_dir = Path(__file__).parents[1] / "examples" / "demo_sources"
    for index, source_path in enumerate(sorted(demo_dir.glob("*.md"))):
        why = "我保存它是为了验证 SnapGraph 的认知语境和图谱召回。" if index == 0 else None
        ingest_source(workspace, source_path, why=why)
    return workspace
