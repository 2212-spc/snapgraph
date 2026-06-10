from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any

from .answer import ANSWER_AI_EXPLORATION, ANSWER_CONCLUSION, ANSWER_NEXT
from .models import AnswerResult, RetrievedContext, RetrievalResult


def build_recall_result_projection(
    result: AnswerResult,
    provider_metadata: dict | None = None,
    space_id: str = "all",
) -> dict:
    """Create the structured Recall Result 2.0 payload from existing answer data."""
    metadata = provider_metadata or {}
    return {
        "judgment": judgment_from_answer_text(result.text, result.question, result.retrieval, metadata),
        "evidence_ladder": evidence_ladder_from_retrieval(result.retrieval),
        "trust_debt": trust_debt_from_retrieval(result.retrieval, metadata),
        "actions": action_cards_from_retrieval(result.retrieval, result.question, space_id),
        "write_back_preview": write_back_preview(result),
    }


def judgment_from_answer_text(
    text: str,
    question: str,
    retrieval: RetrievalResult,
    provider_metadata: dict | None = None,
) -> dict:
    summary = _section_text(text, ANSWER_CONCLUSION) or _section_text(text, ANSWER_AI_EXPLORATION)
    summary = _compact(summary) or _fallback_judgment(question, retrieval)
    return {
        "title": "Recovered judgment" if retrieval.contexts else "No reliable local judgment yet",
        "summary": summary,
        "confidence_label": _confidence_label(retrieval, provider_metadata or {}),
        "source": "answer" if summary else "fallback",
        "space_id": retrieval.contexts[0].graph_space_id if retrieval.contexts else "",
        "space_name": retrieval.contexts[0].space_name if retrieval.contexts else "",
    }


def evidence_ladder_from_retrieval(retrieval: RetrievalResult) -> list[dict]:
    ladder: list[dict] = []
    for context in retrieval.contexts:
        ladder.append(_context_evidence_card(context))
    for index, path in enumerate(retrieval.graph_paths[:6], start=1):
        cleaned = _compact(path, limit=180)
        if not cleaned:
            continue
        ladder.append(
            {
                "id": f"graph:{index}",
                "kind": "graph_path",
                "tone": "graph",
                "title": f"Evidence path {index}",
                "body": cleaned,
                "source_id": "",
                "space_name": "",
                "review_status": "",
                "metadata": {"path": path},
            }
        )
    return ladder


def trust_debt_from_retrieval(retrieval: RetrievalResult, provider_metadata: dict | None = None) -> dict:
    metadata = provider_metadata or {}
    items: list[dict] = []
    if not retrieval.contexts:
        items.append(
            {
                "id": "no-local-evidence",
                "label": "No local evidence",
                "detail": "SnapGraph did not find a saved source that can safely support this answer.",
                "severity": "high",
            }
        )
    if retrieval.diagnostics.ai_inferred_contexts:
        items.append(
            {
                "id": "ai-inferred-context",
                "label": "AI-inferred context needs review",
                "detail": f"{retrieval.diagnostics.ai_inferred_contexts} recalled context item(s) are AI-inferred rather than user-stated.",
                "severity": "medium",
            }
        )
    if retrieval.contexts and not retrieval.graph_paths:
        items.append(
            {
                "id": "missing-graph-path",
                "label": "No graph path",
                "detail": "The answer has source evidence but no visible graph path connecting the judgment.",
                "severity": "medium",
            }
        )
    if retrieval.diagnostics.graph_expansion_truncated:
        items.append(
            {
                "id": "truncated-graph-expansion",
                "label": "Graph expansion was truncated",
                "detail": "SnapGraph stopped expanding the graph early, so some nearby evidence may be missing.",
                "severity": "medium",
            }
        )
    if metadata.get("fallback_used"):
        items.append(
            {
                "id": "provider-fallback",
                "label": "Provider fallback",
                "detail": metadata.get("provider_error") or "The configured model was unavailable, so SnapGraph kept the answer local.",
                "severity": "medium",
            }
        )
    level = "low"
    if any(item["severity"] == "high" for item in items):
        level = "high"
    elif items:
        level = "medium"
    return {
        "level": level,
        "items": items,
        "summary": _trust_debt_summary(level, items),
    }


