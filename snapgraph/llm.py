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
            return "空内容。"
        first = lines[0]
        return first[:220]

    def key_details(self, text: str) -> list[str]:
        lines = _meaningful_lines(text)
        details = lines[:3]
        return details or ["未提取到关键细节。"]

    def infer_why_saved(self, title: str, text: str) -> str:
        summary = self.summarize(text)
        return (
            "AI-inferred: 这份材料可能被保存下来，是因为它有助于之后重新理解"
            f"“{title}”。证据提示：{summary}"
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
        return [f"之后再决定如何使用这份材料：{summary[:120]}"]

    def future_recall_questions(self, title: str, text: str) -> list[str]:
        return [
            f"保存“{title}”时，它为什么重要？",
            f"“{title}”和我当前的项目或问题有什么关系？",
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
            f"[图片 {image_path.name}：MockLLM 无法读取视觉内容。"
            "请使用支持视觉能力的 LLM provider。]"
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
            f"{context.get('space_name', '默认空间')})"
            for i, context in enumerate(contexts, start=1)
        ]
        graph_path_lines = graph_paths or ["未找到图路径。"]
        project = primary.get("related_project") or "一个尚未完全明确的项目或问题"
        next_action = (
            open_loops[0]
            if open_loops
            else f"回看 {primary.get('source_page', '')}，确认这条保存理由现在是否仍然成立。"
        )
        user_lines = [
            f"- `{context.get('title', '')}`：{context.get('why_saved', '')} ({context.get('why_saved_status', '')})"
            for context in contexts
            if context.get("why_saved_status") == "user-stated"
        ] or [
            f"- `{primary.get('title', '')}`：{primary.get('why_saved', '')} ({primary.get('why_saved_status', '')})"
        ]
        return "\n".join(
            [
                "# 回答",
                "## 找回的原话",
                *user_lines[:3],
                "",
                "## 相关材料",
                *evidence_lines,
                "",
                "## 连接路径",
                "```text",
                *graph_path_lines,
                "```",
                "",
                "## AI 探索回应",
                (
                    f"我会把“{question}”当成 `{project}` 里的记忆恢复问题，而不是普通搜索。"
                    "先找回当时为什么在乎它，再看这些材料共同改变了哪个判断。"
                    f"这段回复基于图谱证据推进，不等同于用户原话；当前证据状态是：{status_summary}。"
                ),
                "",
                "## 涌现洞见",
                (
                    f"这条线索最可能连向 `{project}`。"
                    f"状态分布：{status_summary}。先沿用户原话继续追问，比从泛泛材料摘要开始更可靠。"
                ),
                "",
                "## 下一步",
                next_action,
            ]
        )


def _template_no_answer() -> str:
    return "\n".join(
        [
            "# 回答",
            "## 找回的原话",
            "低置信度：我没有找到匹配的 wiki 页面或图谱路径。"
            "在缺少证据时，我不会推断保存原因。",
            "",
            "## 相关材料",
            "无。",
            "",
            "## 连接路径",
            "```text",
            "无。",
            "```",
            "",
            "## AI 探索回应",
            "没有可靠证据时，我不会生成泛化回应。先补充材料或换一个更贴近旧材料的线索。",
            "",
            "## 涌现洞见",
            "无可靠证据时不生成洞见。",
            "",
            "## 下一步",
            "先收集相关材料，或换一个更接近当时材料、项目、判断的线索再问。",
        ]
    )


def _meaningful_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            lines.append(cleaned)
    return lines
