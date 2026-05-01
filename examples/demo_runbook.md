# SnapGraph v0.1 Demo Runbook

This runbook demonstrates the Cognitive LLM Wiki loop:

```text
ingest sources -> preserve cognitive context -> build graph -> ask fuzzy questions -> save useful answers -> report -> lint
```

## Setup

Use MockLLM for deterministic local demos:

```bash
conda run -n snapgraph-dev snapgraph init
conda run -n snapgraph-dev snapgraph load-demo
conda run -n snapgraph-dev snapgraph demo
```

Open `http://localhost:8501` and follow the recall flow:

```text
加载记忆素材 -> 恢复一个判断 -> 查看证据路径 -> 生成认知报告
```

Use DeepSeek only for manual answer-quality demos. Keep the API key in the environment, never in the repo:

```bash
export SNAPGRAPH_LLM_API_KEY="..."
conda run -n snapgraph-dev snapgraph config set-llm-provider deepseek
```

## Ingest Demo Sources

`snapgraph load-demo` runs this sequence automatically. To run it manually from the repository root:

```bash
conda run -n snapgraph-dev snapgraph ingest examples/demo_sources/note_llm_wiki.md \
  --why "我保存它是因为 SnapGraph 需要继承 LLM Wiki 的 raw/wiki/index/log 工作流。"
conda run -n snapgraph-dev snapgraph ingest examples/demo_sources/note_graphrag.md \
  --why "我保存它是因为模糊召回需要图谱路径，而不只是关键词搜索。"
conda run -n snapgraph-dev snapgraph ingest examples/demo_sources/note_screenshot_entry.md \
  --why "我保存它是因为截图应该先作为入口，而不是 v0.1 的核心价值验证。"
conda run -n snapgraph-dev snapgraph ingest examples/demo_sources/note_snapgraph_idea.md
conda run -n snapgraph-dev snapgraph ingest examples/demo_sources/note_methodology.md
conda run -n snapgraph-dev snapgraph ingest examples/demo_sources/note_on_device_models.md
conda run -n snapgraph-dev snapgraph ingest examples/demo_sources/meeting_research_plan.md
conda run -n snapgraph-dev snapgraph ingest examples/demo_sources/todo_open_loops.md
```

## Demo Questions

```bash
conda run -n snapgraph-dev snapgraph ask "我为什么要从 LLM Wiki 开始？" --save
conda run -n snapgraph-dev snapgraph ask "我之前为什么觉得截图不是核心，而只是入口？" --save
conda run -n snapgraph-dev snapgraph ask "我对端侧模型的判断是什么？"
conda run -n snapgraph-dev snapgraph ask "这个项目的 AI 必然性在哪里？"
conda run -n snapgraph-dev snapgraph ask "我现在最应该处理的 open loop 是什么？"
```

Each answer should show:

- evidence sources
- graph paths
- retrieval diagnostics
- clear user-stated vs AI-inferred context

## Close The Demo

```bash
conda run -n snapgraph-dev snapgraph graph
conda run -n snapgraph-dev snapgraph report
conda run -n snapgraph-dev snapgraph lint
```

Expected final state:

- `.my_snapgraph/wiki/questions/` contains saved answers
- `.my_snapgraph/wiki/graph_report.md` exists
- `snapgraph lint` returns `Status: OK`
