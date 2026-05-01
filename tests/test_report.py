from pathlib import Path

from snapgraph.answer import answer_question, save_answer
from snapgraph.ingest import ingest_source
from snapgraph.linting import lint_workspace
from snapgraph.report import write_graph_report
from snapgraph.workspace import Workspace, create_workspace


DEMO_QUESTIONS = [
    "我为什么要从 LLM Wiki 开始？",
    "我之前为什么觉得截图不是核心，而只是入口？",
    "我对端侧模型的判断是什么？",
    "这个项目的 AI 必然性在哪里？",
    "我现在最应该处理的 open loop 是什么？",
]


def test_report_handles_empty_workspace(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)

    report = write_graph_report(workspace)

    assert report.absolute_page_path.exists()
    assert report.relative_page_path == "wiki/graph_report.md"
    assert "## Corpus Summary" in report.text
    assert "- Sources: 0" in report.text
    assert "No cognitive contexts found." in report.text
    assert "No graph paths found yet." in report.text


def test_report_summarizes_demo_workspace(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)
    save_answer(workspace, answer_question(workspace, DEMO_QUESTIONS[0]))
    save_answer(workspace, answer_question(workspace, DEMO_QUESTIONS[1]))

    report = write_graph_report(workspace)
    report_text = report.absolute_page_path.read_text(encoding="utf-8")

    assert "## Top Hubs" in report_text
    assert "## Confidence & Audit Trail" in report_text
    assert "## Project Clusters" in report_text
    assert "## High-Value Review Paths" in report_text
    assert "## Cognitive Gaps" in report_text
    assert "## Honest Audit Trail" in report_text
    assert "Average confidence:" in report_text
    assert "## Open Loops" in report_text
    assert "## Saved Questions" in report_text
    assert "## Graph Paths Worth Reviewing" in report_text
    assert "## Suggested Next Questions" in report_text
    assert "## Lint Summary" in report_text
    assert "user-stated: 3" in report_text
    assert "AI-inferred: 5" in report_text
    assert "[LLM Wiki Note](sources/" in report_text
    assert "confidence 1.00" in report_text
    assert "confidence 0.60" in report_text
    assert "我为什么要从 LLM Wiki 开始？" in report_text
    assert "Status: OK" in report_text

    index_text = workspace.index_path.read_text(encoding="utf-8")
    log_text = workspace.log_path.read_text(encoding="utf-8")
    assert "graph_report.md" in index_text
    assert '"operation": "report"' in log_text


def test_demo_smoke_questions_have_evidence_paths_and_lint_ok(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)

    answers = [answer_question(workspace, question) for question in DEMO_QUESTIONS]
    save_answer(workspace, answers[0])
    save_answer(workspace, answers[1])
    write_graph_report(workspace)
    lint = lint_workspace(workspace)

    for answer in answers:
        assert "## Evidence Sources" in answer.text
        assert "wiki/sources/" in answer.text
        assert "## Graph Paths" in answer.text
        assert "## Retrieval Diagnostics" in answer.text
        assert answer.retrieval.diagnostics.source_pages_used >= 1
        assert answer.retrieval.graph_paths

    question_pages = list((workspace.wiki_dir / "questions").glob("q_*.md"))
    assert len(question_pages) == 2
    assert lint.status == "OK"


def _workspace_with_demo_sources(tmp_path: Path) -> Workspace:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    demo_dir = Path(__file__).parents[1] / "examples" / "demo_sources"
    why_by_name = {
        "note_llm_wiki.md": "我保存它是因为 SnapGraph 需要继承 LLM Wiki 的 raw/wiki/index/log 工作流。",
        "note_graphrag.md": "我保存它是因为模糊召回需要图谱路径，而不只是关键词搜索。",
        "note_screenshot_entry.md": "我保存它是因为截图应该先作为入口，而不是 v0.1 的核心价值验证。",
    }
    for source_path in sorted(demo_dir.glob("*.md")):
        ingest_source(workspace, source_path, why=why_by_name.get(source_path.name))
    return workspace
