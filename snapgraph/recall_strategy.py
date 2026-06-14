from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .models import RetrievedContext, RetrievalResult


def build_recall_strategy_pack(retrieval: RetrievalResult, *, space_id: str = "all") -> dict[str, Any]:
    """Explain how ready a recall answer is before the UI decides how much to show."""
    source_roles = _source_roles(retrieval)
    matrix = _evidence_matrix(retrieval, source_roles)
    failure_modes = _failure_modes(retrieval, matrix)
    readiness = _readiness(retrieval, matrix, failure_modes)
    query_plan = _query_plan(retrieval, readiness, failure_modes)
    return {
        "readiness": readiness,
        "evidence_matrix": matrix,
        "source_roles": source_roles,
        "query_plan": query_plan,
        "failure_modes": failure_modes,
        "space_context": {
            "space_id": space_id,
            "context_count": len(retrieval.contexts),
            "graph_path_count": len(retrieval.graph_paths),
            "pinned_contexts": retrieval.diagnostics.pinned_contexts,
        },
        "display_policy": _display_policy(readiness, failure_modes),
    }


def _readiness(
    retrieval: RetrievalResult,
    matrix: dict[str, Any],
    failure_modes: list[dict[str, Any]],
) -> dict[str, Any]:
    coverage = matrix["coverage"]
    score = 0
    score += min(coverage["source_count"], 5) * 14
    score += min(coverage["graph_paths"], 5) * 10
    score += coverage["user_stated"] * 24
    score += coverage["pinned_contexts"] * 8
    score += min(coverage["future_questions"], 4) * 3
    score -= coverage["ai_inferred"] * 4
    score -= len([item for item in failure_modes if item["severity"] == "high"]) * 24
    score -= len([item for item in failure_modes if item["severity"] == "medium"]) * 10
    score = max(0, min(100, score))
    if not retrieval.contexts:
        label = "needs_collection"
    elif coverage["ai_inferred"]:
        label = "review_first"
    elif any(item["id"] == "ai_inferred_primary" for item in failure_modes):
        label = "review_first"
    elif score >= 78:
        label = "ready"
    elif score >= 55:
        label = "usable"
    else:
        label = "thin"
    return {
        "score": score,
        "label": label,
        "can_answer_as_memory": label in {"ready", "usable", "review_first"} and bool(retrieval.contexts),
        "requires_user_review": label == "review_first" or any(item["requires_user"] for item in failure_modes),
        "short_reason": _readiness_reason(label, coverage, failure_modes),
        "confidence_inputs": {
            "sources": coverage["source_count"],
            "user_stated": coverage["user_stated"],
            "ai_inferred": coverage["ai_inferred"],
            "graph_paths": coverage["graph_paths"],
            "keyword_hits": retrieval.diagnostics.keyword_hits,
            "graph_node_hits": retrieval.diagnostics.graph_node_hits,
        },
    }


def _evidence_matrix(retrieval: RetrievalResult, source_roles: list[dict[str, Any]]) -> dict[str, Any]:
    contexts = retrieval.contexts
    relation_counts = Counter(_path_relation(path) for path in retrieval.graph_paths)
    project_counts = Counter((context.related_project or context.space_name or "unknown") for context in contexts)
    boundary_counts = Counter(context.why_saved_status for context in contexts)
    return {
        "coverage": {
            "source_count": len(contexts),
            "user_stated": sum(1 for context in contexts if context.why_saved_status in {"user-stated", "user-guided"}),
            "ai_inferred": sum(1 for context in contexts if context.why_saved_status == "AI-inferred"),
            "unknown": sum(1 for context in contexts if context.why_saved_status not in {"user-stated", "user-guided", "AI-inferred"}),
            "graph_paths": len(retrieval.graph_paths),
            "open_loops": sum(len([loop for loop in context.open_loops if loop and loop != "None"]) for context in contexts),
            "future_questions": sum(len([question for question in context.future_recall_questions if question and question != "None"]) for context in contexts),
            "pinned_contexts": retrieval.diagnostics.pinned_contexts,
        },
        "boundaries": dict(boundary_counts),
        "relations": dict(relation_counts),
        "projects": dict(project_counts),
        "role_counts": dict(Counter(role["role"] for role in source_roles)),
        "top_reasons": retrieval.diagnostics.top_candidate_reasons[:6],
    }


