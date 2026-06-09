# SnapGraph Live Evaluation Progress

Last updated: 2026-05-07

This is the rolling progress document for SnapGraph capability evaluation. Read this before re-running the project review in a new Codex window.

Do not store real API keys in this file, `config.yaml`, `.env`, wiki pages, reports, issue logs, or screenshots. Use the environment variable name `SNAPGRAPH_LLM_API_KEY`; the value must be supplied by the user or by a local shell/keychain outside the repo.

## 2026-05-07 Frontend UX Red-Team

New durable frontend critique document:

- `docs/snapgraph_frontend_ux_redteam_2026-05-07.md`
- `docs/snapgraph_user_truth_frontend_v2_2026-05-07.md`
- `docs/snapgraph_deep_user_research_2026-05-07.md`
- `docs/snapgraph_interaction_design_direction_2026-05-07.md`

This multi-agent review focused on the current Vue frontend, the temporary high-end UI direction, and the overall interaction logic. It produced:

- 60 explicit user needs across students/researchers, PMs, founders, designers, knowledge workers, teams, heavy collectors, AI-heavy users, privacy-sensitive users, and new users.
- 65 concrete frontend and interaction problems.
- A recommended information architecture: Collect as Memory Receipt, Recall as Answer + Trust + Evidence, Space as question workspace, and Evidence Review as claim/connection review.

Main verdict: SnapGraph should not ask normal users to manage graphs. It should help them recover a past judgment, show why it was saved, expose the evidence path, separate user-stated context from AI-inferred context, and turn uncertainty into a review queue.

V2 product-definition update:

- Initial target user is the "deadline-driven judgment worker": the 小林 + 阿洁 segment of students, PMs, founders, and AI-heavy knowledge workers who need to recover old judgments under time pressure.
- Deep researchers are a long-term architecture constraint, especially for local durability, exact quote recall, source opening, PDF/page anchors, and citation.
- Pure personal writing and visual inspiration users should not define V0.
- Critical correction: only the user can state why something was saved. If no user reason exists, keep it empty or `needs reason`; AI may summarize source content and suggest possible links, but must not silently invent `why_saved`.
- V0 should prioritize exact old words, one-click original source access, local/trust clarity, no-match honesty, optional AI, and reviewable connections.

Deep user-research update:

- The examples are not the boundary. The research method is to enter a real user's pressure moment, substitute behavior, trust trigger, and abandonment trigger.
- Expanded personas now include deadline students, PMs, AI/backend technical decision makers, founders/investment analysts, researchers, evidence workers, team knowledge stewards, visual inspiration workers, and quiet writers.
- The repeated situation is: a person made or saved a judgment under context; later the context is gone, the deadline is real, and a plausible AI answer is tempting. SnapGraph must recover old words, source evidence, uncertainty, and next action without pretending.
- Strongest V0 wedge: deadline-driven judgment workers plus technical decision makers. Strong V1 directions: thesis maintenance, evidence packets, counter-evidence, team-compatible audit fields.

Interaction-design update:

- The current recommended surface is a hybrid: a calm search-like entry, evidence-grounded conversation for depth, and workbench/library structure only after the user needs it.
- Do not expose "graph" as a primary product surface. The graph is the reasoning substrate behind recall, conversation, and evidence expansion.
- Emergence is not a scheduled notification or review task. It should appear naturally inside a strong conversation when the model sees a grounded pattern across the user's materials.
- Review remains useful, but should mostly appear inline around evidence chains and weak relations, with a subtle backlog rather than a primary gamified queue.
- Next frontend prototype should cover six connected screens: Home Recall Input, Recall Result, Evidence Conversation, Evidence Chain Sheet, Capture Sheet, and Library/Space.

## Continuation Protocol

When starting a new session:

1. Read `AGENTS.md`, then this file.
2. Do not repeat the old high-level review unless the code changed materially.
3. Use MockLLM for deterministic unit tests and scale baselines.
4. Use Qwen only for live multimodal/manual quality checks.
5. Never print or persist the real API key.
6. If Qwen is needed, configure the workspace provider, then read the key from `SNAPGRAPH_LLM_API_KEY`.

Useful setup:

```bash
python -m pip install -e ".[demo,test,deepseek]"
snapgraph init
snapgraph config set-llm-provider qwen
export SNAPGRAPH_LLM_API_KEY="..."  # user/local shell only; never commit or log
```

