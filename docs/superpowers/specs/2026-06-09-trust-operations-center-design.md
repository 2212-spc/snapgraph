# Trust Operations Center Design

Status: approved for implementation in the `cxk` branch.

## Goal

Build a Trust Operations Center that helps a user review AI-inferred cognitive context, open loops, weak evidence paths, and unresolved decisions from one focused workspace instead of hunting through source cards, graph panels, and recall answers.

The module must increase useful code volume without padding. Every new surface should either expose trust risk, let the user act on it, or make diagnostics easier to verify.

## User Problem

SnapGraph already captures sources, user-stated reasons, AI-inferred reasons, graph evidence, source maps, topics, and open loops. From a user's point of view, the next problem is operational:

- "Which AI guesses still need my judgment?"
- "Which saved items are risky because the why-saved reason was inferred?"
- "Which open loops are still active, and what evidence do they depend on?"
- "Can I confirm, rewrite, reject, or defer several related items without opening each source manually?"
- "After I act, can I see what changed and why?"

The center should make trust work feel like a daily inbox, not a raw database table.

## Design Principles

- Preserve source traceability. Every review item links back to the source, evidence path, source map, topic, and open loop text when available.
- Never pretend to know intent. AI-inferred reasons remain visibly labeled as AI-inferred until the user confirms or rewrites them.
- Keep raw sources immutable. Actions update cognitive context review metadata and optional open-loop lifecycle records, not source content.
- Prefer SQLite, JSON, and Markdown-compatible records. Do not introduce Neo4j, a mobile app, or a 3D graph.
- Keep MockLLM-compatible behavior deterministic. Review projections and diagnostics are database-derived, not model-generated.
- Optimize for user decisions. The UI should show risk, evidence, action choices, and next best work before decorative visualization.

## Considered Approaches

### Approach A: Projection-Only Review Center

Read from `sources`, `cognitive_contexts`, `graph_nodes`, `graph_edges`, topics, and source map functions. Compute risk, queue ordering, and open-loop summaries on demand. Store only existing review decisions.

Pros:

- Smallest schema change.
- Low migration risk.
- Uses current source traceability.

Cons:

- Hard to preserve review history.
- Open loop statuses remain inferred from source text only.
- Diagnostics cannot show lifecycle changes over time.

### Approach B: Full Workflow Engine

Create durable review item, assignment, history, open-loop, SLA, notification, and audit tables. Use a generic workflow state machine.

Pros:

- Most extensible.
- Strong audit trail.
- Can support team operations later.

Cons:

- Too large for this phase.
- Adds product concepts SnapGraph has not validated.
- Higher risk of building enterprise workflow instead of personal cognition support.

### Approach C: Projection Plus Lightweight Operations Records

Use projection for the review inbox and evidence data. Add small SQLite tables for review history and open-loop lifecycle decisions. Keep every generated item tied to a `source_id`, context field, or topic id.

Pros:

- Gives the user an operations center now.
- Adds durable history and open-loop state without a workflow engine.
- Supports meaningful UI, API, diagnostics, and tests.
- Fits the repo rule: Markdown + SQLite + JSON graph first.

Cons:

- Some queue items are still computed at request time.
- Future collaboration features would need another phase.

Recommendation: Approach C.

## Functional Scope

### 1. Trust Review API

Add review-center endpoints that produce a normalized queue:

- `GET /api/trust/review`
- `GET /api/trust/review/{source_id}`
- `POST /api/trust/review/batch`
- `GET /api/trust/summary`
- `GET /api/trust/diagnostics`

The queue should include:

- source id, title, type, space id, space name, imported time
- why-saved text and status
- review status, review note, reviewed time
- confidence and risk level
- related project
- open loops
- future recall questions
- evidence path snippets
- source map counts when available
- topic references when available
- recommended action

Risk levels:

- `critical`: AI-inferred context with low confidence and no user review.
- `high`: AI-inferred context with medium confidence, active open loops, or graph evidence gaps.
- `medium`: deferred review, weak source map links, or stale open loops.
- `low`: user-stated or confirmed context with adequate evidence.

The API should support filters by:

- status
- risk
- space
- query
- whether the context was user-stated or AI-inferred
- whether open loops exist

### 2. Batch Review Actions

Allow the user to act on several sources at once:

- confirm
- reject
- defer
- rewrite each item with a per-source replacement

Batch action behavior:

- Confirm, reject, and defer can use a shared note.
- Rewrite requires a replacement reason per source.
- Each item produces a durable history row.
- Invalid source ids produce per-item errors without failing the whole batch.
- The response includes counts and changed items.

### 3. Review History

Add a small `trust_review_history` table.

Each row stores:

- id
- source_id
- action
- previous status
- next status
- note
- previous why-saved
- next why-saved
- created_at

This creates a visible audit trail for the user and a useful diagnostic artifact for tests and reports.

