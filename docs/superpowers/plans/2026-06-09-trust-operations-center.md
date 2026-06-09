# Trust Operations Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Trust Operations Center that lets users review AI-inferred context, inspect evidence, batch-update review decisions, and manage open-loop lifecycle states.

**Architecture:** Add a backend `trust_center` module that projects trust queue items from existing SQLite tables and stores only review history plus open-loop lifecycle records. Add a frontend `trust` view composed of focused Vue components, with `App.vue` owning API loading and mutation calls.

**Tech Stack:** Python, FastAPI, SQLite, pytest, Vue 3, TypeScript, Vite, Node test runner.

---

## File Structure

- Create: `snapgraph/trust_center.py`
  - Review projection, risk scoring, history writes, open-loop materialization, diagnostics.
- Modify: `snapgraph/workspace.py`
  - Add `trust_review_history` and `trust_open_loop_states` tables.
- Modify: `snapgraph/api.py`
  - Add thin `/api/trust/*` route handlers.
- Modify: `snapgraph/models.py`
  - Add trust status constants if shared validation needs them.
- Create: `tests/test_trust_center.py`
  - Backend TDD coverage for queue, summary, detail, batch actions, open-loop lifecycle, diagnostics.
- Create: `frontend/src/components/trustCenterTypes.ts`
  - Frontend-only TypeScript types for trust payloads.
- Create: `frontend/src/components/TrustCenterView.vue`
  - Main operations center layout.
- Create: `frontend/src/components/TrustReviewInbox.vue`
  - Filterable review queue list.
- Create: `frontend/src/components/TrustReviewDetail.vue`
  - Detail drawer with traceability, history, and actions.
- Create: `frontend/src/components/TrustBatchActionBar.vue`
  - Selected-item batch operations.
- Create: `frontend/src/components/TrustOpenLoopPanel.vue`
  - Open-loop lifecycle surface.
- Create: `frontend/src/components/TrustDiagnosticsPanel.vue`
  - Deterministic diagnostics view.
- Modify: `frontend/src/App.vue`
  - Add `trust` nav, API state, loading, actions, and refresh orchestration.
- Modify: `frontend/src/styles.css`
  - Operations-center layout, dense cards, responsive constraints.
- Modify: `frontend/src/types.ts`
  - Add trust API types if they are shared outside trust components.
- Create: `tests/trust_operations_ui.test.ts`
  - Frontend source-level tests for navigation, components, flow, and styles.

## Task 1: Backend Review Projection Tests

**Files:**

- Create: `tests/test_trust_center.py`

- [ ] **Step 1: Write failing tests**

Add tests for queue, summary, detail, and diagnostics:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from snapgraph.api import app


def test_trust_review_queue_prioritizes_unreviewed_ai_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/trust/review")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    assert payload["summary"]["total"] == len(payload["items"])
    assert any(item["why_saved_status"] == "AI-inferred" for item in payload["items"])
    assert payload["items"][0]["risk_level"] in {"critical", "high", "medium", "low"}
    assert "recommended_action" in payload["items"][0]


