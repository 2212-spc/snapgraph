from __future__ import annotations

from collections import Counter, defaultdict
import re
from typing import Any


def build_recall_history_insights(
    items: list[dict[str, Any]],
    summary: dict[str, Any],
) -> dict[str, Any]:
    """Build deterministic recall-history guidance for compact UI surfaces."""
    normalized = [_normalize_item(item) for item in items]
    thread_groups = _thread_groups(normalized)
    reuse_candidates = _reuse_candidates(normalized)
    source_map = _source_follow_up_map(normalized)
    conversation_patterns = _conversation_patterns(normalized, thread_groups)
    return {
        "summary": _summary(normalized, summary, thread_groups),
        "conversation_patterns": conversation_patterns,
        "reuse_candidates": reuse_candidates,
        "follow_up_map": source_map,
        "thread_continuity": _thread_continuity(thread_groups),
        "knowledge_gaps": _knowledge_gaps(normalized, conversation_patterns, source_map),
        "cleanup_suggestions": _cleanup_suggestions(normalized, thread_groups),
        "display_policy": _display_policy(normalized, thread_groups),
    }


def _normalize_item(item: dict[str, Any]) -> dict[str, Any]:
    context_source_ids = _string_list(item.get("context_source_ids"))
    previous_turns = _dict_list(item.get("previous_turns"))
    thought = item.get("thought") if isinstance(item.get("thought"), dict) else {}
    return {
        "id": str(item.get("id") or ""),
        "thread_id": str(item.get("thread_id") or ""),
        "turn_id": str(item.get("turn_id") or ""),
        "turn_index": _safe_int(item.get("turn_index")),
        "question": _clean_text(str(item.get("question") or "")),
        "mode": _mode(str(item.get("mode") or "")),
        "depth": _depth(str(item.get("depth") or "")),
        "space_id": str(item.get("space_id") or "all"),
        "previous_turns": previous_turns,
        "context_source_ids": context_source_ids,
        "answer_text": _clean_text(str(item.get("answer_text") or "")),
        "answer_preview": _clean_text(str(item.get("answer_preview") or "")),
        "thought_summary": _clean_text(str(item.get("thought_summary") or "")),
        "thought": thought,
        "context_count": _safe_int(item.get("context_count")),
        "local_file_count": _safe_int(item.get("local_file_count")),
        "created_at": str(item.get("created_at") or ""),
        "updated_at": str(item.get("updated_at") or ""),
    }


