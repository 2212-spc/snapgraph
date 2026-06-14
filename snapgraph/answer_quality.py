from __future__ import annotations

from collections import Counter
import re
from typing import Any

from .models import AnswerResult, RetrievedContext, RetrievalResult


def build_answer_quality_pack(
    result: AnswerResult,
    *,
    provider_metadata: dict[str, Any] | None = None,
    space_id: str | None = "all",
) -> dict[str, Any]:
    retrieval = result.retrieval
    text = str(result.text or "")
    provider = provider_metadata or {}
    sections = _section_inventory(text)
    evidence = _evidence_contract(retrieval, text, sections)
    groundedness = _groundedness_score(retrieval, text, evidence, provider)
    answer_shape = _answer_shape(text, sections, retrieval)
    risk_register = _risk_register(retrieval, text, evidence, answer_shape, provider)
    quality_label = _quality_label(groundedness, risk_register, evidence)
    return {
        "summary": {
            "question": result.question,
            "space_id": space_id or "all",
            "quality_label": quality_label,
            "groundedness_score": groundedness["score"],
            "confidence_label": groundedness["label"],
            "source_count": len(retrieval.contexts),
            "graph_path_count": len(retrieval.graph_paths),
            "risk_count": risk_register["risk_count"],
            "provider_used": provider.get("provider_used") or provider.get("configured_provider") or "unknown",
            "plain_language": _summary_copy(quality_label, groundedness, evidence, risk_register),
        },
        "evidence_contract": evidence,
        "answer_shape": answer_shape,
        "groundedness": groundedness,
        "risk_register": risk_register,
        "traceability": _traceability(result, evidence),
        "quality_ladder": _quality_ladder(retrieval, evidence, groundedness, risk_register),
        "repair_plan": _repair_plan(retrieval, evidence, answer_shape, risk_register),
        "display_policy": _display_policy(quality_label, risk_register),
    }


def _evidence_contract(
    retrieval: RetrievalResult,
    text: str,
    sections: dict[str, Any],
) -> dict[str, Any]:
    contexts = list(retrieval.contexts)
    context_titles = [_clean(context.title) for context in contexts]
    source_ids = [_clean(context.source_id) for context in contexts]
    mentioned_titles = [
        title
        for title in context_titles
        if title and title.lower() in text.lower()
    ]
    mentioned_source_ids = [
        source_id
        for source_id in source_ids
        if source_id and source_id.lower() in text.lower()
    ]
    boundary_counts = Counter(_clean(context.why_saved_status) or "unknown" for context in contexts)
    open_loop_count = sum(len(context.open_loops) for context in contexts)
    future_question_count = sum(len(context.future_recall_questions) for context in contexts)
    source_excerpt_count = sum(1 for context in contexts if _clean(context.source_excerpt))
    return {
        "has_source_context": bool(contexts),
        "has_graph_paths": bool(retrieval.graph_paths),
        "has_materials_section": sections["canonical"].get("materials", False),
        "has_paths_section": sections["canonical"].get("paths", False),
        "has_diagnostics_section": sections["canonical"].get("diagnostics", False),
        "source_count": len(contexts),
        "graph_path_count": len(retrieval.graph_paths),
        "user_stated_count": boundary_counts.get("user-stated", 0) + boundary_counts.get("user-guided", 0),
        "ai_inferred_count": boundary_counts.get("AI-inferred", 0),
        "unknown_boundary_count": boundary_counts.get("unknown", 0),
        "mentioned_title_count": len(mentioned_titles),
        "mentioned_source_id_count": len(mentioned_source_ids),
        "source_excerpt_count": source_excerpt_count,
        "open_loop_count": open_loop_count,
        "future_question_count": future_question_count,
        "coverage_percent": _coverage_percent(contexts, mentioned_titles, mentioned_source_ids),
        "boundary_profile": dict(boundary_counts),
        "source_mentions": _source_mentions(contexts, text),
        "plain_language": _evidence_copy(contexts, retrieval.graph_paths, boundary_counts),
    }


