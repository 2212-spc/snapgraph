# Contributing to SnapGraph

Thanks for improving SnapGraph. The project is intentionally local-first and evidence-first, so small changes with clear diagnostics are preferred.

## Development Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[demo,test]"
npm install
```

## Local Checks

Run these before opening a pull request:

```bash
pytest -q
node --test tests/*.test.ts
npm run build
```

## Engineering Rules

- Preserve raw source traceability.
- Mark user-stated reasons as user-stated.
- Mark inferred context as AI-inferred.
- Keep real LLM providers behind abstractions.
- Use MockLLM for deterministic tests.
- Do not commit `.env`, `.my_snapgraph`, evaluation output, API keys, or local logs.

## Frontend Notes

The current UI is a real product surface built with Vue 3 and Vite. Keep dense app screens compact, readable, and consistent with the StudyAgent-style shell.

For knowledge cloud work, verify both behaviors:

- click a saved-question star opens the original question and answer
- dragging a star never triggers the click/history action