def action_cards_from_retrieval(retrieval: RetrievalResult, question: str, space_id: str = "all") -> list[dict]:
    if not retrieval.contexts:
        return [
            {
                "id": "collect-more-evidence",
                "kind": "collect",
                "label": "Collect supporting material",
                "detail": "Add a source or ask with a more specific old project, decision, or saved reason.",
                "question": "",
                "source_id": "",
                "space_id": space_id,
            }
        ]

    primary = retrieval.contexts[0]
    actions = [
        {
            "id": "ask-primary",
            "kind": "ask",
            "label": "Ask from strongest evidence",
            "detail": f"Continue from {primary.title}.",
            "question": _follow_up_question(question, primary),
            "source_id": primary.source_id,
            "space_id": primary.graph_space_id or space_id,
        }
    ]
    ai_context = next((context for context in retrieval.contexts if context.why_saved_status == "AI-inferred"), None)
    if ai_context:
        actions.append(
            {
                "id": "review-ai-inference",
                "kind": "review",
                "label": "Review AI-inferred context",
                "detail": f"Check whether {ai_context.title} really reflects your intent.",
                "question": "",
                "source_id": ai_context.source_id,
                "space_id": ai_context.graph_space_id or space_id,
            }
        )
    open_loop = _first_open_loop(retrieval)
    if open_loop:
        actions.append(
            {
                "id": "continue-open-loop",
                "kind": "open_loop",
                "label": "Continue open loop",
                "detail": _compact(open_loop, limit=120),
                "question": _open_loop_question(open_loop),
                "source_id": primary.source_id,
                "space_id": primary.graph_space_id or space_id,
            }
        )
    actions.append(
        {
            "id": "save-answer",
            "kind": "save",
            "label": "Save this answer",
            "detail": "Write the recovered judgment and evidence back into the wiki.",
            "question": question,
            "source_id": primary.source_id,
            "space_id": primary.graph_space_id or space_id,
        }
    )
    return actions


def write_back_preview(result: AnswerResult) -> dict:
    source_ids = [context.source_id for context in result.retrieval.contexts]
    next_step = _section_text(result.text, ANSWER_NEXT) or _first_open_loop(result.retrieval)
    return {
        "judgment": _compact(_section_text(result.text, ANSWER_CONCLUSION) or result.text, limit=220),
        "source_ids": source_ids,
        "next_step": _compact(next_step, limit=180),
        "graph_paths": result.retrieval.graph_paths[:6],
        "diagnostics": asdict(result.retrieval.diagnostics),
    }


def _context_evidence_card(context: RetrievedContext) -> dict:
    if context.why_saved_status == "user-stated":
        kind = "user_anchor"
        tone = "trusted"
        title = f"User-stated anchor: {context.title}"
    elif context.why_saved_status == "AI-inferred":
        kind = "ai_inference"
        tone = "review"
        title = f"AI-inferred context: {context.title}"
    else:
        kind = "source"
        tone = "support"
        title = context.title
    return {
        "id": f"source:{context.source_id}",
        "kind": kind,
        "tone": tone,
        "title": title,
        "body": _compact(context.why_saved or context.source_excerpt, limit=180),
        "source_id": context.source_id,
        "space_name": context.space_name,
        "review_status": "",
        "metadata": {
            "why_saved_status": context.why_saved_status,
            "related_project": context.related_project or "",
            "open_loops": context.open_loops,
            "future_recall_questions": context.future_recall_questions,
            "source_page": context.source_page,
        },
    }


def _confidence_label(retrieval: RetrievalResult, provider_metadata: dict) -> str:
    if not retrieval.contexts:
        return "weak"
    if retrieval.diagnostics.user_stated_contexts and retrieval.graph_paths and not provider_metadata.get("fallback_used"):
        return "strong"
    return "mixed"


def _trust_debt_summary(level: str, items: list[dict]) -> str:
    if not items:
        return "No major trust debt detected for this answer."
    if level == "high":
        return "This answer needs more local evidence before it should be treated as a recovered memory."
    return "This answer is usable, but the highlighted items should be reviewed before relying on it."


def _fallback_judgment(question: str, retrieval: RetrievalResult) -> str:
    if retrieval.contexts:
        titles = ", ".join(context.title for context in retrieval.contexts[:3])
        return f"SnapGraph recovered a judgment from {titles}."
    if question:
        return f"SnapGraph could not find reliable local evidence for: {question}"
    return "SnapGraph could not find reliable local evidence for this question."


def _follow_up_question(question: str, context: RetrievedContext) -> str:
    base = question.strip() or "this judgment"
    if context.why_saved_status == "user-stated":
        return f"Using {context.title}, what old judgment does this user-stated reason still support?"
    return f"Using {context.title}, what should I verify before trusting the answer about {base}?"


def _open_loop_question(open_loop: str) -> str:
    cleaned = _compact(open_loop, limit=120)
    return f"Continue this open loop with evidence: {cleaned}"


def _first_open_loop(retrieval: RetrievalResult) -> str:
    for context in retrieval.contexts:
        for open_loop in context.open_loops:
            cleaned = _compact(open_loop, limit=160)
            if cleaned and cleaned.lower() != "none":
                return cleaned
    return ""


def _section_text(text: str, heading: str) -> str:
    if heading not in text:
        return ""
    tail = text.split(heading, 1)[1].lstrip()
    next_index = tail.find("\n## ")
    if next_index >= 0:
        tail = tail[:next_index]
    return _clean_markdown(tail)


def _clean_markdown(text: str) -> str:
    cleaned = re.sub(r"```[\s\S]*?```", " ", text)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"^#+\s*", "", cleaned, flags=re.MULTILINE)
    return re.sub(r"\s+", " ", cleaned).strip()


def _compact(text: Any, limit: int = 260) -> str:
    cleaned = _clean_markdown(str(text or "")).replace("AI-inferred:", "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return f"{cleaned[:limit].rstrip()}..."

