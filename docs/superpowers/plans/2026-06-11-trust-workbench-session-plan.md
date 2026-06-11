# Trust Workbench Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the existing Trust Center into a guided review workbench without adding a new top-level module or changing the semantics of existing review actions.

**Architecture:** Keep the current `/api/trust/*` endpoints and enrich their existing payloads with deterministic derived fields. Split the Vue Trust Center into small subcomponents for session planning, progress, signals, risk explanation, and decision coaching.

**Tech Stack:** Python/FastAPI/SQLite backend helpers, Vue 3 `<script setup lang="ts">`, TypeScript types, Node test runner, pytest, Vite build.

---

## File Structure

- Modify `snapgraph/trust_center.py`: add derived risk reasons, trust signals, review focus, and decision options.
- Modify `tests/test_trust_center.py`: assert deterministic derived fields and existing validation.
- Modify `frontend/src/components/trustCenterTypes.ts`: add frontend types for derived trust fields and session mode.
- Create `frontend/src/components/trustCenterCopy.ts`: centralize action labels, risk labels, and microcopy helpers.
- Create `frontend/src/components/TrustSessionPlanner.vue`: session mode selector and next-step explanation.
- Create `frontend/src/components/TrustReviewProgress.vue`: current session progress and selected-item summary.
- Create `frontend/src/components/TrustReviewSignals.vue`: reusable compact signal chips.
- Create `frontend/src/components/TrustRiskLens.vue`: focused explanation of why an item has risk.
- Create `frontend/src/components/TrustDecisionCoach.vue`: decision guidance, local validation, and submit actions.
- Modify `frontend/src/components/TrustCenterView.vue`: own local session mode and wire the new subcomponents.
- Modify `frontend/src/components/TrustReviewInbox.vue`: render signal strip and mode-aware card copy.
- Modify `frontend/src/components/TrustReviewDetail.vue`: use risk lens and decision coach while preserving `batchAction`.
- Modify `frontend/src/components/TrustBatchActionBar.vue`: improve batch guidance but keep payload shape.
- Modify `frontend/src/components/TrustOpenLoopPanel.vue`: add compact prioritization copy.
- Modify `frontend/src/components/TrustDiagnosticsPanel.vue`: add clearer trust debt summary.
- Modify `frontend/src/styles.css`: style new trust session, progress, signal, lens, and coach surfaces.
- Modify `tests/trust_operations_ui.test.ts`: assert new components and CSS hooks.

## Task 1: Backend Derived Fields

**Files:**
- Modify: `snapgraph/trust_center.py`
- Test: `tests/test_trust_center.py`

- [ ] Add a failing pytest case asserting each review item contains `risk_reasons`, `decision_options`, `review_focus`, and `trust_signals`.

Run:

```bash
pytest tests/test_trust_center.py::test_trust_review_queue_exposes_session_decision_fields -q
```

Expected before implementation: fail because the fields are absent.

- [ ] Implement deterministic helpers in `snapgraph/trust_center.py`:
  - `_risk_reasons(source, risk, evidence_count)`
  - `_decision_options(source, risk)`
  - `_review_focus(source, risk, evidence_count)`
  - `_trust_signals(source, risk, evidence_count, topic_refs)`

- [ ] Attach those fields inside `_review_item`.

- [ ] Run:

```bash
pytest tests/test_trust_center.py::test_trust_review_queue_exposes_session_decision_fields -q
pytest tests/test_trust_center.py -q
```

- [ ] Commit:

```bash
git add snapgraph/trust_center.py tests/test_trust_center.py
git commit -m "feat: enrich trust review decision fields"
```

## Task 2: Frontend Types And Copy Helpers

**Files:**
- Modify: `frontend/src/components/trustCenterTypes.ts`
- Create: `frontend/src/components/trustCenterCopy.ts`
- Test: `tests/trust_operations_ui.test.ts`

- [ ] Add a failing Node test asserting the new session mode type and copy helper names exist.

Run:

```bash
node --test tests/trust_operations_ui.test.ts
```

Expected before implementation: fail because the helper file and types are missing.

- [ ] Add types:
  - `TrustReviewSessionMode`
  - `TrustDecisionOption`
  - `TrustReviewFocus`
  - `TrustSignals`

- [ ] Add copy helpers:
  - `riskToneLabel`
  - `boundaryLabel`
  - `reviewStatusLabel`
  - `decisionActionLabel`
  - `sessionModeLabel`
  - `sessionModeDescription`
  - `confidenceLabel`

- [ ] Run:

```bash
node --test tests/trust_operations_ui.test.ts
```

- [ ] Commit:

```bash
git add frontend/src/components/trustCenterTypes.ts frontend/src/components/trustCenterCopy.ts tests/trust_operations_ui.test.ts
git commit -m "feat: add trust workbench copy helpers"
```

## Task 3: Session Planner And Progress

**Files:**
- Create: `frontend/src/components/TrustSessionPlanner.vue`
- Create: `frontend/src/components/TrustReviewProgress.vue`
- Modify: `frontend/src/components/TrustCenterView.vue`
- Modify: `frontend/src/styles.css`
- Test: `tests/trust_operations_ui.test.ts`

- [ ] Add failing Node assertions for `TrustSessionPlanner`, `TrustReviewProgress`, `trust-session-planner`, and `trust-review-progress`.
- [ ] Implement mode selection inside `TrustCenterView.vue` with local `ref<TrustReviewSessionMode>('high-risk')`.
- [ ] Filter/sort the visible review list by the selected mode while keeping the loaded backend payload unchanged.
- [ ] Render planner above the batch bar and progress between planner and inbox.
- [ ] Run Node UI tests.
- [ ] Commit:

```bash
git add frontend/src/components/TrustSessionPlanner.vue frontend/src/components/TrustReviewProgress.vue frontend/src/components/TrustCenterView.vue frontend/src/styles.css tests/trust_operations_ui.test.ts
git commit -m "feat: add trust review session planner"
```

## Task 4: Signals, Risk Lens, And Decision Coach

**Files:**
- Create: `frontend/src/components/TrustReviewSignals.vue`
- Create: `frontend/src/components/TrustRiskLens.vue`
- Create: `frontend/src/components/TrustDecisionCoach.vue`
- Modify: `frontend/src/components/TrustReviewInbox.vue`
- Modify: `frontend/src/components/TrustReviewDetail.vue`
- Modify: `frontend/src/styles.css`
- Test: `tests/trust_operations_ui.test.ts`

- [ ] Add failing Node assertions for the new component names and CSS hooks.
- [ ] Render `TrustReviewSignals` in inbox cards and detail brief.
- [ ] Render `TrustRiskLens` in the detail panel before raw evidence disclosures.
- [ ] Move single-item note/rewrite/action UI into `TrustDecisionCoach`.
- [ ] Preserve emitted `TrustBatchPayload` shape exactly.
- [ ] Run Node UI tests.
- [ ] Commit:

```bash
git add frontend/src/components/TrustReviewSignals.vue frontend/src/components/TrustRiskLens.vue frontend/src/components/TrustDecisionCoach.vue frontend/src/components/TrustReviewInbox.vue frontend/src/components/TrustReviewDetail.vue frontend/src/styles.css tests/trust_operations_ui.test.ts
git commit -m "feat: add trust decision coaching UI"
```

## Task 5: Secondary Panels And Final Verification

**Files:**
- Modify: `frontend/src/components/TrustBatchActionBar.vue`
- Modify: `frontend/src/components/TrustOpenLoopPanel.vue`
- Modify: `frontend/src/components/TrustDiagnosticsPanel.vue`
- Modify: `frontend/src/styles.css`
- Test: `tests/trust_operations_ui.test.ts`

- [ ] Add concise secondary guidance to batch, open-loop, and diagnostics panels.
- [ ] Add responsive CSS for session planner, signal chips, risk lens, and decision coach.
- [ ] Run:

```bash
node --test tests/*.test.ts
pytest -q
python -m snapgraph.cli lint
npm run build
```

- [ ] Restore generated static assets after build:

```powershell
git restore -- snapgraph/static
$workspace = (Resolve-Path '.').Path
$files = git ls-files --others --exclude-standard snapgraph/static/assets
foreach ($file in $files) {
  $resolved = (Resolve-Path -LiteralPath $file).Path
  if (-not $resolved.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove outside workspace: $resolved"
  }
  Remove-Item -LiteralPath $resolved -Force
}
```

- [ ] Commit:

```bash
git add frontend/src/components/TrustBatchActionBar.vue frontend/src/components/TrustOpenLoopPanel.vue frontend/src/components/TrustDiagnosticsPanel.vue frontend/src/styles.css tests/trust_operations_ui.test.ts
git commit -m "feat: refine trust secondary guidance"
```

## Self-Review

- Spec coverage: the tasks cover derived fields, session planning, progress, signals, risk explanation, decision coaching, secondary panels, tests, and verification.
- Scope: all changes stay inside the Trust Center and existing trust endpoints.
- API compatibility: existing endpoints and action payloads are preserved.
- No placeholder tasks remain; each task names concrete files, commands, and commit boundaries.
