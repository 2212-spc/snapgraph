# SnapGraph

A local cognitive memory wiki that remembers why you saved something.

SnapGraph turns notes, text files, and experimental screenshots into an auditable Markdown wiki plus a lightweight graph. It is designed for fuzzy recall: not just "find this document", but "recover the judgment I had when I saved it."

## 60 Second Demo

```bash
conda create -n snapgraph-dev python=3.11 -y
conda run -n snapgraph-dev python -m pip install -e ".[demo,test]"
conda run -n snapgraph-dev snapgraph init
conda run -n snapgraph-dev snapgraph load-demo
conda run -n snapgraph-dev snapgraph demo
```

Open `http://localhost:8501`, then ask:

```text
我为什么要从 LLM Wiki 开始？
我之前为什么觉得截图不是核心，而只是入口？
我现在最应该处理的 open loop 是什么？
```

The demo flow is:

```text
Capture material -> Recall a judgment -> Inspect evidence paths -> Write back to wiki -> Review open loops
```

## What It Builds

```text
.my_snapgraph/
├── raw/                 immutable copied sources
├── wiki/
│   ├── index.md         content map
│   ├── log.md           append-only JSON operation log
│   ├── sources/         generated source pages
│   ├── questions/       saved answers
│   └── graph_report.md  cognitive graph report
├── memory/
│   ├── graph.json       source/thought/project/task graph
│   └── snapgraph.sqlite queryable metadata mirror
└── config.yaml          provider and retrieval settings, never API keys
```

## Trust Model

- Raw sources are copied and hash-checked.
- User-stated reasons from `--why` are preserved exactly.
- AI-inferred reasons are visibly labeled as `AI-inferred`.
- Answers include evidence sources, graph paths, and retrieval diagnostics.
- Missing evidence returns low confidence instead of invented memory.
- Provider keys live only in environment variables such as `SNAPGRAPH_LLM_API_KEY`.

## CLI

```bash
snapgraph init
snapgraph ingest examples/demo_sources/note_llm_wiki.md \
  --why "我保存它是因为 SnapGraph 需要继承 LLM Wiki 的 raw/wiki/index/log 工作流。"
snapgraph ask "我为什么要从 LLM Wiki 开始？"
snapgraph ask "我为什么要从 LLM Wiki 开始？" --save
snapgraph graph
snapgraph report
snapgraph lint
snapgraph eval --output-dir /tmp/snapgraph_eval
```

## Real LLM Mode

MockLLM is deterministic and best for tests. DeepSeek is the default manual quality-evaluation provider.

```bash
export SNAPGRAPH_LLM_API_KEY="..."
snapgraph config set-llm-provider deepseek
snapgraph config set-llm-model deepseek-v4-flash
snapgraph ask "这些材料共同支持 SnapGraph 的哪条产品判断？"
```

Supported DeepSeek API model names currently include `deepseek-v4-flash` and `deepseek-v4-pro`.
The older `deepseek-v4` identifier is rejected by the API.

Do not put real keys in `config.yaml`, `.env`, wiki pages, evaluation reports, or issue logs.

## Capability Evaluation

`snapgraph eval` creates an isolated workspace and writes:

```text
evaluation_results.json
evaluation_report.md
inputs/
workspace/.my_snapgraph/
```

It covers Markdown, text, mixed Chinese/English, duplicate files, empty files, long files, screenshot placeholders, unsupported PDFs, abstract questions, open-loop recovery, cross-document synthesis, and no-match questions.

Scores are 20 points:

```text
retrieval hit + evidence traceability + cognitive boundary + answer quality + boundary honesty
```

`>=16` is demo-ready, `12-15` is useful but needs polish, and `<12` should not be marketed as a capability.

## Web App Development

The demo UI is built with Vite + Vue + TypeScript and served by FastAPI from `snapgraph/static`.

```bash
npm install
npm run build
snapgraph demo
```

The app is organized around:

```text
Recall / Capture / Memory / Paths / Report / Settings
```

Current product semantics are:

- `Capture`: save a source plus an optional short hint about why it may matter.
- `Recall`: recover evidence paths and saved reasoning, not generic chat answers.
- `Graph`: center the main graph on `source / thought / related project / open loop`.
- `Report`: surface low-confidence AI-inferred context so it can be confirmed or corrected.

## Tests

```bash
conda run -n snapgraph-dev pytest -q
```

Current expected baseline:

```text
70 tests passing
```

FastAPI may emit `on_event` deprecation warnings; they do not affect current behavior.

## Design Notes

- `docs/snapgraph_v0.1_design.md` describes the product boundary.
- `docs/snapgraph_phase7_1_status_evaluation.md` records the previous baseline.
- `docs/evaluation_method.md` documents the Phase 7.2 evaluation matrix.
- `docs/api_contract.md` documents the local API.
- `docs/workspace_schema.md` documents workspace files and schemas.
- `docs/media_boundaries.md` documents PDF/image boundaries.