def _answer_shape(
    text: str,
    sections: dict[str, Any],
    retrieval: RetrievalResult,
) -> dict[str, Any]:
    words = _words(text)
    heading_count = len(sections["headings"])
    bullet_count = len(re.findall(r"(?m)^\s*[-*]\s+", text))
    code_block_count = text.count("```") // 2
    paragraph_count = len([block for block in re.split(r"\n\s*\n", text.strip()) if block.strip()])
    canonical = sections["canonical"]
    missing = [name for name, present in canonical.items() if not present]
    density = _density_label(len(words), heading_count, bullet_count, paragraph_count)
    return {
        "word_count": len(words),
        "heading_count": heading_count,
        "paragraph_count": paragraph_count,
        "bullet_count": bullet_count,
        "code_block_count": code_block_count,
        "section_coverage": canonical,
        "missing_sections": missing,
        "density_label": density,
        "has_clear_conclusion": canonical.get("conclusion", False),
        "has_next_step": canonical.get("next", False),
        "question_term_overlap": _question_overlap(retrieval.question, text),
        "plain_language": _shape_copy(density, missing),
    }


def _groundedness_score(
    retrieval: RetrievalResult,
    text: str,
    evidence: dict[str, Any],
    provider: dict[str, Any],
) -> dict[str, Any]:
    score = 0
    score += min(evidence["source_count"], 4) * 12
    score += min(evidence["graph_path_count"], 4) * 10
    score += min(evidence["user_stated_count"], 4) * 9
    score += min(evidence["mentioned_title_count"] + evidence["mentioned_source_id_count"], 6) * 5
    score += 8 if evidence["has_materials_section"] else 0
    score += 8 if evidence["has_paths_section"] else 0
    score += 5 if evidence["has_diagnostics_section"] else 0
    score += 10 if evidence["has_source_context"] else 0
    score += 12 if evidence["has_source_context"] and evidence["has_graph_paths"] else 0
    score += 12 if _section_inventory(text)["canonical"].get("conclusion") else 0
    score += 6 if evidence["source_excerpt_count"] else 0
    score += 4 if not provider.get("fallback_used") else -6
    score -= min(evidence["ai_inferred_count"], 4) * 4
    score -= 20 if not retrieval.contexts and _assertive_language(text) else 0
    score = max(0, min(100, score))
    return {
        "score": score,
        "label": _score_label(score),
        "components": {
            "sources": min(evidence["source_count"], 4) * 12,
            "graph_paths": min(evidence["graph_path_count"], 4) * 10,
            "user_stated": min(evidence["user_stated_count"], 4) * 9,
            "source_mentions": min(evidence["mentioned_title_count"] + evidence["mentioned_source_id_count"], 6) * 5,
            "contract_sections": (8 if evidence["has_materials_section"] else 0) + (8 if evidence["has_paths_section"] else 0),
        },
        "assertive_without_context": not retrieval.contexts and _assertive_language(text),
        "fallback_used": bool(provider.get("fallback_used")),
        "plain_language": _groundedness_copy(score),
    }


