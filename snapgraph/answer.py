from __future__ import annotations

import re

from .models import AnswerResult, QuestionPage, RetrievalResult
from .wiki import write_question_page
from .llm import LLMProvider
from .retrieval import retrieve_for_question
from .workspace import Workspace

ANSWER_ORIGINAL = "## 找回的原话"
ANSWER_MATERIALS = "## 相关材料"
ANSWER_PATHS = "## 连接路径"
ANSWER_INSIGHT = "## 涌现洞见"
ANSWER_NEXT = "## 下一步"
ANSWER_DIAGNOSTICS = "## 检索诊断"


def answer_question(
    workspace: Workspace,
    question: str,
    llm: LLMProvider | None = None,
    space_id: str | None = None,
    retrieval: RetrievalResult | None = None,
) -> AnswerResult:
    retrieval = retrieval or retrieve_for_question(workspace, question, space_id=space_id)
    if not retrieval.contexts:
        text = render_answer(retrieval)
    elif llm is not None:
        contexts_dicts = [
            {
                "source_id": context.source_id,
                "source_page": context.source_page,
                "title": context.title,
                "why_saved": context.why_saved,
                "why_saved_status": context.why_saved_status,
                "related_project": context.related_project,
                "open_loops": context.open_loops,
                "future_recall_questions": context.future_recall_questions,
                "graph_space_id": context.graph_space_id,
                "space_name": context.space_name,
                "source_excerpt": context.source_excerpt,
            }
            for context in retrieval.contexts
        ]
        text = llm.synthesize_answer(question, contexts_dicts, retrieval.graph_paths)
        text = ensure_answer_contract(text, retrieval)
    else:
        text = render_answer(retrieval)
    text = ensure_retrieval_diagnostics(text, retrieval)
    text = clean_answer_glyphs(text)
    return AnswerResult(
        question=question,
        text=text,
        retrieval=retrieval,
    )


def save_answer(workspace: Workspace, answer: AnswerResult) -> QuestionPage:
    return write_question_page(workspace, answer)


def ensure_answer_contract(text: str, retrieval: RetrievalResult) -> str:
    """Keep real provider answers auditable even when the model omits sections."""
    additions: list[str] = []
    if ANSWER_ORIGINAL not in text:
        additions.extend(
            [
                ANSWER_ORIGINAL,
                _contract_original_lines(retrieval),
                "",
            ]
        )
    if ANSWER_MATERIALS not in text:
        additions.extend(
            [
                ANSWER_MATERIALS,
                _contract_material_lines(retrieval),
                "",
            ]
        )
    if ANSWER_PATHS not in text:
        graph_paths = retrieval.graph_paths or ["无。"]
        additions.extend(
            [
                ANSWER_PATHS,
                "```text",
                *graph_paths,
                "```",
                "",
            ]
        )
    if ANSWER_INSIGHT not in text:
        additions.extend(
            [
                ANSWER_INSIGHT,
                _contract_insight(retrieval),
                "",
            ]
        )
    if ANSWER_NEXT not in text:
        additions.extend(
            [
                ANSWER_NEXT,
                _contract_next_action(retrieval),
                "",
            ]
        )
    if not additions:
        return text
    return "\n".join([text.rstrip(), "", *additions]).rstrip()


def ensure_retrieval_diagnostics(text: str, retrieval: RetrievalResult) -> str:
    if ANSWER_DIAGNOSTICS in text:
        return text
    return "\n".join(
        [
            text.rstrip(),
            "",
            ANSWER_DIAGNOSTICS,
            render_retrieval_diagnostics(retrieval),
        ]
    )


def clean_answer_glyphs(text: str) -> str:
    """Keep provider prose inside SnapGraph's quiet product voice."""
    cleaned = re.sub(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]", "", text)
    return re.sub(r"(?m)^[ \t]+(?=\S)", "", cleaned)


