from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any

from .trust_engine_catalog import (
    first_decision_impact,
    pressure_guardrails_for_surfaces,
    report_sections_by_priority,
    review_path_templates_for_stage,
    rules_for_match,
    session_mode_definition,
)

TRUST_ACTIONS = ("confirmed", "rewritten", "rejected", "deferred")
RISK_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
STATUS_ORDER = {"unreviewed": 0, "deferred": 1, "rewritten": 2, "confirmed": 3, "rejected": 4}


def build_item_analysis(
    item: dict[str, Any],
    *,
    evidence_paths: list[dict[str, Any]] | None = None,
    history: list[dict[str, Any]] | None = None,
    open_loops: list[dict[str, Any]] | None = None,
    peers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    paths = evidence_paths or []
    history_rows = history or []
    loop_rows = open_loops or []
    peer_rows = peers or []
    signal_profile = _signal_profile(item, paths, history_rows, loop_rows)
    rule_matches = _matched_rules(signal_profile)
    trust_score = _trust_score(item, signal_profile, rule_matches)
    evidence_compression = _evidence_compression(item, paths, signal_profile)
    decision_preview = _decision_preview(item, signal_profile, evidence_compression)
    review_path = _review_path(item, signal_profile, evidence_compression, history_rows)
    session_fit = _session_fit(item, peer_rows, signal_profile)
    impact_map = _impact_map(item, signal_profile, loop_rows)
    conflict_review = _conflict_review(item, signal_profile, paths, history_rows)
    completeness = _context_completeness(item, signal_profile, evidence_compression)
    quiet_summary = _quiet_summary(item, trust_score, evidence_compression, conflict_review)
    pressure = _attention_budget(item, signal_profile, evidence_compression, history_rows, loop_rows)
    return {
        "source_id": item.get("source_id", ""),
        "trust_score": trust_score,
        "signal_profile": signal_profile,
        "matched_rules": [_rule_payload(rule) for rule in rule_matches[:12]],
        "evidence_compression": evidence_compression,
        "decision_preview": decision_preview,
        "review_path": review_path,
        "session_fit": session_fit,
        "impact_map": impact_map,
        "conflict_review": conflict_review,
        "context_completeness": completeness,
        "attention_budget": pressure,
        "quiet_summary": quiet_summary,
        "recommended_microcopy": _recommended_microcopy(item, signal_profile, trust_score),
        "hidden_depth_count": _hidden_depth_count(paths, history_rows, loop_rows, rule_matches),
    }


def build_session_payload(
    items: list[dict[str, Any]],
    summary: dict[str, Any],
    filters: dict[str, Any] | None = None,
    mode: str = "high-risk",
) -> dict[str, Any]:
    mode_spec = session_mode_definition(mode)
    ranked = sorted(items, key=_session_sort_key)
    recommended = [item for item in ranked if _matches_mode(item, mode_spec)]
    if not recommended:
        recommended = ranked
    next_item = recommended[0] if recommended else None
    metrics = _session_metrics(items, recommended, summary)
    guardrails = pressure_guardrails_for_surfaces(["session", "queue", "detail", "report"])
    mode_options = []
    for mode_id in ["high-risk", "quick-clear", "open-loops", "all", "deferred", "ai-only", "trusted", "cleanup"]:
        spec = session_mode_definition(mode_id)
        count = sum(1 for item in items if _matches_mode(item, spec))
        mode_options.append({
            "mode": spec.mode_id,
            "label": spec.label,
            "intent": spec.intent,
            "count": count,
            "quiet_rule": spec.quiet_rule,
        })
    return {
        "mode": mode_spec.mode_id,
        "label": mode_spec.label,
        "intent": mode_spec.intent,
        "filters": filters or {},
        "recommended_source_ids": [item.get("source_id", "") for item in recommended],
        "visible_count": len(recommended),
        "total_count": len(items),
        "next_step": _next_step_payload(next_item, mode_spec, metrics),
        "metrics": metrics,
        "mode_options": mode_options,
        "guardrails": [_guardrail_payload(guardrail) for guardrail in guardrails[:8]],
        "completion_copy": mode_spec.completion_copy if not recommended else "The session still has useful decisions to make.",
        "quiet_summary": _session_quiet_summary(mode_spec, metrics, next_item),
    }


def build_report_payload(
    items: list[dict[str, Any]],
    summary: dict[str, Any],
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    risk_counts = Counter(item.get("risk_level", "low") for item in items)
    status_counts = Counter(item.get("review_status", "unreviewed") for item in items)
    boundary_counts = Counter(item.get("why_saved_status", "unknown") for item in items)
    sections = []
    metrics = {
        "risk_count": risk_counts.get("critical", 0) + risk_counts.get("high", 0),
        "ai_count": boundary_counts.get("AI-inferred", 0),
        "evidence_count": sum(int(item.get("evidence_count") or 0) for item in items),
        "loops_count": sum(1 for item in items if item.get("has_open_loops")),
        "history_count": sum(1 for item in items if item.get("review_status") != "unreviewed"),
        "topics_count": sum(len(item.get("topic_refs") or []) for item in items),
        "recall_count": sum(len(item.get("future_recall_questions") or []) for item in items),
        "decisions_count": status_counts.get("unreviewed", 0) + status_counts.get("deferred", 0),
        "traceability_count": sum(1 for item in items if int(item.get("evidence_count") or 0) > 0),
        "quiet_count": len(items),
    }
    for section in report_sections_by_priority(10):
        count = metrics.get(section.metric_key, 0)
        sections.append({
            "id": section.section_id,
            "title": section.title,
            "priority": section.priority,
            "count": count,
            "summary": section.summary_template if count else section.empty_template,
            "detail_prompt": section.detail_prompt,
            "quiet_copy": section.quiet_copy,
            "action_label": section.action_label,
        })
    action_queue = [_report_action(item) for item in sorted(items, key=_session_sort_key)[:8]]
    headline = _report_headline(summary, risk_counts, boundary_counts)
    return {
        "headline": headline,
        "quiet_summary": _report_quiet_summary(summary, risk_counts, boundary_counts),
        "filters": filters or {},
        "metrics": metrics,
        "risk_register": {
            "critical": risk_counts.get("critical", 0),
            "high": risk_counts.get("high", 0),
            "medium": risk_counts.get("medium", 0),
            "low": risk_counts.get("low", 0),
            "unreviewed": status_counts.get("unreviewed", 0),
            "deferred": status_counts.get("deferred", 0),
            "ai_inferred": boundary_counts.get("AI-inferred", 0),
            "user_stated": boundary_counts.get("user-stated", 0),
        },
        "sections": sections,
        "action_queue": action_queue,
        "display_policy": {
            "default_collapsed": True,
            "max_visible_sections": 2,
            "max_visible_actions": 3,
            "reason": "The report is available for traceability but should not compete with the next review decision.",
        },
    }


def build_detail_report_slice(item: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    trust_score = analysis.get("trust_score", {})
    evidence = analysis.get("evidence_compression", {})
    preview = analysis.get("decision_preview", {})
    action = item.get("recommended_action", "monitor")
    return {
        "source_id": item.get("source_id", ""),
        "recommended_action": action,
        "score_label": trust_score.get("label", "unknown"),
        "score": trust_score.get("score", 0),
        "evidence_summary": evidence.get("summary", ""),
        "quiet_summary": analysis.get("quiet_summary", ""),
        "primary_preview": preview.get("confirmed", {}).get("summary", ""),
        "collapsed_by_default": True,
    }


def _signal_profile(item: dict[str, Any], evidence_paths: list[dict[str, Any]], history: list[dict[str, Any]], open_loops: list[dict[str, Any]]) -> dict[str, Any]:
    confidence = float(item.get("confidence") or 0)
    evidence_count = len(evidence_paths) if evidence_paths else int(item.get("evidence_count") or 0)
    open_loop_count = len(open_loops) if open_loops else len(item.get("open_loops") or [])
    topic_count = len(item.get("topic_refs") or [])
    future_count = len(item.get("future_recall_questions") or [])
    history_count = len(history)
    relation_counts = Counter(path.get("relation", "unknown") for path in evidence_paths)
    status = item.get("review_status", "unreviewed")
    boundary = item.get("why_saved_status", "unknown")
    return {
        "boundary": boundary,
        "status": status,
        "risk": item.get("risk_level", "low"),
        "confidence": confidence,
        "confidence_band": _confidence_band(confidence),
        "evidence_count": evidence_count,
        "evidence_band": _evidence_band(evidence_count),
        "open_loop_count": open_loop_count,
        "loop_band": _loop_band(open_loop_count),
        "topic_count": topic_count,
        "topic_band": _topic_band(topic_count),
        "future_question_count": future_count,
        "future_band": "some" if future_count else "none",
        "history_count": history_count,
        "history_band": _history_band(history_count),
        "relation_counts": dict(relation_counts),
        "has_review_note": bool(str(item.get("review_note") or "").strip()),
        "has_user_reason": boundary == "user-stated",
        "needs_user_decision": boundary == "AI-inferred" and status in {"unreviewed", "deferred"},
        "is_reusable": status in {"confirmed", "rewritten"},
        "is_blocked": status == "rejected",
    }


def _matched_rules(profile: dict[str, Any]):
    candidates = []
    candidates.extend(rules_for_match("boundary", str(profile.get("boundary", "unknown"))))
    candidates.extend(rules_for_match("status", str(profile.get("status", "unreviewed"))))
    candidates.extend(rules_for_match("confidence", str(profile.get("confidence_band", "moderate"))))
    candidates.extend(rules_for_match("evidence", str(profile.get("evidence_band", "none"))))
    candidates.extend(rules_for_match("loop", str(profile.get("loop_band", "none"))))
    candidates.extend(rules_for_match("topic", str(profile.get("topic_band", "none"))))
    candidates.extend(rules_for_match("history", str(profile.get("history_band", "none"))))
    candidates.extend(rules_for_match("future", str(profile.get("future_band", "none"))))
    unique = {}
    for rule in candidates:
        unique.setdefault(rule.rule_id, rule)
    return sorted(unique.values(), key=lambda rule: (-rule.weight, rule.rule_id))


def _trust_score(item: dict[str, Any], profile: dict[str, Any], rules) -> dict[str, Any]:
    score = 72
    score += int(float(profile.get("confidence", 0)) * 18)
    score += min(int(profile.get("evidence_count", 0)), 8) * 2
    if profile.get("boundary") == "AI-inferred":
        score -= 18
    if profile.get("status") == "unreviewed":
        score -= 10
    if profile.get("status") == "deferred":
        score -= 8
    if profile.get("status") == "rejected":
        score -= 30
    if profile.get("status") in {"confirmed", "rewritten"}:
        score += 14
    score -= min(int(profile.get("open_loop_count", 0)), 6) * 3
    if not profile.get("has_review_note") and item.get("risk_level") in {"critical", "high"}:
        score -= 7
    score = max(0, min(100, score))
    return {
        "score": score,
        "label": _score_label(score),
        "drivers": [rule.plain_language for rule in rules[:5]],
        "score_parts": {
            "confidence": round(float(profile.get("confidence", 0)) * 100),
            "evidence": int(profile.get("evidence_count", 0)),
            "open_loops": int(profile.get("open_loop_count", 0)),
            "history": int(profile.get("history_count", 0)),
            "boundary": profile.get("boundary", "unknown"),
            "status": profile.get("status", "unreviewed"),
        },
    }


def _evidence_compression(item: dict[str, Any], paths: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    supporting = []
    insufficient = []
    needs_confirmation = []
    if paths:
        for path in paths:
            relation = path.get("relation", "unknown")
            line = _path_line(path)
            if relation in {"triggered_thought", "evidence_for", "belongs_to", "derived_from", "mentions"}:
                supporting.append(line)
            elif relation in {"contradicts", "conflicts_with"}:
                insufficient.append(line)
            else:
                needs_confirmation.append(line)
    else:
        count = int(profile.get("evidence_count", 0))
        if count:
            supporting.append(f"{count} graph evidence path(s) are available; expand detail to inspect exact paths.")
        else:
            insufficient.append("No graph evidence path is attached yet.")
    if item.get("why_saved_status") == "AI-inferred":
        needs_confirmation.append("The saved reason is model-inferred and still needs user confirmation.")
    if item.get("open_loops"):
        needs_confirmation.append(f"{len(item.get('open_loops') or [])} open loop(s) may change whether this reason is still useful.")
    return {
        "summary": _evidence_summary(supporting, insufficient, needs_confirmation, profile),
        "supporting": supporting[:4],
        "insufficient": insufficient[:4],
        "needs_confirmation": needs_confirmation[:4],
        "supporting_count": len(supporting),
        "insufficient_count": len(insufficient),
        "needs_confirmation_count": len(needs_confirmation),
        "path_count": len(paths) if paths else int(profile.get("evidence_count", 0)),
        "primary_relation": _primary_relation(paths, profile),
        "pressure_level": _evidence_pressure(supporting, insufficient, needs_confirmation),
        "collapsed_copy": "Evidence is compressed to decision-level signals; expand only when the decision is unclear.",
    }


def _decision_preview(item: dict[str, Any], profile: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    preview = {}
    for action in TRUST_ACTIONS:
        impact = first_decision_impact(action)
        warnings = list(impact.warnings)
        if action == "confirmed" and item.get("why_saved_status") == "AI-inferred":
            warnings.append("Confirmation will allow future recall to reuse a model-inferred reason as trusted context.")
        if action == "rejected" and profile.get("open_loop_count", 0):
            warnings.append("Rejecting the reason does not resolve connected open loops.")
        if action == "rewritten" and not evidence.get("supporting"):
            warnings.append("Rewrite should mention that graph support is currently weak.")
        if action == "deferred" and item.get("risk_level") in {"critical", "high"}:
            warnings.append("High-risk deferred items remain near the top of future review sessions.")
        preview[action] = {
            "title": impact.title,
            "tone": impact.tone,
            "summary": impact.summary_template,
            "recall_effect": impact.recall_effect,
            "graph_effect": impact.graph_effect,
            "open_loop_effect": impact.open_loop_effect,
            "warnings": warnings[:4],
            "confirmation_question": impact.confirmation_question,
            "next_step": impact.next_step,
            "quiet_copy": impact.user_pressure,
        }
    return preview


def _review_path(item: dict[str, Any], profile: dict[str, Any], evidence: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
    stages = ["orient", "evidence", "conflict", "decision", "writeback", "followup"]
    current_stage = _current_stage(profile, evidence, history)
    steps = []
    for stage in stages:
        template = review_path_templates_for_stage(stage)[0]
        complete = _stage_complete(stage, profile, evidence, history)
        steps.append({
            "stage": stage,
            "label": template.label,
            "instruction": template.instruction,
            "evidence_hint": template.evidence_hint,
            "complete": complete,
            "current": stage == current_stage,
            "fallback_action": template.fallback_action,
            "quiet_copy": template.quiet_copy,
        })
    completed = sum(1 for step in steps if step["complete"])
    return {
        "current_stage": current_stage,
        "completion_percent": round(completed / len(steps) * 100),
        "steps": steps,
        "next_instruction": next((step["instruction"] for step in steps if step["current"]), steps[0]["instruction"]),
    }


def _session_fit(item: dict[str, Any], peers: list[dict[str, Any]], profile: dict[str, Any]) -> dict[str, Any]:
    rank = 1
    if peers:
        ordered = sorted(peers, key=_session_sort_key)
        ids = [peer.get("source_id") for peer in ordered]
        if item.get("source_id") in ids:
            rank = ids.index(item.get("source_id")) + 1
    if item.get("risk_level") in {"critical", "high"}:
        reason = "This item fits the high-risk session because it can affect future answer trust."
    elif profile.get("open_loop_count", 0):
        reason = "This item fits an open-loop session because unresolved follow-up work remains."
    elif profile.get("status") == "deferred":
        reason = "This item fits a deferred session because the previous decision was postponed."
    else:
        reason = "This item fits a cleanup session and does not need to dominate the page."
    return {
        "rank": rank,
        "reason": reason,
        "recommended_mode": _recommended_mode(item, profile),
        "visible_by_default": rank <= 4 or item.get("risk_level") in {"critical", "high"},
        "can_batch": item.get("risk_level") in {"medium", "low"} and not profile.get("needs_user_decision"),
    }


def _impact_map(item: dict[str, Any], profile: dict[str, Any], open_loops: list[dict[str, Any]]) -> dict[str, Any]:
    topics = item.get("topic_refs") or []
    questions = item.get("future_recall_questions") or []
    loops = open_loops or [{"text": text, "state": "active"} for text in item.get("open_loops") or []]
    return {
        "future_recall": [
            {
                "question": question,
                "impact": "This question may reuse the trust decision for answer framing.",
            }
            for question in questions[:5]
        ] or [{"question": "No future recall question is attached.", "impact": "Review only affects this source for now."}],
        "topics": [
            {
                "topic_id": topic.get("topic_id", ""),
                "title": topic.get("title", ""),
                "role": topic.get("role", "evidence"),
                "impact": "Topic recall can cite this source with the selected trust status.",
            }
            for topic in topics[:5]
        ],
        "open_loops": [
            {
                "text": loop.get("text", ""),
                "state": loop.get("state", "active"),
                "impact": "The loop remains actionable until explicitly resolved.",
            }
            for loop in loops[:5]
        ],
        "graph": {
            "evidence_count": int(profile.get("evidence_count", 0)),
            "impact": "Graph paths stay traceable; the trust decision changes how strongly they should be reused.",
        },
    }


def _conflict_review(item: dict[str, Any], profile: dict[str, Any], paths: list[dict[str, Any]], history: list[dict[str, Any]]) -> dict[str, Any]:
    conflicts = []
    cautions = []
    if item.get("review_status") == "rejected":
        conflicts.append("The current saved reason has been rejected before.")
    if item.get("why_saved_status") == "AI-inferred" and not profile.get("has_review_note"):
        cautions.append("AI-inferred reason has no user review note yet.")
    if not paths and int(profile.get("evidence_count", 0)) == 0:
        cautions.append("No direct graph evidence path is available.")
    if len(history) > 1:
        cautions.append("Multiple review actions exist; read history before changing status again.")
    for path in paths:
        if path.get("relation") in {"contradicts", "conflicts_with"}:
            conflicts.append(_path_line(path))
    return {
        "has_conflict": bool(conflicts),
        "conflicts": conflicts[:5],
        "cautions": cautions[:5],
        "resolution_prompt": "Resolve conflicts only if they affect the user's future recall decision.",
        "quiet_copy": "Conflicts stay collapsed unless present; cautions are summarized as one line.",
    }


def _context_completeness(item: dict[str, Any], profile: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    checks = [
        ("saved_reason", bool(item.get("why_saved")), "Saved reason exists"),
        ("boundary", item.get("why_saved_status") in {"AI-inferred", "user-stated"}, "Boundary is labeled"),
        ("evidence", bool(evidence.get("supporting")), "Evidence support exists"),
        ("future_recall", bool(item.get("future_recall_questions")), "Future recall question exists"),
        ("project", bool(item.get("related_project")), "Related project exists"),
        ("review_status", item.get("review_status") != "unreviewed", "Review status has changed from default"),
    ]
    complete = [label for _, ok, label in checks if ok]
    missing = [label for _, ok, label in checks if not ok]
    percent = round(len(complete) / len(checks) * 100)
    return {
        "percent": percent,
        "complete": complete,
        "missing": missing,
        "summary": f"{len(complete)} of {len(checks)} trust context checks are satisfied.",
        "quiet_copy": "Only missing checks need attention; complete checks remain folded into the summary.",
    }


def _attention_budget(item: dict[str, Any], profile: dict[str, Any], evidence: dict[str, Any], history: list[dict[str, Any]], loops: list[dict[str, Any]]) -> dict[str, Any]:
    visible = 2
    if item.get("risk_level") in {"critical", "high"}:
        visible += 1
    if profile.get("needs_user_decision"):
        visible += 1
    hidden = max(0, int(profile.get("evidence_count", 0)) - len(evidence.get("supporting", [])))
    hidden += max(0, len(history) - 2)
    hidden += max(0, len(loops) - 2)
    return {
        "max_visible_blocks": min(5, visible),
        "hidden_blocks": hidden,
        "default_disclosure": "compressed",
        "reason": "The page should present the next decision first and keep supporting detail available but quiet.",
        "expand_when": [
            "The user disputes the recommendation.",
            "Evidence support is weak or missing.",
            "A rejected or rewritten history exists.",
        ],
    }


def _quiet_summary(item: dict[str, Any], trust_score: dict[str, Any], evidence: dict[str, Any], conflict: dict[str, Any]) -> str:
    title = item.get("title") or "This source"
    score = trust_score.get("label", "unknown")
    if conflict.get("has_conflict"):
        return f"{title} has {score} trust with a conflict to inspect before deciding."
    if item.get("why_saved_status") == "AI-inferred":
        return f"{title} has {score} trust; confirm the inferred reason only after scanning compressed evidence."
    return f"{title} has {score} trust; user-stated context can stay compact unless reused broadly."


def _recommended_microcopy(item: dict[str, Any], profile: dict[str, Any], trust_score: dict[str, Any]) -> dict[str, str]:
    return {
        "badge": trust_score.get("label", "unknown"),
        "primary": _primary_microcopy(item, profile),
        "secondary": "Details are available, but the next decision is the main thing to review.",
        "empty": "No additional trust detail needs attention right now.",
    }


def _hidden_depth_count(paths: list[dict[str, Any]], history: list[dict[str, Any]], loops: list[dict[str, Any]], rules) -> int:
    return max(0, len(paths) - 4) + max(0, len(history) - 2) + max(0, len(loops) - 2) + max(0, len(rules) - 5)


def _session_metrics(items: list[dict[str, Any]], recommended: list[dict[str, Any]], summary: dict[str, Any]) -> dict[str, Any]:
    risk_counts = Counter(item.get("risk_level", "low") for item in items)
    status_counts = Counter(item.get("review_status", "unreviewed") for item in items)
    return {
        "total": len(items),
        "visible": len(recommended),
        "high_pressure": risk_counts.get("critical", 0) + risk_counts.get("high", 0),
        "unreviewed": status_counts.get("unreviewed", 0),
        "deferred": status_counts.get("deferred", 0),
        "confirmed": status_counts.get("confirmed", 0),
        "ai_inferred": int(summary.get("ai_inferred", 0)),
        "open_loop_items": int(summary.get("open_loop_items", 0)),
        "batchable": sum(1 for item in items if item.get("risk_level") in {"medium", "low"}),
    }


def _next_step_payload(item: dict[str, Any] | None, mode_spec, metrics: dict[str, Any]) -> dict[str, Any]:
    if not item:
        return {
            "source_id": "",
            "title": "",
            "label": mode_spec.completion_copy,
            "reason": mode_spec.empty_copy,
            "action": "monitor",
        }
    return {
        "source_id": item.get("source_id", ""),
        "title": item.get("title", ""),
        "label": mode_spec.next_step_copy,
        "reason": item.get("review_focus", {}).get("detail") or mode_spec.intent,
        "action": item.get("recommended_action", "monitor"),
        "risk_level": item.get("risk_level", "low"),
        "remaining_after_this": max(0, metrics.get("visible", 1) - 1),
    }


def _report_action(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": item.get("source_id", ""),
        "title": item.get("title", ""),
        "risk_level": item.get("risk_level", "low"),
        "review_status": item.get("review_status", "unreviewed"),
        "recommended_action": item.get("recommended_action", "monitor"),
        "summary": item.get("review_focus", {}).get("headline", "Review this item"),
    }


def _report_headline(summary: dict[str, Any], risk_counts: Counter, boundary_counts: Counter) -> str:
    high = risk_counts.get("critical", 0) + risk_counts.get("high", 0)
    if high:
        return f"{high} high-priority trust decision(s) should be handled before broad cleanup."
    ai_count = boundary_counts.get("AI-inferred", 0)
    if ai_count:
        return f"{ai_count} AI-inferred context(s) remain visible for light review."
    return "Trust context is currently low pressure."


def _report_quiet_summary(summary: dict[str, Any], risk_counts: Counter, boundary_counts: Counter) -> str:
    total = int(summary.get("total", 0))
    ai_count = boundary_counts.get("AI-inferred", 0)
    high = risk_counts.get("critical", 0) + risk_counts.get("high", 0)
    return f"{total} item(s), {ai_count} AI-inferred, {high} high-pressure; details stay collapsed by default."


def _session_quiet_summary(mode_spec, metrics: dict[str, Any], next_item: dict[str, Any] | None) -> str:
    if not next_item:
        return mode_spec.empty_copy
    return f"{mode_spec.label}: show {metrics.get('visible', 0)} item(s), start with {next_item.get('title', 'the first item')}."


def _matches_mode(item: dict[str, Any], mode_spec) -> bool:
    risk = item.get("risk_level", "low")
    status = item.get("review_status", "unreviewed")
    if mode_spec.mode_id == "open-loops":
        return bool(item.get("has_open_loops"))
    if mode_spec.mode_id == "ai-only":
        return item.get("why_saved_status") == "AI-inferred" and status in mode_spec.include_statuses
    if mode_spec.mode_id == "trusted":
        return status in {"confirmed", "rewritten"}
    if mode_spec.mode_id == "cleanup":
        return status in {"rejected", "deferred"} or risk == "low"
    return risk in mode_spec.include_risks or status in mode_spec.include_statuses


def _session_sort_key(item: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        RISK_ORDER.get(item.get("risk_level", "low"), 9),
        STATUS_ORDER.get(item.get("review_status", "unreviewed"), 9),
        0 if item.get("needs_review") else 1,
        str(item.get("imported_at", "")),
    )


def _rule_payload(rule) -> dict[str, Any]:
    payload = asdict(rule)
    payload.pop("report_copy", None)
    payload.pop("quiet_copy", None)
    return payload


def _guardrail_payload(guardrail) -> dict[str, Any]:
    return asdict(guardrail)


def _confidence_band(confidence: float) -> str:
    if confidence < 0.4:
        return "very_low"
    if confidence < 0.55:
        return "low"
    if confidence < 0.75:
        return "moderate"
    return "high"


def _evidence_band(count: int) -> str:
    if count <= 0:
        return "none"
    if count == 1:
        return "single"
    return "multiple"


def _loop_band(count: int) -> str:
    if count <= 0:
        return "none"
    if count == 1:
        return "one"
    return "many"


def _topic_band(count: int) -> str:
    if count <= 0:
        return "none"
    if count == 1:
        return "one"
    return "many"


def _history_band(count: int) -> str:
    if count <= 0:
        return "none"
    if count == 1:
        return "one"
    return "many"


def _score_label(score: int) -> str:
    if score >= 82:
        return "stable"
    if score >= 64:
        return "usable"
    if score >= 42:
        return "needs review"
    return "unsafe"


def _path_line(path: dict[str, Any]) -> str:
    source = path.get("source_label") or path.get("source_node_id") or "source"
    relation = path.get("relation") or "related_to"
    target = path.get("target_label") or path.get("target_node_id") or "target"
    confidence = path.get("confidence")
    if confidence is None:
        return f"{source} --{relation}--> {target}"
    return f"{source} --{relation}--> {target} ({round(float(confidence) * 100)}%)"


def _evidence_summary(supporting: list[str], insufficient: list[str], needs_confirmation: list[str], profile: dict[str, Any]) -> str:
    if supporting and not insufficient:
        return f"{len(supporting)} supporting signal(s), {len(needs_confirmation)} confirmation prompt(s)."
    if insufficient and not supporting:
        return f"Evidence is weak: {len(insufficient)} gap(s), {len(needs_confirmation)} confirmation prompt(s)."
    if supporting and insufficient:
        return f"Mixed evidence: {len(supporting)} support signal(s), {len(insufficient)} gap(s)."
    return "No evidence signal is available yet."


def _primary_relation(paths: list[dict[str, Any]], profile: dict[str, Any]) -> str:
    if paths:
        counts = Counter(path.get("relation", "unknown") for path in paths)
        return counts.most_common(1)[0][0]
    relation_counts = profile.get("relation_counts") or {}
    if relation_counts:
        return max(relation_counts.items(), key=lambda item: item[1])[0]
    return "unavailable"


def _evidence_pressure(supporting: list[str], insufficient: list[str], needs_confirmation: list[str]) -> str:
    if insufficient:
        return "high"
    if len(needs_confirmation) > len(supporting):
        return "medium"
    return "low"


def _current_stage(profile: dict[str, Any], evidence: dict[str, Any], history: list[dict[str, Any]]) -> str:
    if not profile.get("boundary"):
        return "orient"
    if not evidence.get("supporting"):
        return "evidence"
    if evidence.get("insufficient"):
        return "conflict"
    if profile.get("status") in {"unreviewed", "deferred"}:
        return "decision"
    if not history and profile.get("status") != "unreviewed":
        return "writeback"
    if profile.get("open_loop_count", 0):
        return "followup"
    return "decision"


def _stage_complete(stage: str, profile: dict[str, Any], evidence: dict[str, Any], history: list[dict[str, Any]]) -> bool:
    if stage == "orient":
        return bool(profile.get("boundary"))
    if stage == "evidence":
        return bool(evidence.get("supporting") or evidence.get("insufficient"))
    if stage == "conflict":
        return not bool(evidence.get("insufficient"))
    if stage == "decision":
        return profile.get("status") not in {"unreviewed", "deferred"}
    if stage == "writeback":
        return bool(history) or profile.get("status") == "unreviewed"
    if stage == "followup":
        return profile.get("open_loop_count", 0) == 0
    return False


def _recommended_mode(item: dict[str, Any], profile: dict[str, Any]) -> str:
    if item.get("risk_level") in {"critical", "high"}:
        return "high-risk"
    if profile.get("open_loop_count", 0):
        return "open-loops"
    if item.get("review_status") == "deferred":
        return "deferred"
    if item.get("why_saved_status") == "AI-inferred":
        return "ai-only"
    return "quick-clear"


def _primary_microcopy(item: dict[str, Any], profile: dict[str, Any]) -> str:
    if item.get("risk_level") in {"critical", "high"}:
        return "Scan compressed evidence, then decide."
    if profile.get("open_loop_count", 0):
        return "Use the open loop to choose the next action."
    if item.get("review_status") in {"confirmed", "rewritten"}:
        return "Trusted enough to keep as a recall anchor."
    return "Low pressure; batch handling is acceptable."
