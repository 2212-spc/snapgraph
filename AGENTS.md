# SnapGraph AGENTS.md

You are building SnapGraph, a cognitive LLM Wiki system.

## Product Goal

SnapGraph helps users preserve not only information, but also the cognitive context behind saved information:

- what the source says
- why it may have mattered when saved
- what project, person, task, or question it relates to
- how it connects to other saved materials
- how it can help the user in the future

## Design Lineage

SnapGraph starts from the LLM Wiki pattern:

- raw sources are immutable
- wiki pages are generated and maintained by the agent
- index.md is the content map
- log.md is the chronological operation log
- useful answers can be written back into the wiki

SnapGraph extends this with:

- Cognitive Context
- graph.json
- source-to-thought links
- evidence paths
- Hybrid GraphRAG

## Engineering Rules

- Implement in small testable phases.
- Do not build a mobile app yet.
- Do not use Neo4j yet.
- Do not build a 3D graph yet.
- Prefer Markdown + SQLite + JSON graph first.
- Every phase must include diagnostics.
- Every ingestion must preserve source traceability.
- Never pretend to know the user's real intention.
- If the system infers why something was saved, mark it as AI-inferred.
- If the user explicitly writes why something was saved, mark it as user-stated.
- Use MockLLM first so tests are deterministic.
- Keep real LLM and embedding providers behind abstractions.

## Required Commands

The project should eventually support:

```bash
snapgraph init
snapgraph ingest <path> --why "optional user note"
snapgraph ask "question"
snapgraph lint
snapgraph graph
snapgraph report
snapgraph load-demo
snapgraph demo
```

## Test Rule

After each phase:

- run unit tests
- run a small demo dataset
- print diagnostics
- document what works and what fails
