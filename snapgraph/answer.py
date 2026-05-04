from __future__ import annotations

from .models import AnswerResult, QuestionPage, RetrievalResult
from .wiki import write_question_page
from .llm import LLMProvider
from .retrieval import retrieve_for_question
from .workspace import Workspace

ANSWER_DIRECT = "## 直接回答"
ANSWER_CONTEXT = "## 恢复出的认知上下文"
ANSWER_EVIDENCE = "## 证据来源"
ANSWER_PATHS = "## 图谱路径"
ANSWER_NEXT = "## 建议的下一步"
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
    if ANSWER_CONTEXT not in text:
        additions.extend(
            [
                ANSWER_CONTEXT,
                _contract_context_lines(retrieval),
                "",
            ]
        )
    if ANSWER_EVIDENCE not in text:
        additions.extend(
            [
                ANSWER_EVIDENCE,
                _contract_evidence_lines(retrieval),
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


def render_answer(retrieval: RetrievalResult) -> str:
    contexts = retrieval.contexts
    if not contexts:
        return _render_no_answer(retrieval)

    primary = contexts[0]
    status_counts = _status_counts(contexts)
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
            ANSWER_DIRECT,
            _direct_answer(primary, next_action),
            "",
            ANSWER_CONTEXT,
            f"状态分布：{_format_status_counts(status_counts)}。",
            *[
                (
                    f"- `{context.title}`：{context.why_saved} "
                    f"({context.why_saved_status})"
                )
                for context in contexts
            ],
            "",
            ANSWER_EVIDENCE,
            *evidence_lines,
            "",
            ANSWER_PATHS,
            "```text",
            *graph_path_lines,
            "```",
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
            ANSWER_DIRECT,
            "低置信度：我没有找到匹配的 wiki 页面或图谱路径。在缺少证据时，我不会推断保存原因。",
            "",
            ANSWER_CONTEXT,
            "无。",
            "",
            ANSWER_EVIDENCE,
            "无。",
            "",
            ANSWER_PATHS,
            "```text",
            "无。",
            "```",
            "",
            ANSWER_NEXT,
            "先导入相关材料，或补一条简短的 `--why` 提示，再重新提问。",
            "",
            ANSWER_DIAGNOSTICS,
            render_retrieval_diagnostics(retrieval),
        ]
    )


def _contract_context_lines(retrieval: RetrievalResult) -> str:
    if not retrieval.contexts:
        return "无。"
    return "\n".join(
        (
            f"- `{context.title}`：{context.why_saved} "
            f"({context.why_saved_status})"
        )
        for context in retrieval.contexts
    )


def _contract_evidence_lines(retrieval: RetrievalResult) -> str:
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
    return "先导入相关材料，或补一条简短的 `--why` 提示，再重新提问。"


def _status_counts(contexts) -> dict[str, int]:
    counts: dict[str, int] = {}
    for context in contexts:
        counts[context.why_saved_status] = counts.get(context.why_saved_status, 0) + 1
    return counts


def _format_status_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{status}: {count}" for status, count in sorted(counts.items()))


def _direct_answer(primary, next_action: str) -> str:
    project = primary.related_project or "一个尚未完全明确的项目或问题"
    return (
        f"你当时很可能保存了 `{primary.title}`，因为它和 {project} 有关。"
        f"当前保留下来的理由是：{primary.why_saved}。"
        f"从知识库里恢复出的最具体下一步是：{next_action}"
    )


def render_retrieval_diagnostics(retrieval: RetrievalResult) -> str:
    diagnostics = retrieval.diagnostics
    return "\n".join(
        [
            f"- 关键词命中：{diagnostics.keyword_hits}",
            f"- 图节点命中：{diagnostics.graph_node_hits}",
            f"- 扩展节点数：{diagnostics.expanded_nodes}",
            f"- 使用的材料页：{diagnostics.source_pages_used}",
            f"- 用户引导上下文：{diagnostics.user_stated_contexts}",
            f"- AI 推断上下文：{diagnostics.ai_inferred_contexts}",
            f"- 图扩展是否截断：{diagnostics.graph_expansion_truncated}",
            "- 候选理由：",
            *[f"  - {reason}" for reason in diagnostics.top_candidate_reasons],
        ]
    )
