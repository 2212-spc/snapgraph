from __future__ import annotations

from .models import GraphDiagnostics, IngestResult, LintResult


def format_ingest_result(result: IngestResult) -> str:
    lines = [
        "SnapGraph ingest",
        f"Source ID: {result.source.id}",
        f"Raw source: {result.source.path}",
        f"Wiki page: {result.page.relative_page_path}",
        f"Cognitive status: {result.cognitive_context.why_saved_status}",
        f"Summary: {result.source.summary}",
        "Warnings:",
    ]
    lines.extend([f"- {warning}" for warning in result.warnings] or ["- None"])
    return "\n".join(lines)


def format_lint_result(result: LintResult) -> str:
    lines = ["SnapGraph Lint", f"Status: {result.status}"]
    lines.append("Errors:")
    lines.extend([f"- {error}" for error in result.errors] or ["- None"])
    lines.append("Warnings:")
    lines.extend([f"- {warning}" for warning in result.warnings] or ["- None"])
    return "\n".join(lines)


def format_graph_diagnostics(result: GraphDiagnostics) -> str:
    lines = [
        "SnapGraph diagnostics",
        f"Nodes: {result.node_count}",
        f"Edges: {result.edge_count}",
        "Node types:",
    ]
    if result.node_types:
        for node_type, count in sorted(result.node_types.items()):
            lines.append(f"- {node_type}: {count}")
    else:
        lines.append("- None")

    lines.append("Top hubs:")
    lines.extend([f"- {label}: {degree} edges" for label, degree in result.top_hubs] or ["- None"])
    lines.append("Orphans:")
    lines.extend([f"- {label}" for label in result.orphans] or ["- None"])
    lines.append("Warnings:")
    lines.extend([f"- {warning}" for warning in result.warnings] or ["- None"])
    return "\n".join(lines)
