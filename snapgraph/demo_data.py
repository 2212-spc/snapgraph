from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .answer import answer_question, save_answer
from .ingest import ingest_source
from .llm import LLMProvider, MockLLM
from .models import DEFAULT_GRAPH_SPACE_ID
from .report import write_graph_report
from .workspace import Workspace, create_workspace


DEMO_WHYS = {
    "note_llm_wiki.md": "我保存它是因为 SnapGraph 需要继承 LLM Wiki 的 raw/wiki/index/log 工作流。",
    "note_graphrag.md": "我保存它是因为模糊召回需要图谱路径，而不只是关键词搜索。",
    "note_screenshot_entry.md": "我保存它是因为截图应该先作为入口，而不是 v0.1 的核心价值验证。",
}

DEMO_QUESTIONS = [
    "我为什么要从 LLM Wiki 开始？",
    "我之前为什么觉得截图不是核心，而只是入口？",
    "我对端侧模型的判断是什么？",
    "这个项目的 AI 必然性在哪里？",
    "我现在最应该处理的 open loop 是什么？",
]

SAVED_DEMO_QUESTIONS = DEMO_QUESTIONS[:2]


@dataclass(frozen=True)
class DemoLoadResult:
    ingested: int
    skipped: int
    saved_answers: int
    report_path: str


def demo_sources_dir() -> Path:
    package_root = Path(__file__).resolve().parents[1]
    candidates = [
        Path.cwd() / "examples" / "demo_sources",
        package_root / "examples" / "demo_sources",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("Could not find examples/demo_sources.")


def load_demo_dataset(
    workspace: Workspace,
    llm: LLMProvider | None = None,
) -> DemoLoadResult:
    create_workspace(workspace)
    llm = llm or MockLLM()
    existing_hashes = _existing_content_hashes(workspace)
    ingested = 0
    skipped = 0

    for source_path in sorted(demo_sources_dir().glob("*.md")):
        content_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        if content_hash in existing_hashes:
            skipped += 1
            continue
        ingest_source(
            workspace,
            source_path,
            why=DEMO_WHYS.get(source_path.name),
            llm=llm,
            space_id=DEFAULT_GRAPH_SPACE_ID,
        )
        existing_hashes.add(content_hash)
        ingested += 1

    saved_answers = 0
    existing_questions = _existing_saved_questions(workspace)
    for question in SAVED_DEMO_QUESTIONS:
        if question in existing_questions:
            continue
        save_answer(workspace, answer_question(workspace, question))
        existing_questions.add(question)
        saved_answers += 1

    report = write_graph_report(workspace)
    return DemoLoadResult(
        ingested=ingested,
        skipped=skipped,
        saved_answers=saved_answers,
        report_path=report.relative_page_path,
    )


def _existing_content_hashes(workspace: Workspace) -> set[str]:
    with sqlite3.connect(workspace.sqlite_path) as conn:
        rows = conn.execute("SELECT content_hash FROM sources").fetchall()
    return {row[0] for row in rows}


def _existing_saved_questions(workspace: Workspace) -> set[str]:
    questions_dir = workspace.wiki_dir / "questions"
    questions: set[str] = set()
    for page_path in questions_dir.glob("*.md"):
        text = page_path.read_text(encoding="utf-8")
        question = _section_text(text, "## Question")
        if question:
            questions.add(question)
    return questions


def _section_text(text: str, heading: str) -> str:
    if heading not in text:
        return ""
    tail = text.split(heading, 1)[1].lstrip()
    if "\n## " in tail:
        tail = tail.split("\n## ", 1)[0]
    return " ".join(tail.strip().split())