def _source_roles(retrieval: RetrievalResult) -> list[dict[str, Any]]:
    roles = []
    for index, context in enumerate(retrieval.contexts):
        role = _source_role(index, context)
        roles.append(
            {
                "source_id": context.source_id,
                "title": context.title,
                "role": role,
                "rank": index + 1,
                "why_saved_status": context.why_saved_status,
                "space_id": context.graph_space_id,
                "space_name": context.space_name,
                "open_loop_count": len([loop for loop in context.open_loops if loop and loop != "None"]),
                "future_question_count": len([question for question in context.future_recall_questions if question and question != "None"]),
                "excerpt_signal": _excerpt_signal(context),
                "use_in_answer": role in {"primary_anchor", "supporting_evidence", "current_batch_anchor"},
                "review_before_reuse": context.why_saved_status == "AI-inferred",
            }
        )
    return roles


def _failure_modes(retrieval: RetrievalResult, matrix: dict[str, Any]) -> list[dict[str, Any]]:
    coverage = matrix["coverage"]
    failures: list[dict[str, Any]] = []
    if not retrieval.contexts:
        failures.append(
            {
                "id": "no_local_evidence",
                "severity": "high",
                "requires_user": True,
                "label": "No local evidence",
                "repair": "Collect a source or ask with a more specific project/file name.",
            }
        )
    if retrieval.contexts and coverage["user_stated"] == 0:
        failures.append(
            {
                "id": "no_user_anchor",
                "severity": "medium",
                "requires_user": True,
                "label": "No user-stated anchor",
                "repair": "Review AI-inferred saved reasons before treating the answer as memory.",
            }
        )
    if retrieval.contexts and retrieval.contexts[0].why_saved_status == "AI-inferred":
        failures.append(
            {
                "id": "ai_inferred_primary",
                "severity": "medium",
                "requires_user": True,
                "label": "Primary source is AI-inferred",
                "repair": "Ask the user to confirm or rewrite the saved reason.",
            }
        )
    if retrieval.contexts and not retrieval.graph_paths:
        failures.append(
            {
                "id": "missing_graph_path",
                "severity": "medium",
                "requires_user": False,
                "label": "No graph path",
                "repair": "Use local source evidence but keep graph detail collapsed as unavailable.",
            }
        )
    if retrieval.diagnostics.graph_expansion_truncated:
        failures.append(
            {
                "id": "truncated_expansion",
                "severity": "medium",
                "requires_user": False,
                "label": "Graph expansion truncated",
                "repair": "Offer a follow-up query scoped to the strongest source.",
            }
        )
    if coverage["open_loops"] >= 3:
        failures.append(
            {
                "id": "many_open_loops",
                "severity": "low",
                "requires_user": False,
                "label": "Many open loops",
                "repair": "Show one next step and keep the rest collapsed.",
            }
        )
    return failures or [
        {
            "id": "none",
            "severity": "info",
            "requires_user": False,
            "label": "No major recall failure mode",
            "repair": "Keep source traceability visible and proceed.",
        }
    ]


def _query_plan(
    retrieval: RetrievalResult,
    readiness: dict[str, Any],
    failure_modes: list[dict[str, Any]],
) -> dict[str, Any]:
    primary = retrieval.contexts[0] if retrieval.contexts else None
    repair_ids = {item["id"] for item in failure_modes}
    rewrite_suggestions = []
    follow_up_questions = []
    if "no_local_evidence" in repair_ids:
        rewrite_suggestions.extend(_empty_retrieval_rewrites(retrieval.question))
    if primary:
        follow_up_questions.append(f"Open {primary.title} and verify the saved reason.")
        follow_up_questions.extend(_future_questions_from_contexts(retrieval.contexts))
    if "ai_inferred_primary" in repair_ids or "no_user_anchor" in repair_ids:
        rewrite_suggestions.append("Ask: which part of this saved reason did I actually write or confirm?")
    if "missing_graph_path" in repair_ids:
        rewrite_suggestions.append("Ask again with the exact project or source title to recover a graph path.")
    return {
        "intent": _query_intent(retrieval.question),
        "readiness_label": readiness["label"],
        "rewrite_suggestions": _dedupe_keep_order(rewrite_suggestions)[:5],
        "follow_up_questions": _dedupe_keep_order(follow_up_questions)[:5],
        "source_scope": [context.source_id for context in retrieval.contexts[:4]],
        "avoid": [
            "Do not present unsupported guesses as recovered memory.",
            "Do not hide AI-inferred context behind user-stated wording.",
        ],
    }


