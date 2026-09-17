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
- Every task: write the named failing test, run it RED, implement minimally, run its PASS command and named regression command, commit, and stop for review.

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

`#workspace-bootstrap` is `<script type="application/json">` with `{schema_version:"workspace-bootstrap-v1",project:{id:number,name:string,analysis_type:"TRUSS_2D"},draft:{schema_version:"physical-draft-v1",version:number,nodes:Array<{client_key:string,x_mm:number,y_mm:number,label:string}>,physical_members:Array<{client_key:string,start_node_client_key:string,end_node_client_key:string,material_id:number,section_id:number,label:string,is_active:boolean}>,connections:Array<{client_key:string,geometry_node_client_key:string,participating_member_client_keys:string[]}>,supports:Array<{target_connection_client_key:string,support_type:"PINNED"|"ROLLER",restrained_axis:"X"|"Y"|null}>,node_loads:Array<{client_key:string,target_connection_client_key:string,fx_N:number,fy_N:number,label:string}>},read_only:boolean,urls:{save:string,check:string,prediction_current:string,prediction_create:string,prediction_complete_template:string,analyze:string,result_template:string,comparison_template:string,explanation_template:string,reflection_template:string,reflection_complete_template:string}}`. Exact URLs are: save `/projects/<project_id>/model/save/`; check `/projects/<project_id>/model/check/`; current Prediction `/projects/<project_id>/predictions/current/`; create `/projects/<project_id>/predictions/`; complete `/projects/<project_id>/predictions/{prediction_id}/complete/` (`prediction_id` comes from discovery/create); analyze `/projects/<project_id>/analyze/`; result `/projects/<project_id>/analyses/{run_id}/data/`; comparison `/projects/<project_id>/analyses/{run_id}/comparison/`; explanation `/projects/<project_id>/analyses/{run_id}/explanation/`; reflection `/projects/<project_id>/analyses/{run_id}/reflection/`; reflection complete `/projects/<project_id>/analyses/{run_id}/reflection/complete/` (each `run_id` comes from successful Analyze). Result/evidence/text are lazy-loaded and never bootstrap fields.

## Browser harness and isolation

Add test-only `playwright==1.63.0` (PyPI supports Python 3.13) to `[project.optional-dependencies].test`; install Chromium with `python3 -m playwright install chromium`. Mark browser tests `@pytest.mark.browser`, register the marker, and skip them when `PLAYWRIGHT_BROWSERS_PATH`/Chromium is unavailable; ordinary `pytest -q` excludes browser tests via `-m 'not browser'`, while Final B runs `pytest tests/browser -q`. Fixture `workspace_page` in `tests/browser/conftest.py` opens Django `live_server`; pure-module tests call `page.evaluate("import('/static/projects/workspace/cad-input.js')")`, invoke exports, and return plain JSON for pytest assertions.

## Execution command matrix

Each task uses its row's exact commands; browser node IDs run through `workspace_page` above. “RED reason” is the required failure before implementation; “Regression” runs after PASS.