def _summary(
    items: list[dict[str, Any]],
    source_summary: dict[str, Any],
    thread_groups: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    context_count = sum(item["context_count"] for item in items)
    local_file_count = sum(item["local_file_count"] for item in items)
    deep_count = sum(1 for item in items if item["depth"] == "deep")
    thread_count = len(thread_groups)
    return {
        "total": _safe_int(source_summary.get("total")),
        "returned": _safe_int(source_summary.get("returned"), fallback=len(items)),
        "thread_count": thread_count,
        "deep_count": deep_count,
        "quick_count": sum(1 for item in items if item["depth"] == "quick"),
        "context_count": context_count,
        "local_file_count": local_file_count,
        "average_context_count": _average(context_count, len(items)),
        "average_local_file_count": _average(local_file_count, len(items)),
        "has_threaded_history": any(len(group) > 1 for group in thread_groups.values()),
        "has_reusable_context": bool(context_count or local_file_count),
    }


def _conversation_patterns(
    items: list[dict[str, Any]],
    thread_groups: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    mode_counts = Counter(item["mode"] for item in items)
    depth_counts = Counter(item["depth"] for item in items)
    space_counts = Counter(item["space_id"] for item in items)
    question_terms = Counter()
    for item in items[:12]:
        question_terms.update(_question_terms(item["question"]))
    threaded_turns = [
        _thread_summary(thread_id, group)
        for thread_id, group in thread_groups.items()
        if len(group) > 1
    ]
    threaded_turns.sort(key=lambda row: (-row["turn_count"], row["thread_id"]))
    return {
        "mode_counts": dict(mode_counts),
        "depth_counts": dict(depth_counts),
        "space_counts": dict(space_counts),
        "dominant_mode": _dominant(mode_counts),
        "dominant_depth": _dominant(depth_counts),
        "dominant_space": _dominant(space_counts),
        "threaded_turns": threaded_turns[:8],
        "recent_question_terms": [
            {"term": term, "count": count}
            for term, count in question_terms.most_common(12)
        ],
        "plain_language": _patterns_copy(mode_counts, depth_counts, threaded_turns),
    }


def _reuse_candidates(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for item in items:
        score = _reuse_score(item)
        if score <= 0:
            continue
        candidates.append(
            {
                "id": item["id"],
                "thread_id": item["thread_id"],
                "question": item["question"],
                "mode": item["mode"],
                "depth": item["depth"],
                "space_id": item["space_id"],
                "context_count": item["context_count"],
                "local_file_count": item["local_file_count"],
                "context_source_ids": item["context_source_ids"][:8],
                "answer_preview": _preview(item["answer_preview"] or item["answer_text"], 180),
                "thought_summary": _preview(item["thought_summary"], 120),
                "reuse_score": score,
                "reason": _reuse_reason(item, score),
                "default_collapsed": score < 35,
            }
        )
    candidates.sort(key=lambda row: (-row["reuse_score"], row["question"], row["id"]))
    return candidates[:10]


def _source_follow_up_map(items: list[dict[str, Any]]) -> dict[str, Any]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        for source_id in item["context_source_ids"]:
            by_source[source_id].append(item)
    source_rows = []
    for source_id, source_items in by_source.items():
        source_items.sort(key=lambda row: row["updated_at"], reverse=True)
        source_rows.append(
            {
                "source_id": source_id,
                "question_count": len(source_items),
                "latest_question": source_items[0]["question"],
                "latest_history_id": source_items[0]["id"],
                "modes": dict(Counter(item["mode"] for item in source_items)),
                "depths": dict(Counter(item["depth"] for item in source_items)),
                "suggested_follow_up": _source_follow_up_prompt(source_id, source_items),
                "default_collapsed": len(source_items) <= 1,
            }
        )
    source_rows.sort(key=lambda row: (-row["question_count"], row["source_id"]))
    return {
        "source_count": len(source_rows),
        "sources": source_rows[:12],
        "unmapped_history_ids": [
            item["id"]
            for item in items
            if not item["context_source_ids"]
        ][:12],
        "plain_language": _source_map_copy(source_rows, items),
    }


def _thread_continuity(thread_groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    rows = []
    for thread_id, group in thread_groups.items():
        ordered = sorted(group, key=lambda item: (item["turn_index"], item["updated_at"]))
        if not thread_id or len(ordered) <= 1:
            continue
        rows.append(
            {
                "thread_id": thread_id,
                "turn_count": len(ordered),
                "first_question": ordered[0]["question"],
                "latest_question": ordered[-1]["question"],
                "context_growth": _context_growth(ordered),
                "depth_shift": _depth_shift(ordered),
                "continuity_label": _continuity_label(ordered),
                "default_collapsed": len(ordered) > 3,
            }
        )
    rows.sort(key=lambda row: (-row["turn_count"], row["thread_id"]))
    return {
        "thread_count": len(rows),
        "threads": rows[:8],
        "plain_language": _thread_copy(rows),
    }


def _knowledge_gaps(
    items: list[dict[str, Any]],
    patterns: dict[str, Any],
    follow_up_map: dict[str, Any],
) -> list[dict[str, Any]]:
    gaps = []
    if not items:
        gaps.append(_gap("empty_history", "No recall history yet", "Ask one question to create a reusable recall trace.", 1))
        return gaps
    no_context = [item for item in items if item["context_count"] == 0 and item["local_file_count"] == 0]
    if no_context:
        gaps.append(
            _gap(
                "thin_context",
                "Some answers have thin evidence",
                f"{len(no_context)} recent recall item(s) did not attach context or local files.",
                1,
            )
        )
    if not follow_up_map["sources"]:
        gaps.append(
            _gap(
                "missing_source_links",
                "History lacks source follow-up routes",
                "Recall history can be more useful when answers keep source ids attached.",
                2,
            )
        )
    depth_counts = patterns.get("depth_counts") or {}
    if depth_counts.get("quick", 0) > depth_counts.get("deep", 0) * 2 and len(items) >= 3:
        gaps.append(
            _gap(
                "mostly_quick_answers",
                "Most answers are quick checks",
                "Use deep recall when a question needs evidence paths or reviewable reasoning.",
                3,
            )
        )
    repeated_terms = [
        term["term"]
        for term in patterns.get("recent_question_terms", [])
        if int(term.get("count") or 0) >= 2
    ]
    if repeated_terms:
        gaps.append(
            _gap(
                "repeated_intent",
                "Repeated topics are forming",
                f"Recent questions repeat: {', '.join(repeated_terms[:4])}.",
                4,
            )
        )
    if not gaps:
        gaps.append(_gap("ready", "History is reusable", "Recent answers have enough structure to support follow-up recall.", 5))
    return gaps[:6]


def _cleanup_suggestions(
    items: list[dict[str, Any]],
    thread_groups: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    suggestions = []
    long_threads = [
        (thread_id, group)
        for thread_id, group in thread_groups.items()
        if thread_id and len(group) >= 4
    ]
    if long_threads:
        suggestions.append(
            _suggestion(
                "collapse_long_threads",
                "Collapse long threads",
                f"{len(long_threads)} thread(s) have enough turns to hide older context by default.",
                1,
            )
        )
    empty_answers = [
        item
        for item in items
        if not item["answer_preview"] and not item["answer_text"]
    ]
    if empty_answers:
        suggestions.append(
            _suggestion(
                "hide_empty_answers",
                "Hide empty answer previews",
                f"{len(empty_answers)} history item(s) have no preview.",
                2,
            )
        )
    duplicate_questions = [
        question
        for question, count in Counter(item["question"] for item in items if item["question"]).items()
        if count > 1
    ]
    if duplicate_questions:
        suggestions.append(
            _suggestion(
                "group_duplicate_questions",
                "Group repeated questions",
                f"{len(duplicate_questions)} repeated question(s) can be grouped.",
                3,
            )
        )
    if not suggestions:
        suggestions.append(
            _suggestion(
                "keep_recent_first",
                "Keep recent answers first",
                "The current history is short enough to show without heavy cleanup.",
                1,
            )
        )
    return suggestions[:5]


def _display_policy(
    items: list[dict[str, Any]],
    thread_groups: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    long_thread_count = sum(1 for group in thread_groups.values() if len(group) > 2)
    pressure = _history_pressure(items, long_thread_count)
    if pressure == "high":
        visible = 5
    elif pressure == "medium":
        visible = 6
    else:
        visible = 8
    return {
        "max_visible_history": min(8, visible),
        "collapse_old_threads": True,
        "collapse_low_context_answers": True,
        "show_recent_first": True,
        "show_reuse_candidates_first": bool(items),
        "pressure": pressure,
        "reason": _display_reason(pressure, len(items), long_thread_count),
    }


def _thread_groups(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        key = item["thread_id"] or item["id"]
        groups[key].append(item)
    return dict(groups)


def _thread_summary(thread_id: str, group: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(group, key=lambda item: (item["turn_index"], item["updated_at"]))
    return {
        "thread_id": thread_id,
        "turn_count": len(ordered),
        "latest_question": ordered[-1]["question"] if ordered else "",
        "context_total": sum(item["context_count"] for item in ordered),
        "local_file_total": sum(item["local_file_count"] for item in ordered),
    }


def _reuse_score(item: dict[str, Any]) -> int:
    score = 0
    score += min(item["context_count"], 8) * 8
    score += min(item["local_file_count"], 4) * 6
    score += 12 if item["depth"] == "deep" else 4
    score += 8 if item["thought_summary"] else 0
    score += min(len(item["context_source_ids"]), 6) * 3
    score += 5 if item["answer_preview"] else 0
    return max(0, min(100, score))


def _reuse_reason(item: dict[str, Any], score: int) -> str:
    reasons = []
    if item["context_count"]:
        reasons.append(f"{item['context_count']} context item(s)")
    if item["local_file_count"]:
        reasons.append(f"{item['local_file_count']} local file(s)")
    if item["depth"] == "deep":
        reasons.append("deep recall")
    if item["thought_summary"]:
        reasons.append("thought summary")
    if not reasons:
        reasons.append(f"reuse score {score}")
    return ", ".join(reasons)


def _source_follow_up_prompt(source_id: str, source_items: list[dict[str, Any]]) -> str:
    latest = source_items[0]["question"] if source_items else ""
    if len(source_items) > 1:
        return f"Compare follow-up answers that reused {source_id}."
    if latest:
        return f"Ask what changed after: {latest[:80]}"
    return f"Review whether {source_id} needs another recall pass."


def _context_growth(items: list[dict[str, Any]]) -> int:
    if len(items) < 2:
        return 0
    return items[-1]["context_count"] - items[0]["context_count"]


def _depth_shift(items: list[dict[str, Any]]) -> str:
    if len(items) < 2:
        return "none"
    first = items[0]["depth"]
    latest = items[-1]["depth"]
    if first == latest:
        return "stable"
    if first == "quick" and latest == "deep":
        return "expanded"
    if first == "deep" and latest == "quick":
        return "narrowed"
    return f"{first}_to_{latest}"


def _continuity_label(items: list[dict[str, Any]]) -> str:
    total_context = sum(item["context_count"] for item in items)
    if len(items) >= 4 and total_context:
        return "active_thread"
    if total_context:
        return "connected"
    return "thin"


def _history_pressure(items: list[dict[str, Any]], long_thread_count: int) -> str:
    if len(items) >= 16 or long_thread_count >= 3:
        return "high"
    if len(items) >= 8 or long_thread_count:
        return "medium"
    return "low"


def _display_reason(pressure: str, item_count: int, long_thread_count: int) -> str:
    if pressure == "high":
        return f"{item_count} history item(s) and {long_thread_count} long thread(s) should be collapsed."
    if pressure == "medium":
        return "Show recent answers first and keep older thread details folded."
    return "History is short enough to keep the first screen compact."


def _patterns_copy(
    mode_counts: Counter[str],
    depth_counts: Counter[str],
    threaded_turns: list[dict[str, Any]],
) -> str:
    mode = _dominant(mode_counts) or "auto"
    depth = _dominant(depth_counts) or "quick"
    if threaded_turns:
        return f"Recent recall mostly uses {mode}/{depth}, with threaded follow-up available."
    return f"Recent recall mostly uses {mode}/{depth}."


def _source_map_copy(source_rows: list[dict[str, Any]], items: list[dict[str, Any]]) -> str:
    if source_rows:
        return f"{len(source_rows)} source route(s) can support follow-up questions."
    if items:
        return "Recent history exists but does not expose source routes."
    return "No recall history exists yet."


def _thread_copy(rows: list[dict[str, Any]]) -> str:
    if rows:
        return f"{len(rows)} multi-turn thread(s) can be resumed."
    return "No multi-turn recall thread needs special handling."


def _question_terms(question: str) -> list[str]:
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]{2,}", question)
        if word.lower() not in _STOP_WORDS
    ]
    if words:
        return words[:10]
    compact = re.sub(r"\s+", "", question)
    return [compact[:8]] if compact else []


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\r", " ").replace("\n", " ")).strip()


def _preview(value: str, limit: int) -> str:
    cleaned = _clean_text(value)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item)]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _safe_int(value: Any, *, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _average(total: int, count: int) -> float:
    if count <= 0:
        return 0.0
    return round(total / count, 2)


def _mode(value: str) -> str:
    allowed = {"auto", "wiki", "files", "hybrid"}
    return value if value in allowed else "auto"


def _depth(value: str) -> str:
    allowed = {"quick", "deep"}
    return value if value in allowed else "quick"


def _dominant(counter: Counter[str]) -> str:
    if not counter:
        return ""
    return counter.most_common(1)[0][0]


def _gap(gap_id: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": gap_id,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


def _suggestion(suggestion_id: str, label: str, detail: str, priority: int) -> dict[str, Any]:
    return {
        "id": suggestion_id,
        "label": label,
        "detail": detail,
        "priority": priority,
    }


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
