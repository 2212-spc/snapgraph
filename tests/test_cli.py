from pathlib import Path

from typer.testing import CliRunner

from snapgraph.cli import app


def test_graph_cli_prints_diagnostics(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "note.md"
    source_path.write_text("# SnapGraph Note\n\nOpen loop: inspect graph.", encoding="utf-8")
    runner = CliRunner()

    init_result = runner.invoke(app, ["init"])
    ingest_result = runner.invoke(app, ["ingest", str(source_path)])
    graph_result = runner.invoke(app, ["graph"])

    assert init_result.exit_code == 0
    assert ingest_result.exit_code == 0
    assert graph_result.exit_code == 0
    assert "SnapGraph diagnostics" in graph_result.stdout
    assert "Nodes:" in graph_result.stdout


def test_ask_cli_prints_retrieval_diagnostics(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "note.md"
    source_path.write_text("# LLM Wiki Note\n\nOpen loop: inspect ask.", encoding="utf-8")
    runner = CliRunner()

    runner.invoke(app, ["init"])
    runner.invoke(app, ["ingest", str(source_path)])
    ask_result = runner.invoke(app, ["ask", "LLM Wiki"])

    assert ask_result.exit_code == 0
    assert "## 检索诊断" in ask_result.stdout
    assert "- 关键词命中：" in ask_result.stdout


def test_ask_cli_save_writes_question_page(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "note.md"
    source_path.write_text("# LLM Wiki Note\n\nOpen loop: inspect ask.", encoding="utf-8")
    runner = CliRunner()

    runner.invoke(app, ["init"])
    runner.invoke(app, ["ingest", str(source_path)])
    ask_result = runner.invoke(app, ["ask", "LLM Wiki", "--save"])

    question_pages = list((tmp_path / ".my_snapgraph" / "wiki" / "questions").glob("q_*.md"))
    assert ask_result.exit_code == 0
    assert "Saved answer: wiki/questions/" in ask_result.stdout
    assert len(question_pages) == 1
    assert "## 检索诊断" in question_pages[0].read_text(encoding="utf-8")


def test_ask_cli_without_save_does_not_write_question_page(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "note.md"
    source_path.write_text("# LLM Wiki Note\n\nOpen loop: inspect ask.", encoding="utf-8")
    runner = CliRunner()

    runner.invoke(app, ["init"])
    runner.invoke(app, ["ingest", str(source_path)])
    ask_result = runner.invoke(app, ["ask", "LLM Wiki"])

    question_pages = list((tmp_path / ".my_snapgraph" / "wiki" / "questions").glob("q_*.md"))
    assert ask_result.exit_code == 0
    assert question_pages == []


def test_report_cli_writes_graph_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    source_path = tmp_path / "note.md"
    source_path.write_text("# LLM Wiki Note\n\nOpen loop: inspect report.", encoding="utf-8")
    runner = CliRunner()

    runner.invoke(app, ["init"])
    runner.invoke(app, ["ingest", str(source_path)])
    report_result = runner.invoke(app, ["report"])

    report_path = tmp_path / ".my_snapgraph" / "wiki" / "graph_report.md"
    assert report_result.exit_code == 0
    assert "Cognitive graph report: wiki/graph_report.md" in report_result.stdout
    assert report_path.exists()
    assert "## 语料概览" in report_path.read_text(encoding="utf-8")


def test_demo_cli_help_is_available() -> None:
    runner = CliRunner()

    result = runner.invoke(app, ["demo", "--help"])

    assert result.exit_code == 0
    assert "Launch the SnapGraph cognitive recall demo" in result.stdout


def test_eval_cli_writes_isolated_outputs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "eval_out"
    runner = CliRunner()

    result = runner.invoke(app, ["eval", "--output-dir", str(output_dir)])

    assert result.exit_code == 0
    assert "SnapGraph evaluation" in result.stdout
    assert (output_dir / "evaluation_results.json").exists()
    assert (output_dir / "evaluation_report.md").exists()
    assert (output_dir / "workspace" / ".my_snapgraph").exists()
    assert not (tmp_path / ".my_snapgraph").exists()