| Task | RED command / reason | PASS command | Regression command | Commit |
|---|---|---|---|---|
| 1 | `pytest tests/endpoints/test_workspace.py::test_owner_gets_bootstrap_and_manager_gets_read_only -q` / route 404 | `pytest tests/endpoints/test_workspace.py::test_owner_gets_bootstrap_and_manager_gets_read_only -q` | `pytest tests/permissions/test_event_project_access.py -q` | `feat: add workspace shell` |
| 2 | `pytest tests/browser/test_workspace.py::test_renderer_emits_stable_physical_svg -q` / module unavailable | `pytest tests/browser/test_workspace.py::test_renderer_emits_stable_physical_svg -q` | `pytest tests/endpoints/test_workspace.py -q` | `feat: render physical draft SVG` |
| 3 | `pytest tests/browser/test_workspace.py::test_cad_parser_and_state_transitions -q` / exports unavailable | `pytest tests/browser/test_workspace.py::test_cad_parser_and_state_transitions -q` | `pytest tests/browser/test_workspace.py::test_cad_keyboard_tab_accessibility -q` | `feat: add CAD parser and state` |
| 4 | `pytest tests/browser/test_workspace.py::test_snap_resolver_priority_grid_and_intersection_boundary -q` / resolver unavailable | `pytest tests/browser/test_workspace.py::test_snap_resolver_priority_grid_and_intersection_boundary -q` | `pytest tests/browser/test_workspace.py::test_grid_midpoint_and_ortho_resolution -q` | `feat: add deterministic snap resolver` |
| 5 | `pytest tests/browser/test_workspace.py::test_editor_crossing_members_do_not_create_connection -q` / editor unavailable | `pytest tests/browser/test_workspace.py::test_editor_crossing_members_do_not_create_connection -q` | `pytest tests/browser/test_workspace.py::test_editor_mutations_are_immutable -q` | `feat: add structural editor mutations` |
| 6 | `pytest tests/browser/test_workspace.py::test_canvas_picking_pan_zoom_and_fit -q` / interaction module unavailable | `pytest tests/browser/test_workspace.py::test_canvas_picking_pan_zoom_and_fit -q` | `pytest tests/browser/test_workspace.py::test_svg_objects_are_keyboard_focusable -q` | `feat: add canvas navigation` |
| 7 | `pytest tests/browser/test_workspace.py::test_save_check_error_presentation -q` / API workflow unavailable | `pytest tests/browser/test_workspace.py::test_save_check_error_presentation -q` | `pytest tests/endpoints/test_project_json.py -q` | `feat: add workspace save and model check` |
| 8 | `pytest tests/application/test_prediction.py::test_current_prediction_singleton -q` / service absent | `pytest tests/application/test_prediction.py::test_current_prediction_singleton -q` | `pytest tests/endpoints/test_prediction_json.py -q` | `feat: add prediction discovery` |
| 9 | `pytest tests/browser/test_workspace.py::test_prediction_workspace_states_and_skip -q` / prediction module unavailable | `pytest tests/browser/test_workspace.py::test_prediction_workspace_states_and_skip -q` | `pytest tests/application/test_prediction.py tests/endpoints/test_prediction_json.py -q` | `feat: add prediction workspace UI` |
| 10 | `pytest tests/browser/test_workspace.py::test_analyze_level_one_and_stale_run -q` / results module unavailable | `pytest tests/browser/test_workspace.py::test_analyze_level_one_and_stale_run -q` | `pytest tests/endpoints/test_project_json.py -q` | `feat: add analyze result level one` |
| 11 | `pytest tests/browser/test_workspace.py::test_compare_explain_states_and_canvas_link -q` / comparison UI unavailable | `pytest tests/browser/test_workspace.py::test_compare_explain_states_and_canvas_link -q` | `pytest tests/endpoints/test_compare_explanation_json.py -q` | `feat: add compare and explain UI` |
| 12 | `pytest tests/browser/test_workspace.py::test_engineering_details_authoritative_values -q` / details region absent | `pytest tests/browser/test_workspace.py::test_engineering_details_authoritative_values -q` | `pytest tests/endpoints/test_project_json.py -q` | `feat: add engineering details` |
| 13 | `pytest tests/browser/test_workspace.py::test_reflection_draft_complete_and_readonly -q` / reflection module unavailable | `pytest tests/browser/test_workspace.py::test_reflection_draft_complete_and_readonly -q` | `pytest tests/endpoints/test_reflection_json.py -q` | `feat: add reflection workspace UI` |

### Task 1 (Gate 1, BCG-01/03): Workspace delivery
**Files:**
- Create: `projects/workspace.py`; `templates/projects/workspace.html`; `projects/static/projects/workspace/state.js`; `projects/static/projects/workspace/api.js`; `projects/static/projects/workspace/workspace.css`; `tests/browser/conftest.py`
- Modify: `projects/urls.py`; `pyproject.toml`
- Test: `tests/endpoints/test_workspace.py`

**Consumes:** Project authorization through `can_view_project`; the current Physical Draft; the Bootstrap and URL Contract; and the Stable Workspace DOM Contract.

**Produces:** `workspace(request, project_id) -> TemplateResponse` and `#workspace-bootstrap` containing the exact `workspace-bootstrap-v1` project, draft, `read_only`, and URL fields.

**Test to create:** `test_owner_gets_bootstrap_and_manager_gets_read_only` asserts the owner receives the bootstrap and the manager receives the same readable workspace marked read-only.

**RED command:** `pytest tests/endpoints/test_workspace.py::test_owner_gets_bootstrap_and_manager_gets_read_only -q`

