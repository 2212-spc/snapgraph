from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


INBOX_GRAPH_SPACE_ID = "inbox"
DEFAULT_GRAPH_SPACE_ID = "default"
USER_GUIDED_CONTEXT_STATUSES = {"user-stated", "user-guided"}


def is_user_guided_status(status: str) -> bool:
    return status in USER_GUIDED_CONTEXT_STATUSES


def is_ai_inferred_status(status: str) -> bool:
    return status == "AI-inferred"


@dataclass(frozen=True)
class ParsedSource:
    path: Path
    source_type: str
    title: str
    text: str
    content_hash: str


@dataclass(frozen=True)
class Source:
    id: str
    path: str
    type: str
    imported_at: str
    content_hash: str
    title: str
    original_filename: str
    summary: str | None = None
    graph_space_id: str = DEFAULT_GRAPH_SPACE_ID


@dataclass(frozen=True)
class CognitiveContext:
    source_id: str
    why_saved: str
    why_saved_status: str
    related_project: str | None
    open_loops: list[str]
    future_recall_questions: list[str]
    importance: str
    confidence: float


@dataclass(frozen=True)
class GraphNode:
    id: str
    type: str
    label: str
    properties: dict
    graph_space_id: str = DEFAULT_GRAPH_SPACE_ID
    status: str = "confirmed"


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str
    relation: str
    evidence_source_id: str | None
    confidence: float
    graph_space_id: str = DEFAULT_GRAPH_SPACE_ID
    status: str = "confirmed"


@dataclass(frozen=True)
class GraphDiagnostics:
    node_count: int
    edge_count: int
    node_types: dict[str, int]
    top_hubs: list[tuple[str, int]]
    orphans: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class RetrievalDiagnostics:
    keyword_hits: int
    graph_node_hits: int
    expanded_nodes: int
    source_pages_used: int
    user_stated_contexts: int
    ai_inferred_contexts: int
    top_candidate_reasons: list[str]
    graph_expansion_truncated: bool


@dataclass(frozen=True)
class RetrievedContext:
    source_id: str
    source_page: str
    title: str
    why_saved: str
    why_saved_status: str
    related_project: str | None
    open_loops: list[str]
    future_recall_questions: list[str]
    graph_space_id: str = DEFAULT_GRAPH_SPACE_ID
    space_name: str = "Default"
    source_excerpt: str = ""


@dataclass(frozen=True)
class RetrievalResult:
    question: str
    contexts: list[RetrievedContext]
    graph_paths: list[str]
    diagnostics: RetrievalDiagnostics


@dataclass(frozen=True)
class AnswerResult:
    question: str
    text: str
    retrieval: RetrievalResult


@dataclass(frozen=True)
class QuestionPage:
    id: str
    question: str
    relative_page_path: str
    absolute_page_path: Path


@dataclass(frozen=True)
class SourcePage:
    source: Source
    relative_page_path: str
    absolute_page_path: Path


@dataclass(frozen=True)
class IngestResult:
    source: Source
    cognitive_context: CognitiveContext
    raw_path: Path
    page: SourcePage
    warnings: list[str]
    routing_suggestion_id: str | None = None


@dataclass(frozen=True)
class LintResult:
    status: str
    errors: list[str]
    warnings: list[str]
