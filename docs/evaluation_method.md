# SnapGraph Evaluation Method

Phase 7.2 evaluates whether SnapGraph is useful, trustworthy, and worth carrying toward an on-device app.

## Runner

```bash
snapgraph eval --output-dir /tmp/snapgraph_eval
snapgraph eval --provider deepseek --api-key-env SNAPGRAPH_LLM_API_KEY
```

The runner always creates an isolated workspace under the output directory. It does not mutate the current `.my_snapgraph` workspace.

## Scenario Matrix

| Scenario | Inputs | Question style | Expected behavior |
|---|---|---|---|
| Markdown recall | LLM Wiki, GraphRAG, screenshot-boundary notes | Why did I save this? | Recovers user-stated reason and graph paths. |
| Mixed language | Chinese and English terms in one corpus | Chinese question with English terms | Recalls cross-language concepts. |
| Open loops | Notes with `Open loop:`, `Todo:`, `Next:` | What should I handle next? | Returns actionable next step. |
| Cross-document synthesis | Product, graph, methodology notes | Abstract product judgment | Uses multiple sources and separates evidence from inference. |
| PDF boundary | Valid-looking and broken `.pdf` files | Can PDFs enter now? | Reports unsupported boundary honestly. |
| Screenshot placeholder | PNG screenshot input | What did the screenshot show? | MockLLM proves pipeline only; real vision is experimental. |
| Bad input | Empty, duplicate, long, no-match | Unrelated question | Does not hallucinate. |

## Scoring

Each case is scored out of 20:

- retrieval hit: 0-4
- evidence traceability: 0-4
- cognitive boundary: 0-4
- answer quality and actionability: 0-4
- boundary honesty: 0-4

Verdicts:

- `demo`: 16-20
- `needs-work`: 12-15
- `fail`: 0-11

MockLLM verifies deterministic system behavior. DeepSeek verifies answer quality.