**Expected RED:** workspace route does not exist.

**Implementation boundary:** Authorize and serialize the existing draft/version and render the three panels/status regions; provide local ES-module assets and the authenticated browser fixture; do not alter physical-draft persistence, mechanics, prediction, result, or reflection semantics.

**PASS command:** `pytest tests/endpoints/test_workspace.py::test_owner_gets_bootstrap_and_manager_gets_read_only -q`

**Regression command:** `pytest tests/permissions/test_event_project_access.py -q`

**Commit:** `feat: add workspace shell`

### Task 2 (Gate 2A): Deterministic SVG renderer

**Files:**
- Create: `projects/static/projects/workspace/renderer.js`
- Modify: `templates/projects/workspace.html`; `projects/static/projects/workspace/state.js`
- Test: `tests/browser/test_workspace.py`

**Consumes:** `workspace-bootstrap-v1.draft`; `#workspace-canvas`; the Stable Workspace DOM Contract; the accessible SVG object contract.

**Produces:** `renderWorkspace(svg, draft, uiState) -> void`, rendering `GeometryNode`, `PhysicalMember`, `Connection`, `Support`, and `NodeLoad`. Every selectable SVG object has `data-client-key`, `data-object-kind`, `tabindex="0"`, and an accessible `aria-label`.

**Test to create:** `test_renderer_emits_stable_physical_svg` asserts stable keyed physical objects, no student-visible `AnalysisElement` label, and the selectable-object accessibility contract.

**RED command:** `pytest tests/browser/test_workspace.py::test_renderer_emits_stable_physical_svg -q`

**Expected RED:** renderer module/export does not yet exist.

**Implementation boundary:** Render only the physical draft into the supplied SVG; preserve the input draft without mutation; do not infer mechanics, classify member force, create a `Connection`, or expose analysis-element identity as a student object.

**PASS command:** `pytest tests/browser/test_workspace.py::test_renderer_emits_stable_physical_svg -q`

**Regression command:** `pytest tests/endpoints/test_workspace.py -q`

**Commit:** `feat: render physical draft SVG`

### Task 3 (Gate 2B-1): Pure CAD parser and drawing state

**Files:**
- Create: `projects/static/projects/workspace/cad-input.js`; `projects/static/projects/workspace/cad-state.js`
- Modify: None
- Test: `tests/browser/test_workspace.py`

**Consumes:** the frozen CAD input grammar; O-M5-CAD-03; the Dynamic Input DOM Contract; the angle convention `0° = +X` and positive counter-clockwise. O-M5-CAD-03 defines exact event payloads, `{state,fieldIndex}` semantics, valid/invalid Enter, Esc, Tab, no chaining, and Task 3/4/5 responsibility boundaries.

**Produces:** `parseCadInput(text, origin) -> {ok:true,kind:"ABSOLUTE"|"RELATIVE"|"POLAR",point:{x:number,y:number}}|{ok:false,code:"EMPTY"|"INCOMPLETE"|"MALFORMED"}` and `transition(state, event) -> {state, fieldIndex}`. States are `IDLE`, `SELECTING`, `DRAW_NODE`, `DRAW_MEMBER_WAIT_START`, `DRAW_MEMBER_WAIT_END`, and `DYNAMIC_INPUT`; events are `SELECT_TOOL`, `POINTER_POINT`, `INPUT_CHANGE`, `TAB`, `ENTER`, and `ESC`.

**Test to create:** `test_cad_parser_and_state_transitions` asserts `1000,500`, `@-2.5, 3`, `1000<30`, whitespace, malformed and partial input; all SELECT_TOOL outcomes; pointer transitions from each drawing state; COMMAND/DYNAMIC input changes; valid/invalid Enter; and Esc. `test_cad_keyboard_tab_accessibility` asserts `DYNAMIC_INPUT` Tab 0→1→0 and unchanged Tab outside it.

**RED command:** `pytest tests/browser/test_workspace.py::test_cad_parser_and_state_transitions -q`

**Expected RED:** CAD parser/state exports do not exist.

**Implementation boundary:** Keep parsing DOM-independent; Esc returns in-progress drawing to stable `IDLE`; intercept Tab only in `DYNAMIC_INPUT` and leave browser Tab navigation untouched in every other state; do not render SVG, mutate drafts, resolve pointer snaps, or perform mechanics operations.