def _display_policy(readiness: dict[str, Any], failure_modes: list[dict[str, Any]]) -> dict[str, Any]:
    high_risk = any(item["severity"] == "high" for item in failure_modes)
    return {
        "show_summary_first": True,
        "default_visible_sources": 0 if readiness["label"] == "needs_collection" else 2,
        "collapse_graph_paths": readiness["label"] not in {"ready", "review_first"},
        "collapse_ai_inferred": True,
        "show_repair_prompt": high_risk or readiness["requires_user_review"],
        "reason": _display_reason(readiness["label"], high_risk),
    }


def _source_role(index: int, context: RetrievedContext) -> str:
    if index == 0 and context.why_saved_status in {"user-stated", "user-guided"}:
        return "primary_anchor"
    if index == 0:
        return "primary_candidate"
    if context.why_saved_status in {"user-stated", "user-guided"}:
        return "supporting_evidence"
    if context.why_saved_status == "AI-inferred":
        return "review_context"
    return "background_context"


def _excerpt_signal(context: RetrievedContext) -> str:
    text = context.source_excerpt or context.why_saved or context.title
    text = _compact(text, 120)
    if not text:
        return "No compact excerpt is available."
    return text


def _path_relation(path: str) -> str:
    if "triggered_thought" in path:
        return "triggered_thought"
    if "evidence_for" in path:
        return "evidence_for"
    if "belongs_to" in path:
        return "belongs_to"
    if "mentions" in path:
        return "mentions"
    if "follow_up" in path:
        return "follow_up"
    return "path"


def _readiness_reason(label: str, coverage: dict[str, int], failures: list[dict[str, Any]]) -> str:
    if label == "needs_collection":
        return "No saved source supports this question yet."
    if label == "review_first":
        return "Evidence exists, but AI-inferred context needs review before reuse."
    if label == "ready":
        return "User-stated anchors and graph paths are both available."
    if label == "usable":
        return "Local sources are available, but the answer should keep evidence visible."
    important = next((item for item in failures if item["severity"] != "info"), None)
    if important:
        return important["repair"]
    return f"{coverage['source_count']} source(s) were recovered."


def _empty_retrieval_rewrites(question: str) -> list[str]:
    terms = _key_terms(question)
    suggestions = [
        "Mention a concrete project, file, person, meeting, or saved reason.",
        "Ask what you were deciding, not only what the topic was.",
    ]
    if terms:
        suggestions.append(f"Try one of these anchors: {', '.join(terms[:4])}.")
    return suggestions


def _future_questions_from_contexts(contexts: list[RetrievedContext]) -> list[str]:
    questions = []
    for context in contexts:
        questions.extend(
            question
            for question in context.future_recall_questions
            if question and question != "None"
        )
        for loop in context.open_loops:
            if loop and loop != "None":
                questions.append(_open_loop_to_question(loop))
    return questions


def _open_loop_to_question(loop: str) -> str:
    cleaned = _compact(loop, 100)
    if cleaned.endswith("?") or cleaned.endswith("？"):
        return cleaned
    return f"Has this open loop changed: {cleaned}?"


def _query_intent(question: str) -> str:
    lowered = question.lower()
    if any(term in lowered for term in ["why", "为什么", "为啥"]):
        return "reason_recovery"
    if any(term in lowered for term in ["what", "什么", "哪些"]):
        return "fact_recovery"
    if any(term in lowered for term in ["next", "下一步", "todo"]):
        return "next_step"
    return "general_recall"


def _key_terms(question: str) -> list[str]:
    english = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", question)
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", question)
    terms = english + chinese
    stop = {"what", "why", "how", "the", "and", "that", "this"}
    return [term for term in terms if term.lower() not in stop]


def _display_reason(label: str, high_risk: bool) -> str:
    if label == "needs_collection":
        return "The user needs a repair prompt more than evidence detail."
    if high_risk:
        return "High-risk failure modes should be visible without expanding all details."
    return "The UI can stay compact because the strategy pack carries the deeper detail."


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        cleaned = _compact(value, 160)
        if cleaned and cleaned not in seen:
            output.append(cleaned)
            seen.add(cleaned)
    return output


def _compact(value: str, limit: int) -> str:
    cleaned = " ".join(str(value or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."
