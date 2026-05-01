# SnapGraph Phase 7.1 Status and Evaluation

Date: 2026-05-01

## Executive Summary

SnapGraph has reached a local v0.1 demo baseline:

```text
ingest -> cognitive context -> graph -> ask -> ask --save -> report -> lint -> web demo
```

It is no longer just a paper design. The file-based LLM Wiki loop works locally, has CLI/API/UI entry points, and passes the current test suite.

Latest verified baseline:

```text
54 passed, 2 warnings
```

The two warnings are FastAPI `on_event` deprecation warnings. They do not affect current behavior.

The product value is partially proven:

- SnapGraph can preserve user-stated saved reasons.
- It can label AI-inferred reasons separately.
- It can create graph paths from sources to thoughts, projects, questions, and tasks.
- It can answer fuzzy recall questions with evidence sources and graph paths.
- It can write useful answers and graph reports back into the wiki.

The remaining gap is not that the system fails to run. The gap is quality and trust:

- MockLLM answers still feel template-like.
- `graph_insights` is still partly metadata summarization, not true graph analysis.
- The UI needs a tighter five-minute demo script.
- The wiki is not yet a continuously curated working memory.
- Schema and API contracts need stronger documentation.

## Current Design

SnapGraph is a Cognitive LLM Wiki.

It starts from the LLM Wiki pattern:

```text
immutable raw sources
  -> maintained Markdown wiki
  -> index.md content map
  -> log.md operation timeline
  -> query/ask
  -> useful answer write-back
  -> lint
```

SnapGraph extends this with:

- Cognitive Context: `why_saved`, `why_saved_status`, `open_loops`, `future_recall_questions`, `related_project`, `confidence`.
- Graph Wiki: `graph.json` plus SQLite `nodes` and `edges`.
- Evidence paths: source -> thought -> project, source -> question/task.
- Retrieval diagnostics: keyword hits, graph node hits, expanded nodes, source pages used.
- Cognitive Graph Report: project clusters, review paths, cognitive gaps, audit trail.
- Web demo: FastAPI + Vue static UI focused on recall.

The primary product claim remains:

```text
Normal tools help the user find information again.
SnapGraph helps the user recover why the information mattered.
```

## Implemented Surface

CLI commands:

```bash
snapgraph init
snapgraph ingest <path> --why "optional user note"
snapgraph ask "question"
snapgraph ask "question" --save
snapgraph graph
snapgraph report
snapgraph lint
snapgraph load-demo
snapgraph demo
snapgraph serve
snapgraph config show
snapgraph config set-llm-provider <mock|deepseek|anthropic>
```

Workspace:

```text
.my_snapgraph/
├── raw/
├── wiki/
│   ├── index.md
│   ├── log.md
│   ├── sources/
│   ├── questions/
│   └── graph_report.md
├── memory/
│   ├── graph.json
│   └── snapgraph.sqlite
├── schema/
│   └── AGENTS.md
└── config.yaml
```

API surface currently used by the demo:

```text
GET  /api/workspace
GET  /api/sources
GET  /api/sources/{source_id}
POST /api/ingest
GET  /api/graph
POST /api/ask
GET  /api/report
POST /api/report/generate
GET  /api/lint
GET  /api/questions
GET  /api/questions/{question_id}
POST /api/demo/load
GET  /api/config
PUT  /api/config
GET  /api/demo/questions
```

## LLM Wiki Alignment

What is working:

- Raw source traceability exists through copied raw files, raw path, original filename, and content hash.
- Source pages, saved question pages, and graph reports are maintained as Markdown wiki pages.
- `index.md` is updated for sources, questions, and reports.
- `log.md` records parseable append-only JSON events for ingest, ask save, and report generation.
- `snapgraph lint` checks workspace shape, source page fields, question page evidence, index dead links, log events, SQLite drift, graph JSON, duplicate hashes, and source traceability.
- `ask --save` writes useful answers back into `wiki/questions/`.
- `report` writes `wiki/graph_report.md`.

Where it still falls short of the LLM Wiki spirit:

- Raw immutability is enforced by hash checking, not by file permissions or content-addressed storage.
- Wiki pages are mostly generated views; the system does not yet curate/update concept/project/thought pages after useful questions.
- `index.md` is still a structured list, not yet a rich content map with project and concept navigation.
- `log.md` is append-style, but not tamper-proof and not replayable.
- Schema discipline is mostly soft: `schema/AGENTS.md` exists, but there is no JSON Schema for frontmatter, graph, or log events.
- Retrieval is still v0: keyword + aliases + graph one-hop expansion, not Hybrid GraphRAG with embeddings or span-level source excerpts.
- Real LLM providers may produce text that weakens the evidence boundary; SnapGraph appends diagnostics but does not yet validate provider answer structure.
- Write-back is currently saved-answer write-back, not full wiki maintenance.

