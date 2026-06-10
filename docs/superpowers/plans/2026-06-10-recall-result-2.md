# Recall Result 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the existing Recall result page into an evidence-first recovery desk without adding a new top-level module.

**Architecture:** Add a deterministic backend projection builder in `snapgraph/recall_projection.py`, include it in ask responses, then render it through focused Vue child components inside the existing `RecallResult.vue`. Keep existing answer text, focus graph, and review APIs compatible.

**Tech Stack:** Python, FastAPI, SQLite-backed retrieval models, Vue 3, TypeScript, Vite, Node test runner, pytest.

---

## File Structure

- Create `snapgraph/recall_projection.py`: pure projection functions for judgment brief, evidence ladder, trust debt, actions, and write-back preview.
- Modify `snapgraph/api.py`: include `recall_projection` in ask payloads and stream final payloads.
- Modify `frontend/src/types.ts`: add `RecallProjection` and attach it to `AskResponse`.
- Create `frontend/src/components/RecallJudgmentBrief.vue`: summary card for recovered judgment and evidence counters.
- Create `frontend/src/components/RecallEvidenceLadder.vue`: ordered evidence cards with user-stated, source, AI-inferred, and graph tones.
- Create `frontend/src/components/RecallTrustDebtPanel.vue`: user-facing uncertainty and trust debt list.
- Create `frontend/src/components/RecallActionRail.vue`: follow-up, review, save, and open-loop actions.
- Create `frontend/src/components/RecallWriteBackPreview.vue`: preview of what is worth saving from this answer.
- Modify `frontend/src/components/RecallResult.vue`: import and render the new components when projection exists.
- Modify `frontend/src/styles.css`: add responsive result-desk styles.
- Modify `tests/test_answer.py`: add projection unit tests.
- Modify `tests/test_api.py`: assert ask and stream include projection.
- Modify `tests/recall_phase1_ui.test.ts`: assert frontend structure and styles.

## Tasks

### Task 1: Backend Projection

- [ ] Add failing tests in `tests/test_answer.py` for `build_recall_result_projection`.
- [ ] Run `pytest tests/test_answer.py -q` and confirm the new tests fail because `snapgraph.recall_projection` is missing.
- [ ] Create `snapgraph/recall_projection.py` with pure projection helpers.
- [ ] Run `pytest tests/test_answer.py -q` and confirm projection tests pass.
- [ ] Commit with `feat: add recall result projection`.

### Task 2: API Contract

- [ ] Add failing API assertions in `tests/test_api.py` for `recall_projection` in `/api/ask` and `/api/ask/stream`.
- [ ] Run the targeted API tests and confirm they fail because the payload lacks `recall_projection`.
- [ ] Import and call `build_recall_result_projection` in `_ask_response_payload`.
- [ ] Run targeted API tests and confirm they pass.
- [ ] Commit with `feat: expose recall result projection`.

### Task 3: Frontend Types and Structure

- [ ] Add failing UI structure assertions in `tests/recall_phase1_ui.test.ts`.
- [ ] Run `node --test tests/recall_phase1_ui.test.ts` and confirm failure.
- [ ] Add `RecallProjection` types to `frontend/src/types.ts`.
- [ ] Create the five child components with typed props and emits.
- [ ] Import and render them from `RecallResult.vue`.
- [ ] Run the targeted Node UI test and confirm it passes.
- [ ] Commit with `feat: add recall result workbench components`.

### Task 4: Styling and Responsive Polish

- [ ] Add failing style assertions in `tests/recall_phase1_ui.test.ts`.
- [ ] Run the targeted Node UI test and confirm failure.
- [ ] Add styles for `.recall-result-desk`, `.recall-judgment-brief`, `.recall-evidence-ladder`, `.recall-trust-debt-panel`, `.recall-action-rail`, and `.recall-writeback-preview`.
- [ ] Run the targeted Node UI test and confirm it passes.
- [ ] Commit with `feat: polish recall result 2 layout`.

### Task 5: Full Verification

- [ ] Run `node --test tests/*.test.ts`.
- [ ] Run `pytest -q`.
- [ ] Run `npm run build`.
- [ ] Restore `snapgraph/static/demo-v2.html` and `snapgraph/static/vis-network.min.js` if Vite deletes them.
- [ ] Run demo CLI chain in a temporary directory.
- [ ] Scan for accidental API keys.
- [ ] Commit build artifacts if changed.