**PASS command:** `pytest tests/browser/test_workspace.py::test_cad_parser_and_state_transitions -q`

**Regression command:** `pytest tests/browser/test_workspace.py::test_cad_keyboard_tab_accessibility -q`

**Commit:** `feat: add CAD parser and state`

### Task 4 (Gate 2B-2): Geometry, SNAP, Grid, and topology boundary

**Files:**
- Create: `projects/static/projects/workspace/geometry.js`
- Modify: `projects/static/projects/workspace/renderer.js`
- Test: `tests/browser/test_workspace.py`

**Consumes:** O-M5-CAD-01; O-M5-CAD-02; a world pointer; a screen pointer; a candidate list; drawing origin; ORTHO state; Grid Snap state; and the world/screen transform.

**Produces:** `resolvePointerPoint({worldPointer,screenPointer,candidates,origin,ortho,gridEnabled,explicitNumeric}) -> {point:{x:number,y:number},snapType:"NODE"|"INT"|"GRID"|null,candidateKey:string|null}` and `gridNearest(value) -> number`.

**Test to create:** `test_snap_resolver_priority_grid_and_intersection_boundary` asserts Node/Endpoint > Intersection > Grid priority, 12 CSS px screen tolerance, nearest same-class candidate, deterministic canonical-key tie break, explicit-numeric bypass, and no `Connection` count mutation for an intersection candidate. `test_grid_midpoint_and_ortho_resolution` asserts `493 -> 500`, `247 -> 200`, `50 -> 100`, `-50 -> 0`, `-150 -> -100`, and ORTHO free-axis-only Grid behavior.

**RED command:** `pytest tests/browser/test_workspace.py::test_snap_resolver_priority_grid_and_intersection_boundary -q`

**Expected RED:** geometry resolver export does not exist.

**Implementation boundary:** Implement geometry only through one final-point resolver; use the fixed 100 mm global-origin grid and frozen priority/tolerance rules; explicit numeric input bypasses pointer SNAP; do not mutate the draft or Connections, invoke editor actions, render analysis, or perform mechanics.

**PASS command:** `pytest tests/browser/test_workspace.py::test_snap_resolver_priority_grid_and_intersection_boundary -q`

**Regression command:** `pytest tests/browser/test_workspace.py::test_grid_midpoint_and_ortho_resolution -q`

**Commit:** `feat: add deterministic snap resolver`

### Task 5 (Gate 2B-3): Structural editor mutation bridge

**Files:**
- Create: `projects/static/projects/workspace/editor.js`
- Modify: `projects/static/projects/workspace/state.js`; `projects/static/projects/workspace/renderer.js`
- Test: `tests/browser/test_workspace.py`

**Consumes:** the current local Physical Draft and resolved geometric points from Task 4.

**Produces:** `applyEditorAction(draft, action) -> newDraft` with the action discriminators `CREATE_NODE`, `CREATE_MEMBER`, `UPDATE_OBJECT`, `DELETE_OBJECT`, and `CREATE_CONNECTION`.

**Test to create:** `test_editor_crossing_members_do_not_create_connection` asserts crossing members do not add a Connection unless the action is explicit. `test_editor_mutations_are_immutable` asserts each supported action returns an updated local draft without mutating the input draft.

**RED command:** `pytest tests/browser/test_workspace.py::test_editor_crossing_members_do_not_create_connection -q`

**Expected RED:** editor module/export does not exist.

**Implementation boundary:** Return immutable updated local drafts for the named editor actions; permit `CREATE_CONNECTION` only on an explicit user action; never derive a Connection from a geometric crossing; do not save to the server, resolve snaps, render mechanics, or run solver behavior.

**PASS command:** `pytest tests/browser/test_workspace.py::test_editor_crossing_members_do_not_create_connection -q`

**Regression command:** `pytest tests/browser/test_workspace.py::test_editor_mutations_are_immutable -q`

**Commit:** `feat: add structural editor mutations`

### Task 6 (Gate 2B-4): Canvas navigation and picking

**Files:**
- Create: `projects/static/projects/workspace/canvas-interaction.js`
- Modify: `projects/static/projects/workspace/renderer.js`; `projects/static/projects/workspace/state.js`
- Test: `tests/browser/test_workspace.py`

