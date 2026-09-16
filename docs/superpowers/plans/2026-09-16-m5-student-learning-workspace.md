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

`1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15`.

## Stable Workspace DOM Contract

All modules/tests use these hooks: `#workspace-root`, `#workspace-project-header`, `#workspace-read-only`, `#workspace-modeling-panel`, `#workspace-properties-panel`, `#workspace-canvas`, `#workspace-workflow-panel`, `#workspace-workflow-steps`, `#workspace-status-bar`, `#workspace-dynamic-input`, `#workspace-dynamic-distance`, `#workspace-dynamic-angle`, `#workspace-snap-indicator`, `#workspace-save-status`, `#workspace-save`, `#workspace-model-check`, `#workspace-results`, `#workspace-reflection`, and `#workspace-bootstrap`. Dynamic input has `data-active-field="distance|angle"`; it is hidden outside `DYNAMIC_INPUT`. SVG selectable objects have `data-client-key`, `data-object-kind`, `tabindex="0"`, `role="button"`, and an `aria-label` such as `节点 n1` or `构件 m1`; selection is not color-only.

## Bootstrap and URL Contract

`#workspace-bootstrap` is `<script type="application/json">` with `{schema_version:"workspace-bootstrap-v1",project:{id:number,name:string,analysis_type:"TRUSS_2D"},draft:{schema_version:"physical-draft-v1",version:number,nodes:Array<{client_key:string,x_mm:number,y_mm:number,label:string}>,physical_members:Array<{client_key:string,start_node_client_key:string,end_node_client_key:string,material_id:number,section_id:number,label:string,is_active:boolean}>,connections:Array<{client_key:string,geometry_node_client_key:string,participating_member_client_keys:string[]}>,supports:Array<{target_connection_client_key:string,support_type:"PINNED"|"ROLLER",restrained_axis:"X"|"Y"|null}>,node_loads:Array<{client_key:string,target_connection_client_key:string,fx_N:number,fy_N:number,label:string}>},read_only:boolean,urls:{save:string,check:string,prediction_current:string,prediction_create:string,prediction_complete_template:string,analyze:string,result_template:string,comparison_template:string,explanation_template:string,reflection_template:string,reflection_complete_template:string}}`. URLs are `/projects/<project_id>/model/save/`, `/model/check/`, `/predictions/current/`, `/predictions/`, `/predictions/{prediction_id}/complete/`, `/analyze/`, `/analyses/{run_id}/data/`, `/comparison/`, `/explanation/`, `/analyses/{run_id}/reflection/`, and `/reflection/complete/` relative to `/projects/<project_id>/`. Result/evidence/text are lazy-loaded and never bootstrap fields.

## Browser harness and isolation

Add test-only `playwright==1.63.0` (PyPI supports Python 3.13) to `[project.optional-dependencies].test`; install Chromium with `python3 -m playwright install chromium`. Mark browser tests `@pytest.mark.browser`, register the marker, and skip them when `PLAYWRIGHT_BROWSERS_PATH`/Chromium is unavailable; ordinary `pytest -q` excludes browser tests via `-m 'not browser'`, while Final B runs `pytest tests/browser -q`. Fixture `workspace_page` in `tests/browser/conftest.py` opens Django `live_server`; pure-module tests call `page.evaluate("import('/static/projects/workspace/cad-input.js')")`, invoke exports, and return plain JSON for pytest assertions.

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

### Task 3 (Gate 2B-1): Pure CAD parser and drawing state
**Files:** Create `cad-input.js`, `cad-state.js`; test `tests/browser/test_workspace.py`.
**Interfaces:** `parseCadInput(text, origin) -> {ok:true,kind:"ABSOLUTE"|"RELATIVE"|"POLAR",point:{x:number,y:number}}|{ok:false,code:"EMPTY"|"INCOMPLETE"|"MALFORMED"}`; `transition(state,event) -> {state,fieldIndex}`. Events are `SELECT_TOOL`, `POINTER_POINT`, `INPUT_CHANGE`, `TAB`, `ENTER`, `ESC`; Esc returns `IDLE`, and Tab is intercepted only in `DYNAMIC_INPUT`.
- [ ] Test `1000,500`, `@-2.5, 3`, `1000<30`, whitespace, malformed/partial, Enter/Esc/Tab states; RED.
- [ ] Implement DOM-free parser and enum states `IDLE,SELECTING,DRAW_NODE,DRAW_MEMBER_WAIT_START,DRAW_MEMBER_WAIT_END,DYNAMIC_INPUT`; Tab only intercepts dynamic input; PASS; commit.

