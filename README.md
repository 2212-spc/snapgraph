# SnapGraph

A local capture-to-connection space that preserves why something mattered when you saved it.

SnapGraph turns links, notes, text files, and screenshots into an auditable Markdown wiki plus a lightweight cognitive graph. Its core action is simple: drop a material in, leave one or two sentences of context, and let SnapGraph connect that capture to related materials, open loops, and projects over time.

## 60 Second Demo

```bash
conda create -n snapgraph-dev python=3.11 -y
conda run -n snapgraph-dev python -m pip install -e ".[demo,test]"
conda run -n snapgraph-dev snapgraph init
conda run -n snapgraph-dev snapgraph load-demo
conda run -n snapgraph-dev snapgraph demo
```

Open `http://localhost:8501`, then try the capture table:

```text
丢进一段摘录、链接或文件。
补一句：为什么这条值得记下？
看右侧是否浮出旧线索，以及它接到了哪个未闭环问题。
```

The demo flow is:

```text
Drop material -> Add context -> See related old clues -> Attach to a live problem -> Review open loops
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
- User-stated reasons from `--why` or the web context note are preserved exactly.
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

MockLLM is deterministic and best for tests. Qwen can be used for multimodal manual evaluation.

```bash
export SNAPGRAPH_LLM_API_KEY="..."
snapgraph config set-llm-provider qwen
snapgraph config set-llm-model qwen3-vl-plus
snapgraph ask "这些材料共同支持 SnapGraph 的哪条产品判断？"
```

Qwen uses the DashScope OpenAI-compatible endpoint by default. Override it with `SNAPGRAPH_QWEN_BASE_URL` when using a regional endpoint.

Do not put real keys in `config.yaml`, `.env`, wiki pages, evaluation reports, or issue logs.

## Capability Evaluation

`snapgraph eval` creates an isolated workspace and writes:

```text
evaluation_results.json
evaluation_report.md
inputs/
workspace/.my_snapgraph/
```

It covers Markdown, text, webpage exports, PDF capture with local text extraction when available, mixed Chinese/English, duplicate files, empty files, long files, screenshot placeholders, abstract questions, open-loop recovery, cross-document synthesis, and no-match questions.

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
Capture table / Context note / Memory stream / Problem view / Settings
```

Current product semantics are:

- `Capture table`: receive a link, text, webpage export, PDF, screenshot, file, or loose thought without asking the user to choose a space first.
- `Context note`: preserve the user's own reason as `user-stated`; AI may summarize sources, but it must not invent the user's motive.
- `Recall`: when the main text sounds like "我之前为什么..." or another fuzzy clue, recover old contexts without saving that question as a new source.
- `Memory stream`: surface related old clues, prior judgments, source excerpts, and open loops beside the current capture.
- `Problem view`: group captures around live questions/open loops instead of making the homepage a graph canvas.
- `Settings`: keep provider/runtime details out of the first-run experience.

## Tests

```bash
conda run -n snapgraph-dev pytest -q
```

Current expected baseline:

```text
71 tests passing
```

FastAPI may emit `on_event` deprecation warnings; they do not affect current behavior.

## Design Notes

- `docs/snapgraph_v0.1_design.md` describes the product boundary.
- `docs/snapgraph_phase7_1_status_evaluation.md` records the previous baseline.
- `docs/evaluation_method.md` documents the Phase 7.2 evaluation matrix.
- `docs/api_contract.md` documents the local API.
- `docs/workspace_schema.md` documents workspace files and schemas.
- `docs/media_boundaries.md` documents PDF/image boundaries.