### 4. Open Loop Lifecycle

Add a lightweight open-loop projection and lifecycle table:

- `GET /api/trust/open-loops`
- `PATCH /api/trust/open-loops/{loop_id}`

Open loops are materialized from `cognitive_contexts.open_loops_json` and topic open loops. A stable id is derived from source id, loop text, and index. A lifecycle table stores user state:

- `active`
- `next`
- `resolved`
- `dismissed`

Each open-loop item includes:

- loop id
- text
- source ids
- source titles
- risk level
- review status summary
- evidence count
- topic ids
- updated_at

### 5. Frontend Trust Operations Center

Add a primary app view named `trust`.

The view should contain:

- summary header with counts for critical, high, medium, low, confirmed, deferred, rejected, and open loops
- filter rail with risk, status, space, and query controls
- review inbox list with stable cards
- detail drawer for source evidence, why-saved status, graph/source-map context, history, and open loops
- batch action bar for selected review items
- open-loop lifecycle panel with status transitions
- diagnostics panel that shows API-derived counts and warnings

The first screen is the actual operations workspace. It should not become a marketing page or a decorative dashboard.

### 6. Diagnostics

The module should expose diagnostics that can be used by tests, CLI reports later, and manual QA:

- total queue items
- AI-inferred unreviewed count
- deferred count
- rejected count
- critical/high risk count
- open-loop count by lifecycle state
- history count
- stale review warnings
- orphan lifecycle records

Diagnostics must be deterministic.

## Data Flow

1. Ingestion creates `sources` and `cognitive_contexts`.
2. Review Center reads sources plus cognitive context review fields.
3. Trust projection enriches each source with evidence snippets from graph/source-map/topic data.
4. User acts through batch or detail endpoints.
5. Action endpoint calls existing `review_ai_inference` where appropriate, writes history, and returns the updated projection.
6. Open-loop lifecycle endpoint stores only lifecycle metadata; the original open-loop text remains in the context/topic JSON.
7. Frontend refreshes summary, queue, detail, diagnostics, and open-loop panels after each action.

## Backend Boundaries

Create a new backend module:

- `snapgraph/trust_center.py`

Responsibilities:

- query review candidates
- compute risk levels
- normalize queue payloads
- write review history
- materialize open loops
- persist open-loop lifecycle state
- compute diagnostics

Keep FastAPI route functions thin in `snapgraph/api.py`.

Do not put UI-specific wording in backend except stable status labels and recommendation codes.

## Frontend Boundaries

Create focused components:

- `frontend/src/components/TrustCenterView.vue`
- `frontend/src/components/trustCenterTypes.ts`
- `frontend/src/components/TrustReviewInbox.vue`
- `frontend/src/components/TrustReviewDetail.vue`
- `frontend/src/components/TrustBatchActionBar.vue`
- `frontend/src/components/TrustOpenLoopPanel.vue`
- `frontend/src/components/TrustDiagnosticsPanel.vue`

`App.vue` should own loading and API calls. Components should receive typed props and emit actions.

## Error Handling

- Missing source detail returns 404.
- Invalid review action returns 400.
- Batch actions return a 200 response with per-item errors unless the request shape itself is invalid.
- Open-loop patch returns 404 when the derived id cannot be found in current projection.
- Diagnostics include warnings for lifecycle records whose source no longer exists.

## Testing Strategy

Use TDD for each slice.

Backend tests:

- queue projection ranks AI-inferred unreviewed items above confirmed items
- summary counts match demo data
- detail endpoint includes history and open loops
- batch confirm writes review history and updates queue status
- batch rewrite requires per-source text
- open-loop lifecycle patch persists state
- diagnostics reports review and open-loop counts

Frontend tests:

- shell nav exposes Trust Center
- Trust Center renders summary, inbox, filters, detail, batch bar, open-loop panel, diagnostics panel
- batch action flow emits selected ids and actions
- detail drawer shows source traceability and history
- styles include dense operations layout and responsive constraints

Manual/demo verification:

- `node --test tests/*.test.ts`
- `pytest -q`
- `npm run build`
- demo CLI chain: init, load-demo, lint, graph, report, ask
- local demo server opens the new Trust Center for acceptance
- scan repository for accidental API key commits

## Non-Goals

- No mobile app.
- No Neo4j.
- No 3D graph.
- No team assignment, notifications, due dates, or permissions.
- No real LLM dependency for queue ranking or diagnostics.
- No upload of API keys or secrets.

## Acceptance Criteria

- A user can open Trust Center from the app shell.
- A user can see which AI-inferred contexts need review and why they are risky.
- A user can confirm, reject, defer, or rewrite review items, including batch actions.
- A user can inspect evidence paths and source traceability before acting.
- A user can track open loops as active, next, resolved, or dismissed.
- Every action has deterministic diagnostics and test coverage.
- The project builds and the demo server opens for user acceptance.
