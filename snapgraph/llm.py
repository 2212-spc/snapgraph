from __future__ import annotations

from pathlib import Path
from typing import Protocol


class LLMProvider(Protocol):
    def summarize(self, text: str) -> str: ...

    def key_details(self, text: str) -> list[str]: ...

    def infer_why_saved(self, title: str, text: str) -> str: ...

    def open_loops(self, text: str) -> list[str]: ...

    def future_recall_questions(self, title: str, text: str) -> list[str]: ...

    def related_project(self, text: str) -> str | None: ...

    def describe_image(self, image_path: Path) -> str: ...

    def synthesize_answer(
        self,
        question: str,
        contexts: list[dict],
        graph_paths: list[str],
    ) -> str: ...


class MockLLM(LLMProvider):
    """Deterministic source summarizer used until real providers are added."""

    def summarize(self, text: str) -> str:
        lines = _meaningful_lines(text)
        if not lines:
            return "Empty source."
        first = lines[0]
        return first[:220]

    def key_details(self, text: str) -> list[str]:
        lines = _meaningful_lines(text)
        details = lines[:3]
        return details or ["No key details found."]

    def infer_why_saved(self, title: str, text: str) -> str:
        summary = self.summarize(text)
        return (
            "AI-inferred: this source may have been saved because it could help "
            f"revisit '{title}' later. Evidence hint: {summary}"
        )

    def open_loops(self, text: str) -> list[str]:
        loops = []
        for line in _meaningful_lines(text):
            lowered = line.lower()
            if lowered.startswith(("open loop:", "todo:", "next:")):
                loops.append(line)
        if loops:
            return loops[:3]

        summary = self.summarize(text)
        return [f"Decide how to use this source later: {summary[:120]}"]

    def future_recall_questions(self, title: str, text: str) -> list[str]:
        return [
            f"Why did '{title}' matter when it was saved?",
            f"How does '{title}' connect to my current project or question?",
        ]

    def related_project(self, text: str) -> str | None:
        lowered = text.lower()
        if "llm wiki" in lowered:
            return "LLM Wiki"
        if "graphrag" in lowered or "graph rag" in lowered:
            return "GraphRAG"
        if "screenshot" in lowered or "截图" in text:
            return "Screenshot ingestion"
        if "on-device" in lowered or "端侧" in text:
            return "On-device multimodal memory"
        if "开题" in text or "thesis" in lowered:
            return "Thesis proposal"
        if "snapgraph" in lowered:
            return "SnapGraph"
        return None

    def describe_image(self, image_path: Path) -> str:
        return (
            f"[Image at {image_path.name}: visual content not available "
            "with MockLLM. Use a vision-enabled LLM provider.]"
        )

    def synthesize_answer(
        self,
        question: str,
        contexts: list[dict],
        graph_paths: list[str],
    ) -> str:
        if not contexts:
            return _template_no_answer()
        primary = contexts[0]
        status_counts: dict[str, int] = {}
        for context in contexts:
            status = context.get("why_saved_status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        status_summary = ", ".join(
            f"{s}: {c}" for s, c in sorted(status_counts.items())
        )
        open_loops = [
            loop
            for context in contexts
            for loop in context.get("open_loops", [])
            if loop != "None"
        ]
        evidence_lines = [
            f"{i}. `{context.get('title', '')}` - {context.get('source_page', '')} "
            f"(`{context.get('source_id', '')}`, {context.get('why_saved_status', '')}, "
            f"{context.get('space_name', 'Default')})"
            for i, context in enumerate(contexts, start=1)
        ]
        graph_path_lines = graph_paths or ["No graph path found."]
        project = primary.get("related_project") or "an unresolved project or question"
        next_action = (
            open_loops[0]
            if open_loops
            else f"Review {primary.get('source_page', '')} and decide whether its saved reason still matters."
        )
        return "\n".join(
            [
                "# Answer",
                "## Direct Answer",
                (
                    f"You likely saved `{primary.get('title', '')}` because it connected to {project}. "
                    f"The preserved reason is: {primary.get('why_saved', '')} "
                    f"The most concrete next step recovered from the wiki is: {next_action}"
                ),
                "",
                "## Recovered Cognitive Context",
                f"Status mix: {status_summary}.",
                *[
                    f"- `{context.get('title', '')}`: {context.get('why_saved', '')} "
                    f"({context.get('why_saved_status', '')})"
                    for context in contexts
                ],
                "",
                "## Evidence Sources",
                *evidence_lines,
                "",
                "## Graph Paths",
                "```text",
                *graph_path_lines,
                "```",
                "",
                "## Suggested Next Action",
                next_action,
            ]
        )


def _template_no_answer() -> str:
    return "\n".join(
        [
            "# Answer",
            "## Direct Answer",
            "Low confidence: I could not find matching wiki pages or graph paths. "
            "I will not infer a reason without evidence.",
            "",
            "## Evidence Sources",
            "None.",
            "",
            "## Graph Paths",
            "```text",
            "None.",
            "```",
            "",
            "## Suggested Next Action",
            "Ingest a relevant source or add a user-stated `--why` note before asking again.",
        ]
    )


def _meaningful_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            lines.append(cleaned)
    return lines
