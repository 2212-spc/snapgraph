from pathlib import Path

from snapgraph.answer import answer_question, save_answer
from snapgraph.ingest import ingest_source
from snapgraph.linting import lint_workspace
from snapgraph.report import write_graph_report
from snapgraph.workspace import Workspace, create_workspace


DEMO_QUESTIONS = [
    "鎴戜负浠€涔堣浠?LLM Wiki 寮€濮嬶紵",
    "鎴戜箣鍓嶄负浠€涔堣寰楁埅鍥句笉鏄牳蹇冿紝鑰屽彧鏄叆鍙ｏ紵",
    "鎴戝绔晶妯″瀷鐨勫垽鏂槸浠€涔堬紵",
    "杩欎釜椤圭洰鐨?AI 蹇呯劧鎬у湪鍝噷锛?",
    "鎴戠幇鍦ㄦ渶搴旇澶勭悊鐨?open loop 鏄粈涔堬紵",
]


def test_report_handles_empty_workspace(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)

    report = write_graph_report(workspace)

    assert report.absolute_page_path.exists()
    assert report.relative_page_path == "wiki/graph_report.md"
    assert "## 语料概览" in report.text
    assert "- 材料数：0" in report.text
    assert "未发现认知上下文。" in report.text
    assert "暂时还没有可复查的图谱路径。" in report.text


def test_report_summarizes_demo_workspace(tmp_path: Path) -> None:
    workspace = _workspace_with_demo_sources(tmp_path)
    save_answer(workspace, answer_question(workspace, DEMO_QUESTIONS[0]))
    save_answer(workspace, answer_question(workspace, DEMO_QUESTIONS[1]))

    report = write_graph_report(workspace)
    report_text = report.absolute_page_path.read_text(encoding="utf-8")

    assert "## 关键枢纽" in report_text
    assert "## 置信度与审计轨迹" in report_text
    assert "## 项目簇" in report_text
    assert "## 高价值复查路径" in report_text
    assert "## 认知缺口" in report_text
    assert "## 诚实审计说明" in report_text
    assert "平均置信度：" in report_text
    assert "## Open Loops" in report_text
    assert "## 已保存问题" in report_text
    assert "## 值得复查的图谱路径" in report_text
    assert "## 建议的后续问题" in report_text
    assert "## 检查摘要" in report_text
    assert "用户确认：3" in report_text
    assert "AI 推断：5" in report_text
    assert "[LLM Wiki Note](sources/" in report_text
    assert "置信度 1.00" in report_text
    assert "置信度 0.60" in report_text
    assert "状态：OK" in report_text

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

    evidenced = 0
    for answer in answers:
        assert "## 找回的原话" in answer.text
        assert "## 相关材料" in answer.text
        assert "## 连接路径" in answer.text
        assert "## AI 探索回应" in answer.text
        assert "## 涌现洞见" in answer.text
        assert "## 下一步" in answer.text
        assert "## 检索诊断" in answer.text
        if answer.retrieval.diagnostics.source_pages_used >= 1:
            evidenced += 1
            assert "wiki/sources/" in answer.text
            assert answer.retrieval.graph_paths

    question_pages = list((workspace.wiki_dir / "questions").glob("q_*.md"))
    assert len(question_pages) == 2
    assert lint.status == "OK"
    assert evidenced >= 3


def _workspace_with_demo_sources(tmp_path: Path) -> Workspace:
    workspace = Workspace(tmp_path)
    create_workspace(workspace)
    demo_dir = Path(__file__).parents[1] / "examples" / "demo_sources"
    why_by_name = {
        "note_llm_wiki.md": "鎴戜繚瀛樺畠鏄洜涓?SnapGraph 闇€瑕佺户鎵?LLM Wiki 鐨?raw/wiki/index/log 宸ヤ綔娴併€?",
        "note_graphrag.md": "鎴戜繚瀛樺畠鏄洜涓烘ā绯婂彫鍥為渶瑕佸浘璋辫矾寰勶紝鑰屼笉鍙槸鍏抽敭璇嶆悳绱€?",
        "note_screenshot_entry.md": "鎴戜繚瀛樺畠鏄洜涓烘埅鍥惧簲璇ュ厛浣滀负鍏ュ彛锛岃€屼笉鏄?v0.1 鐨勬牳蹇冧环鍊奸獙璇併€?",
    }
    for source_path in sorted(demo_dir.glob("*.md")):
        ingest_source(workspace, source_path, why=why_by_name.get(source_path.name))
    return workspace
