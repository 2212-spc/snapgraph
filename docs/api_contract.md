# SnapGraph Local API Contract

The demo app uses a local FastAPI server. Responses never include raw provider API keys.

## Runtime Metadata

Provider-aware responses include:

```json
{
  "provider": {
    "configured_provider": "deepseek",
    "provider_used": "deepseek",
    "model_used": "deepseek-chat",
    "api_key_env": "SNAPGRAPH_LLM_API_KEY",
    "has_api_key": true,
    "provider_ready": true,
    "fallback_used": false,
    "provider_error": ""
  }
}
```

If a real provider is configured but the key is missing, provider-backed endpoints fail fast with HTTP 503 and the same metadata shape in `detail`.

## Endpoints

- `GET /api/workspace`: source/question counts, graph counts, lint state, graph insights, provider status.
- `GET /api/sources`: source rows with cognitive context.
- `GET /api/sources/{source_id}`: generated source Markdown and structured detail.
- `PATCH /api/sources/{source_id}/context`: confirm or correct `why_saved`, project/theme, and open loops.
- `POST /api/ingest`: multipart file plus optional short `why` hint; supports `.md`, `.markdown`, `.txt`, `.png`, `.jpg`, `.jpeg`, `.webp`.
- `POST /api/ask`: JSON `{ "question": "...", "save": false }`; returns answer, contexts, graph paths, diagnostics, provider metadata.
- `GET /api/graph`: graph JSON plus diagnostics and insights.
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
- Unsupported media returns 400.
- `api_key_env` is an environment variable name, not a secret value.