### Task 4 (Gate 2B-2): Geometry, SNAP, Grid, and topology boundary
**Files:** Create `geometry.js`; modify renderer; test `tests/browser/test_workspace.py`.
**Interfaces:** `resolvePointerPoint({worldPointer,screenPointer,candidates,origin,ortho,gridEnabled,explicitNumeric}) -> {point:{x,y},snapType:"NODE"|"INT"|"GRID"|null,candidateKey:string|null}`; `gridNearest(value) -> number` uses 100 mm/global origin/positive midpoint.
- [ ] Test 12 CSS px, priority/nearest/canonical tie, `493→500`, `50→100`, `-50→0`, ORTHO free axis, numeric bypass, intersection candidate without Connection mutation; RED.
- [ ] Implement single resolver and visible `NODE|INT|GRID`; keep `createConnection` solely in editor; PASS; commit.

### Task 5 (Gate 2B-3): Structural editor mutation bridge
**Files:** Create `editor.js`; modify state/renderer; test browser file.
**Interfaces:** `applyEditorAction(draft, action) -> draft`; actions include explicit `CREATE_CONNECTION` only.
- [ ] Test node/member/property edits and crossing-members preserve connection count; RED.
- [ ] Implement immutable local draft actions only; PASS; commit.

### Task 6 (Gate 2B-4): Canvas navigation and picking
**Files:** Create `canvas-interaction.js`; modify renderer/state; test `tests/browser/test_workspace.py`.
**Interfaces:** `pickAt(screenPoint, renderedObjects) -> clientKey|null`; `reduceView(view,event) -> view` for `PAN`,`ZOOM`,`FIT_VIEW`.
- [ ] Test keyboard-accessible selected SVG items, pan/zoom/fit retain world Grid origin; run `pytest tests/browser/test_workspace.py -q` (RED: module unavailable).
- [ ] Implement view transform only; PASS and Task 4 regression; commit `feat: add canvas navigation`.

### Task 7 (Gate 2C): Save, check, and error boundary
**Files:** Create `errors.js`; modify `api.js`, `workflow.js`, template; tests `test_workspace.py`, `test_project_json.py`.
**Interfaces:** `normalizeApiError(response) -> {code,message,details}`; `presentWorkspaceError(error) -> {what,why,nextAction,technicalCode}`; `saveDraft(draft)`, `checkModel(version)`.
- [ ] Test dirty/version update, stale reload advice, check issue focus, and no JS mechanics diagnosis; RED.
- [ ] Use existing save/check endpoints, CSRF client, three-part zh-CN error presentation; PASS plus endpoint regression; commit.

### Task 8 (Gate 3A, BCG-02): Prediction cardinality, migration, discovery
**Files:** Modify `learning/{models,services,views,urls}.py`; create migration `learning/migrations/0004_prediction_project_draft_unique.py`; tests `test_prediction.py`, `test_prediction_json.py`.
**Interfaces:** `discover_current_prediction(project, actor) -> {state:"NONE",source_draft_version:number}|{state:"DRAFT"|"COMPLETED",prediction:Prediction}|raise PredictionError("PREDICTION_AMBIGUOUS")`; `GET /projects/<project_id>/predictions/current/` returns `{ok:true,state:"NONE",source_draft_version}` or `{ok:true,state:"DRAFT"|"COMPLETED",prediction:<existing response>}`, and 409 `{ok:false,error:{code:"PREDICTION_AMBIGUOUS",message,details:{project_id,source_draft_version,duplicate_count}}}`. POST `/projects/<project_id>/predictions/` resumes DRAFT, returns COMPLETED unchanged, and rejects ambiguity.
- [ ] Test duplicate preflight fails `PREDICTION_AMBIGUOUS`, concurrent create returns same DRAFT, completed binds only explicitly, draft/null remains analyzable; RED.
- [ ] Lock Project in `transaction.atomic`, re-query pair, create only when absent; on uniqueness `IntegrityError`, re-query and return sole DRAFT/COMPLETED, else ambiguity. Migration queries `values("project_id","source_draft_version").annotate(count=Count("id")).filter(count__gt=1)` and raises with each pair/count before adding the constraint; no mutation/remediation. PASS plus `pytest tests/application/test_prediction.py tests/endpoints/test_prediction_json.py -q`; commit.