**Consumes:** rendered keyed SVG physical objects; the current view transform; and a screen-space pointer.

**Produces:** `pickAt(screenPoint, renderedObjects) -> clientKey | null` and `reduceView(view, event) -> view` for `PAN`, `ZOOM`, and `FIT_VIEW` events.

**Test to create:** `test_canvas_picking_pan_zoom_and_fit` asserts picking returns the keyed physical object and pan, zoom, and fit update navigation without changing the world Grid origin. `test_svg_objects_are_keyboard_focusable` asserts rendered SVG objects meet the keyboard-focusable contract.

**RED command:** `pytest tests/browser/test_workspace.py::test_canvas_picking_pan_zoom_and_fit -q`

**Expected RED:** canvas interaction module does not exist.

**Implementation boundary:** Change view/navigation state only; do not mutate the structural draft, alter the global Grid origin, create Connections, resolve mechanics, or run solver operations.

**PASS command:** `pytest tests/browser/test_workspace.py::test_canvas_picking_pan_zoom_and_fit -q`

**Regression command:** `pytest tests/browser/test_workspace.py::test_svg_objects_are_keyboard_focusable -q`

**Commit:** `feat: add canvas navigation`

### Task 7 (Gate 2C): Save, check, and error boundary

**Files:**
- Create: `projects/static/projects/workspace/errors.js`; `projects/static/projects/workspace/workflow.js`
- Modify: `projects/static/projects/workspace/api.js`; `projects/static/projects/workspace/state.js`; `templates/projects/workspace.html`
- Test: `tests/browser/test_workspace.py`; `tests/endpoints/test_project_json.py`

**Consumes:** a local dirty draft; bootstrap `urls.save`; bootstrap `urls.check`; existing backend save/check contracts; a CSRF-capable API client; and backend machine error codes.

**Produces:** `normalizeApiError(response) -> {code, message, details}`; `presentWorkspaceError(error) -> {what, why, nextAction, technicalCode}`; and workflow functions that save the current draft and model-check the current server draft version.

**Test to create:** `test_save_check_error_presentation` asserts dirty -> successful save -> new server version, stale-draft advice, model-check issue focus, and no JavaScript mechanics diagnosis.

**RED command:** `pytest tests/browser/test_workspace.py::test_save_check_error_presentation -q`

**Expected RED:** workspace save/check workflow and error boundary do not exist.

**Implementation boundary:** Treat the server as authoritative for draft version; do not increment it in the frontend; clear dirty state only after successful save; call only existing save/check endpoints using the CSRF-capable client; present what happened, why, and next action while retaining the technical machine code in details; do not diagnose mechanics in JavaScript.

**PASS command:** `pytest tests/browser/test_workspace.py::test_save_check_error_presentation -q`

**Regression command:** `pytest tests/endpoints/test_project_json.py -q`

**Commit:** `feat: add workspace save and model check`

### Task 8 (Gate 3A, BCG-02): Prediction cardinality, migration, discovery
**Files:**
- Create: `learning/migrations/0004_prediction_project_draft_unique.py`
- Modify: `learning/models.py`; `learning/services.py`; `learning/views.py`; `learning/urls.py`
- Test: `tests/application/test_prediction.py`; `tests/endpoints/test_prediction_json.py`

**Consumes:** O-M5-P01; the existing `Prediction` model and create/complete services; Project authorization; `source_draft_version`; and the existing prediction response serializer.

**Produces:** database uniqueness for `(project, source_draft_version)`; concurrency-safe create/resume; `discover_current_prediction(project, actor) -> {state:"NONE",source_draft_version:number}|{state:"DRAFT"|"COMPLETED",prediction:Prediction}|raise PredictionError("PREDICTION_AMBIGUOUS")`; `GET /projects/<project_id>/predictions/current/`; and POST create behavior NONE -> DRAFT, DRAFT -> same DRAFT, COMPLETED -> same COMPLETED, multiple records -> fail closed.

**Test to create:** `test_current_prediction_singleton` asserts NONE, DRAFT resume, COMPLETED return, duplicate ambiguity, concurrent/race-safe creation, and HTTP 409 `PREDICTION_AMBIGUOUS`.

**RED command:** `pytest tests/application/test_prediction.py::test_current_prediction_singleton -q`

