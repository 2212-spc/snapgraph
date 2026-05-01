# SnapGraph Workspace Schema

`snapgraph init` creates `.my_snapgraph/` in the current directory.

## Files

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

## Source Page

Generated source pages include frontmatter:

```yaml
id: src_...
title: ...
type: markdown | text | screenshot
created_at: ...
imported_at: ...
raw_path: raw/...
original_filename: ...
content_hash: ...
```

Required sections:

- Objective Summary
- Key Details
- Cognitive Context
- Links
- Evidence

`user-stated` reasons must preserve `--why` exactly. `AI-inferred` reasons must stay visibly labeled.

## SQLite Tables

- `sources`: immutable provenance and summary.
- `cognitive_contexts`: why saved, status, project, open loops, recall questions, confidence.
- `nodes`: graph nodes mirrored from `graph.json`.
- `edges`: graph edges mirrored from `graph.json`.

## Graph JSON

Node types:

```text
source, thought, question, task, project
```

Edge relations:

```text
triggered_thought, evidence_for, follow_up, belongs_to, related_to
```

Every edge should preserve `evidence_source_id` when possible.

## Config

`config.yaml` stores only non-secret configuration:

```json
{
  "llm": {
    "provider": "mock",
    "model": "",
    "api_key_env": "SNAPGRAPH_LLM_API_KEY"
  }
}
```

The environment variable value must not be written to workspace files.