### Task 9 (Gate 3B): Prediction workspace UI
**Files:** Create `prediction.js`; modify workflow/api/renderer; test browser file.
**Interfaces:** `loadPrediction()`, `completePrediction(payload)`, `predictionForAnalyze() -> id|null`.
- [ ] Test NONE/DRAFT/COMPLETED/AMBIGUOUS, all member choices, point/path selection, skip; RED.
- [ ] Wire existing endpoints and no selector/history; PASS; commit.

### Task 10 (Gate 4A): Analyze and Level 1 results
**Files:** Create `results.js`; modify workflow/api/renderer; tests browser and `test_project_json.py`.
**Interfaces:** `analyze(version,predictionId)`, `showLevelOne(run,data)`.
- [ ] Test null prediction allowed, completed explicit binding, stale-result label and text/non-color force overlay; RED.
- [ ] Consume authoritative analysis data only; PASS; commit.

### Task 11 (Gate 4B): Compare and Explain
**Files:** Modify `results.js`; tests browser, `test_compare_explanation_json.py`.
**Interfaces:** `showComparison(comparison)`, `showExplanation(explanation)`, `focusPhysicalMember(clientKey)`.
- [ ] Test MATCH/MISMATCH/UNSURE/NOT_COMPARABLE/NO_PREDICTION and MIXED segment evidence; RED.
- [ ] Render backend wording/blocks and Canvas linkage without recomputation; PASS; commit.

### Task 12 (Gate 4C): Engineering details
**Files:** Modify `results.js`; test `tests/browser/test_workspace.py`.
**Interfaces:** `showEngineeringDetails(resultJson) -> void`.
- [ ] Test Level-3 only exposes authoritative displacement/reaction/axial-force/stress/mass and optional deformation warning; run `pytest tests/browser/test_workspace.py -q` (RED).
- [ ] Render supplied values only; if deformation view is added, show “变形显示已放大，仅用于观察变形趋势。”; PASS plus compare regression; commit.

### Task 13 (Gate 5): Reflection UI
**Files:** Create `reflection.js`; modify workflow/api/template; tests browser, `test_reflection_json.py`.
**Interfaces:** `loadReflection(runId)`, `saveReflection(fields)`, `completeReflection()`.
- [ ] Test draft partial/clear/complete, owner-only editing, completed reader view, skip; RED.
- [ ] Wire existing singleton routes; PASS and soft-gate regression; commit.

### Task 14 (Final Gate A): Reconciliation
**Files:** Modify `docs/superpowers/plans/2026-09-16-m5-student-learning-workspace.md` only if implementation records require factual status; no production/test files.
- [ ] Compare each UX acceptance scenario to implementation/tests and classify any mismatch as `SPEC_IMPLEMENTATION_CONFLICT`, `TEST_CONTRACT_CONFLICT`, `PRODUCTION_DEFECT`, or `SPEC_GAP`; run `git diff --check`.
- [ ] If a mismatch exists, STOP without edits; otherwise record reconciliation evidence and commit `docs: reconcile M5 workspace`.

### Task 15 (Final Gate B): Fresh verification and acceptance evidence
**Files:** no changes.
- [ ] Run `python manage.py check`, `python manage.py makemigrations --check --dry-run`, targeted M5 tests, `pytest -q`, `pytest tests/browser -q`, `git diff --check`, and `git status`; any failure is STOP/classified.
- [ ] Make no production, test, spec, or merge change; report commands/output as final evidence.

## Coverage review

Tasks 1–2 cover layout/delivery/rendering; 3–5 cover CAD precision, SNAP/Grid and `Intersection ≠ Connection`; 6 covers save/check; 7–8 cover O-M5-P01 and soft skip; 9–10 cover progressive result disclosure; 11 covers Reflection; 12 covers scenarios A–E. No task changes mechanics authority or introduces a frontend framework.