**Expected RED:** singleton discovery / uniqueness behavior is not implemented.

**Implementation boundary:** Lock the Project or authoritative parent in the existing service convention inside a transaction, re-query after lock, and use the uniqueness constraint with an `IntegrityError` re-query fallback; return ambiguity unless exactly one result exists. The migration preflights duplicate `project_id`/`source_draft_version` pairs and reports pair/count before adding the constraint; it must not delete, merge, choose latest/earliest, or rewrite evidence.

**PASS command:** `pytest tests/application/test_prediction.py::test_current_prediction_singleton -q`

**Regression command:** `pytest tests/endpoints/test_prediction_json.py -q`

**Commit:** `feat: add prediction discovery`

### Task 9 (Gate 3B): Prediction workspace UI
**Files:**
- Create: `projects/static/projects/workspace/prediction.js`
- Modify: `projects/static/projects/workspace/workflow.js`; `projects/static/projects/workspace/api.js`; `projects/static/projects/workspace/renderer.js`; `projects/static/projects/workspace/state.js`
- Test: `tests/browser/test_workspace.py`

**Consumes:** bootstrap `urls.prediction_current`, `urls.prediction_create`, and `urls.prediction_complete_template`; Task 8 states NONE, DRAFT, COMPLETED, and AMBIGUOUS; the existing Prediction payload contract; PhysicalMember client keys; and the PhysicalPointRef contract.

**Produces:** prediction workflow state, DRAFT-resume UI, COMPLETED read-only/restored UI, member-prediction interaction, maximum-displacement prediction, representative-load-path selection, explicit skip behavior, and `predictionForAnalyze(...) -> predictionId|null`, where only COMPLETED returns its ID, NONE returns null, skipped DRAFT returns null, and AMBIGUOUS fails closed.

**Test to create:** `test_prediction_workspace_states_and_skip` asserts NONE, DRAFT resume, COMPLETED restoration, AMBIGUOUS fail-closed behavior, member choices `TENSION`, `COMPRESSION`, `ZERO_FORCE`, `UNSURE`, point selection, representative load path, and skip -> null binding.

**RED command:** `pytest tests/browser/test_workspace.py::test_prediction_workspace_states_and_skip -q`

**Expected RED:** Prediction workspace module/UI behavior does not exist.

**Implementation boundary:** Use the frozen endpoints and existing payload only; never show history/selectors or latest-wins behavior, score/correct-wrong language, browser mechanics classification, or a result-reveal side effect; a DRAFT must never auto-bind Analyze.

**PASS command:** `pytest tests/browser/test_workspace.py::test_prediction_workspace_states_and_skip -q`

**Regression command:** `pytest tests/application/test_prediction.py tests/endpoints/test_prediction_json.py -q`

**Commit:** `feat: add prediction workspace UI`

### Task 10 (Gate 4A): Analyze and Level 1 results
**Files:**
- Create: `projects/static/projects/workspace/results.js`
- Modify: `projects/static/projects/workspace/workflow.js`; `projects/static/projects/workspace/api.js`; `projects/static/projects/workspace/renderer.js`; `projects/static/projects/workspace/state.js`
- Test: `tests/browser/test_workspace.py`; `tests/endpoints/test_project_json.py`

**Consumes:** bootstrap `urls.analyze` and `urls.result_template`; the server-authoritative draft version; `predictionForAnalyze(...)`; POST Analyze JSON `{expected_draft_version:number,prediction_id:number|null}`; and the result endpoint JSON `{analysis_run_id,model_revision_id,model_hash,solver_version,input_hash,input_schema_version,result_schema_version,status,failure_code,diagnostics,result_json}`.

**Produces:** an Analyze workflow call, successful `run_id`, Level-1 result state, maximum-displacement presentation, authoritative member tension/compression/near-zero presentation, stale/previous-draft indication, and a non-color-only Canvas result overlay.

**Test to create:** `test_analyze_level_one_and_stale_run` asserts null prediction is accepted, one COMPLETED prediction can be explicitly bound, DRAFT is not auto-bound, success stores `run_id`, stale/previous-draft results are visibly identified, and result states are not color-only.

**RED command:** `pytest tests/browser/test_workspace.py::test_analyze_level_one_and_stale_run -q`

**Expected RED:** results module / Level-1 workflow does not exist.

