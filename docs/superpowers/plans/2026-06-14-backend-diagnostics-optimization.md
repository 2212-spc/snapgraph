# Backend Diagnostics Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand SnapGraph's recall, trust, and collection logic with deeper diagnostics and decision layers while keeping the current frontend layout essentially unchanged.

**Architecture:** Add a shared backend diagnostics layer that turns existing retrieval, review, and ingest data into richer decision payloads. Keep the current API surface stable by extending existing responses with new nested fields instead of redesigning the UI flow. Cover the new behavior with focused tests around pure helpers and API contracts.

**Tech Stack:** Python, FastAPI, SQLite, Pytest, existing SnapGraph domain modules.

---

### Task 1: Add shared diagnostics builders

**Files:**
- Create: `snapgraph/decision_layers.py`
- Modify: `snapgraph/api.py`
- Modify: `snapgraph/recall_projection.py`

- [ ] **Step 1: Write the failing test**

```python
def test_build_recall_decision_layer_includes_boundary_and_next_step(tmp_path: Path, monkeypatch) -> None:
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_decision_layers.py::test_build_recall_decision_layer_includes_boundary_and_next_step -v`
Expected: FAIL because `decision_layers` helpers do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create pure helper functions that build:
- recall decision layers
- trust queue decision layers
- collect ingest decision layers

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_decision_layers.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snapgraph/decision_layers.py snapgraph/recall_projection.py snapgraph/api.py tests/test_decision_layers.py
git commit -m "feat: add shared diagnostics layers"
```

### Task 2: Enrich ask and trust API payloads

**Files:**
- Modify: `snapgraph/api.py`
- Modify: `snapgraph/trust_center.py`
- Modify: `snapgraph/trust_engine.py`

- [ ] **Step 1: Write the failing test**

```python
def test_api_ask_includes_decision_layers(tmp_path: Path, monkeypatch) -> None:
    ...

def test_api_trust_review_includes_decision_layers(tmp_path: Path, monkeypatch) -> None:
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -k "decision_layers" -v`
Expected: FAIL because the new payload keys are missing.

- [ ] **Step 3: Write minimal implementation**

Extend the existing API responses with compact diagnostics objects:
- `decision_layers` for `/api/ask`
- `decision_layers` for `/api/trust/review`
- `decision_layers` for `/api/trust/review/{source_id}`

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -k "decision_layers" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snapgraph/api.py snapgraph/trust_center.py snapgraph/trust_engine.py tests/test_api.py
git commit -m "feat: enrich recall and trust payloads"
```

### Task 3: Add ingest quality and routing diagnostics

**Files:**
- Modify: `snapgraph/ingest.py`
- Modify: `snapgraph/spaces.py`
- Modify: `snapgraph/api.py`

- [ ] **Step 1: Write the failing test**

```python
def test_api_ingest_exposes_capture_diagnostics(tmp_path: Path, monkeypatch) -> None:
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api.py -k "capture_diagnostics" -v`
Expected: FAIL because ingest responses do not expose the new diagnostics yet.

- [ ] **Step 3: Write minimal implementation**

Expose:
- dedupe and routing explanations
- capture quality summary
- source traceability summary
- route suggestion rationale

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api.py -k "capture_diagnostics" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snapgraph/ingest.py snapgraph/spaces.py snapgraph/api.py tests/test_api.py
git commit -m "feat: add capture diagnostics"
```

### Task 4: Add focused regression coverage

**Files:**
- Create: `tests/test_decision_layers.py`
- Modify: `tests/test_answer.py`
- Modify: `tests/test_trust_center.py`
- Modify: `tests/test_ingest.py`

- [ ] **Step 1: Write the failing test**

Add regression checks for:
- recall decision layering
- trust queue decision layering
- ingest/routing quality summaries

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_decision_layers.py tests/test_api.py -v`
Expected: FAIL until all new payloads are wired through.

- [ ] **Step 3: Write minimal implementation**

Keep the new helpers deterministic and reuse existing domain data.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_decision_layers.py tests/test_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_decision_layers.py tests/test_answer.py tests/test_trust_center.py tests/test_ingest.py
git commit -m "test: cover diagnostics layers"
```

