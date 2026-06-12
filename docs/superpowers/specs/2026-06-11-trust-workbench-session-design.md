# Trust Workbench 2.1 Session Design

## Goal

Trust Workbench 2.1 keeps the current Trust Center feature set intact while making the same review work feel more guided, lower pressure, and easier to finish. The user still reviews AI-inferred save reasons, inspects evidence, updates open loops, and checks diagnostics. The change is in the interaction model: the screen should help the user decide what to review first, why that item matters, what action is safest, and what changed after the decision.

This is deliberately not a new top-level module. It is a deeper version of the existing trust module.

## User Problem

The current trust workbench reduced visual density, but a user can still feel uncertain about three things:

- where to start when many items are waiting
- what confidence, risk, evidence, open loops, and review status mean in practical terms
- whether a confirmation, rewrite, rejection, or deferral is the right decision

The design should preserve information depth while staging it across a review session.

## Recommended Approach

Use a "review session" layer inside the existing Trust Center:

1. A compact session planner at the top lets the user choose a review mode, see the queue scope, and understand the next best action.
2. Review cards expose richer but compact decision signals: trust boundary, risk reason, evidence count, open-loop pressure, and recommended action.
3. The detail panel becomes a decision cockpit: brief, evidence, risk explanation, rewrite guidance, decision note, and action preview.
4. A small progress/summary area shows what has been selected or acted on in the current session.
5. Diagnostics and open loops remain secondary and progressively disclosed.

This creates substantial code because the current components need richer typed view models, helper utilities, UI sections, tests, and styles, but it stays inside the existing module.

## Non-Goals

- Do not add a new top-level route or sidebar item.
- Do not add a new database table for sessions.
- Do not change the semantics of existing review actions.
- Do not require a real LLM or external API.
- Do not upload or store API keys.

## Frontend Design

Add new Trust Center subcomponents:

- `TrustSessionPlanner.vue`: chooses review mode and explains the current session goal.
- `TrustReviewProgress.vue`: summarizes selected count, high-priority remaining count, and suggested next step.
- `TrustDecisionCoach.vue`: explains each action and validates rewrite/note intent before submit.
- `TrustRiskLens.vue`: shows why a selected item is risky without forcing users to open all raw evidence.
- `TrustReviewSignals.vue`: reusable compact signal strip for cards and detail panels.

Existing components stay in place and become orchestrators:

- `TrustCenterView.vue` owns session mode and passes derived context down.
- `TrustReviewInbox.vue` renders richer cards and emits the same selection/review events.
- `TrustReviewDetail.vue` uses coach/lens components while still emitting the existing `batchAction` payload.
- `TrustBatchActionBar.vue`, `TrustOpenLoopPanel.vue`, and `TrustDiagnosticsPanel.vue` gain clearer microcopy and summary helpers.

## Backend Design

Keep existing endpoints and payloads. Add derived fields to review items where useful:

- `risk_reasons`: human-readable reasons for risk level
- `decision_options`: action labels, descriptions, and whether a rewrite is required
- `review_focus`: the recommended next thing the user should inspect
- `trust_signals`: normalized counts and booleans for frontend display

These fields are computed from existing source, cognitive context, graph, lifecycle, and review data. They do not change stored data.

## Data Flow

The frontend continues to load:

- `/api/trust/review`
- `/api/trust/review/{source_id}`
- `/api/trust/open-loops`
- `/api/trust/diagnostics`

The Trust Center builds a local session state:

- selected mode: high risk, quick clear, open loops, or all
- selected source ids
- current focused source
- local draft notes and rewrites

Submitting still calls `/api/trust/review/batch` or `/api/trust/open-loops/{loop_id}`.

## Error Handling

- If no review item exists, the session planner shows an empty-state next step.
- If rewrite is selected without text, the decision coach blocks submit locally and the backend still enforces the existing validation.
- If diagnostics are missing, the UI uses neutral fallback text.
- If a selected item disappears after refresh, the existing detail reset behavior remains.

## Testing

Add or expand tests for:

- review payload exposes derived decision and signal fields
- risk reasons are deterministic and match existing data
- rewrite action remains blocked without replacement text
- Trust Center renders session planner, progress, decision coach, risk lens, and signal strip
- compact mode still uses progressive disclosure and mobile-safe layout

## Success Criteria

- The Trust module has more code because the review workflow is better decomposed and tested, not because logic is duplicated.
- The user can review the same items with fewer context switches.
- Information remains available but is staged by priority.
- All existing trust API tests continue to pass.
- Frontend build and lint/test commands remain green.