**Implementation boundary:** Submit only the exact Analyze fields and display backend response values; do not calculate displacement, reactions, force, stress, member-force class, or a zero-force threshold in the browser.

**PASS command:** `pytest tests/browser/test_workspace.py::test_analyze_level_one_and_stale_run -q`

**Regression command:** `pytest tests/endpoints/test_project_json.py -q`

**Commit:** `feat: add analyze result level one`

### Task 11 (Gate 4B): Compare and Explain
**Files:**
- Create: None
- Modify: `projects/static/projects/workspace/results.js`; `projects/static/projects/workspace/workflow.js`; `projects/static/projects/workspace/api.js`; `projects/static/projects/workspace/renderer.js`
- Test: `tests/browser/test_workspace.py`; `tests/endpoints/test_compare_explanation_json.py`

**Consumes:** a successful `run_id`; bootstrap run-scoped `urls.comparison_template` and `urls.explanation_template`; backend `comparison-v1`; and backend `explanation-v1`.

**Produces:** `showComparison(comparison) -> void`; `showExplanation(explanation) -> void`; and `focusPhysicalMember(clientKey) -> void`, supporting the authoritative `MATCH`, `MISMATCH`, `UNSURE`, `NOT_COMPARABLE`, `NO_PREDICTION`, and MIXED-evidence states.

**Test to create:** `test_compare_explain_states_and_canvas_link` asserts every authoritative state, MIXED segment evidence, and Canvas focus/highlight linkage.

**RED command:** `pytest tests/browser/test_workspace.py::test_compare_explain_states_and_canvas_link -q`

**Expected RED:** Compare/Explain workspace presentation does not exist.

**Implementation boundary:** Render backend wording and blocks without recomputing comparison or regenerating explanation; use no correct/wrong score language; retain MIXED as backend/segment evidence; Canvas focus is presentation only.

**PASS command:** `pytest tests/browser/test_workspace.py::test_compare_explain_states_and_canvas_link -q`

**Regression command:** `pytest tests/endpoints/test_compare_explanation_json.py -q`

**Commit:** `feat: add compare and explain UI`

### Task 12 (Gate 4C): Engineering details
**Files:**
- Create: None
- Modify: `projects/static/projects/workspace/results.js`; `projects/static/projects/workspace/renderer.js`; `templates/projects/workspace.html`
- Test: `tests/browser/test_workspace.py`; `tests/endpoints/test_project_json.py`

**Consumes:** the authoritative `analysis_data` response field `result_json`, whose `truss2d-result-v1` keys are `node_displacements` (`node_id`, `ux_mm`, `uy_mm`), `support_reactions` (`node_id`, `rx_N`, `ry_N`), `member_results` (`analysis_member_id`, `physical_member_id`, `axial_force_N`, `axial_stress_MPa`, `state`, `mass_g`, `buckling`), and `total_mass_g`.

**Produces:** `showEngineeringDetails(resultJson) -> void` presenting Level-3 nodal displacement, support reaction, member axial force, member stress, and total/member mass; any optional deformation view displays exactly “变形显示已放大，仅用于观察变形趋势。”.

**Test to create:** `test_engineering_details_authoritative_values` asserts Level 3 exposes only the authoritative displacement, reaction, axial-force, stress, and mass values, and checks the exact warning if the optional deformation view is present.

**RED command:** `pytest tests/browser/test_workspace.py::test_engineering_details_authoritative_values -q`

**Expected RED:** Level-3 engineering detail UI does not exist.

**Implementation boundary:** Render supplied authoritative values only; do not derive mechanics, stress, or mass in the browser and do not invent absent engineering values. If a required UX value is absent from the backend contract, stop and record `BACKEND_CAPABILITY_GAP` rather than computing it.

**PASS command:** `pytest tests/browser/test_workspace.py::test_engineering_details_authoritative_values -q`

**Regression command:** `pytest tests/endpoints/test_project_json.py -q`

**Commit:** `feat: add engineering details`

### Task 13 (Gate 5): Reflection UI
**Files:**
- Create: `projects/static/projects/workspace/reflection.js`
- Modify: `projects/static/projects/workspace/workflow.js`; `projects/static/projects/workspace/api.js`; `projects/static/projects/workspace/state.js`; `templates/projects/workspace.html`
- Test: `tests/browser/test_workspace.py`; `tests/endpoints/test_reflection_json.py`