def _risk_register(
    retrieval: RetrievalResult,
    text: str,
    evidence: dict[str, Any],
    shape: dict[str, Any],
    provider: dict[str, Any],
) -> dict[str, Any]:
    risks: list[dict[str, Any]] = []
    if not retrieval.contexts:
        risks.append(_risk("no_context", "high", "No source context", "The answer cannot cite saved material.", 1))
    if retrieval.contexts and not retrieval.graph_paths:
        risks.append(_risk("missing_graph_path", "medium", "No graph path", "Source context exists but graph evidence is not visible.", 2))
    if evidence["ai_inferred_count"] and not evidence["user_stated_count"]:
        risks.append(_risk("ai_only_boundary", "medium", "AI-inferred boundary", "Saved reason depends on AI inference.", 3))
    if shape["missing_sections"]:
        risks.append(_risk("missing_contract_section", "low", "Missing answer section", ", ".join(shape["missing_sections"]), 4))
    if provider.get("fallback_used"):
        risks.append(_risk("provider_fallback", "medium", "Provider fallback", str(provider.get("provider_error") or "LLM provider fallback was used."), 5))
    if retrieval.diagnostics.graph_expansion_truncated:
        risks.append(_risk("truncated_graph", "medium", "Graph expansion truncated", "Nearby evidence may be missing.", 6))
    if _contains_overclaim(text) and evidence["source_count"] <= 1:
        risks.append(_risk("possible_overclaim", "medium", "Possible overclaim", "Strong language appears with limited evidence.", 7))
    risks.sort(key=lambda item: (item["priority"], item["id"]))
    return {
        "risk_count": len(risks),
        "highest_severity": _highest_severity(risks),
        "risks": risks[:12],
        "safe_to_write_back": not any(risk["severity"] in {"critical", "high"} for risk in risks),
        "plain_language": _risk_copy(risks),
    }


def _traceability(result: AnswerResult, evidence: dict[str, Any]) -> dict[str, Any]:
    context_rows = []
    for context in result.retrieval.contexts:
        context_rows.append(
            {
                "source_id": context.source_id,
                "title": context.title,
                "source_page": context.source_page,
                "space_id": context.graph_space_id,
                "space_name": context.space_name,
                "why_saved_status": context.why_saved_status,
                "has_excerpt": bool(_clean(context.source_excerpt)),
                "open_loop_count": len(context.open_loops),
                "future_question_count": len(context.future_recall_questions),
                "mentioned_in_answer": _clean(context.title).lower() in result.text.lower()
                or _clean(context.source_id).lower() in result.text.lower(),
            }
        )
    return {
        "contexts": context_rows[:12],
        "graph_paths": result.retrieval.graph_paths[:8],
        "traceability_label": _traceability_label(evidence),
        "writeback_guardrail": _writeback_guardrail(evidence),
    }


def _quality_ladder(
    retrieval: RetrievalResult,
    evidence: dict[str, Any],
    groundedness: dict[str, Any],
    risk_register: dict[str, Any],
) -> list[dict[str, Any]]:
    ladder = [
        _ladder("source", "Source evidence", evidence["source_count"], bool(retrieval.contexts), 1),
        _ladder("graph", "Graph paths", evidence["graph_path_count"], bool(retrieval.graph_paths), 2),
        _ladder("boundary", "User boundary", evidence["user_stated_count"], evidence["user_stated_count"] > 0, 3),
        _ladder("coverage", "Answer mentions evidence", evidence["coverage_percent"], evidence["coverage_percent"] >= 50, 4),
        _ladder("risk", "Risk review", risk_register["risk_count"], risk_register["highest_severity"] not in {"critical", "high"}, 5),
    ]
    for item in ladder:
        item["score_label"] = groundedness["label"]
    return ladder


