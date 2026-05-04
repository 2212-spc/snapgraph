# SnapGraph Local API Contract

The demo app uses a local FastAPI server. Responses never include raw provider API keys.

The current web experience is capture-first: the UI calls `/api/focus` while the user is preparing a capture, then calls `/api/ingest` to save the material and the user-stated context note.

## Runtime Metadata

Provider-aware responses include:

```json
{
  "provider": {
    "configured_provider": "qwen",
    "provider_used": "qwen",
    "model_used": "qwen3-vl-plus",
    "api_key_env": "SNAPGRAPH_LLM_API_KEY",
    "has_api_key": true,
    "provider_ready": true,
    "fallback_used": false,
    "provider_error": ""
  }
}
```

If a real provider is configured but the key is missing, provider-backed answer endpoints fail fast with HTTP 503 and the same metadata shape in `detail`.

## Endpoints

- `GET /api/workspace`: source/question counts, graph counts, lint state, graph insights, provider status.
- `GET /api/sources`: source rows with cognitive context.
- `GET /api/sources/{source_id}`: generated source Markdown and structured detail.
- `PATCH /api/sources/{source_id}/context`: confirm or correct `why_saved`, project/theme, and open loops.
- `POST /api/ingest`: multipart file plus optional user-stated `why`; supports `.md`, `.markdown`, `.txt`, `.html`, `.htm`, `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`. The `why` field is preserved exactly as `user-stated`. PDF capture stores the original file and extracts text when local `pdftotext` is available; otherwise it honestly falls back to saving the file plus context note.
- `POST /api/focus`: JSON focus payload such as `{ "question": "...", "space_id": "all" }` or `{ "source_id": "..." }`; returns evidence cards, open loops, and confidence summary for the memory stream.
- `POST /api/ask`: JSON `{ "question": "...", "save": false }`; returns answer, contexts, graph paths, diagnostics, provider metadata.
- `GET /api/graph`: graph JSON plus diagnostics and insights.
- `GET /api/suggestions`: route suggestions for spaces/projects.
- `POST /api/suggestions/{suggestion_id}/accept`: accept a suggested graph-space route.
- `POST /api/suggestions/{suggestion_id}/reject`: reject a suggested graph-space route.
- `GET /api/report`: current Markdown graph report.
- `POST /api/report/generate`: regenerate report.
- `GET /api/lint`: workspace lint result.
- `GET /api/questions`: saved question pages.
- `GET /api/questions/{question_id}`: saved question Markdown.
- `POST /api/demo/load`: deterministic MockLLM demo load by default; pass `{ "use_provider": true }` only for explicit provider demos.
- `GET /api/config`: configured provider, model, API key environment variable name, readiness.
- `PUT /api/config`: update provider/model/api-key-env name. Rejects actual key-shaped values such as `sk-...`.
- `GET /api/demo/questions`: recommended demo prompts.

## Failure Policy

- Mock provider errors are treated as application bugs.
- Real provider setup errors return 503.
- Real provider runtime errors return 502.
- Capture should remain local-first: `/api/ingest` falls back to MockLLM when a configured real provider is missing its API key, and returns provider metadata with `fallback_used: true`.
- Unsupported media returns 400.
- `api_key_env` is an environment variable name, not a secret value.
- Qwen uses DashScope OpenAI-compatible mode by default; set `SNAPGRAPH_QWEN_BASE_URL` to override the regional endpoint.
