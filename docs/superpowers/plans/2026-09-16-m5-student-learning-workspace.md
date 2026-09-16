# M5 Student Learning Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the zh-CN, server-rendered SVG Project Workspace through independently reviewable M5 gates.

**Architecture:** Django supplies authorized page/bootstrap and thin JSON endpoints; Vanilla ES modules own UI/drawing state and SVG rendering. Existing services remain authoritative for drafts, mechanics, learning evidence, and authorization.

**Tech Stack:** Django 5.2, pytest/pytest-django, HTML/CSS, Vanilla JavaScript ES modules, SVG; no npm framework.

**Spec:** `docs/specs/STUDENT_LEARNING_WORKSPACE_UX.md`

## Global Constraints

- UI copy is zh-CN; identifiers remain English.
- Use `TRUSS_2D`, mm/N/MPa/g, existing JSON services, CSRF, and server authorization.
- No browser solver/classifier, automatic Connection, SPA, WebGL, adaptive/custom Grid, history selector, scoring, or DesignIteration.
- Every task: write the named failing test, run it RED, implement minimally, run PASS plus named regression, commit, and stop for review.

## File responsibility map

| File | Responsibility |
|---|---|
| `projects/workspace.py` | authorized page/bootstrap and draft serialization |
| `projects/views.py`, `projects/urls.py` | existing draft/result routes plus Workspace route |
| `learning/services.py`, `learning/views.py`, `learning/urls.py`, `learning/models.py` | current-Prediction discovery, singleton creation, uniqueness |
| `templates/projects/workspace.html` | three-panel shell/status regions/bootstrap JSON |
| `projects/static/projects/workspace/{api,state,renderer,cad-input,cad-state,geometry,editor,workflow,prediction,results,reflection,errors}.js` | respectively HTTP, state, SVG, pure input, state machine, snap/grid, mutations, stages, prediction, results, reflection, error presentation |
| `projects/static/projects/workspace/workspace.css` | accessible layout/focus/non-color state |
| `tests/endpoints/test_workspace.py` | page/bootstrap/read-only contracts |
| `tests/endpoints/test_prediction_json.py` | discovery/CSRF/ambiguity routes |
| `tests/application/test_prediction.py` | singleton creation/legacy preflight service behavior |
| `tests/browser/test_workspace.py` | final Playwright product paths; add `playwright` only as test extra because Node is absent |
| `pyproject.toml`, `tests/browser/conftest.py` | pinned Python browser-test extra and authenticated live-server fixture |

## Dependency graph

`1 → 2 → 3/4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12`.

### Task 1 (Gate 1, BCG-01/03): Workspace delivery
**Files:** Create `projects/workspace.py`, `templates/projects/workspace.html`, `projects/static/projects/workspace/{state.js,api.js,workspace.css}`, `tests/browser/conftest.py`; modify `projects/urls.py`, `pyproject.toml`; test `tests/endpoints/test_workspace.py`.
**Interfaces:** `workspace(request, project_id) -> TemplateResponse`; bootstrap `{project,draft,read_only,urls}`.
- [ ] Write `test_owner_gets_bootstrap_and_manager_gets_read_only`; run `pytest tests/endpoints/test_workspace.py -q` (RED).
- [ ] Add pinned Python `playwright` to the test extra and an authenticated `live_server` fixture; install its Chromium runtime once for browser tests because the repository has no Node/JS runner.
- [ ] Serialize current mutable draft with client keys/version, authorize by `can_view_project`, render labeled left/center/right/status regions and local assets; rerun PASS and `pytest tests/permissions/test_event_project_access.py -q`.
- [ ] Commit `feat: add workspace shell`.

### Task 2 (Gate 2A): Deterministic SVG renderer
**Files:** Create `renderer.js`; modify template/state; test `tests/browser/test_workspace.py`.
**Interfaces:** `renderWorkspace(svg, draft, uiState)`; emits nodes/members/connections/supports/loads keyed by client key.
- [ ] Write renderer fixture test asserting stable keyed SVG and no analysis-element label; RED.
- [ ] Render physical objects only, text/non-color selection; PASS and Task 1 test; commit.

### Task 3 (Gate 2B): Pure CAD parser and drawing state
**Files:** Create `cad-input.js`, `cad-state.js`; test `tests/browser/test_workspace.py`.
**Interfaces:** `parseCadInput(text, origin) -> {kind,point}|{error}`; `transition(state,event) -> state`.
- [ ] Test `1000,500`, `@-2.5, 3`, `1000<30`, whitespace, malformed/partial, Enter/Esc/Tab states; RED.
- [ ] Implement DOM-free parser and enum states `IDLE,SELECTING,DRAW_NODE,DRAW_MEMBER_WAIT_START,DRAW_MEMBER_WAIT_END,DYNAMIC_INPUT`; Tab only intercepts dynamic input; PASS; commit.