def _repair_plan(
    retrieval: RetrievalResult,
    evidence: dict[str, Any],
    shape: dict[str, Any],
    risk_register: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not retrieval.contexts:
        actions.append(_action("collect_evidence", "Collect source evidence", "Add or select saved material before trusting this answer.", 1))
    if retrieval.contexts and not retrieval.graph_paths:
        actions.append(_action("recover_graph_path", "Recover graph path", "Use source titles or project names to expose evidence routes.", 2))
    if evidence["ai_inferred_count"] and not evidence["user_stated_count"]:
        actions.append(_action("review_boundary", "Review AI-inferred reason", "Confirm or rewrite the saved reason before write-back.", 3))
    if shape["missing_sections"]:
        actions.append(_action("restore_sections", "Restore answer contract", f"Missing: {', '.join(shape['missing_sections'])}.", 4))
    if risk_register["highest_severity"] in {"critical", "high"}:
        actions.append(_action("hold_writeback", "Hold write-back", "Resolve high-severity quality risks first.", 5))
    if not actions:
        actions.append(_action("reuse_answer", "Reuse answer", "Answer is grounded enough for recall and possible write-back.", 1))
    return actions[:6]


def _display_policy(quality_label: str, risk_register: dict[str, Any]) -> dict[str, Any]:
    risk_count = int(risk_register.get("risk_count") or 0)
    if quality_label in {"strong", "usable"} and risk_count <= 1:
        max_reasons = 3
    elif risk_count <= 3:
        max_reasons = 4
    else:
        max_reasons = 5
    return {
        "show_quality_badge": True,
        "collapse_diagnostics": True,
        "collapse_source_table": True,
        "max_visible_reasons": max_reasons,
        "max_visible_risks": min(4, max(1, risk_count)),
        "reason": "Quality evidence is useful, but recall results should keep the answer readable first.",
    }


def _section_inventory(text: str) -> dict[str, Any]:
    headings = re.findall(r"(?m)^#{1,4}\s+(.+?)\s*$", text)
    normalized = [_normalize_heading(heading) for heading in headings]
    canonical = {
        "conclusion": _has_any(normalized, {"conclusion", "结论", "回答"}),
        "original": _has_any(normalized, {"original", "原话", "找回"}),
        "materials": _has_any(normalized, {"materials", "相关材料", "source", "sources"}),
        "paths": _has_any(normalized, {"paths", "连接路径", "graph", "图谱"}),
        "next": _has_any(normalized, {"next", "下一步"}),
        "diagnostics": _has_any(normalized, {"diagnostics", "诊断", "检索"}),
    }
    return {
        "headings": headings,
        "normalized": normalized,
        "canonical": canonical,
    }


def _source_mentions(contexts: list[RetrievedContext], text: str) -> list[dict[str, Any]]:
    lowered = text.lower()
    rows = []
    for context in contexts:
        title = _clean(context.title)
        source_id = _clean(context.source_id)
        rows.append(
            {
                "source_id": source_id,
                "title": title,
                "title_mentioned": bool(title and title.lower() in lowered),
                "source_id_mentioned": bool(source_id and source_id.lower() in lowered),
                "boundary": context.why_saved_status,
                "space_id": context.graph_space_id,
            }
        )
    return rows[:12]


def _coverage_percent(contexts: list[RetrievedContext], mentioned_titles: list[str], mentioned_source_ids: list[str]) -> int:
    if not contexts:
        return 0
    mentioned = len(set(mentioned_titles + mentioned_source_ids))
    return round(min(len(contexts), mentioned) / len(contexts) * 100)


def _quality_label(groundedness: dict[str, Any], risk_register: dict[str, Any], evidence: dict[str, Any]) -> str:
    score = int(groundedness.get("score") or 0)
    highest = risk_register.get("highest_severity", "none")
    if not evidence["has_source_context"]:
        return "unsupported"
    if highest in {"critical", "high"} and score < 60:
        return "thin"
    if score >= 78 and highest not in {"critical", "high"}:
        return "strong"
    if score >= 52:
        return "usable"
    return "thin"


def _score_label(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 55:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def _traceability_label(evidence: dict[str, Any]) -> str:
    if not evidence["source_count"]:
        return "none"
    if evidence["has_graph_paths"] and evidence["user_stated_count"]:
        return "auditable"
    if evidence["has_graph_paths"] or evidence["user_stated_count"]:
        return "traceable"
    return "thin"


def _writeback_guardrail(evidence: dict[str, Any]) -> dict[str, Any]:
    allowed = bool(evidence["has_source_context"] and (evidence["has_graph_paths"] or evidence["user_stated_count"]))
    return {
        "can_write_back": allowed,
        "requires_user_review": evidence["ai_inferred_count"] > evidence["user_stated_count"],
        "reason": "Source evidence and either graph path or user boundary are present." if allowed else "More evidence is needed before write-back.",
    }


def _ladder(step_id: str, label: str, value: int, passed: bool, priority: int) -> dict[str, Any]:
    return {
        "id": step_id,
        "label": label,
        "value": value,
        "passed": passed,
        "priority": priority,
    }


def _risk(risk_id: str, severity: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": risk_id,
        "severity": severity,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


def _action(action_id: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": action_id,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


def _highest_severity(risks: list[dict[str, Any]]) -> str:
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    if not risks:
        return "none"
    return min((risk["severity"] for risk in risks), key=lambda severity: order.get(severity, 9))


def _density_label(word_count: int, heading_count: int, bullet_count: int, paragraph_count: int) -> str:
    if word_count > 900 or paragraph_count > 12:
        return "heavy"
    if word_count > 450 or heading_count > 8:
        return "medium"
    if bullet_count > 12:
        return "scannable"
    return "compact"


def _question_overlap(question: str, text: str) -> dict[str, Any]:
    question_terms = set(_important_terms(question))
    answer_terms = set(_important_terms(text))
    overlap = sorted(question_terms & answer_terms)
    percent = 0 if not question_terms else round(len(overlap) / len(question_terms) * 100)
    return {
        "terms": overlap[:12],
        "percent": percent,
        "label": "aligned" if percent >= 35 else "loose",
    }


def _contains_overclaim(text: str) -> bool:
    lowered = text.lower()
    terms = ["always", "never", "guarantee", "certainly", "must", "必然", "一定", "完全"]
    return any(term in lowered for term in terms)


def _assertive_language(text: str) -> bool:
    lowered = text.lower()
    terms = ["therefore", "clearly", "must", "should", "证明", "说明", "一定", "显然"]
    return any(term in lowered for term in terms)


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_\\-]+|[\u4e00-\u9fff]", text)


def _important_terms(text: str) -> list[str]:
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", text)
        if word.lower() not in _STOP_WORDS
    ]
    return words[:60]


def _normalize_heading(heading: str) -> str:
    cleaned = re.sub(r"[`*_#：:]", "", heading).strip().lower()
    return cleaned


def _has_any(values: list[str], needles: set[str]) -> bool:
    for value in values:
        if any(needle in value for needle in needles):
            return True
    return False


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _summary_copy(
    quality_label: str,
    groundedness: dict[str, Any],
    evidence: dict[str, Any],
    risk_register: dict[str, Any],
) -> str:
    if quality_label == "unsupported":
        return "No saved source evidence supports this answer yet."
    if risk_register["risk_count"]:
        return f"{groundedness['score']} quality score with {risk_register['risk_count']} review risk(s)."
    return f"{groundedness['score']} quality score with source evidence available."


def _evidence_copy(contexts: list[RetrievedContext], graph_paths: list[str], boundary_counts: Counter[str]) -> str:
    if not contexts:
        return "No source context was retrieved."
    if graph_paths:
        return f"{len(contexts)} source(s) and {len(graph_paths)} graph path(s) support the answer."
    if boundary_counts.get("user-stated", 0):
        return f"{len(contexts)} source(s) support the answer, including user-stated context."
    return f"{len(contexts)} source(s) support the answer, but graph paths are thin."


def _shape_copy(density: str, missing: list[str]) -> str:
    if missing:
        return f"Answer is {density}; missing sections: {', '.join(missing)}."
    return f"Answer is {density} and keeps the expected sections."


def _groundedness_copy(score: int) -> str:
    if score >= 80:
        return "Evidence support is strong enough for confident recall."
    if score >= 55:
        return "Evidence support is usable but should keep diagnostics available."
    if score:
        return "Evidence support is thin and should stay reviewable."
    return "No meaningful grounding was detected."


def _risk_copy(risks: list[dict[str, Any]]) -> str:
    if not risks:
        return "No major answer quality risk detected."
    top = risks[0]
    return f"{len(risks)} risk(s), starting with {top['label']}."


_STOP_WORDS = {
    "and",
    "are",
    "can",
    "does",
    "for",
    "from",
    "how",
    "into",
    "the",
    "this",
    "that",
    "what",
    "when",
    "where",
    "why",
    "with",
}