**Consumes:** a successful `run_id`; bootstrap run-scoped `urls.reflection_template` and `urls.reflection_complete_template`; the existing Reflection HTTP contract; Reflection states DRAFT and COMPLETED; and M4C authorization/privacy rules.

**Produces:** `loadReflection(runId) -> Reflection`; `saveReflection(fields) -> Reflection`; `completeReflection() -> Reflection`; a Reflection DRAFT editor with save/update and completion, COMPLETED read-only presentation, optional skip behavior, and the browser acceptance tests `test_workspace_full_learning_loop` and `test_workspace_soft_gates`.

**Test to create:** `test_reflection_draft_complete_and_readonly` asserts partial DRAFT save, clear, backend-validated completion, owner-only editing, COMPLETED reader view, and skip. `test_workspace_full_learning_loop` covers build/model-check -> Prediction -> Analyze -> Result -> Compare -> Explain -> Reflection. `test_workspace_soft_gates` covers skip Prediction -> Analyze with null prediction -> understand result -> skip Reflection. Run these acceptance tests with `pytest tests/browser/test_workspace.py::test_workspace_full_learning_loop tests/browser/test_workspace.py::test_workspace_soft_gates -q` after the individual reflection PASS; if they expose missing behavior outside Reflection integration, stop and classify `PRODUCTION_DEFECT` or `PLAN_CONTRACT_CONFLICT`.

**RED command:** `pytest tests/browser/test_workspace.py::test_reflection_draft_complete_and_readonly -q`

**Expected RED:** Reflection workspace module/UI does not exist.

**Implementation boundary:** Use only the existing singleton routes; Reflection remains a Soft Gate, permits partial DRAFT save and clear, requires backend validation to complete, and makes COMPLETED immutable. Never disclose DRAFT content to Manager/Developer, reveal results as a side effect, or add a scoring/mechanics feature.

**PASS command:** `pytest tests/browser/test_workspace.py::test_reflection_draft_complete_and_readonly -q`

**Regression command:** `pytest tests/endpoints/test_reflection_json.py -q`

**Commit:** `feat: add reflection workspace UI`

### Task 14 (Final Gate A): Reconciliation
**Files:** Modify `docs/superpowers/plans/2026-09-16-m5-student-learning-workspace.md` only if implementation records require factual status; no production/test files.
- [ ] Compare each UX acceptance scenario to implementation/tests and classify any mismatch as `SPEC_IMPLEMENTATION_CONFLICT`, `TEST_CONTRACT_CONFLICT`, `PRODUCTION_DEFECT`, or `SPEC_GAP`; run `git diff --check`.
- [ ] If a mismatch exists, STOP without edits; otherwise record reconciliation evidence and commit `docs: reconcile M5 workspace`.

### Task 15 (Final Gate B): Fresh verification and acceptance evidence
**Files:** no changes.
- [ ] Run in order: `python3 manage.py check`; `python3 manage.py makemigrations --check --dry-run`; `pytest tests/endpoints/test_workspace.py -q`; `pytest tests/application/test_prediction.py tests/endpoints/test_prediction_json.py tests/endpoints/test_project_json.py tests/endpoints/test_compare_explanation_json.py tests/endpoints/test_reflection_json.py -q`; `pytest tests/browser -q`; `pytest -q -m 'not browser'`; `git diff --check`; `git status`. Any failure is STOP/classified.
- [ ] Make no production, test, spec, or merge change; report commands/output as final evidence.

## Coverage review

Task 1 covers Workspace delivery; 2 SVG rendering; 3 parser/state; 4 SNAP/Grid/geometry; 5 editor mutation; 6 navigation/picking; 7 save/check/errors; 8 Prediction backend; 9 Prediction UI; 10 Analyze/Level 1; 11 Compare/Explain; 12 engineering details; 13 Reflection; 14 reconciliation; 15 fresh verification. Scenario A is Tasks 1–13 plus `test_workspace_full_learning_loop`; B is Tasks 7,9,10,13 plus `test_workspace_soft_gates`; C is Tasks 3–4 plus `test_cad_parser_and_state_transitions`; D is Tasks 4–5 plus `test_editor_crossing_members_do_not_create_connection`. No task changes mechanics authority or introduces a frontend framework.
