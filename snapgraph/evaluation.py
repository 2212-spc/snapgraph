from __future__ import annotations

import json
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .answer import answer_question
from .config import LLMConfig, SnapGraphConfig, load_config, save_config, validate_api_key_env_name
from .graph_store import graph_diagnostics
from .ingest import ingest_source
from .linting import lint_workspace
from .llm import LLMProvider, MockLLM
from .llm_providers import provider_metadata, resolve_llm_with_metadata
from .report import write_graph_report
from .workspace import Workspace, create_workspace


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    scenario: str
    question: str
    expected_sources: list[str]
    expected_claims: list[str]
    provider: str
    actual_sources_used: list[str]
    retrieval_diagnostics: dict
    answer_text: str
    scores: dict[str, int]
    total_score: int
    verdict: str
    fail_reason: str


@dataclass(frozen=True)
class EvaluationRun:
    output_dir: str
    workspace_dir: str
    provider: dict
    material_results: list[dict]
    cases: list[EvaluationCase]
    lint_status: str
    graph: dict
    results_path: str
    report_path: str


def run_evaluation(
    *,
    output_dir: Path | None = None,
    provider: str = "mock",
    model: str = "",
    api_key_env: str = "SNAPGRAPH_LLM_API_KEY",
) -> EvaluationRun:
    if provider not in {"mock", "deepseek", "anthropic"}:
        raise ValueError("provider must be mock, deepseek, or anthropic")
    api_key_env = validate_api_key_env_name(api_key_env)

    base_dir = output_dir or Path(tempfile.mkdtemp(prefix="snapgraph_eval_"))
    base_dir = base_dir.expanduser().resolve()
    inputs_dir = base_dir / "inputs"
    workspace_root = base_dir / "workspace"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    workspace = Workspace(workspace_root)
    create_workspace(workspace)

    if provider != "mock" or model:
        current = load_config(workspace)
        save_config(
            workspace,
            SnapGraphConfig(
                workspace_version=current.workspace_version,
                retrieval=current.retrieval,
                llm=LLMConfig(provider=provider, model=model, api_key_env=api_key_env),
            ),
        )

    answer_llm, metadata = _evaluation_llm(workspace, provider)
    materials = _write_eval_materials(inputs_dir)
    material_results = _ingest_materials(workspace, materials)

    cases = [
        _run_case(
            workspace,
            answer_llm,
            provider,
            case_id="markdown_recall",
            scenario="Markdown baseline recall",
            question="我为什么要从 LLM Wiki 开始？",
            expected_sources=["LLM Wiki Baseline"],
            expected_claims=["raw/wiki/index/log", "user-stated"],
        ),
        _run_case(
            workspace,
            answer_llm,
            provider,
            case_id="open_loop",
            scenario="Open loop recovery",
            question="我现在最应该处理的 open loop 是什么？",
            expected_sources=["Open Loop Ledger"],
            expected_claims=["Open loop", "next action"],
        ),
        _run_case(
            workspace,
            answer_llm,
            provider,
            case_id="cross_document",
            scenario="Cross-document synthesis",
            question="这些材料共同支持 SnapGraph 的哪条产品判断？",
            expected_sources=["LLM Wiki Baseline", "GraphRAG Judgment", "Screenshot Boundary"],
            expected_claims=["cognitive context", "graph", "evidence"],
        ),
        _run_case(
            workspace,
            answer_llm,
            provider,
            case_id="abstract_graph_ai",
            scenario="Abstract graph plus AI judgment",
            question="这个项目为什么需要 AI 加 graph？",
            expected_sources=["GraphRAG Judgment", "Methodology Reflection"],
            expected_claims=["AI", "graph"],
        ),
        _run_case(
            workspace,
            answer_llm,
            provider,
            case_id="media_boundary",
            scenario="PDF capability boundary",
            question="PDF 资料现在能进入系统吗？",
            expected_sources=["Capability Boundary"],
            expected_claims=["PDF", "unsupported"],
        ),
        _run_case(
            workspace,
            answer_llm,
            provider,
            case_id="irrelevant_question",
            scenario="No-match boundary",
            question="unrelated quantum pineapple",
            expected_sources=[],
            expected_claims=["Low confidence"],
        ),
    ]

    report = write_graph_report(workspace)
    lint = lint_workspace(workspace)
    graph_diag = graph_diagnostics(workspace)
    run = EvaluationRun(
        output_dir=str(base_dir),
        workspace_dir=str(workspace.path),
        provider=metadata.as_dict(),
        material_results=material_results,
        cases=cases,
        lint_status=lint.status,
        graph={
            "nodes": graph_diag.node_count,
            "edges": graph_diag.edge_count,
            "node_types": graph_diag.node_types,
            "warnings": graph_diag.warnings,
        },
        results_path=str(base_dir / "evaluation_results.json"),
        report_path=str(base_dir / "evaluation_report.md"),
    )
    _write_outputs(run, workspace_report_path=report.absolute_page_path)
    return run


def _evaluation_llm(workspace: Workspace, provider: str) -> tuple[LLMProvider, object]:
    if provider == "mock":
        return MockLLM(), provider_metadata(workspace, provider_used="mock")
    return resolve_llm_with_metadata(workspace)