## Graphify Alignment

What SnapGraph has borrowed well:

- A human-readable report as a navigation artifact.
- Audit-trail language around confidence and evidence.
- A graph JSON file that can be inspected independently.
- Top hubs, review paths, suggested questions, and cognitive gaps.
- UI flow that uses graph/report as explanation, not just storage.

What should not be copied into v0.1:

- AST/tree-sitter extraction.
- Full Leiden/community detection.
- MCP server/hooks.
- Video/audio/image-heavy multimodal pipeline.
- Codebase-oriented "god node" language.

What is still weak:

- `graph_insights()` currently uses SQLite cognitive contexts heavily; the graph is mainly used for source degree.
- `high_value_review_paths` are generated from context fields, not by verifying actual paths through the graph.
- `bridge_sources` mostly counts signals and degree; it does not yet find real cross-project bridges.
- Top hubs include mechanical nodes unless filtered by type or role.
- There is no explicit Graphify-style evidence label on edges such as `user_stated`, `ai_inferred`, `structural`, `duplicate`, or `ambiguous`.
- Report sections `Confidence & Audit Trail` and `Honest Audit Trail` overlap.

## Web Demo Status

Current main demo stack:

```text
FastAPI + static Vue + ECharts
```

`snapgraph demo` starts the local server. In the current environment, `8501` was already occupied by an older service, so the newest server was verified on:

```text
http://127.0.0.1:8502/
```

Verified API state from that service:

```text
sources: 9
saved_questions: 2
nodes: 52
edges: 65
lint_status: OK
```

What improved in Phase 7.1:

- The first screen is now a recall workspace, not a metrics dashboard.
- It surfaces user-stated saved reasons first.
- It provides a guided recall loop.
- Ask results are split into answer, evidence, graph paths, and diagnostics.
- Saved question detail no longer 404s.
- The graph page includes project clusters, open loops, and low-confidence contexts.

Remaining UI/product issues:

- The demo still needs a more explicit "recommended path" for new users.
- Preset questions are present, but their value is not explained.
- Graph paths are still long strings; they should become readable evidence-chain cards.
- Diagnostics are developer-oriented; the UI should translate them into "why this answer is trustworthy".
- `Save answer` is exposed as a technical operation; for a demo it should be framed as "make this part of the wiki memory".
- The answer text from MockLLM still feels like a field template.

Browser note:

The in-app browser was open at `http://127.0.0.1:8502/`, but the Browser Use Node REPL execution tool was not exposed in this session. Therefore this evaluation used API, HTTP, CLI, static HTML/code inspection, and sub-agent review rather than direct click/screenshot automation.

## Stress Evaluation

An isolated evaluation workspace was created at:

```text
/tmp/snapgraph_phase7_1_eval
```

The generated evaluation files included:

- 30 Markdown files covering LLM Wiki, Graphify, screenshot boundary, thesis methodology, on-device models, AI inevitability, product demo, and open loops.
- 1 PNG image placeholder.
- 1 PDF placeholder.

Artifacts:

```text
/tmp/snapgraph_phase7_1_eval/inputs/
/tmp/snapgraph_phase7_1_eval/evaluation_results.json
/tmp/snapgraph_phase7_1_eval/.my_snapgraph/
```

Stress run results:

```text
Markdown ingests: 30/30 succeeded
Image ingest: succeeded as screenshot source with MockLLM placeholder description
PDF ingest: failed as expected
Graph: 161 nodes, 215 edges
Lint: OK
Saved questions: 2
Report: generated
```

PDF behavior:

```text
Unsupported source type '.pdf'. Supported: .jpeg, .jpg, .markdown, .md, .png, .txt, .webp
```

This is acceptable because PDF support is not part of the stable v0.1 baseline, but the error should be cleaner in the UI and docs.

Image behavior:

- Images enter as `source_type="screenshot"`.
- Without a VLM provider, MockLLM produces a placeholder visual description.
- The image still receives Cognitive Context and graph nodes.
- This confirms the source-agnostic schema works, but screenshot ingestion should remain experimental until VLM/OCR tests exist.

## Ask Quality Evaluation

Questions tested:

```text
我为什么要从 LLM Wiki 开始？
Graphify 对 SnapGraph 最大的启发是什么？
我为什么说截图不是核心，而只是入口？
现在最应该处理的 open loop 是什么？
这个项目为什么需要 AI 加 graph？
PDF 资料现在能进入系统吗？
```

Strong results:

- Concrete recall questions worked best.
- "我为什么要从 LLM Wiki 开始？" recovered the user-stated reason about raw/wiki/index/log.
- "我为什么说截图不是核心，而只是入口？" recovered the intended product judgment and included the screenshot source.
- Open-loop questions returned actionable next steps from source contexts.
- Evidence sources, graph paths, and retrieval diagnostics were present in normal answers.

