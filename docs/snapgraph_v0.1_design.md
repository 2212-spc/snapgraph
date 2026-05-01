# SnapGraph v0.1 Design

## One-Sentence Definition

SnapGraph is a Cognitive LLM Wiki: a personal knowledge base that preserves not only saved materials, but also the reason, uncertainty, open loops, and graph relationships around why those materials mattered.

## Core Product Claim

Normal knowledge tools help the user find information again. SnapGraph should help the user recover the past cognitive context behind that information:

- why did I save this?
- what project or question was it connected to?
- what judgment did it support?
- what open loop did it leave behind?
- what should I do with it now?

## Design Lineage

SnapGraph starts from a file-based LLM Wiki pattern:

```text
immutable raw sources
  -> maintained Markdown wiki
  -> index.md content map
  -> log.md operation timeline
```

SnapGraph extends it in four steps:

```text
LLM Wiki
  -> Cognitive Wiki
  -> Graph Wiki
  -> Hybrid GraphRAG
  -> Demo UI
```

The first version should validate the core value before moving into screenshot capture, mobile capture, on-device models, Neo4j, or 3D graphs.

## V0.1 Boundary

Build first:

- Python CLI
- file-based workspace
- Markdown/text ingestion
- source wiki pages
- cognitive context
- graph.json and SQLite metadata
- keyword plus graph retrieval
- deterministic MockLLM
- lint diagnostics
- FastAPI + Vue local web demo

Do not build yet:

- mobile app
- Neo4j
- 3D graph visualization
- complex agent framework
- dependency on a real LLM for tests
- screenshot-first product experience
- production PDF ingestion

## Workspace Shape

After `snapgraph init`, the current directory should contain:

```text
.my_snapgraph/
├── raw/
│   ├── screenshots/
│   ├── docs/
│   ├── pdfs/
│   ├── webpages/
│   └── notes/
├── wiki/
│   ├── index.md
│   ├── log.md
│   ├── sources/
│   ├── concepts/
│   ├── people/
│   ├── projects/
│   ├── thoughts/
│   ├── tasks/
│   └── questions/
├── memory/
│   ├── graph.json
│   └── snapgraph.sqlite
└── config.yaml
```

## Data Model

### Source

```python
@dataclass
class Source:
    id: str
    path: str
    type: str
    imported_at: str
    content_hash: str
    summary: str | None = None
```

### Cognitive Context

```python
@dataclass
class CognitiveContext:
    source_id: str
    why_saved: str
    why_saved_status: str  # user-stated | AI-inferred | unknown
    related_project: str | None
    open_loops: list[str]
    future_recall_questions: list[str]
    importance: str  # low | medium | high
    confidence: float
```

The most important product rule is that `user-stated`, `AI-inferred`, and `unknown` must remain visibly distinct. SnapGraph must not fabricate certainty about the user's memory.

### Graph

Initial node types:

- source
- person
- project
- concept
- thought
- task
- question

Initial edge types:

- mentions
- belongs_to
- supports
- contradicts
- triggered_thought
- related_to
- follow_up
- evidence_for

Each edge should carry `evidence_source_id` when possible.

## Implementation Phases

### Phase 1: LLM Wiki Foundation

Goal: ingest markdown/text into immutable raw files and generated source pages.

Commands:

- `snapgraph init`
- `snapgraph ingest <path>`
- `snapgraph lint`

Success:

- workspace exists
- source copied into raw
- source page generated in wiki/sources
- index.md updated
- log.md appended
- lint checks the basic wiki shape

### Phase 2: Cognitive Context

Goal: make saved reasons first-class.

Command:

- `snapgraph ingest <path> --why "..."`

Success:

- user-supplied why is preserved exactly
- missing why is marked AI-inferred, not user-stated
- open loops and future recall questions are stored
- SQLite stores cognitive contexts

### Phase 3: Graph Wiki

Goal: make the wiki machine-readable as a graph.

Success:

- graph.json stores nodes and edges
- SQLite mirrors sources, contexts, nodes, edges
- every source gets a source node
- why_saved becomes a thought node
- future questions become question nodes
- open loops become task nodes
- graph diagnostics print node/edge counts, hubs, orphans, and warnings

### Phase 4: Ask

Goal: answer fuzzy recall questions using wiki pages and graph paths.

Retrieval v0:

- keyword search over wiki pages
- match graph labels
- expand matched nodes by one hop
- collect source pages and thought nodes

Answer format:

- direct answer
- recovered cognitive context
- evidence sources
- graph paths
- suggested next action
- retrieval diagnostics

### Phase 5: Hybrid Retrieval

Goal: combine keyword, optional embeddings, graph proximity, and recency.

Suggested scoring:

```text
score = 0.4 * keyword_score
      + 0.3 * vector_score
      + 0.2 * graph_proximity_score
      + 0.1 * recency_score
```

Use deterministic mock embeddings in tests.

### Phase 6: Lint

Goal: make long-term memory auditable.

Check:

- required workspace files
- source page sections
- cognitive status labels
- future recall questions
- source traceability
- graph source nodes
- broken edges
- orphans
- duplicate labels

### Phase 7: Demo UI

Goal: show the core value quickly.

Phase 7.1 uses FastAPI + Vue as the main demo surface. The older Streamlit app is experimental/legacy.

Main UI surfaces:

- Recall workspace
- Memory browser
- Evidence graph
- Cognitive report
- Ingest

Demo story:

1. load memory material
2. recover a past judgment from a vague question
3. inspect user-stated vs AI-inferred context
4. inspect evidence sources and graph paths
5. save useful answers and reports back into the wiki
6. lint keeps the memory base healthy

### Phase 8: Screenshot Ingestion

Goal: treat screenshots as one source type, not as the product foundation.

Start with manual image ingestion and placeholder descriptions when no VLM provider exists.

## Suggested Project Structure

```text
snapgraph/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── snapgraph/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── workspace.py
│   ├── ingest.py
│   ├── parsers.py
│   ├── wiki.py
│   ├── graph_store.py
│   ├── retrieval.py
│   ├── answer.py
│   ├── linting.py
│   ├── diagnostics.py
│   ├── llm.py
│   ├── api.py
│   └── static/index.html
├── prompts/
├── tests/
└── examples/
```

## Demo Dataset

Use 8 mock markdown/text sources before any private real data:

- note_snapgraph_idea.md
- note_llm_wiki.md
- note_graphrag.md
- note_methodology_anxiety.md
- note_advisor_feedback.md
- article_personal_knowledge_management.md
- meeting_research_plan.md
- todo_open_loops.md

Good demo questions:

- 我为什么要从 LLM Wiki 开始？
- 我之前为什么觉得截图不是核心，而只是入口？
- 我对端侧模型的判断是什么？
- 这个项目的 AI 必然性在哪里？
- 我现在最应该补的 open loop 是什么？
- 我之前反复担心的问题是什么？

## Main Risk Controls

- Do not let AI-inferred memory look like user-stated memory.
- Keep raw sources immutable and traceable.
- Keep every answer tied to source evidence and graph paths.
- Keep graph.json explainable before optimizing retrieval quality.
- Make lint a core workflow, not an afterthought.
- Build the demo around fuzzy recall, not generic document search.

## Next Recommended Step

See `docs/snapgraph_phase7_1_status_evaluation.md` for the current implementation and evaluation status.

Next recommended implementation phase:

1. improve the five-minute demo path
2. make MockLLM answers less template-like
3. make high-value graph paths come from actual graph traversal
4. document API and workspace schemas
5. add curated wiki write-back beyond saved question pages