def _write_eval_materials(inputs_dir: Path) -> list[Path]:
    files = {
        "01_llm_wiki.md": """# LLM Wiki Baseline

SnapGraph starts from the LLM Wiki pattern because immutable raw sources, generated wiki pages, index.md, and log.md make every recovered memory auditable.

Open loop: decide how index.md should scale after 100 sources.
""",
        "02_graph_rag.md": """# GraphRAG Judgment

GraphRAG matters because vague recall questions depend on relationships between sources, saved thoughts, projects, and open loops.

The graph should explain why a source mattered, not just retrieve a matching paragraph.
""",
        "03_screenshot_boundary.md": """# Screenshot Boundary

Screenshots are a capture entry point, not the core value proof. The core value is recovering why a screenshot or note mattered later.

Open loop: keep screenshot ingestion experimental until text recall is persuasive.
""",
        "04_mixed_language.md": """# On-device / 端侧 Memory

Future SnapGraph should move toward an on-device app, but the current version must first prove local cognitive recall with text notes and graph paths.
""",
        "05_methodology.txt": """# Methodology Reflection

AI is useful when it extracts candidate reasons and recall questions. The graph is useful when it keeps evidence paths inspectable.
""",
        "06_open_loops.md": """# Open Loop Ledger

Todo: improve the answer format so it feels like recovered judgment rather than a field template.
Next: add a provider status panel so users know whether MockLLM or DeepSeek answered.
""",
        "07_capability_boundary.md": """# Capability Boundary

Current stable ingestion supports Markdown, plain text, and experimental images. PDF ingestion is not part of the v0.1 stable baseline and should be reported as unsupported.
""",
        "08_empty.md": "",
        "09_long_noise.md": "# Long Noise\n\n" + ("needle signal noise " * 1200),
        "10_duplicate.md": "# LLM Wiki Baseline\n\nDuplicate copy for content hash checks.\n",
        "11_fake_pdf.txt": "%PDF-like text saved as txt. This should be treated as plain text, not real PDF parsing.",
    }
    paths = []
    for name, text in files.items():
        path = inputs_dir / name
        path.write_text(text, encoding="utf-8")
        paths.append(path)

    image_path = inputs_dir / "12_ui_screenshot.png"
    image_path.write_bytes(_tiny_png_bytes())
    paths.append(image_path)

    pdf_path = inputs_dir / "13_research_paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n% minimal placeholder\n")
    paths.append(pdf_path)

    broken_pdf_path = inputs_dir / "14_broken.pdf"
    broken_pdf_path.write_bytes(b"not actually a pdf")
    paths.append(broken_pdf_path)
    return paths


def _ingest_materials(workspace: Workspace, paths: list[Path]) -> list[dict]:
    results = []
    ingest_llm = MockLLM()
    for path in paths:
        try:
            why = _why_for_material(path.name)
            result = ingest_source(workspace, path, why=why, llm=ingest_llm)
            results.append(
                {
                    "path": path.name,
                    "status": "ingested",
                    "source_id": result.source.id,
                    "source_type": result.source.type,
                    "warnings": result.warnings,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "path": path.name,
                    "status": "unsupported" if path.suffix.lower() == ".pdf" else "error",
                    "error": str(exc),
                }
            )
    return results


def _why_for_material(filename: str) -> str | None:
    whys = {
        "01_llm_wiki.md": "我保存它是因为 SnapGraph 需要继承 LLM Wiki 的 raw/wiki/index/log 工作流。",
        "02_graph_rag.md": "我保存它是因为模糊召回需要图谱路径，而不只是关键词搜索。",
        "03_screenshot_boundary.md": "我保存它是因为截图应该先作为入口，而不是 v0.1 的核心价值验证。",
        "07_capability_boundary.md": "I saved this to keep the PDF and image capability boundary honest.",
    }
    return whys.get(filename)


def _run_case(
    workspace: Workspace,
    llm: LLMProvider,
    provider: str,
    *,
    case_id: str,
    scenario: str,
    question: str,
    expected_sources: list[str],
    expected_claims: list[str],
) -> EvaluationCase:
    try:
        answer = answer_question(workspace, question, llm=llm)
    except Exception as exc:
        return EvaluationCase(
            case_id=case_id,
            scenario=scenario,
            question=question,
            expected_sources=expected_sources,
            expected_claims=expected_claims,
            provider=provider,
            actual_sources_used=[],
            retrieval_diagnostics={},
            answer_text="",
            scores={name: 0 for name in _score_names()},
            total_score=0,
            verdict="fail",
            fail_reason=str(exc),
        )

    actual_sources = [context.title for context in answer.retrieval.contexts]
    scores = _score_case(
        answer_text=answer.text,
        actual_sources=actual_sources,
        expected_sources=expected_sources,
        expected_claims=expected_claims,
        graph_paths=answer.retrieval.graph_paths,
        diagnostics=asdict(answer.retrieval.diagnostics),
    )
    total = sum(scores.values())
    return EvaluationCase(
        case_id=case_id,
        scenario=scenario,
        question=question,
        expected_sources=expected_sources,
        expected_claims=expected_claims,
        provider=provider,
        actual_sources_used=actual_sources,
        retrieval_diagnostics=asdict(answer.retrieval.diagnostics),
        answer_text=_redact(answer.text),
        scores=scores,
        total_score=total,
        verdict="demo" if total >= 16 else "needs-work" if total >= 12 else "fail",
        fail_reason="" if total >= 12 else "Score below quality threshold.",
    )