def render_answer(retrieval: RetrievalResult) -> str:
    contexts = retrieval.contexts
    if not contexts:
        return _render_no_answer(retrieval)

    primary = contexts[0]
    open_loops = [
        open_loop
        for context in contexts
        for open_loop in context.open_loops
        if open_loop != "None"
    ]
    evidence_lines = [
        (
                f"{index}. `{context.title}` - {context.source_page} "
                f"(`{context.source_id}`, {context.why_saved_status}, {context.space_name})"
        )
        for index, context in enumerate(contexts, start=1)
    ]
    graph_path_lines = retrieval.graph_paths or ["未找到图路径。"]
    next_action = (
        open_loops[0]
        if open_loops
        else f"Review {primary.source_page} and decide whether its saved reason still matters."
    )

    return "\n".join(
        [
            "# 回答",
            ANSWER_ORIGINAL,
            _contract_original_lines(retrieval),
            "",
            ANSWER_MATERIALS,
            *evidence_lines,
            "",
            ANSWER_PATHS,
            "```text",
            *graph_path_lines,
            "```",
            "",
            ANSWER_INSIGHT,
            _contract_insight(retrieval),
            "",
            ANSWER_NEXT,
            next_action,
            "",
            ANSWER_DIAGNOSTICS,
            render_retrieval_diagnostics(retrieval),
        ]
    )


def _render_no_answer(retrieval: RetrievalResult) -> str:
    return "\n".join(
        [
            "# 回答",
            ANSWER_ORIGINAL,
            "低置信度：没有找到匹配的用户原话或图谱路径。在缺少证据时，我不会推断保存原因。",
            "",
            ANSWER_MATERIALS,
            "无。",
            "",
            ANSWER_PATHS,
            "```text",
            "无。",
            "```",
            "",
            ANSWER_INSIGHT,
            "无可靠证据时不生成洞见。",
            "",
            ANSWER_NEXT,
            "先收集相关材料，或换一个更接近当时材料、项目、判断的线索再问。",
            "",
            ANSWER_DIAGNOSTICS,
            render_retrieval_diagnostics(retrieval),
        ]
    )


def _contract_original_lines(retrieval: RetrievalResult) -> str:
    if not retrieval.contexts:
        return "无。"
    user_contexts = [
        context for context in retrieval.contexts
        if context.why_saved_status == "user-stated" and context.why_saved
    ]
    contexts = user_contexts or retrieval.contexts[:1]
    return "\n".join(
        (
            f"- `{context.title}`：{context.why_saved} ({context.why_saved_status})"
        )
        for context in contexts[:3]
    )


def _contract_material_lines(retrieval: RetrievalResult) -> str:
    if not retrieval.contexts:
        return "无。"
    return "\n".join(
        (
            f"{index}. `{context.title}` - {context.source_page} "
            f"(`{context.source_id}`, {context.why_saved_status}, {context.space_name})"
        )
        for index, context in enumerate(retrieval.contexts, start=1)
    )


def _contract_next_action(retrieval: RetrievalResult) -> str:
    for context in retrieval.contexts:
        for open_loop in context.open_loops:
            if open_loop and open_loop != "None":
                return open_loop
    if retrieval.contexts:
        return f"回看 {retrieval.contexts[0].source_page}，确认恢复出的保存理由是否仍然准确。"
    return "先收集相关材料，或换一个更接近当时材料、项目、判断的线索再问。"


def _contract_insight(retrieval: RetrievalResult) -> str:
    if not retrieval.contexts:
        return "无。"
    primary = retrieval.contexts[0]
    project = primary.related_project or primary.space_name or "当前问题"
    user_stated = sum(1 for context in retrieval.contexts if context.why_saved_status == "user-stated")
    return (
        f"这条线索最可能连向 `{project}`。"
        f"当前有 {user_stated} 条用户原话可作为高信任证据；"
        "先沿这些原话继续追问，比从泛泛材料摘要开始更可靠。"
    )


def render_retrieval_diagnostics(retrieval: RetrievalResult) -> str:
    diagnostics = retrieval.diagnostics
    return "\n".join(
        [
            f"- 关键词命中：{diagnostics.keyword_hits}",
            f"- 图节点命中：{diagnostics.graph_node_hits}",
            f"- 扩展节点数：{diagnostics.expanded_nodes}",
            f"- 使用的材料页：{diagnostics.source_pages_used}",
            f"- 用户确认上下文：{diagnostics.user_stated_contexts}",
            f"- AI 推断上下文：{diagnostics.ai_inferred_contexts}",
            f"- 图扩展是否截断：{diagnostics.graph_expansion_truncated}",
            "- 候选理由：",
            *[f"  - {reason}" for reason in diagnostics.top_candidate_reasons],
        ]
    )
