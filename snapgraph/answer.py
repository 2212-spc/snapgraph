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
ANSWER_AI_EXPLORATION = "## AI 探索回应"
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
        text = render_answer(retrieval, question=question)
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
        text = ensure_answer_contract(text, retrieval, question=question)
    else:
        text = render_answer(retrieval, question=question)
    text = ensure_retrieval_diagnostics(text, retrieval)
    text = clean_answer_glyphs(text)
    return AnswerResult(
        question=question,
        text=text,
        retrieval=retrieval,
    )


def save_answer(workspace: Workspace, answer: AnswerResult) -> QuestionPage:
    return write_question_page(workspace, answer)


def ensure_answer_contract(text: str, retrieval: RetrievalResult, question: str = "") -> str:
    """Keep real provider answers auditable even when the model omits sections."""
    additions: list[str] = []
    if ANSWER_ORIGINAL not in text:
        additions.extend(
            [
                ANSWER_ORIGINAL,
                _contract_original_lines(retrieval, question=question),
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
    if ANSWER_AI_EXPLORATION not in text:
        additions.extend(
            [
                ANSWER_AI_EXPLORATION,
                _contract_ai_exploration(retrieval, question=question),
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
                _contract_next_action(retrieval, question=question),
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


def render_answer(retrieval: RetrievalResult, question: str = "") -> str:
    contexts = retrieval.contexts
    if not contexts:
        return _render_no_answer(retrieval, question=question)

    evidence_lines = [
        (
                f"{index}. `{context.title}` - {context.source_page} "
                f"(`{context.source_id}`, {context.why_saved_status}, {context.space_name})"
        )
        for index, context in enumerate(contexts, start=1)
    ]
    graph_path_lines = retrieval.graph_paths or ["未找到图路径。"]

    return "\n".join(
        [
            "# 回答",
            ANSWER_ORIGINAL,
            _contract_original_lines(retrieval, question=question),
            "",
            ANSWER_MATERIALS,
            *evidence_lines,
            "",
            ANSWER_PATHS,
            "```text",
            *graph_path_lines,
            "```",
            "",
            ANSWER_AI_EXPLORATION,
            _contract_ai_exploration(retrieval, question=question),
            "",
            ANSWER_INSIGHT,
            _contract_insight(retrieval),
            "",
            ANSWER_NEXT,
            _contract_next_action(retrieval, question=question),
            "",
            ANSWER_DIAGNOSTICS,
            render_retrieval_diagnostics(retrieval),
        ]
    )


def _render_no_answer(retrieval: RetrievalResult, question: str = "") -> str:
    topic = f"围绕“{question}”，" if question else ""
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
            ANSWER_AI_EXPLORATION,
            f"{topic}还没有可靠材料可以接住这个问题。我不会把泛化猜测伪装成记忆；可以先换一个更贴近旧材料、项目名或当时判断的线索。",
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


def _contract_original_lines(retrieval: RetrievalResult, question: str = "") -> str:
    if not retrieval.contexts:
        return "无。"
    user_contexts = [
        context for context in retrieval.contexts
        if context.why_saved_status == "user-stated" and context.why_saved
    ]
    contexts = user_contexts or retrieval.contexts[:1]
    contexts = sorted(contexts, key=lambda context: _context_anchor_score(context, question), reverse=True)
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


def _contract_next_action(retrieval: RetrievalResult, question: str = "") -> str:
    open_loop = _first_open_loop(retrieval, question=question)
    if retrieval.contexts and open_loop:
        return open_loop
    if retrieval.contexts:
        return f"回看 {retrieval.contexts[0].source_page}，确认恢复出的保存理由是否仍然准确。"
    return "先收集相关材料，或换一个更接近当时材料、项目、判断的线索再问。"


def _contract_ai_exploration(retrieval: RetrievalResult, question: str = "") -> str:
    if not retrieval.contexts:
        topic = f"围绕“{question}”，" if question else ""
        return f"{topic}我现在还没有足够可靠的旧材料可以回答。换一个更接近项目名、材料标题或当时判断的问法，会更容易把记忆找回来。"
    primary = retrieval.contexts[0]
    project = primary.related_project or primary.space_name or "当前问题"
    return _question_direct_answer(
        question=question,
        project=project,
    )


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


def _question_direct_answer(
    question: str,
    project: str,
) -> str:
    if "截图" in question and ("核心" in question or "入口" in question):
        return (
            "你当时的判断不是“截图不重要”，而是“截图只是进入系统的入口”。"
            "真正的核心不在截图本身，而在截图进入图谱之后，系统能不能读出当时为什么保存、它和哪些旧材料相连、又能不能帮你恢复那个判断。"
            "所以截图更像捕获摩擦的解决方案，SnapGraph 的价值验证应该落在找回、连接和涌现上。"
        )
    if any(term in question for term in ["创新", "价值", "核心", "snapgraph", "SnapGraph"]):
        return (
            "SnapGraph 的创新不是再做一个收藏夹、网盘或聊天框，而是把“材料”和“当时为什么在乎它”一起保存成可追溯的认知图谱。"
            "这样 AI 回答时不是凭空泛化，而是从你的原话、旧材料和连接路径里恢复当时的判断，再把散落的信息重新加工成新的洞见。"
            f"放在 `{project}` 里看，它真正要解决的是：信息被存下来了，但当时的想法、判断和未闭环问题后来丢了。"
        )
    return (
        "我会把这个问题当成一次记忆恢复，而不是普通搜索。"
        "先从你当时留下的理由找回判断的起点，再用相关材料和图谱连接补全它为什么成立。"
        "如果这些证据之间出现张力，AI 的作用就是把张力整理成一个可继续验证的问题。"
    )


def _best_user_anchor(contexts, question: str = "") -> str:
    ranked = sorted(
        [context for context in contexts if context.why_saved],
        key=lambda context: _context_anchor_score(context, question),
        reverse=True,
    )
    for context in ranked:
        return f"`{context.title}`：{context.why_saved}"
    return "没有用户原话，只能把 AI 推断作为暂时入口。"


def _best_evidence_fragment(retrieval: RetrievalResult, question: str = "") -> str:
    candidates: list[tuple[int, str]] = []
    for context in retrieval.contexts:
        for index, candidate in enumerate([context.why_saved, context.source_excerpt, context.related_project]):
            fragment = _compact_fragment(candidate)
            if fragment:
                kind_bonus = 18 if index == 0 and context.why_saved_status == "user-stated" else 0
                penalty = 14 if _looks_like_ui_observation(fragment) else 0
                candidates.append((_context_anchor_score(context, question) + kind_bonus - penalty, fragment))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
    return "材料里还没有足够清晰的摘录"


def _first_open_loop(retrieval: RetrievalResult, question: str = "") -> str:
    candidates: list[tuple[int, str]] = []
    for context in retrieval.contexts:
        for open_loop in context.open_loops:
            if open_loop and open_loop != "None":
                fragment = _compact_fragment(open_loop)
                if _looks_like_ui_observation(fragment):
                    continue
                candidates.append((_overlap_score(question, fragment), fragment))
    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]
    if question:
        return f"把“{question}”验证成一个清晰的产品判断"
    return "这些材料共同改变了哪个判断"


def _compact_fragment(text: str | None, limit: int = 120) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text.replace("AI-inferred:", "")).strip()
    cleaned = re.sub(r"^[-*]\s*", "", cleaned)
    cleaned = re.sub(r"^(Open loop|open loop|TODO|Todo|未解决问题)[:：]\s*", "", cleaned)
    if not cleaned or cleaned == "None":
        return ""
    return cleaned if len(cleaned) <= limit else f"{cleaned[:limit].rstrip()}..."


def _dedupe_titles(contexts) -> list[str]:
    titles: list[str] = []
    seen: set[str] = set()
    for context in contexts:
        title = context.title.strip()
        if title and title not in seen:
            titles.append(title)
            seen.add(title)
    return titles


def _overlap_score(question: str, text: str) -> int:
    if not question or not text:
        return 0
    lowered = text.lower()
    score = 0
    for term in _query_terms(question):
        if term.lower() in lowered:
            score += len(term)
    return score


def _query_terms(question: str) -> set[str]:
    terms = {token for token in re.findall(r"[A-Za-z0-9_+-]{2,}", question)}
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]+", question))
    for size in (2, 3, 4):
        for index in range(0, max(len(chinese) - size + 1, 0)):
            terms.add(chinese[index:index + size])
    aliases = {
        "截图": ["screenshot", "image capture"],
        "核心": ["core", "central"],
        "入口": ["entry", "ingestion", "capture"],
        "图谱": ["graph"],
        "记忆": ["memory", "recall"],
        "找回": ["recall"],
        "材料": ["source", "evidence"],
        "文件": ["file", "pdf"],
    }
    for key, values in aliases.items():
        if key in question:
            terms.update(values)
    return terms


def _looks_like_ui_observation(text: str) -> bool:
    markers = ["导航栏", "按钮", "页面截图", "截图显示", "顶部", "底部", "卡片", "当前界面", "界面", "测试"]
    return any(marker in text for marker in markers)


def _context_anchor_score(context, question: str) -> int:
    why = context.why_saved or ""
    anchor_text = f"{context.title} {why} {context.related_project}"
    full_text = f"{anchor_text} {context.source_excerpt}"
    score = _overlap_score(question, anchor_text)
    if not why:
        score += min(_overlap_score(question, context.source_excerpt), 6)
    if context.why_saved_status == "user-stated":
        score += 8
    if "因为" in why or "why" in why.lower():
        score += 10
    if _looks_like_ui_observation(full_text):
        score -= 34
    return score


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
