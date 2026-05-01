# SnapGraph Phase Gate

Before each new implementation phase, repeat this checkpoint.

## 1. Re-read Project Context

- `AGENTS.md`
- `README.md`
- `docs/snapgraph_v0.1_design.md`

## 2. Re-check LLM Wiki Lineage

Use Karpathy's LLM Wiki gist as the design reference:

- raw sources are immutable
- wiki pages are maintained working memory
- schema files discipline the agent
- `index.md` maps content before query
- `log.md` records append-only operations
- core operations are ingest, query, and lint

Reference: https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f

## 2.5 Re-check Graphify Lessons

Use `references/graphify` only as a design reference, not as a runtime dependency.

Borrow:

- human-readable graph report
- honest audit trail
- confidence language
- review paths and suggested questions
- graph as navigation, not decoration

Do not blindly borrow:

- AST/tree-sitter extraction
- Leiden/community detection as a default
- MCP hooks
- codebase-specific "god node" terminology
- large multimodal ingestion pipeline

## 3. Verify Baseline

```bash
conda run -n snapgraph-dev pytest -q
```

Run a demo smoke test with:

```bash
snapgraph init
snapgraph load-demo
snapgraph graph
snapgraph ask "Why did I start from LLM Wiki?"
snapgraph report
snapgraph lint
```

## 4. State The Phase Boundary

Write down:

- goal
- success criteria
- diagnostics
- what will not be built in this phase

For v0.1, keep the project file-based. Do not add Neo4j, mobile capture, screenshot ingestion, or real LLM dependency until the current phase proves its value.

## 5. Stability Checks

Before adding a new feature, confirm:

- `config.yaml` remains backward compatible with old workspaces
- `lint` can detect graph/wiki/SQLite drift
- retrieval diagnostics explain why sources were selected
- no answer claims certainty about user intent unless `--why` was user-stated
- graph insights are based on actual graph evidence where possible, not only metadata summaries
- demo questions still demonstrate cognitive recall, not generic search
