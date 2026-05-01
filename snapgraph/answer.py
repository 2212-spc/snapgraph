from __future__ import annotations

from .models import AnswerResult, QuestionPage, RetrievalResult
from .wiki import write_question_page
from .llm import LLMProvider
from .retrieval import retrieve_for_question
from .workspace import Workspace


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
    if "## Recovered Cognitive Context" not in text:
        additions.extend(
            [
                "## Recovered Cognitive Context",
                _contract_context_lines(retrieval),
                "",
            ]
        )
    if "## Evidence Sources" not in text:
        additions.extend(
            [
                "## Evidence Sources",
                _contract_evidence_lines(retrieval),
                "",
            ]
        )
    if "## Graph Paths" not in text:
        graph_paths = retrieval.graph_paths or ["None."]
        additions.extend(
            [
                "## Graph Paths",
                "```text",
                *graph_paths,
                "```",
                "",
            ]
        )
    if "## Suggested Next Action" not in text:
        additions.extend(
            [
                "## Suggested Next Action",
                _contract_next_action(retrieval),
                "",
            ]
        )
    if not additions:
        return text
    return "\n".join([text.rstrip(), "", *additions]).rstrip()


def ensure_retrieval_diagnostics(text: str, retrieval: RetrievalResult) -> str:
    if "## Retrieval Diagnostics" in text:
        return text
    return "\n".join(
        [
            text.rstrip(),
            "",
            "## Retrieval Diagnostics",
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
    graph_path_lines = retrieval.graph_paths or ["No graph path found."]
    next_action = (
        open_loops[0]
        if open_loops
        else f"Review {primary.source_page} and decide whether its saved reason still matters."
    )

    return "\n".join(
        [
            "# Answer",
            "## Direct Answer",
            _direct_answer(primary, next_action),
            "",
            "## Recovered Cognitive Context",
            f"Status mix: {_format_status_counts(status_counts)}.",
            *[
                (
                    f"- `{context.title}`: {context.why_saved} "
                    f"({context.why_saved_status})"
                )
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
            "",
            "## Retrieval Diagnostics",
            render_retrieval_diagnostics(retrieval),
        ]
    )


def _render_no_answer(retrieval: RetrievalResult) -> str:
    return "\n".join(
        [
            "# Answer",
            "## Direct Answer",
            "Low confidence: I could not find matching wiki pages or graph paths. I will not infer a reason without evidence.",
            "",
            "## Recovered Cognitive Context",
            "None.",
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
            "",
            "## Retrieval Diagnostics",
            render_retrieval_diagnostics(retrieval),
        ]
    )


def _contract_context_lines(retrieval: RetrievalResult) -> str:
    if not retrieval.contexts:
        return "None."
    return "\n".join(
        (
            f"- `{context.title}`: {context.why_saved} "
            f"({context.why_saved_status})"
        )
        for context in retrieval.contexts
    )


def _contract_evidence_lines(retrieval: RetrievalResult) -> str:
    if not retrieval.contexts:
        return "None."
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
        return f"Review {retrieval.contexts[0].source_page} and confirm whether the recovered reason is still accurate."
    return "Ingest a relevant source or add a user-stated `--why` note before asking again."


def _status_counts(contexts) -> dict[str, int]:
    counts: dict[str, int] = {}
    for context in contexts:
        counts[context.why_saved_status] = counts.get(context.why_saved_status, 0) + 1
    return counts


def _format_status_counts(counts: dict[str, int]) -> str:
    return ", ".join(f"{status}: {count}" for status, count in sorted(counts.items()))


def _direct_answer(primary, next_action: str) -> str:
    project = primary.related_project or "an unresolved project or question"
    return (
        f"You likely saved `{primary.title}` because it connected to {project}. "
        f"The preserved reason is: {primary.why_saved} "
        f"The most concrete next step recovered from the wiki is: {next_action}"
    )


def render_retrieval_diagnostics(retrieval: RetrievalResult) -> str:
    diagnostics = retrieval.diagnostics
    return "\n".join(
        [
            f"- keyword hits: {diagnostics.keyword_hits}",
            f"- graph node hits: {diagnostics.graph_node_hits}",
            f"- expanded nodes: {diagnostics.expanded_nodes}",
            f"- source pages used: {diagnostics.source_pages_used}",
            f"- user-stated contexts: {diagnostics.user_stated_contexts}",
            f"- AI-inferred contexts: {diagnostics.ai_inferred_contexts}",
            f"- graph expansion truncated: {diagnostics.graph_expansion_truncated}",
            "- top candidate reasons:",
            *[f"  - {reason}" for reason in diagnostics.top_candidate_reasons],
        ]
    )
