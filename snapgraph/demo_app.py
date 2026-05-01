from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path

import streamlit as st

from snapgraph.answer import answer_question, save_answer
from snapgraph.demo_data import DEMO_QUESTIONS, demo_sources_dir, load_demo_dataset
from snapgraph.diagnostics import format_lint_result
from snapgraph.graph_store import graph_diagnostics, load_graph
from snapgraph.ingest import ingest_source
from snapgraph.linting import lint_workspace
from snapgraph.llm_providers import _resolve_llm
from snapgraph.report import write_graph_report
from snapgraph.wiki import question_pages, source_pages
from snapgraph.workspace import Workspace, create_workspace, get_workspace


st.set_page_config(
    page_title="SnapGraph · 认知知识图谱",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; margin-bottom: 0; color: #1a1a2e; }
    .sub-header { font-size: 1rem; color: #6b7280; margin-top: 0; }
    .metric-card { background: #f8fafc; border-radius: 12px; padding: 20px; text-align: center;
                    border: 1px solid #e2e8f0; }
    .metric-value { font-size: 2rem; font-weight: 700; color: #1e40af; }
    .metric-label { font-size: 0.85rem; color: #64748b; margin-top: 4px; }
    .status-ok { color: #16a34a; font-weight: 600; }
    .status-warn { color: #d97706; font-weight: 600; }
    .status-error { color: #dc2626; font-weight: 600; }
    .section-title { font-size: 1.3rem; font-weight: 600; color: #1e293b; margin-top: 1.5rem;
                      padding-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0; }
    .user-stated { background: #dcfce7; color: #166534; padding: 2px 8px; border-radius: 4px;
                    font-size: 0.8rem; font-weight: 600; }
    .ai-inferred { background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 4px;
                    font-size: 0.8rem; font-weight: 600; }
    .unknown-status { background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px;
                       font-size: 0.8rem; font-weight: 600; }
    .stButton > button { border-radius: 8px; font-weight: 500; }
    .primary-btn > button { background: #1e40af; color: white; border: none; }
    .stExpander { border: 1px solid #e2e8f0; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)


def main() -> None:
    workspace = get_workspace()
    create_workspace(workspace)

    st.markdown('<p class="main-header">🧠 SnapGraph</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">认知型知识库 — 不仅保存信息，更保存<strong>为什么这个信息重要</strong></p>',
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### ⚡ 快速开始")
        if st.button("📦 加载演示数据集", use_container_width=True, type="primary"):
            with st.spinner("正在构建知识图谱..."):
                result = load_demo_dataset(workspace)
            st.success(
                f"已摄入 {result.ingested} 个来源，"
                f"保存 {result.saved_answers} 条问答，"
                f"生成认知报告"
            )
            st.rerun()

        st.divider()
        st.markdown("### 📍 导航")
        page = st.radio(
            "选择页面",
            ["🏠 总览", "📥 摄入来源", "📚 知识库浏览", "🕸️ 知识图谱", "💬 提问", "📊 认知报告"],
            label_visibility="collapsed",
        )

        st.divider()
        st.caption("SnapGraph v0.1 · Cognitive LLM Wiki")

    if page == "🏠 总览":
        _dashboard(workspace)
    elif page == "📥 摄入来源":
        _ingest(workspace)
    elif page == "📚 知识库浏览":
        _wiki_browser(workspace)
    elif page == "🕸️ 知识图谱":
        _graph_view(workspace)
    elif page == "💬 提问":
        _ask(workspace)
    elif page == "📊 认知报告":
        _report_and_lint(workspace)


# ── Dashboard ──

def _dashboard(workspace: Workspace) -> None:
    metrics = _dashboard_metrics(workspace)
    st.markdown('<p class="section-title">📊 工作区概况</p>', unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    _metric_card(c1, "📄", metrics["sources"], "来源文件")
    _metric_card(c2, "💬", metrics["saved_questions"], "已保存问答")
    _metric_card(c3, "🕸️", metrics["nodes"], "图节点")
    _metric_card(c4, "🔗", metrics["edges"], "图连接")
    _metric_card(c5, "✅" if metrics["lint_status"] == "OK" else "⚠️",
                  metrics["lint_status"], "健康检查", metrics["lint_status"])

    if metrics["sources"] == 0:
        st.info("👈 工作区还是空的，点击左侧 **加载演示数据集** 按钮快速体验。")
        return

    left, right = st.columns([1, 2])
    with left:
        st.markdown('<p class="section-title">🧠 认知语境构成</p>', unsafe_allow_html=True)
        status_counts = _context_status_counts(workspace)
        for status, count in sorted(status_counts.items()):
            label = {"user-stated": "用户明确陈述", "AI-inferred": "AI 推断", "unknown": "未知"}.get(status, status)
            color = {"user-stated": "#16a34a", "AI-inferred": "#d97706", "unknown": "#94a3b8"}.get(status, "#64748b")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;padding:8px 0;'
                f'border-bottom:1px solid #f1f5f9">'
                f'<span style="color:{color};font-weight:600">● {label}</span>'
                f'<span style="font-weight:700">{count}</span></div>',
                unsafe_allow_html=True,
            )

    with right:
        st.markdown('<p class="section-title">📈 认知报告预览</p>', unsafe_allow_html=True)
        report_path = workspace.wiki_dir / "graph_report.md"
        if report_path.exists():
            text = report_path.read_text(encoding="utf-8")
            lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#")][:25]
            st.markdown("\n".join(lines) if lines else "报告为空。")
        else:
            st.info("尚未生成认知报告。前往 **📊 认知报告** 页面生成。")


def _metric_card(col, icon: str, value, label: str, status: str = "") -> None:
    color = {"OK": "#16a34a", "WARN": "#d97706", "ERROR": "#dc2626"}.get(status, "#1e40af")
    with col:
        st.markdown(
            f'<div class="metric-card">'
            f'<div style="font-size:1.5rem">{icon}</div>'
            f'<div class="metric-value" style="color:{color}">{value}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )


# ── Ingest ──

def _ingest(workspace: Workspace) -> None:
    st.markdown('<p class="section-title">📥 摄入新来源</p>', unsafe_allow_html=True)
    st.caption("添加文件到知识库。保存时将同时记录文件内容和你对「为什么保存它」的说明。")

    why = st.text_area(
        "为什么保存这个文件？（可选但强烈推荐）",
        placeholder="例如：这篇笔记记录了开题时导师对方法论的建议，我需要保留当时的讨论上下文...",
        height=70,
    )

    tab1, tab2 = st.tabs(["上传文件", "选择演示来源"])
    with tab1:
        uploaded = st.file_uploader("选择 Markdown 或纯文本文件", type=["md", "markdown", "txt"])
        if uploaded and st.button("摄入上传的文件", type="primary"):
            with tempfile.TemporaryDirectory() as tmpdir:
                source_path = Path(tmpdir) / uploaded.name
                source_path.write_bytes(uploaded.getvalue())
                result = ingest_source(workspace, source_path, why=why or None)
            st.success(f"已创建来源页面：`{result.page.relative_page_path}`")
            with st.expander("查看生成的来源页面"):
                st.markdown(result.page.absolute_page_path.read_text(encoding="utf-8"))

    with tab2:
        demo_files = sorted(demo_sources_dir().glob("*.md"))
        selected = st.selectbox("选择一个演示来源", demo_files, format_func=lambda p: f"📄 {p.stem}")
        if selected and st.button("摄入选中的来源", type="primary"):
            result = ingest_source(workspace, selected, why=why or None)
            st.success(f"已创建来源页面：`{result.page.relative_page_path}`")
            with st.expander("查看生成的来源页面"):
                st.markdown(result.page.absolute_page_path.read_text(encoding="utf-8"))


# ── Wiki Browser ──

def _wiki_browser(workspace: Workspace) -> None:
    st.markdown('<p class="section-title">📚 知识库浏览</p>', unsafe_allow_html=True)
    st.caption("浏览所有已保存的来源页面、问答记录和认知报告。每页都包含认知语境标注。")

    pages = source_pages(workspace) + question_pages(workspace)
    report_path = workspace.wiki_dir / "graph_report.md"
    if report_path.exists():
        pages.append(report_path)

    if not pages:
        st.info("知识库中还没有页面。请先摄入来源。")
        return

    page_type = st.radio("筛选", ["全部", "来源页面", "问答记录", "认知报告"], horizontal=True)
    if page_type == "来源页面":
        pages = [p for p in pages if "sources" in str(p)]
    elif page_type == "问答记录":
        pages = [p for p in pages if "questions" in str(p)]
    elif page_type == "认知报告":
        pages = [p for p in pages if "report" in str(p)]

    selected = st.selectbox(
        "选择页面",
        pages,
        format_func=lambda p: {
            "sources": "📄 ",
            "questions": "💬 ",
            "graph_report": "📊 ",
        }.get(p.parent.name, "") + p.stem,
    )
    if selected:
        st.markdown(selected.read_text(encoding="utf-8"))


# ── Graph View ──

def _graph_view(workspace: Workspace) -> None:
    st.markdown('<p class="section-title">🕸️ 知识图谱</p>', unsafe_allow_html=True)
    st.caption("每个来源、想法、项目、问题和待办事项都是一个节点。连线表示它们之间的关系。")

    diag = graph_diagnostics(workspace)
    if diag.node_count == 0:
        st.info("图中还没有节点。请先摄入来源。")
        return

    c1, c2 = st.columns([2, 1])
    with c1:
        graph = load_graph(workspace)
        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])
        try:
            from pyvis.network import Network
            import streamlit.components.v1 as components

            net = Network(height="480px", width="100%", directed=True)
            colors = {"source": "#4E79A7", "thought": "#59A14F", "project": "#F28E2B",
                      "question": "#B07AA1", "task": "#E15759"}
            for node in nodes[:160]:
                node_type = node.get("type", "unknown")
                net.add_node(
                    node["id"],
                    label=node.get("label", node["id"])[:50],
                    title=json.dumps(node, ensure_ascii=False, indent=2),
                    color=colors.get(node_type, "#9C755F"),
                )
            node_ids = {n["id"] for n in nodes[:160]}
            for edge in edges:
                if edge.get("source") in node_ids and edge.get("target") in node_ids:
                    net.add_edge(
                        edge["source"], edge["target"],
                        label=edge.get("relation", ""),
                        title=json.dumps(edge, ensure_ascii=False, indent=2),
                    )
            components.html(net.generate_html(), height=500, scrolling=False)
        except Exception:
            st.warning("图谱可视化加载失败。")

    with c2:
        st.metric("节点总数", diag.node_count)
        st.metric("连接总数", diag.edge_count)
        st.markdown("**节点类型分布**")
        for ntype, count in sorted(diag.node_types.items()):
            label = {"source": "📄 来源", "thought": "💭 想法", "project": "📁 项目",
                     "question": "❓ 问题", "task": "✅ 任务"}.get(ntype, ntype)
            st.markdown(f"{label}：**{count}**")

        st.markdown("**核心枢纽（连接最多）**")
        for label, degree in diag.top_hubs[:5]:
            st.markdown(f"· {label[:40]} — {degree} 条连接")

        if diag.orphans:
            st.markdown("**⚠️ 孤立节点**")
            for orphan in diag.orphans:
                st.markdown(f"· {orphan[:40]}")


# ── Ask ──

def _ask(workspace: Workspace) -> None:
    st.markdown('<p class="section-title">💬 向知识库提问</p>', unsafe_allow_html=True)
    st.caption(
        "输入一个模糊的问题——SnapGraph 会在你保存的来源和图关系中寻找答案，"
        "并明确标注哪些是你自己说的、哪些是 AI 推断的。"
    )

    suggestion = DEMO_QUESTIONS[0] if DEMO_QUESTIONS else ""
    col1, col2 = st.columns([4, 1])
    with col1:
        question = st.text_input("你的问题", value=suggestion, placeholder="例如：我为什么要从 LLM Wiki 开始？")
    with col2:
        save = st.checkbox("保存到知识库", value=True)
        st.write("")
        search_btn = st.button("🔍 提问", type="primary", use_container_width=True)

    if not search_btn:
        return

    with st.spinner("正在检索知识库并综合答案..."):
        try:
            result = answer_question(workspace, question, llm=_resolve_llm(workspace))
        except Exception as exc:
            st.error(f"提问失败：{exc}")
            return

    st.divider()
    st.markdown(result.text)

    st.divider()
    st.markdown("### 🔬 检索过程对照：关键词 vs 图谱")

    diag = result.retrieval.diagnostics
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("关键词命中", diag.keyword_hits)
    k2.metric("图谱节点命中", diag.graph_node_hits)
    k3.metric("图谱展开节点", diag.expanded_nodes)
    k4.metric("使用的来源页", diag.source_pages_used)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**📄 证据来源**")
        if result.retrieval.contexts:
            st.table([{
                "来源": ctx.title,
                "保存原因的状态": ctx.why_saved_status,
                "关联项目": ctx.related_project or "-",
            } for ctx in result.retrieval.contexts])
        else:
            st.info("未找到匹配的来源。")

    with c2:
        st.markdown("**🕸️ 图谱路径（语境关系）**")
        if result.retrieval.graph_paths:
            for path in result.retrieval.graph_paths:
                st.text(path)
        else:
            st.info("未找到图谱路径。")

    if save:
        page = save_answer(workspace, result)
        st.success(f"已保存问答到：`{page.relative_page_path}`")


# ── Report & Lint ──

def _report_and_lint(workspace: Workspace) -> None:
    st.markdown('<p class="section-title">📊 认知报告与健康检查</p>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.subheader("📊 认知图谱报告")
        st.caption("综合你所有的来源、问答、图结构和认知语境，生成一份可读的认知状态总览。")
        if st.button("生成报告", type="primary", use_container_width=True):
            with st.spinner("正在生成..."):
                report = write_graph_report(workspace)
            st.success(f"报告已生成：`{report.relative_page_path}`")

        report_path = workspace.wiki_dir / "graph_report.md"
        if report_path.exists():
            with st.expander("查看完整报告"):
                st.markdown(report_path.read_text(encoding="utf-8"))

    with right:
        st.subheader("🩺 健康检查")
        st.caption("检查知识库的完整性：来源追溯、图一致性、认知标注规范。")
        lint = lint_workspace(workspace)
        status_color = {"OK": "green", "WARN": "orange", "ERROR": "red"}.get(lint.status, "gray")
        st.markdown(f"### 状态：:{status_color}[{lint.status}]")

        if lint.errors:
            st.error("\n".join(f"· {e}" for e in lint.errors))
        else:
            st.success("无错误")

        if lint.warnings:
            st.warning("\n".join(f"· {w}" for w in lint.warnings))
        else:
            st.success("无警告")


# ── Helpers ──

def _dashboard_metrics(workspace: Workspace) -> dict:
    diag = graph_diagnostics(workspace)
    lint = lint_workspace(workspace)
    return {
        "sources": _count_rows(workspace, "sources"),
        "saved_questions": len(question_pages(workspace)),
        "nodes": diag.node_count,
        "edges": diag.edge_count,
        "lint_status": lint.status,
    }


def _context_status_counts(workspace: Workspace) -> dict[str, int]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute(
            "SELECT why_saved_status, COUNT(*) FROM cognitive_contexts GROUP BY why_saved_status"
        ).fetchall()
    return {row[0]: row[1] for row in rows}


def _count_rows(workspace: Workspace, table: str) -> int:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


if __name__ == "__main__":
    main()
