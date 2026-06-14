# Backend Governance 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add substantial backend-only governance, quality, traceability, and trust-density logic while keeping the current frontend layout unchanged.

**Architecture:** Build pure deterministic Python modules that summarize existing answer, trust, graph, source, and workspace data into compact governance payloads. Extend existing API responses with additive nested fields and add one backend diagnostics endpoint; do not change frontend source files.

**Tech Stack:** Python, FastAPI, SQLite, Pytest, existing SnapGraph domain modules.

---

### Task 1: Answer Quality Pack

**Files:**
- Create: `snapgraph/answer_quality.py`
- Modify: `snapgraph/api.py`
- Test: `tests/test_backend_governance.py`

- [ ] Write failing tests for answer quality contract and `/api/ask` payload.
- [ ] Run `pytest tests/test_backend_governance.py -k answer_quality -v` and confirm it fails because `answer_quality` is missing.
- [ ] Implement deterministic answer quality scoring using retrieval contexts, graph paths, diagnostics, answer sections, and source traceability.
- [ ] Add `answer_quality` to `_ask_response_payload`.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Trust Noise Reduction Pack

**Files:**
- Create: `snapgraph/trust_noise.py`
- Modify: `snapgraph/trust_center.py`
- Test: `tests/test_backend_governance.py`

- [ ] Write failing tests for compact trust sections, action lanes, and display policy.
- [ ] Run `pytest tests/test_backend_governance.py -k trust_noise -v` and confirm it fails because `trust_noise` is missing.
- [ ] Implement queue grouping into immediate, next, monitor, and collapsed lanes.
- [ ] Add `noise_reduction` to `list_review_items`.
- [ ] Run the focused tests and confirm they pass.

### Task 3: Source Traceability Audit

**Files:**
- Create: `snapgraph/source_traceability.py`
- Modify: `snapgraph/api.py`
- Test: `tests/test_backend_governance.py`

- [ ] Write failing tests for traceability audit and workspace API payload.
- [ ] Run `pytest tests/test_backend_governance.py -k traceability -v` and confirm it fails because traceability payloads are missing.
- [ ] Implement source coverage checks across SQLite sources, cognitive contexts, graph nodes, graph edges, review status, and recall history.
- [ ] Add `traceability_audit` to `/api/workspace`.
- [ ] Run the focused tests and confirm they pass.

### Task 4: Workspace Governance Report

**Files:**
- Create: `snapgraph/workspace_governance.py`
- Modify: `snapgraph/api.py`
- Test: `tests/test_backend_governance.py`

- [ ] Write failing tests for `/api/governance/report`.
- [ ] Run `pytest tests/test_backend_governance.py -k governance_report -v` and confirm it fails because the endpoint is missing.
- [ ] Implement a report builder that composes workspace health, traceability, trust noise, and graph evidence into a compact backend report.
- [ ] Add `GET /api/governance/report`.
- [ ] Run the focused tests and confirm they pass.

### Task 5: Regression Verification

**Files:**
- Test: `tests/test_backend_governance.py`
- Existing tests from API, trust, ingest, answer, decision, optimization, and backend insight suites.

- [ ] Run `pytest tests/test_backend_governance.py -v`.
- [ ] Run `pytest tests/test_api.py tests/test_trust_center.py tests/test_ingest.py tests/test_answer.py tests/test_decision_layers.py tests/test_optimization_packs.py tests/test_backend_insights.py tests/test_backend_governance.py -q`.
- [ ] Run `npm run build` only if API/static serving needs verification; do not edit frontend source.
- [ ] Restart `snapgraph.cli demo --port 8765` and verify `http://127.0.0.1:8765/` returns 200.