Weak results:

- Abstract questions like "这个项目为什么需要 AI 加 graph？" rely too much on keyword and graph proximity and do not synthesize deeply with MockLLM.
- "PDF 资料现在能进入系统吗？" retrieved nearby screenshot/thesis contexts instead of directly explaining capability boundaries. The system needs a capability-aware answer path or docs-aware fallback.
- MockLLM answers often sound like field concatenation:

```text
You likely saved ... because it connected to ...
The preserved reason is ...
```

- Many AI-inferred contexts are generic:

```text
AI-inferred: this source may have been saved because it could help revisit ...
```

This is deterministic and testable, but not impressive for a demo.

## Current Problems

Product problems:

- The system can show the memory structure, but the answer quality is not yet "wow".
- The best demo still needs a presenter to guide it.
- The UI shows evidence, but does not yet make graph paths feel like surprising recovered context.
- The distinction between user-stated and AI-inferred is present but not emotionally obvious enough.

Retrieval/answer problems:

- Keyword + graph expansion is not enough for abstract Chinese questions.
- No embeddings or semantic reranking yet.
- No source excerpt citations.
- No capability-aware fallback for questions about unsupported source types.
- Real LLM providers are available, but answer contracts are not validated.

Graph problems:

- Project clusters are useful, but rule-based.
- Current high-value paths are mostly templated from context.
- Bridge detection is shallow.
- Edge provenance exists as `evidence_source_id` and `confidence`, but not as a human-readable evidence category.
- Top hubs can be structural/mechanical rather than meaningful.

Wiki problems:

- `index.md` is still mostly a registry.
- Source pages link to graph-derived question/task/project labels, but project/concept/thought pages are not yet real maintained pages.
- Saved answers are written back, but not distilled into durable project/concept pages.

Documentation problems:

- `docs/snapgraph_v0.1_design.md` still mentions Streamlit as the demo UI, while the main demo is now FastAPI + Vue.
- API schemas are undocumented.
- Workspace file formats are undocumented.
- Data lifecycle is undocumented: backup, deletion, repair, reindexing, graph rebuild.
- Experimental screenshot/image support needs clearer boundaries.

## Does It Achieve The Original Goal?

Original goal:

```text
Use graph + LLM to find the past cognitive context,
then use LLM + graph to help understand and solve problems.
```

Current answer:

```text
Partially yes.
```

It succeeds for:

- concrete recall,
- user-stated saved reasons,
- source-to-project reasoning,
- open-loop recovery,
- auditable wiki/report workflows.

It is not yet strong for:

- abstract synthesis,
- surprising cross-document discovery,
- high-quality natural-language reasoning in MockLLM mode,
- true Hybrid GraphRAG,
- robust multimodal/PDF ingestion.

The current best characterization:

```text
SnapGraph v0.1 is a working Cognitive LLM Wiki demo.
It proves the storage, traceability, graph path, and write-back loop.
It does not yet prove best-in-class answer intelligence.
```

## Recommended Next Phase

Phase 7.2 should focus on demo trust and answer quality, not new large infrastructure.

Priority 1: Demo narrative

- Add an explicit "recommended demo path".
- Highlight the three best questions:
  - 我为什么要从 LLM Wiki 开始？
  - 我为什么说截图不是核心，而只是入口？
  - 我现在最应该处理的 open loop 是什么？
- Reword or temporarily remove weak abstract demo questions.

Priority 2: Answer quality

- Rewrite MockLLM answer template into a more human synthesis format:
  - conclusion,
  - strongest user-stated evidence,
  - AI-inferred support,
  - graph path,
  - next action,
  - uncertainty.
- Add a capability-aware answer path for questions about unsupported formats such as PDF.
- Use DeepSeek only for manual demo mode, while preserving deterministic tests.

Priority 3: Graph insight honesty

- Add edge evidence status:

```text
user_stated | ai_inferred | structural | duplicate | ambiguous
```

- Filter top hubs by node type.
- Make high-value review paths come from actual graph traversal.
- Add lightweight review connections:
  - low-confidence AI-inferred edge to important project,
  - duplicate source relation,
  - source connecting project + open loop + saved question,
  - unassigned but high-degree source.

Priority 4: Documentation/schema

- Update design doc to FastAPI + Vue.
- Add API contract documentation.
- Add workspace schema documentation.
- Add data lifecycle documentation.
- Clarify screenshot and PDF boundaries.

Priority 5: LLM Wiki compounding

- Introduce a curated write-back mode later:

```text
ask --save
  -> saved question page
  -> optional distilled project/concept page update
  -> index.md navigation improvement
```

This is the step that would make SnapGraph feel more like a compounding wiki rather than a saved Q&A archive.