Current CLI gap: `snapgraph config set-llm-model` is not implemented yet. Qwen defaults to `qwen3-vl-plus`; if a model override is needed, use the API config endpoint or edit workspace config carefully without storing secrets.

API config path:

```bash
curl --noproxy '*' -X PUT http://127.0.0.1:8501/api/config \
  -H 'content-type: application/json' \
  -d '{"provider":"qwen","model":"qwen3-vl-plus","api_key_env":"SNAPGRAPH_LLM_API_KEY"}'
```

## Latest Evaluation Summary

The second-round evaluation tested real files, real API upload paths, non-default graph spaces, scale behavior, and live Qwen.

High-level verdict:

- The product idea is strong: preserve source, user-stated why, evidence path, and future recall context.
- Qwen works and gives much better image/PDF understanding than MockLLM.
- The current product is not yet daily-use ready because batch ingestion with real providers is too slow, no-match retrieval is unsafe, and the UI exposes too much graph/debug machinery.
- The user-facing product should sell remembered judgments and evidence cards, not node/edge graph mechanics.

## Live Qwen Results

Representative live Qwen ingest timings:

| File | Type | Result | Time |
|---|---|---|---:|
| `01_project_aurora.md` | Markdown | success | 12.0s |
| `03_web_export.html` | webpage | success | 9.2s |
| `04_pdf_research_brief.pdf` | PDF with extractable text | success | 9.6s |
| `05_capture_receipt.png` | image/screenshot | success | 24.9s |
| `06_whiteboard.jpg` | image/screenshot | success | 17.7s |
| `08_broken.pdf` | broken PDF fallback | success, no usable body text | 11.2s |

Live Qwen ask timings:

- Representative questions took about 15.6s to 24.9s.
- Qwen image understanding was accurate in direct vision calls:
  - It read `Save to Graph`, `AI-inferred needs review`, and `fix evidence paths before UI polish` from the receipt image.
  - It read the whiteboard flow `Raw Source -> User Why -> Answer / Graph Path` and the decision `show evidence cards before graph canvas`.

Qwen quality observation:

- Qwen can rescue some retrieval noise by obeying user constraints such as "only answer from image materials".
- Product retrieval should not rely on the model to clean this up. If the user asks about images, retrieval should filter to images before answer synthesis.

## Batch And Scale Results

MockLLM local API ingest remains fast:

| Requested files | Files sent | Total ingest | Average/file | P95/file |
|---:|---:|---:|---:|---:|
| 10 | 12 | 0.11s | 0.009s | 0.011s |
| 50 | 52 | 0.59s | 0.011s | 0.014s |
| 100 | 102 | 1.49s | 0.015s | 0.020s |

Separate scale-agent run:

| Files | Ingest total | Ask average | Mean retrieved | Positive precision | No-match false retrieval |
|---:|---:|---:|---:|---:|---:|
| 10 | 0.053s | 2.01ms | 6.4 | 0.229 | 2 |
| 50 | 0.338s | 7.40ms | 8.0 | 0.688 | 8 |
| 100 | 0.930s | 16.31ms | 8.0 | 0.906 | 8 |
| 200 | 2.841s | 31.29ms | 8.0 | 1.000 | 8 |

Live Qwen 10-text-file batch:

- Total ingest: 104.7s.
- Average per file: 8.6s.
- Ask after 10 files: 18.9s.

Interpretation:

- Mock speed is not representative of real provider UX.
- At current serial/provider-call structure, 100 real Qwen files can become a 10+ minute workflow.
- The system needs async background ingestion, per-file status, retry, provider-call consolidation, and likely concurrency limits.

## Format Support Findings

| Format | Status | Notes |
|---|---|---|
| `.md` | good | Preserves title/body/why/raw/hash/wiki/log. |
| `.txt` | good | Text enters summary and retrieval; title uses file stem when no heading. |
| `.html` | good | Body extraction works; script/style/head are stripped. |
| `.pdf` | mixed | Born-digital PDFs work when `pdftotext` can extract text. Scanned/broken PDFs fall back to shell text. |
| `.png`, `.jpg` | provider-dependent | MockLLM only stores placeholder text. Qwen can read image text and UI content accurately, but image ingest is slow. |
| unsupported, e.g. `.csv` | rejected | API gives clear 400; CLI currently prints traceback. |

Missing structured extraction fields:

- `text_extracted`
- `visual_extracted`
- `text_char_count`
- `parser`
- `warnings`
- `material_type_filterable`

## Retrieval Quality Risks

Most serious current risk:

- No-match questions can still retrieve 8 irrelevant sources once the corpus grows.
- Example class: unrelated questions such as `unrelated quantum pineapple` should return low confidence, but scale testing showed full false retrieval at 50/100/200 files.

Recommended retrieval fixes:

- Add minimum score and query coverage thresholds.
- Use BM25/SQLite FTS or IDF-aware ranking instead of scanning all source Markdown with raw substring counts.
- Do not graph-expand if lexical/source evidence is weak.
- Deduplicate by content hash and title before presenting evidence.
- Add material-type filters for image/PDF/web/text questions.
- Surface "no reliable evidence found" as a first-class success state.

## UI And Product Direction

First-principles user need:

Users do not want to manage graphs. They want to recover a half-remembered judgment, understand why they saved something, see the few sources that support it, and know what to do next.

Default UI should be:

1. Memory receipt after upload.
2. Direct answer.
3. Evidence cards.
4. User-stated why vs AI-inferred labels.
5. Open-loop / next-action queue.
6. Advanced audit view only when requested.

Graph canvas should not be the main product surface. Keep it as an advanced/debug/audit mode.

Recommended user-facing views:

```text
Collect
- Upload or paste
- Memory receipt
- Confirm/edit why
- Confirm space
- Accept/reject suggested connection
- Open loops created from this capture

Recall
- Direct answer
- Trust summary
- User-stated evidence
- Source excerpts
- Evidence path cards
- AI-inferred section collapsed by default
- Save answer back to wiki

Space
- Project/theme lanes
- Recent materials
- Open-loop queue
- Low-confidence items needing review
- Advanced graph audit

Evidence Review
- One claim or path
- Supporting source excerpts
- Edge/relation explanation
- Confirm / weaken / reject
```

Fields to show by default:

- `title`
- `summary` / `source_excerpt`
- `why_saved`
- `why_saved_status`
- `related_project`
- `open_loops`
- `future_recall_questions`
- `space_name`
- material type
- imported time
- natural-language relation
- source title
- evidence status

Fields to hide by default:

- internal ids
- raw graph node ids
- `graph_space_id`
- `content_hash`
- raw paths
- SQLite details
- source/target ids
- numeric confidence unless translated
- layout coordinates
- provider runtime details

## Current Top Issues

P0:

- Real-provider batch ingestion is too slow because each file triggers many remote calls.
- No-match retrieval can fabricate confidence by returning irrelevant evidence.
- UI exposes graph mechanics instead of evidence-first memory.
- CLI has no model override command such as `set-llm-model`.
- CLI errors print tracebacks for common user mistakes.

P1:

- Add async job queue for ingest.
- Consolidate LLM calls per file.
- Add type-aware retrieval filters.
- Convert graph path strings into evidence path cards.
- Add open-loop status lifecycle: `new`, `confirmed`, `deferred`, `done`.
- Add extraction status and warnings to API/UI.

P2:

- Add true provider health checks.
- Add Qwen/provider extra dependencies.
- Add skipped-by-default live provider tests.
- Add project/person/concept extraction beyond the current source/thought/task/project skeleton.
- Add duplicate and empty-file handling in retrieval and lint.

## Test Artifacts From 2026-05-06

These were temporary evaluation directories and may be removed by the OS:

- `/tmp/snapgraph_live_deep_eval_1778080505`
- `/tmp/snapgraph_qwen_text_batch_1778080798`
- `/tmp/snapgraph_space_errors_eval_1778080757`
- `/tmp/snapgraph_format_eval_FFzncE`
- `/tmp/snapgraph_scale_eval_20260506`

Do not depend on these paths for permanent project state. Use the numbers above as the durable record.

## Next Evaluation Checklist

Before claiming progress:

```bash
pytest -q
npm run build
node --test tests/*.test.ts
snapgraph eval --output-dir /tmp/snapgraph_eval_latest
```

For live Qwen smoke tests:

1. Use only a small representative set first: one Markdown, one HTML, one PDF, one PNG/JPG, one broken PDF.
2. Record per-file ingest seconds.
3. Ask one type-specific question, e.g. "only answer from image materials".
4. Verify retrieval contexts match the requested material type.
5. Verify no real API key appears in logs, docs, config, wiki, or reports.