def _score_case(
    *,
    answer_text: str,
    actual_sources: list[str],
    expected_sources: list[str],
    expected_claims: list[str],
    graph_paths: list[str],
    diagnostics: dict,
) -> dict[str, int]:
    lowered_answer = answer_text.lower()
    lowered_sources = [source.lower() for source in actual_sources]
    if expected_sources:
        hits = sum(
            1
            for expected in expected_sources
            if any(expected.lower() in source for source in lowered_sources)
        )
        retrieval = 4 if hits >= min(2, len(expected_sources)) else 2 if hits else 0
    else:
        retrieval = 4 if not actual_sources else 1

    evidence = 0
    if "## evidence sources" in lowered_answer or actual_sources:
        evidence += 2
    if graph_paths or "## graph paths" in lowered_answer:
        evidence += 2

    boundary = 0
    if "user-stated" in answer_text:
        boundary += 2
    if "AI-inferred" in answer_text or "low confidence" in lowered_answer:
        boundary += 2

    quality = 0
    if "## direct answer" in lowered_answer:
        quality += 1
    if "## suggested next action" in lowered_answer:
        quality += 1
    if sum(1 for claim in expected_claims if claim.lower() in lowered_answer) >= min(2, len(expected_claims)):
        quality += 2

    edge = 0
    if expected_sources or "low confidence" in lowered_answer:
        edge += 2
    if diagnostics.get("source_pages_used", 0) == len(actual_sources):
        edge += 1
    if "i will not infer a reason without evidence" in lowered_answer or actual_sources:
        edge += 1

    return {
        "retrieval_hit": min(4, retrieval),
        "evidence_traceability": min(4, evidence),
        "cognitive_boundary": min(4, boundary),
        "answer_quality": min(4, quality),
        "boundary_honesty": min(4, edge),
    }


def _write_outputs(run: EvaluationRun, *, workspace_report_path: Path) -> None:
    results_path = Path(run.results_path)
    report_path = Path(run.report_path)
    results_path.write_text(
        json.dumps(_run_to_dict(run), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(_render_eval_report(run, workspace_report_path), encoding="utf-8")


def _run_to_dict(run: EvaluationRun) -> dict:
    return {
        "output_dir": run.output_dir,
        "workspace_dir": run.workspace_dir,
        "provider": run.provider,
        "material_results": run.material_results,
        "cases": [asdict(case) for case in run.cases],
        "lint_status": run.lint_status,
        "graph": run.graph,
        "results_path": run.results_path,
        "report_path": run.report_path,
    }


def _render_eval_report(run: EvaluationRun, workspace_report_path: Path) -> str:
    created_at = datetime.now(timezone.utc).isoformat()
    demo_ready = [case for case in run.cases if case.verdict == "demo"]
    lines = [
        f"# SnapGraph Evaluation Report ({created_at})",
        "",
        "## Summary",
        f"- Provider used: {run.provider['provider_used']} ({run.provider['model_used']})",
        f"- Fallback used: {run.provider['fallback_used']}",
        f"- Lint status: {run.lint_status}",
        f"- Graph: {run.graph['nodes']} nodes, {run.graph['edges']} edges",
        f"- Demo-ready cases: {len(demo_ready)}/{len(run.cases)}",
        f"- Workspace report: `{workspace_report_path}`",
        "",
        "## Material Ingestion",
    ]
    for material in run.material_results:
        status = material["status"]
        suffix = f" - {material.get('error', '')}" if material.get("error") else ""
        lines.append(f"- {material['path']}: {status}{suffix}")
    lines.extend(["", "## Case Scores"])
    for case in run.cases:
        lines.extend(
            [
                f"### {case.case_id}: {case.verdict} ({case.total_score}/20)",
                f"- Scenario: {case.scenario}",
                f"- Question: {case.question}",
                f"- Sources used: {', '.join(case.actual_sources_used) or 'None'}",
                f"- Scores: {case.scores}",
                f"- Fail reason: {case.fail_reason or 'None'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Interpretation",
            "- `>=16`: safe to demonstrate.",
            "- `12-15`: useful but needs polish.",
            "- `<12`: do not market as a capability yet.",
        ]
    )
    return "\n".join(lines) + "\n"


def _redact(text: str) -> str:
    return re.sub(r"sk-[A-Za-z0-9_-]+", "sk-REDACTED", text)


def _score_names() -> list[str]:
    return [
        "retrieval_hit",
        "evidence_traceability",
        "cognitive_boundary",
        "answer_quality",
        "boundary_honesty",
    ]


def _tiny_png_bytes() -> bytes:
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00"
        b"\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01"
        b"\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
    )