def test_trust_review_detail_exposes_traceability(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    queue = client.get("/api/trust/review").json()
    source_id = queue["items"][0]["source_id"]

    response = client.get(f"/api/trust/review/{source_id}")

    assert response.status_code == 200
    detail = response.json()
    assert detail["item"]["source_id"] == source_id
    assert "evidence_paths" in detail
    assert "history" in detail
    assert "open_loops" in detail


def test_trust_diagnostics_reports_counts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")

    response = client.get("/api/trust/diagnostics")

    assert response.status_code == 200
    diagnostics = response.json()
    assert diagnostics["queue_total"] >= 1
    assert "ai_inferred_unreviewed" in diagnostics
    assert "open_loop_total" in diagnostics
    assert "warnings" in diagnostics
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
pytest tests/test_trust_center.py -q
```

Expected: FAIL because `/api/trust/review` and related endpoints do not exist.

## Task 2: Backend Review Projection Implementation

**Files:**

- Create: `snapgraph/trust_center.py`
- Modify: `snapgraph/workspace.py`
- Modify: `snapgraph/api.py`
- Modify: `snapgraph/models.py` if shared constants are needed

- [ ] **Step 1: Add schema tables**

In `Workspace._init_db`, add:

```python
CREATE TABLE IF NOT EXISTS trust_review_history (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    action TEXT NOT NULL,
    previous_status TEXT NOT NULL,
    next_status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    previous_why_saved TEXT NOT NULL DEFAULT '',
    next_why_saved TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(id)
)
```

and:

```python
CREATE TABLE IF NOT EXISTS trust_open_loop_states (
    loop_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
)
```

- [ ] **Step 2: Implement projection helpers**

Add functions:

```python
def list_review_items(workspace: Workspace, filters: dict | None = None) -> dict:
    """Return a dict with keys items, summary, and filters."""


def get_review_detail(workspace: Workspace, source_id: str) -> dict:
    """Return a dict with keys item, evidence_paths, history, and open_loops."""


def trust_summary(workspace: Workspace) -> dict:
    """Return deterministic aggregate counts derived from current review projection."""


def trust_diagnostics(workspace: Workspace) -> dict:
    """Return queue, history, open-loop, and warning diagnostics."""
```

Risk scoring:

```python
if why_saved_status == "AI-inferred" and review_status == "unreviewed" and confidence < 0.55:
    return "critical"
if why_saved_status == "AI-inferred" and review_status == "unreviewed":
    return "high"
if review_status == "deferred" or open_loops:
    return "medium"
return "low"
```

- [ ] **Step 3: Add FastAPI routes**

```python
@app.get("/api/trust/review")
def api_trust_review(
    status: str = "",
    risk: str = "",
    space_id: str = "",
    q: str = "",
    inferred: str = "",
    has_open_loops: bool | None = None,
):
    return list_review_items(
        _workspace(),
        {
            "status": status,
            "risk": risk,
            "space_id": space_id,
            "q": q,
            "inferred": inferred,
            "has_open_loops": has_open_loops,
        },
    )

@app.get("/api/trust/review/{source_id}")
def api_trust_review_detail(source_id: str):
    return get_review_detail(_workspace(), source_id)

@app.get("/api/trust/summary")
def api_trust_summary():
    return trust_summary(_workspace())

@app.get("/api/trust/diagnostics")
def api_trust_diagnostics():
    return trust_diagnostics(_workspace())
```

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
pytest tests/test_trust_center.py -q
pytest tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add snapgraph/trust_center.py snapgraph/workspace.py snapgraph/api.py snapgraph/models.py tests/test_trust_center.py
git commit -m "feat: add trust review projection API"
```

## Task 3: Batch Review Actions And History

**Files:**

- Modify: `tests/test_trust_center.py`
- Modify: `snapgraph/trust_center.py`
- Modify: `snapgraph/api.py`

- [ ] **Step 1: Write failing tests**

Add:

```python
def test_trust_batch_confirm_writes_history(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    item = next(
        item for item in client.get("/api/trust/review").json()["items"]
        if item["why_saved_status"] == "AI-inferred"
    )

    response = client.post(
        "/api/trust/review/batch",
        json={"source_ids": [item["source_id"]], "action": "confirmed", "note": "User confirmed."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["updated_count"] == 1
    detail = client.get(f"/api/trust/review/{item['source_id']}").json()
    assert detail["item"]["review_status"] == "confirmed"
    assert detail["history"][0]["action"] == "confirmed"


def test_trust_batch_rewrite_requires_replacement_text(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    source_id = client.get("/api/trust/review").json()["items"][0]["source_id"]

    response = client.post(
        "/api/trust/review/batch",
        json={"source_ids": [source_id], "action": "rewritten", "note": "Missing rewrite map."},
    )

    assert response.status_code == 400
    assert "rewrite" in response.json()["detail"].lower()
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
pytest tests/test_trust_center.py::test_trust_batch_confirm_writes_history tests/test_trust_center.py::test_trust_batch_rewrite_requires_replacement_text -q
```

Expected: FAIL because batch endpoint and history writes are missing.

- [ ] **Step 3: Implement action handling**

Add:

```python
def batch_review(
    workspace: Workspace,
    source_ids: list[str],
    action: str,
    note: str = "",
    rewrites: dict[str, str] | None = None,
) -> dict:
    """Return a dict with updated_count, failed_count, items, and errors."""
```

Allowed actions:

- `confirmed`
- `rejected`
- `deferred`
- `rewritten`

Call existing `review_ai_inference` for each valid source and insert history after success.

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
pytest tests/test_trust_center.py -q
pytest tests/test_api.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add snapgraph/trust_center.py snapgraph/api.py tests/test_trust_center.py
git commit -m "feat: add trust batch review history"
```

## Task 4: Open Loop Lifecycle

**Files:**

- Modify: `tests/test_trust_center.py`
- Modify: `snapgraph/trust_center.py`
- Modify: `snapgraph/api.py`

- [ ] **Step 1: Write failing tests**

Add:

```python
def test_trust_open_loops_can_be_marked_next(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    client = TestClient(app)
    client.post("/api/demo/load")
    loops = client.get("/api/trust/open-loops").json()["items"]
    assert loops

    response = client.patch(
        f"/api/trust/open-loops/{loops[0]['loop_id']}",
        json={"state": "next", "note": "Work this next."},
    )

    assert response.status_code == 200
    updated = response.json()["item"]
    assert updated["state"] == "next"
    assert updated["note"] == "Work this next."
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
pytest tests/test_trust_center.py::test_trust_open_loops_can_be_marked_next -q
```

Expected: FAIL because open-loop endpoints are missing.

- [ ] **Step 3: Implement lifecycle helpers**

Add:

```python
def list_open_loops(workspace: Workspace, state: str | None = None) -> dict:
    """Return a dict with items and summary for materialized source and topic open loops."""


def update_open_loop_state(workspace: Workspace, loop_id: str, state: str, note: str = "") -> dict:
    """Persist lifecycle state and return a dict with item for the updated loop."""
```

Stable loop id format:

```python
loop_id = sha256(f"{origin}:{source_id}:{index}:{text}".encode("utf-8")).hexdigest()[:16]
```

Allowed states:

- `active`
- `next`
- `resolved`
- `dismissed`

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
pytest tests/test_trust_center.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add snapgraph/trust_center.py snapgraph/api.py tests/test_trust_center.py
git commit -m "feat: add trust open loop lifecycle"
```

## Task 5: Frontend Trust Center Tests

**Files:**

- Create: `tests/trust_operations_ui.test.ts`

- [ ] **Step 1: Write failing source-level tests**

Add tests:

```typescript
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = process.cwd()
function read(relativePath: string) {
  return readFileSync(resolve(root, relativePath), 'utf8')
}

test('App exposes Trust Center as a primary workspace view', () => {
  const app = read('frontend/src/App.vue')
  assert.match(app, /type ActiveView = 'recall' \| 'spaces' \| 'trust' \| 'collect'/)
  assert.match(app, /label: '信任'/)
  assert.match(app, /<TrustCenterView/)
  assert.match(app, /\/api\/trust\/review/)
  assert.match(app, /\/api\/trust\/open-loops/)
})

test('Trust Center components expose review operations, evidence, open loops, and diagnostics', () => {
  const view = read('frontend/src/components/TrustCenterView.vue')
  const inbox = read('frontend/src/components/TrustReviewInbox.vue')
  const detail = read('frontend/src/components/TrustReviewDetail.vue')
  const batch = read('frontend/src/components/TrustBatchActionBar.vue')
  const loops = read('frontend/src/components/TrustOpenLoopPanel.vue')
  const diagnostics = read('frontend/src/components/TrustDiagnosticsPanel.vue')
  const styles = read('frontend/src/styles.css')

  assert.match(view, /trust-center-view/)
  assert.match(inbox, /risk_level/)
  assert.match(detail, /evidence_paths/)
  assert.match(batch, /batchAction/)
  assert.match(loops, /open-loop/)
  assert.match(diagnostics, /queue_total/)
  assert.match(styles, /\.trust-center-view/)
})
```

- [ ] **Step 2: Verify RED**

Run:

```powershell
node --test tests/trust_operations_ui.test.ts
```

Expected: FAIL because components do not exist and App has no trust view.

- [ ] **Step 3: Commit tests**

Commit the failing frontend tests only after observing RED if useful for review history:

```powershell
git add tests/trust_operations_ui.test.ts
git commit -m "test: cover trust operations center UI"
```

If committing RED tests would interrupt later CI, skip this separate commit and commit tests with the implementation after GREEN.

## Task 6: Frontend Types And Components

**Files:**

- Create: `frontend/src/components/trustCenterTypes.ts`
- Create: `frontend/src/components/TrustCenterView.vue`
- Create: `frontend/src/components/TrustReviewInbox.vue`
- Create: `frontend/src/components/TrustReviewDetail.vue`
- Create: `frontend/src/components/TrustBatchActionBar.vue`
- Create: `frontend/src/components/TrustOpenLoopPanel.vue`
- Create: `frontend/src/components/TrustDiagnosticsPanel.vue`

- [ ] **Step 1: Add TypeScript payload types**

Types:

```typescript
export type TrustRiskLevel = 'critical' | 'high' | 'medium' | 'low'
export type TrustReviewStatus = 'unreviewed' | 'confirmed' | 'rewritten' | 'rejected' | 'deferred'
export type TrustOpenLoopState = 'active' | 'next' | 'resolved' | 'dismissed'
```

- [ ] **Step 2: Build focused components**

Each component should be prop-driven, use stable class names, and emit typed events. Avoid fetching inside child components.

- [ ] **Step 3: Verify component source tests still RED for App only**

Run:

```powershell
node --test tests/trust_operations_ui.test.ts
```

Expected: component file assertions pass, App assertions fail until Task 7.

## Task 7: App Integration And Styles

**Files:**

- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/types.ts` if shared types are needed
- Modify: `tests/study_agent_shell_ui.test.ts` if active view union/nav assertions need the new view

- [ ] **Step 1: Add nav and state**

Add `trust` to `ActiveView`, `navItems`, and the main render branch.

- [ ] **Step 2: Add API orchestration**

Add loading functions:

```typescript
async function loadTrustCenter() {
  const [review, loops, diagnostics] = await Promise.all([
    api('/api/trust/review'),
    api('/api/trust/open-loops'),
    api('/api/trust/diagnostics'),
  ])
  trustReview.value = review
  trustOpenLoops.value = loops
  trustDiagnostics.value = diagnostics
}

async function applyTrustBatch(payload: TrustBatchPayload) {
  await api('/api/trust/review/batch', { method: 'POST', body: JSON.stringify(payload) })
  await loadTrustCenter()
}

async function updateTrustOpenLoop(loopId: string, payload: TrustOpenLoopUpdatePayload) {
  await api(`/api/trust/open-loops/${loopId}`, { method: 'PATCH', body: JSON.stringify(payload) })
  await loadTrustCenter()
}
```

- [ ] **Step 3: Add styles**

Add classes for:

- `.trust-center-view`
- `.trust-summary-grid`
- `.trust-review-inbox`
- `.trust-review-card`
- `.trust-detail-panel`
- `.trust-batch-bar`
- `.trust-open-loop-panel`
- `.trust-diagnostics-panel`

- [ ] **Step 4: Verify GREEN**

Run:

```powershell
node --test tests/*.test.ts
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add frontend/src/App.vue frontend/src/components/Trust*.vue frontend/src/components/trustCenterTypes.ts frontend/src/styles.css frontend/src/types.ts tests/*.test.ts snapgraph/static
git commit -m "feat: add trust operations center UI"
```

## Task 8: Final Verification, Server, Push, PR

**Files:**

- No planned source edits except regenerated static assets if build changes them.

- [ ] **Step 1: Run full verification**

```powershell
node --test tests/*.test.ts
pytest -q
npm run build
```

- [ ] **Step 2: Run demo CLI chain**

Use a temporary directory with `PYTHONPATH=E:\VScode\snapgraph`:

```powershell
python -m snapgraph.cli init
python -m snapgraph.cli load-demo
python -m snapgraph.cli lint
python -m snapgraph.cli graph
python -m snapgraph.cli report
python -m snapgraph.cli ask "Why was LLM Wiki important?"
```

- [ ] **Step 3: Scan secrets**

```powershell
rg -n "sk-[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}" -g "!.git" -g "!.my_snapgraph" -g "!node_modules"
```

Expected: no output.

- [ ] **Step 4: Open local app**

Run demo server on an available port, then open the Trust Center route in the browser for user acceptance.

- [ ] **Step 5: Push and create PR**

```powershell
git push origin cxk
gh pr create --base main --head cxk --title "Add Trust Operations Center" --body "Adds a Trust Operations Center for AI-inferred context review, open-loop lifecycle management, diagnostics, and UI workflows."
```

Expected: branch is pushed and a new PR URL is returned.
