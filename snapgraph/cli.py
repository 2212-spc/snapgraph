from __future__ import annotations

from pathlib import Path

import typer

from .answer import answer_question, save_answer
from .config import LLMConfig, SnapGraphConfig, load_config, save_config
from .diagnostics import (
    format_graph_diagnostics,
    format_ingest_result,
    format_lint_result,
)
from .demo_data import load_demo_dataset
from .evaluation import run_evaluation
from .graph_store import graph_diagnostics
from .ingest import ingest_source
from .linting import lint_workspace
from .llm_providers import _resolve_llm
from .report import write_graph_report
from .workspace import create_workspace, get_workspace


app = typer.Typer(help="SnapGraph cognitive LLM Wiki CLI.")
config_app = typer.Typer(help="Manage SnapGraph configuration.")
app.add_typer(config_app, name="config")


@app.command("init")
def init_command() -> None:
    """Create a SnapGraph workspace in the current directory."""
    workspace = get_workspace()
    create_workspace(workspace)
    typer.echo(f"Initialized SnapGraph workspace: {workspace.path}")


@app.command("ingest")
def ingest_command(
    path: Path,
    why: str | None = typer.Option(
        None,
        "--why",
        help="Optional user-stated note for why this source was saved.",
    ),
) -> None:
    """Ingest a markdown or text source into the workspace."""
    workspace = get_workspace()
    llm = _resolve_llm(workspace)
    result = ingest_source(workspace, path, why=why, llm=llm)
    typer.echo(format_ingest_result(result))


@app.command("lint")
def lint_command() -> None:
    """Run basic workspace and wiki diagnostics."""
    workspace = get_workspace()
    result = lint_workspace(workspace)
    typer.echo(format_lint_result(result))
    if result.status == "ERROR":
        raise typer.Exit(code=1)


@app.command("graph")
def graph_command() -> None:
    """Print graph diagnostics for the current workspace."""
    workspace = get_workspace()
    result = graph_diagnostics(workspace)
    typer.echo(format_graph_diagnostics(result))


@app.command("report")
def report_command() -> None:
    """Generate a human-readable Cognitive Graph Report."""
    workspace = get_workspace()
    result = write_graph_report(workspace)
    typer.echo(f"Cognitive graph report: {result.relative_page_path}")


@app.command("load-demo")
def load_demo_command() -> None:
    """Load the repeatable SnapGraph demo dataset."""
    workspace = get_workspace()
    result = load_demo_dataset(workspace)
    typer.echo("SnapGraph demo dataset")
    typer.echo(f"Ingested sources: {result.ingested}")
    typer.echo(f"Skipped existing sources: {result.skipped}")
    typer.echo(f"Saved answers: {result.saved_answers}")
    typer.echo(f"Report: {result.report_path}")


@app.command("eval")
def eval_command(
    output_dir: Path | None = typer.Option(
        None,
        "--output-dir",
        help="Directory for isolated evaluation inputs, workspace, and reports.",
    ),
    provider: str = typer.Option(
        "mock",
        "--provider",
        help="Answer provider for evaluation: mock, deepseek, or anthropic.",
    ),
    model: str = typer.Option("", "--model", help="Optional provider model override."),
    api_key_env: str = typer.Option(
        "SNAPGRAPH_LLM_API_KEY",
        "--api-key-env",
        help="Environment variable name that contains the provider API key.",
    ),
) -> None:
    """Run an isolated multi-angle capability evaluation."""
    try:
        result = run_evaluation(
            output_dir=output_dir,
            provider=provider,
            model=model,
            api_key_env=api_key_env,
        )
    except Exception as exc:
        typer.echo(f"SnapGraph evaluation failed: {exc}", err=True)
        raise typer.Exit(code=1)

    typer.echo("SnapGraph evaluation")
    typer.echo(f"Output: {result.output_dir}")
    typer.echo(f"Workspace: {result.workspace_dir}")
    typer.echo(f"Provider: {result.provider['provider_used']} ({result.provider['model_used']})")
    typer.echo(f"Lint: {result.lint_status}")
    typer.echo(f"Results JSON: {result.results_path}")
    typer.echo(f"Report: {result.report_path}")


@app.command("serve")
def serve_command(
    port: int = typer.Option(8501, "--port", help="Server port."),
) -> None:
    """Launch the SnapGraph web server (FastAPI + Vue frontend)."""
    _run_demo_server(port)


@app.command("demo")
def demo_command(
    port: int = typer.Option(8501, "--port", help="Demo server port."),
) -> None:
    """Launch the SnapGraph cognitive recall demo."""
    _run_demo_server(port)


def _run_demo_server(port: int) -> None:
    try:
        import uvicorn
    except ImportError:
        typer.echo("Missing dependencies. Run: python -m pip install -e '.[demo]'", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"SnapGraph server starting at http://localhost:{port}")
    uvicorn.run("snapgraph.api:app", host="0.0.0.0", port=port, reload=False)


@app.command("ask")
def ask_command(
    question: str,
    save: bool = typer.Option(
        False,
        "--save",
        help="Save the answer into wiki/questions/ for future recall.",
    ),
) -> None:
    """Answer a question using wiki pages and graph paths."""
    workspace = get_workspace()
    llm = _resolve_llm(workspace)
    result = answer_question(workspace, question, llm=llm)
    typer.echo(result.text)
    if save:
        page = save_answer(workspace, result)
        typer.echo(f"\nSaved answer: {page.relative_page_path}")


@config_app.command("show")
def config_show() -> None:
    """Print the current workspace configuration."""
    workspace = get_workspace()
    config = load_config(workspace)
    typer.echo(f"Workspace: {workspace.path}")
    typer.echo(f"  version: {config.workspace_version}")
    typer.echo(f"  llm.provider: {config.llm.provider}")
    typer.echo(f"  llm.model: {config.llm.model or '(default)'}")
    typer.echo(f"  llm.api_key_env: {config.llm.api_key_env}")
    typer.echo(f"  retrieval.title_weight: {config.retrieval.title_weight}")
    typer.echo(f"  retrieval.keyword_weight: {config.retrieval.keyword_weight}")
    typer.echo(f"  retrieval.max_expanded_nodes: {config.retrieval.max_expanded_nodes}")
    typer.echo(f"  retrieval.max_source_pages: {config.retrieval.max_source_pages}")


@config_app.command("set-llm-provider")
def config_set_llm_provider(provider: str) -> None:
    """Set the LLM provider (mock or anthropic)."""
    if provider not in ("mock", "anthropic", "deepseek"):
        typer.echo(f"Unknown provider: {provider}. Use 'mock', 'anthropic', or 'deepseek'.", err=True)
        raise typer.Exit(code=1)
    workspace = get_workspace()
    config = load_config(workspace)
    updated = SnapGraphConfig(
        workspace_version=config.workspace_version,
        llm=LLMConfig(
            provider=provider,
            model=config.llm.model,
            api_key_env=config.llm.api_key_env,
        ),
        retrieval=config.retrieval,
    )
    save_config(workspace, updated)
    typer.echo(f"LLM provider set to: {provider}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