### Task 4 (Gate 2B): Geometry, SNAP, Grid, and topology boundary
**Files:** Create `geometry.js`; modify renderer; test `tests/browser/test_workspace.py`.
**Interfaces:** `resolvePointerPoint({pointer,origin,candidates,ortho,gridEnabled,transform}) -> {point,snapType}`; `gridNearest(value) -> number`.
- [ ] Test 12 CSS px, priority/nearest/canonical tie, `493→500`, `50→100`, `-50→0`, ORTHO free axis, numeric bypass, intersection candidate without Connection mutation; RED.
- [ ] Implement single resolver and visible `NODE|INT|GRID`; keep `createConnection` solely in editor; PASS; commit.

### Task 5 (Gate 2B): Editor mutation bridge
**Files:** Create `editor.js`; modify state/renderer; test browser file.
**Interfaces:** `applyEditorAction(draft, action) -> draft`; actions include explicit `CREATE_CONNECTION` only.
- [ ] Test node/member/property edits and crossing-members preserve connection count; RED.
- [ ] Implement immutable local draft actions/picking/pan/zoom/fit; PASS; commit.

### Task 6 (Gate 2C): Save, check, and error boundary
**Files:** Create `errors.js`; modify `api.js`, `workflow.js`, template; tests `test_workspace.py`, `test_project_json.py`.
**Interfaces:** `saveDraft(draft)`, `checkModel(version)`, `presentError(error)`.
- [ ] Test dirty/version update, stale reload advice, check issue focus, and no JS mechanics diagnosis; RED.
- [ ] Use existing save/check endpoints, CSRF client, three-part zh-CN error presentation; PASS plus endpoint regression; commit.

### Task 7 (Gate 3, BCG-02): Prediction cardinality, migration, discovery
**Files:** Modify `learning/{models,services,views,urls}.py`; create migration `learning/migrations/0004_prediction_project_draft_unique.py`; tests `test_prediction.py`, `test_prediction_json.py`.
**Interfaces:** `discover_current_prediction(project, actor) -> NONE|Prediction`; `create_prediction(...)` resumes singleton; `GET .../predictions/current/`.
- [ ] Test duplicate preflight fails `PREDICTION_AMBIGUOUS`, concurrent create returns same DRAFT, completed binds only explicitly, draft/null remains analyzable; RED.
- [ ] Add preflight migration that aborts without deletion on duplicates, then unique `(project,source_draft_version)` constraint; discovery 409 ambiguity and owner authorization; PASS plus compare/reveal tests; commit.

### Task 8 (Gate 3): Prediction workspace UI
**Files:** Create `prediction.js`; modify workflow/api/renderer; test browser file.
**Interfaces:** `loadPrediction()`, `completePrediction(payload)`, `predictionForAnalyze() -> id|null`.
- [ ] Test NONE/DRAFT/COMPLETED/AMBIGUOUS, all member choices, point/path selection, skip; RED.
- [ ] Wire existing endpoints and no selector/history; PASS; commit.

### Task 9 (Gate 4A): Analyze and Level 1 results
**Files:** Create `results.js`; modify workflow/api/renderer; tests browser and `test_project_json.py`.
**Interfaces:** `analyze(version,predictionId)`, `showLevelOne(run,data)`.
- [ ] Test null prediction allowed, completed explicit binding, stale-result label and text/non-color force overlay; RED.
- [ ] Consume authoritative analysis data only; PASS; commit.

### Task 10 (Gate 4B/4C): Compare, Explain, engineering details
**Files:** Modify `results.js`; tests browser, `test_compare_explanation_json.py`.
**Interfaces:** `showComparison(comparison)`, `showExplanation(explanation)`, `showEngineeringDetails(data)`.
- [ ] Test MATCH/MISMATCH/UNSURE/NOT_COMPARABLE/NO_PREDICTION and MIXED segment evidence; RED.
- [ ] Render backend wording/blocks and displacement/reaction/force/stress/mass disclosure without recomputation; PASS; commit.

### Task 11 (Gate 5): Reflection UI
**Files:** Create `reflection.js`; modify workflow/api/template; tests browser, `test_reflection_json.py`.
**Interfaces:** `loadReflection(runId)`, `saveReflection(fields)`, `completeReflection()`.
- [ ] Test draft partial/clear/complete, owner-only editing, completed reader view, skip; RED.
- [ ] Wire existing singleton routes; PASS and soft-gate regression; commit.

### Task 12 (Final A/B): Reconciliation and acceptance
**Files:** Modify `tests/browser/test_workspace.py`; no production files.
- [ ] Write browser scenarios A–D plus read-only scenario E; RED.
- [ ] Complete smallest missing contract work, PASS targeted browser tests; run `pytest -q`, `git diff --check`; commit `test: verify M5 workspace acceptance`.

## Coverage review

Tasks 1–2 cover layout/delivery/rendering; 3–5 cover CAD precision, SNAP/Grid and `Intersection ≠ Connection`; 6 covers save/check; 7–8 cover O-M5-P01 and soft skip; 9–10 cover progressive result disclosure; 11 covers Reflection; 12 covers scenarios A–E. No task changes mechanics authority or introduces a frontend framework.
