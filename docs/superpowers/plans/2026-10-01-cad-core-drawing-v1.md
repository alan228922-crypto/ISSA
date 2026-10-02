# CAD Core Drawing V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execution method is selected by the Product Owner after review; this document authorizes planning only.

**Goal:** Let a student draw a member with two canvas clicks, use understandable precision aids, and navigate without changing structural topology accidentally.

**Architecture:** Approach B: a small Interaction Controller owns transient drawing/gesture/input state, a coordinate adapter supplies one client/SVG/world pipeline, and existing pure geometry/grid/input helpers are reused. Only the v2 editor reducer authors committed Nodes, members, and explicit incidences; existing history/save remain authoritative. Candidate discovery and renderer stay read-only.

**Tech Stack:** Browser ES modules and SVG, Django workspace bootstrap, pytest and Playwright Chromium. Use existing dependencies and test fixtures; introduce no build system or spatial database.

**Spec:** `docs/superpowers/specs/2026-10-01-cad-core-drawing-v1-design.md`, approved at `e710781`, based on `main@9c45ace`.

## Global Constraints

- Canonical units remain `mm / N / MPa / g`; Solver, mechanics, Draft schema, DB and historical revisions do not change.
- `GRID_SPACING = 1 mm` is the sole logical Grid and Grid Snap authority; visual 1/10/100 mm LOD never changes snap precision.
- Node identity plus explicit endpoint/incidence is topology authority. No nearest-coordinate identity lookup, hover-created topology, or renderer-created topology.
- Empty-space first Member point is transient only. Completion is one atomic action/history entry. Tool returns to `WAITING_FOR_START`; no automatic chaining.
- At an unjoined crossing of 2+ pre-existing members, reject a provisional Member start/end. Exact copy: “此处是尚未连接的构件交点；请先用「节点」工具建立连接”. Node Tool explicitly creates the Joint and all passing incidences.
- ORTHO preserves the exact locked coordinate; only the moving axis can Grid-snap. Off-axis NODE/INT candidates cannot defeat ORTHO.
- NODE > INTERSECTION > GRID, initially 10 CSS px object-snap radius. Markers are screen-size stable and pointer-inert.
- Explicit numeric input preserves decimals and bypasses pointer ORTHO/Grid/OSNAP adjustment; it still obeys identity and topology validation.
- Priority: middle pan/wheel zoom → focused numeric input → Node/Member drawing → existing selection. View operations never request a Draft action.
- Cursor-centered zoom drift ≤1 CSS px; retain wheel step 1.1 and existing scale limits 0.05–20. Toolbar center is measured, not `(500,300)`.
- Existing selection, grips, delete, history and v1 compatibility are protected but not redesigned. No merge, push, deploy, real Project conversion, or dirty-root cleanup.
- Completion wording: **CAD CORE DRAWING V1 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING**. Browser automation does not replace Product Owner visual acceptance.

## Review Focus

1. Draft replacement by save/undo while a start is pending: cancel the stale start, never reinterpret its coordinates as another Node (Task 2).
2. Same-location legacy Node identities, and a precise point near an existing Node: preserve explicit selected identity or block ambiguity; never silently merge (Tasks 1–2).
3. Pointer cancellation/lost capture/window blur while panning or holding Shift: release gesture/temporary override without committing or leaving stuck navigation (Tasks 3–4).
4. Blank, malformed, non-finite numeric fields or repeated Enter: do not turn blank into zero, overwrite focused input on pointermove, or duplicate a completed member (Task 3).
5. Existing numeric topology-effect confirmation: preserve the preview/second-Enter confirmation before attaching to a single existing member or passing existing Nodes, and clear it when input/Draft changes (Tasks 2–3).

## Execution workspace and file map

At execution, read the approved Spec and this Plan, verify the design branch contains both commits and is clean, then use `superpowers:using-git-worktrees` to create `feat/cad-core-drawing-v1` in `.worktrees/cad-core-drawing-v1-implementation` **from the design branch HEAD containing this Plan**, not bare main. Verify `.worktrees` is ignored. Record main/root statuses and hashes before and after; do not operate on the four historical dirty root files. Do not merge/cherry-pick the old CAD branch. Run a clean non-browser baseline before implementation and stop to diagnose any baseline failure.

All production module paths below are under `projects/static/projects/workspace/`:

| File | Disposition and boundary |
| --- | --- |
| `coordinate-space.js` | **NEW**: validated CTM snapshot and pure affine conversion, pixel scale and visible-viewport helpers; no Draft/DOM writes. |
| `interaction-controller.js` | **NEW**: transient tool/gesture/pending/input state and requested effects; no persistence, history or DOM ownership. |
| `snap-candidates.js` | **NEW**: Draft-keyed lightweight spatial discovery for nearby Nodes/segments/intersections; no topology writes. |
| `geometry.js` | **ADAPT** existing `resolvePointerPoint`; keep one resolver, enforce ORTHO and return typed identity-bearing results. |
| `grid.js` | **REUSE** spacing, `gridNearest`, `visibleGridLevels`; no new Grid resolver. |
| `cad-input.js` | **REUSE** `parseCadInput`; **ADAPT** with mini-form parsing that feeds the same precise-point contract. |
| `joint-candidates.js` | **REUSE** `segmentParameter`, `candidateMembersAtNode`, `nodesOnMember` for strict editor validation; **ADAPT** with endpoint-effect discovery shared by UI/reducer. |
| `editor-v2.js` | **ADAPT** with one atomic two-endpoint action and independent crossing/identity guards. |
| `editor.js` | **REUSE** v1/v2 dispatch and `EditorActionError`; compatibility changes only if action/error forwarding requires them. |
| `state.js` | **REUSE** `applyWorkspaceEditorAction`, undo/redo and save checkpoint; transient presentation remains outside Draft/history. |
| `canvas-interaction.js` | **ADAPT** event routing/view updates to adapter/controller; retain existing selection/grip/chooser behavior. |
| `modeling-interaction.js`, `cad-state.js` | **ADAPT** existing bindings/transition helpers to controller, removing duplicate Member start/resolution ownership; retain Support/Load and legacy behavior. |
| `renderer.js` | **ADAPT** typed feedback, screen-sized presentation and view-only update; read-only. |
| `structural-symbols.js`, `workflow.js` | **REUSE**, no planned production changes; symbols and save/check/analyze contracts protected by tests. |
| `student-shell.js` | **ADAPT** only empty-Canvas Member entry/hint; retain stage transitions. |
| `templates/projects/workspace.html` | **ADAPT** bootstrap binding, dynamic input fields, four status labels, measured Fit/toolbar anchors and blank-start guidance. |
| `workspace.css`, `ux-v2.css` | **ADAPT** only mini-input placement/focus/readability and minimal status layout. |
| `tests/browser/test_cad_core_drawing.py` | **NEW** focused ES-module contracts plus real-pointer Package 1 tests using `workspace_page`. |
| `tests/browser/test_cad_core_journey.py` | **NEW** public-control student journey and screenshot evidence. |
| `tests/browser/test_workspace.py`, `test_node_joint_workspace.py`, `test_node_joint_journey.py`, `test_ux_v2_student_journey.py` | **ADAPT** only assertions/interfaces/copy intentionally superseded by the Spec; retain independent compatibility coverage. |

Existing test infrastructure: `tests/browser/conftest.py::workspace_page` launches Chromium with Django-authenticated session; `context` is imported from `tests.application.test_physical_draft`; create new v2 Projects with `projects.models.Project` or use `v2_project` from `tests.application.test_node_joint_draft`. The browser conftest overrides the default `not browser` mark when browser paths are explicitly requested. No separate JS runner is configured: use `page.evaluate` imports for pure ES-module assertions and actual `page.mouse`/keyboard/locators for behavior. Browser tests must fail, not skip, if required Chromium is unavailable during acceptance. Only test DB fixtures may be changed.

## Shared interface decisions

Use JSDoc discriminated unions in existing plain JS, not a TypeScript migration:

- `Point = {x:number, y:number}`; `Affine = {a,b,c,d,e,f:number}`; `CoordinateSpace = {svgToClient:Affine, worldToSvg:Affine}`. The first matrix includes responsive SVG/viewBox offset/letterboxing; the second is the current view transform.
- In `coordinate-space.js`: `readCoordinateSpace(svg, viewTransform): CoordinateSpace`; `clientPointToSvgLocal(point, space): Point`; `svgLocalToWorld(point, space): Point`; `worldToSvgLocal(point, space): Point`; `svgLocalToClient(point, space): Point`; `worldToClient(point, space): Point`; `clientDeltaToSvgLocal(from, to, space): Point`; `visibleSvgViewport(svg, space): {left,top,width,height}`; `cssPixelsPerWorldUnit(space): number`. Pure converters take the captured matrices. Invalid/missing/singular matrices or non-finite points throw `CoordinateSpaceError` with `code: 'INVALID_COORDINATE_SPACE'`; no raw-client fallback. Bindings catch it, cancel affected transient gesture and show feedback.
  `visibleSvgViewport` intersects the SVG client rectangle with its `.workspace-center` and browser viewport, then inverse-transforms that visible rectangle; center/Fit use its SVG-local bounds including left/top. All coordinate helpers are centralized here even when selection continues to compare client-space points.
- `SnapCandidate` is `{kind:'NODE', nodeClientKey, worldPoint}` or `{kind:'INTERSECTION', memberClientKeys:[string,string], worldPoint}`. Member keys are sorted, nonempty and distinct.
- `SnapResolution` is `{kind:'GRID'|'FREE'|'PRECISE', worldPoint, axis:null|'HORIZONTAL'|'VERTICAL'}` or the NODE/INTERSECTION candidate plus `axis`. Only NODE has `nodeClientKey`; only INTERSECTION has `memberClientKeys`. `PRECISE` does not acquire a nearby Node. Legacy DOM `data-snap-type='INT'` is a presentation mapping only.
- `resolvePointerPoint({worldPointer,clientPointer,candidates,coordinates,origin,ortho,gridEnabled,explicitNumeric}): SnapResolution` remains the single resolver in `geometry.js`. `origin` may be null before a first point. Object distance is CSS pixels through `worldToClient`; tied category/distance candidates at different positions sort by stable source keys. Multiple eligible Node identities at the same snapped position throw `SnapResolutionError` with `code: 'AMBIGUOUS_NODE_IDENTITY'` instead of silently choosing; bindings explain the ambiguity and retain the existing selection chooser without adding a new one. Under ORTHO a candidate's locked coordinate must equal the exact origin coordinate; otherwise reject it, not project the Node onto a different coordinate. Explicit numeric returns PRECISE unchanged.
- `PendingEndpoint = {kind:'EXISTING_NODE',nodeClientKey,worldPoint}` or `{kind:'PROVISIONAL_POINT',worldPoint}`. Resolve by NODE identity or precise/provisional point; do not infer identity later. `inspectEndpointCandidates(draft, endpoint)` in `joint-candidates.js` returns `{passingMemberClientKeys, collocatedNodeClientKeys}` for validation/feedback only, using existing strict geometry; equal coordinates may identify a conflict, never select a key.
- `createInteractionController({resolvePointer,inspectEndpoint}): {getState(),dispatch(event,context)}` in `interaction-controller.js`. Context contains current immutable `draft`, `readOnly`, `focusedInput`, and drawing settings. Events are `SELECT_TOOL`, `POINTER_RESOLVE`, `CONFIRM_POINT`, `PRECISE_POINT`, `INPUT_CHANGE`, `INPUT_FOCUS`, `KEY`, `CANCEL`, `DRAFT_CHANGED`, `VIEW_CHANGED`, `PAN_START`, `PAN_END`, and `EDITOR_RESULT`. `POINTER_RESOLVE` carries `{worldPointer,clientPointer,candidates,coordinates}` and calls the supplied resolver; `CONFIRM_POINT` carries that event's fresh SnapResolution, not a coordinate re-lookup; `PRECISE_POINT` carries an unadjusted worldPoint. Output is `{state,consumed,effects}`. Effects are `{type:'PRESENT',cad}`, `{type:'REQUEST_MEMBER_COMMIT',start:PendingEndpoint,end:PendingEndpoint}`, `{type:'REQUEST_NODE_CONFIRM',resolution:SnapResolution}`, `{type:'REQUEST_VIEW',event:ViewEvent}`, or `{type:'ERROR',code,message}`. Host bindings allocate IDs/profile and dispatch the one editor/view action; `EDITOR_RESULT` carries `{ok:boolean,error?}`. Controller owns no Draft/history/DOM mutation. Existing selection runs only when `consumed === false`.
- Controller state exposes `activeTool`, `phase:'WAITING_FOR_START'|'WAITING_FOR_END'`, `pendingMemberStart`, `basisDraft` (object identity), latest `snapResolution`, `dynamicInput`, `preview`, `gesture`, `temporaryOrtho`. Settings stay in existing `state.cad`; preview mirrors controller output for renderer only. Save/undo/redo or any changed Draft identity cancels pending state; pan/zoom do not. Remove the old independent `memberStart` variable as authority.
- `EditorEndpoint = {kind:'EXISTING_NODE',nodeClientKey}` or `{kind:'PROVISIONAL_POINT',newNodeClientKey,worldPoint}`. Atomic action: `{type:'CREATE_MEMBER_BETWEEN_POINTS',start:EditorEndpoint,end:EditorEndpoint,member:{client_key,material_id,section_id,label,is_active}}`. Reducer resolves explicit refs, constructs missing Nodes plus member/incidences on a proposed immutable Draft, validates, and returns the complete result or throws; it cannot return a partial result. IDs are allocated once by the host at commit request, from existing key allocation, never at first click. Existing history records the single action once.
- `reduceView` keeps its affine math but view events now use `{type:'PAN',deltaSvgLocal}`, `{type:'ZOOM',factor,anchorSvgLocal}`, and `{type:'FIT_VIEW',worldBounds,viewport:{left,top,width,height}}`, all SVG-local. Update every caller/helper test to these names; no alternate raw-client view path.
- In `renderer.js`, retain `renderWorkspace` for Draft/selection changes; add `renderWorkspaceView(svg,draft,uiState,coordinates): void` for transform/LOD/screen-size updates, with Draft-keyed topology-presentation cache. Keep `renderCadPresentation(svg,cad,uiState,coordinates): void` for transient feedback. Renderer cannot dispatch any action.

## Task 1: Interaction foundation and coordinate authority

**Files:** Create `coordinate-space.js`, `interaction-controller.js`; adapt `geometry.js`, drawing routing in `canvas-interaction.js`/`modeling-interaction.js`, transition use in `cad-state.js`, and bootstrap/view callers in `templates/projects/workspace.html`; create `tests/browser/test_cad_core_drawing.py`; update affected pure-helper assertions in `tests/browser/test_workspace.py`.

**Interfaces:** Produces CoordinateSpace conversions, typed SnapResolution, controller event/effect API and SVG-local ViewEvent above. Uses existing Grid rounding and editor/history without changing topology. At this stage use current cached candidates through an adapter; Task 4 supplies the spatial query implementation.

- [ ] **1. Write RED module contract tests.** Add `test_core_coordinate_roundtrip_and_invalid_matrix`, `test_core_typed_snap_identity_priority_and_ortho`, and `test_core_controller_routes_without_draft_effects`. Assertions include a translated/scaled SVG matrix, inverse roundtrip, singular/missing CTM error, 10 CSS px radius, NODE over closer INT, NODE key unchanged, INTERSECTION source keys unchanged, and off-axis NODE/INT ignored. Example numeric anchors:

  ```python
  assert result['local'] == {'x': 20, 'y': 30}  # client (140,110), SVG→client scale 2 + (100,50)
  assert result['invalid_code'] == 'INVALID_COORDINATE_SPACE'
  assert result['node']['nodeClientKey'] == 'n3'
  assert result['coincident_node_error'] == 'AMBIGUOUS_NODE_IDENTITY'
  assert result['off_axis']['worldPoint'] == {'x': 13, 'y': 7.6}
  assert result['view_only_editor_requests'] == 0
  ```

- [ ] **2. Write RED real-pointer routing tests.** Add `test_core_offset_responsive_pointer_uses_one_adapter` (two viewport widths, canvas positioned away from page origin) and `test_core_direct_node_click_cannot_bypass_ortho`. Move/click using measured world→client CTM, assert visible preview/readout and selected candidate agree; test singular CTM cancellation through a controlled matrix stub without dispatching a commit. Direct click on an off-axis rendered Node must use constrained resolution, not the old target shortcut.
- [ ] **3. Run RED.** `pytest tests/browser/test_cad_core_drawing.py -q -k 'coordinate or typed_snap or routes or offset_responsive_pointer or bypass_ortho'`; require assertion/import failures for absent contracts, not fixture/server errors.
- [ ] **4. Implement the shared interfaces in this task's files.** Capture SVG CTM once per event, validate/invert in adapter, route Node/Member pointer resolution through controller, and update all view callers to SVG-local fields. Keep existing selection/grip handlers in place, feeding their world conversion through the adapter. Preserve explicit numeric bypass and Grid resolver; adapt current candidate records once at discovery. Do not add any new Member editor action yet.
- [ ] **5. Run targeted GREEN and legacy-path audit.** Re-run Step 3; run `pytest tests/browser/test_workspace.py -q -k 'snap_resolver or grid_midpoint or one_mm or canvas_picking or canvas_binds or middle_pan_does_not_consume'`. Audit `rg -n 'clientX|clientY|offsetX|offsetY|getScreenCTM|viewBox|anchorScreen|deltaScreen' projects/static/projects/workspace templates/projects/workspace.html`: raw client usage may capture pointer/selection/overlay client points, but all view/world conversion must delegate to adapter. `worldPointFromEvent`, marquee client→SVG conversion, grip conversion, toolbar/Fit, old `localScreenPoint`, and renderer pixel-scale calculation cannot bypass it. Keep one resolver, with migrated helper tests using an explicit CoordinateSpace.
- [ ] **6. Review and commit.** Check event consumption cannot invoke selection after a drawing click, Node/INT metadata survives preview→request, and view effects never call `applyWorkspaceEditorAction`. Run `git diff --check`; stage only this task's changed files and commit `refactor: unify drawing coordinates and interaction state`.

## Task 2: Atomic Member drawing from provisional endpoints

**Files:** Adapt `editor-v2.js`, `joint-candidates.js`, `interaction-controller.js`, `modeling-interaction.js`, `student-shell.js`, `templates/projects/workspace.html`; extend `tests/browser/test_cad_core_drawing.py`; adapt the superseded numeric identity test in `tests/browser/test_node_joint_workspace.py`.

**Interfaces:** Consumes PendingEndpoint/controller results from Task 1. Produces `CREATE_MEMBER_BETWEEN_POINTS` and `inspectEndpointCandidates` as specified. Host feeds one action through existing `applyWorkspaceEditorAction`; v1 dispatch and ordinary Support/Load creation remain unchanged.

- [ ] **1. Write RED reducer/history tests.** Add parametrized `test_core_atomic_member_endpoint_combinations` for blank→blank, NODE→blank, blank→NODE and NODE→NODE; assert exact endpoint keys, new Node counts 2/1/1/0, one added member, and history `past` increases by one. Add `test_core_atomic_member_incidence_and_crossing_guard`: pass an existing normal Node→explicit incidence; cross a member without Node→no incidence; create endpoint in one existing member interior→its incidence; 2+/3-member unjoined crossing endpoints→error with original Draft unchanged. Include same identity/zero length, invalid/stale reference and legacy co-located identity rejection, rollback with no partial Nodes, Undo/Redo exact keys.

  ```python
  assert result['created_node_counts'] == [2, 1, 1, 0]
  assert result['history_delta'] == 1
  assert result['through_mid'] == [{'member_client_key': 'member-1', 'node_client_key': 'mid'}]
  assert result['crossing_error'] == 'EDITOR_UNJOINED_CROSSING_ENDPOINT'
  assert result['after_failure'] == result['before']
  ```
- [ ] **2. Write RED real-pointer tests.** Add `test_core_blank_start_pending_cancel_and_atomic_commit`, `test_core_node_endpoint_identity_and_no_chaining`, and `test_core_crossing_requires_node_tool`. Choose Member on an empty v2 Project, select material/section, click blank start: no Node/member, no dirty flag/history entry; Esc: unchanged Draft. Repeat two clicks: 2 Nodes + 1 Member. After completion, one further click is only a fresh pending start. Test start/end at existing NODE markers and crossing guard for pointer/Grid/numeric paths; Node Tool at the same crossing creates all incidences. Include `test_core_pending_start_invalidated_by_save_undo_and_tool_change` with Draft replacement, no coordinate reinterpretation, and existing public undo/save controls.
- [ ] **3. Run RED.** `pytest tests/browser/test_cad_core_drawing.py -q -k 'atomic_member or blank_start or endpoint_identity or crossing_requires or pending_start'`; failures must demonstrate current missing atomic action/blank start/guard.
- [ ] **4. Implement atomic action and transient Member lifecycle.** Build proposed Draft without reusing `placeNode` coordinate-fallback for provisional endpoints: reuse explicit NODE refs by key, reject provisional coordinates colliding with an existing Node (`EDITOR_EXPLICIT_NODE_REQUIRED`), reject unjoined crossing (`EDITOR_UNJOINED_CROSSING_ENDPOINT`), and call existing strict authoring/validation for required incidences. Preserve existing member material/section requirement. Controller rejects guarded first/second points early and reducer checks again. Numeric/direct routes use the same action. On `EDITOR_RESULT` success clear pending state and return to WAITING_FOR_START; failures retain valid input/start. Hide empty-state overlay when Member is chosen and adjust only empty-state guidance to allow two-click Member creation.
- [ ] **5. Run targeted GREEN and Node-as-Joint compatibility.** Re-run Step 3; run `pytest tests/browser/test_node_joint_workspace.py tests/browser/test_node_joint_journey.py -q` and `pytest tests/browser/test_workspace.py -q -k 'member_creation_with_new_endpoint or decimal_node or numeric_node_reentry or undo_redo_create or blank_project_creates'`. Replace the v2 test `test_numeric_near_existing_endpoint_reuses_identity_without_false_new_joint_preview` with `test_numeric_member_does_not_relookup_nearby_node`: precise input must retain its value, never silently reference the nearby key; if strict topology validation rejects that fixture, assert rejection and unchanged Draft. Add the matching NODE-snapped identity case. Do not weaken save/incidence assertions. Exact duplicate numeric Node reentry must remain non-duplicating; v2 new drawing paths request explicit identity rather than infer it.
- [ ] **6. Review and commit.** Inspect the full action for one reducer invocation/history entry and all-or-nothing validation; inspect both provisional endpoints against pre-action existing crossings, not a half-built Draft. Verify only explicit Node Tool confirms a bare crossing, no hidden Connection or coordinate re-lookup in new Member commit. Run `git diff --check`; commit `feat: create members atomically from provisional endpoints` with this task's files only.

## Task 3: Student drawing feedback, constraints and dynamic numeric input

**Files:** Adapt `interaction-controller.js`, `modeling-interaction.js`, `cad-input.js`, `cad-state.js`, `renderer.js` typed presentation, `templates/projects/workspace.html`, `workspace.css`, `ux-v2.css`; extend `tests/browser/test_cad_core_drawing.py` and relevant precision/keyboard tests in `tests/browser/test_workspace.py`. Reuse `grid.js` unchanged unless correcting a demonstrated regression is necessary.

**Interfaces:** Consumes Task 1 resolution and Task 2 atomic requests. Add `parseDynamicPoint({mode,values,origin}): {ok:true,point:Point}|{ok:false,code:'EMPTY'|'INCOMPLETE'|'MALFORMED'}` in `cad-input.js`, with modes `XY`, `POLAR`, `RELATIVE`; values are raw strings `{x,y}`, `{length,angle}`, or `{dx,dy}` respectively, so blank is checked before Number conversion. POLAR/RELATIVE require a finite origin, and mini-form length must be >0; reuse existing parsing/math without changing advanced syntax. Add distinct floating selectors `data-cad-dynamic-length`, `data-cad-dynamic-angle`, `data-cad-dynamic-dx`, `data-cad-dynamic-dy`, retaining advanced-area selectors so existing consumers remain unambiguous. Input state is controller-owned; host reads/writes DOM values but never overwrites a focused field on pointermove.

- [ ] **1. Write RED precision/control tests.** Add `test_core_grid_ortho_decimal_contract` for `(12.6,8.4)→(13,8)`, horizontal `(12.4,7.6)→(13,7.6)`, vertical locked X, Snap OFF decimals, numeric precise bypass, and near/mid/far LOD with unchanged logical result. Add `test_core_shift_and_fkeys_respect_input_focus_and_blur`: Shift XOR persistent ORTHO, keyup/blur/cancel reset, F7/F8/F9/F3 toggle only canvas focus and never consume editable fields.
- [ ] **2. Write RED real-input tests.** Add `test_core_dynamic_xy_polar_relative_and_cancel` using floating fields/keyboard: decimal X/Y pending start, length 100.5/angle 30.25 completion within 1e-9 mm of expected trig coordinates, relative ΔX=10.25/ΔY=-3.75, empty/malformed/non-finite field rejection, Esc unchanged committed Draft, and no duplicate member on repeated Enter. Add `test_core_dynamic_numeric_topology_preview_requires_confirmation` to preserve current second-Enter topology-effect preview; changed input/Draft clears its signature. Assert cursor decimal display and visible units without typing units, and pointer movement cannot overwrite a focused input.

  ```python
  assert result['horizontal']['worldPoint'] == {'x': 13, 'y': 7.6}
  assert result['precise']['worldPoint'] == {'x': 12.4, 'y': 7.6}
  assert result['relative_endpoint'] == pytest.approx({'x': 22.65, 'y': 3.85}, abs=1e-9)
  assert result['focused_shift_changes'] == result['focused_fkey_changes'] == 0
  assert result['draft_after_escape'] == result['committed_draft']
  ```
- [ ] **3. Run RED.** `pytest tests/browser/test_cad_core_drawing.py -q -k 'grid_ortho or shift_and_fkeys or dynamic_'`.
- [ ] **4. Implement progressive mini-input and status bindings.** Show X/Y before first point and Length/Angle after start. Tab cycles LENGTH→ANGLE→DX→DY→LENGTH (Shift+Tab reverse), showing only the relevant pair; X/Y cycles within its pair. Esc exits the operation and clears transient state; Enter validates the complete current pair. Retain `parseCadInput` advanced syntax and existing numeric-effect second confirmation. Mirror new inputs to existing precise-point path; never snap numeric values. Use approved four Chinese status labels, current resolved candidate and decimal readout; keep other existing controls compatible. Route direct Node clicks through the same ORTHO filter. Approximate displayed values without rounding stored coordinates; persistent control state and effective temporary ORTHO are separately visible.
- [ ] **5. Run targeted GREEN and precision compatibility.** Re-run Step 3; run `pytest tests/browser/test_workspace.py -q -k 'grid_display or object_snap_toggle or shift_temporarily or pointer_dynamic or blank_dynamic or member_numeric or dynamic_tab or numeric_modeling or parser_and_state or keyboard_tab or decimal_node'` and `pytest tests/browser/test_node_joint_workspace.py tests/browser/test_node_joint_journey.py -q -k 'numeric or crossing'`. Inspect accessible labels, clickable fallback for every F-key, focus ownership, and unchanged Grid authority. Screenshot the progressive states for later owner review; tests still require actual keyboard/mouse entry.
- [ ] **6. Review and commit.** Check parser returns and controller events use the same Point/PRECISE contract as Tasks 1–2, no duplicate command transition state, no Package 3 repeat-command changes, and read-only view lacks editing inputs. Run `git diff --check`; commit `feat: unify student precision input and snap feedback` with this task's files only.

## Task 4: View navigation, spatial discovery and rendering cost

**Files:** Create `snap-candidates.js`; adapt `canvas-interaction.js`, `modeling-interaction.js`, `interaction-controller.js`, `renderer.js` and measured viewport bindings in `templates/projects/workspace.html`; extend `tests/browser/test_cad_core_drawing.py`. Reuse coordinate adapter, strict joint helpers and structural-symbol renderers.

**Interfaces:** `getSnapCandidateIndex(draft): SnapCandidateIndex` uses WeakMap by immutable Draft identity; `querySnapCandidates(index,{clientPoint,coordinates,radiusPx=10,diagnostics=null}): SnapCandidate[]` returns nearby candidates. Optional test-only diagnostics accumulates `{nodesVisited,segmentsVisited,pairsTested}` and cannot alter results. Build compact static bounding-box trees for Nodes and complete segments (balanced median split), query the inverse-transformed client-radius square, then test true screen distance. Intersections are computed only among nearby queried segments, deduplicated by sorted pair; no initial global pairwise intersection table. Incomplete members lack segments and are excluded. No view-dependent index rebuild; Draft replacement invalidates by new identity. Dense local output may be expensive, but sparse query must not scan all geometry. Task 1's resolver remains the only priority/constraint decision.

- [ ] **1. Write RED real-navigation tests.** Add `test_core_cursor_centered_zoom_at_offset_responsive_and_limits` with client target roundtrip drift ≤1 px, near/mid/far scales, view 0.05/20 boundaries and measured toolbar center. Add `test_core_middle_pan_preserves_pending_member_and_updates_preview`: actual middle down/move/up changes only transform, preserves start, immediately aligns preview with post-pan pointer, and next left click completes once. Add `test_core_pointercancel_blur_release_pan_without_commit` for lost capture/cancel/blur and next ordinary click.
- [ ] **2. Write RED discovery/render tests.** Add `test_core_snap_index_lifecycle_and_local_query`: identical Draft returns same index, new Draft after move/create/undo/save returns fresh index; a sparse fixture of 100 clusters spaced 1000 mm apart, each with 10 Nodes/20 short complete segments, queries one cluster with fewer than 100 Node and 200 segment leaf visits and no global pairwise construction; malformed/incomplete segments are skipped and intersection source IDs stable. Add `test_core_view_grid_marker_and_pointer_dom_cost` parametrized for 500×500, 1000×1000, 2000×1000 mm and offset/responsive canvases: 3 pattern definitions, zero per-mm line growth, same physical-object DOM identity through pointermove and pan, NODE/INT marker bounding dimensions stable within 1 px over zoom, and LOD does not change snap. Include Grid coverage after pan beyond former ±10000 mm fill rectangle.

  ```python
  assert result['zoom_drift_css_px'] <= 1
  assert result['marker_size_drift_css_px'] <= 1
  assert result['grid_patterns'] == 3
  assert result['draft_after_pan'] == result['draft_before_pan']
  assert result['member_dom_replaced_by_pointermove'] is False
  assert result['same_draft_reuses_index'] and result['changed_draft_replaces_index']
  assert result['local_query_stats']['nodesVisited'] < 100
  assert result['local_query_stats']['segmentsVisited'] < 200
  ```
- [ ] **3. Run RED.** `pytest tests/browser/test_cad_core_drawing.py -q -k 'zoom_at or middle_pan or pointercancel or snap_index or dom_cost'`.
- [ ] **4. Implement view-only rendering and indexed query.** Apply pan/zoom first, then capture the updated CoordinateSpace and re-resolve preview in the same event/render cycle; suppress middle-up click commitment. Preserve existing Space-pan and double-middle Fit as compatibility behavior. Implement the small discovery index above and remove global `drawingCandidates` pairwise cache. Add `renderWorkspaceView` updating world transform, viewport-covering pattern rect, Grid LOD, and screen-sized symbol/marker presentation; cache topology warning metadata per Draft so pan never repeats Node×Member scans. Pure translation updates transform only; zoom may refresh symbol presentation in O(objects), but no topology inference. Pointermove uses `renderCadPresentation` only. Avoid per-frame full Canvas replacement; do not change structural symbol engineering semantics.
- [ ] **5. Run targeted GREEN and navigation/performance review.** Re-run Step 3; run `pytest tests/browser/test_workspace.py -q -k 'middle_navigation or middle_pan or large_view or grid_pattern or canvas_picking or visible_cad_controls or canvas_keyboard or structural_sketch'`. Repeat Task 1's legacy coordinate-path audit and review each remaining CTM/viewBox conversion. Measure pointer/pan/zoom frame timings after warmup for all three view ranges and save p50/p95 with fixture size; deterministic gates are bounded Grid DOM, reused index, local discovery, stable object DOM on pointermove/pan, and no Draft action from navigation. Timing evidence supports manual smoothness review, rather than a hardware-dependent flaky threshold. Ensure view updates preserve results/legacy warnings/selection styles.
- [ ] **6. Review and commit.** Check cached metadata invalidates on actual Draft replacement, query index cannot author topology, no old event path bypasses adapter, and pan cleanup cannot lose the pending start. Run `git diff --check`; commit `perf: stabilize canvas navigation and local snap discovery` with this task's files only.

## Task 5: Public-control student journey, full regression and visual handoff

**Files:** Create `tests/browser/test_cad_core_journey.py`; complete focused assertions in `tests/browser/test_cad_core_drawing.py`; adapt only approved copy/interfaces in existing browser tests. No new product capability belongs to this integration task. If a regression requires a production fix, add a failing focused test in the owning Task 1–4 seam, fix minimally, and re-run that task's targeted checks before integration.

**Interfaces:** Uses visible controls, saved `physical-draft-v2` payload and unchanged workflow/endpoints. Screenshot/read-only evidence may inspect CTMs/DOM/bootstrap; user actions must use actual pointer, keyboard and public controls, not reducer imports or JS-dispatched synthetic events.

- [ ] **1. Write RED combined journey.** Add `test_core_student_blank_member_to_analysis_journey`: open new v2 Project, choose Member/profile, blank start/blank end atomic creation, a fresh start with Node Snap, a geometrical crossing remaining disconnected, INT marker hover, explicit Node Tool crossing Joint, ORTHO, decimal floating Length/Angle, cursor-centered wheel, transparent middle pan, Save/reload exact endpoint/incidence identities, Support/Load placement/editing, Model Check, and Analyze. Use an independently complete supported truss fixture for successful Analyze; verify an incomplete Draft still blocks without new revision/run. Assert tool remains active without chaining. Do not use browser-wait sleeps; wait for observable DOM/network responses.

  ```python
  assert saved['schema_version'] == 'physical-draft-v2'
  assert saved['physical_members'][0]['start_node_client_key'] == created_start_key
  assert saved['physical_members'][0]['end_node_client_key'] == created_end_key
  assert 'connections' not in saved
  assert complete_run.status == 'SUCCESS'
  assert (blocked_project.model_revisions.count(), blocked_project.analysis_runs.count()) == before_counts
  ```
- [ ] **2. Write compatibility/evidence checks.** Add `test_core_selection_support_load_history_compatibility` covering existing left/right marquee, two-click marquee, Shift selection, grip valid/rejected move, Delete/Backspace editable-focus safety, independent deletion and undo/redo. Retain v1 historic student journey and read-only tests. Add screenshots for near/mid/far, NODE versus INT, blank Member preview, precise-input state, offset/responsive viewport and pan preview; place evidence under `.superpowers/sdd/2026-10-01-cad-core-drawing-v1/screenshots/`, with an inspection note listing dimensions, tool/settings, actual observations and any visual limitation. Avoid screenshots containing real user data.
- [ ] **3. Run RED and complete journey integration.** `pytest tests/browser/test_cad_core_journey.py -q`; any failure must be meaningful. Wire only missing integration between the approved interfaces; preserve frozen scope. Pure-interface tests can be updated to explicit new types, but do not remove behavioral coverage to make the suite green. Update empty-state wording assertions to the new direct-Member entry; leave old public-control journeys working.
- [ ] **4. Run targeted GREEN.** `pytest tests/browser/test_cad_core_drawing.py tests/browser/test_cad_core_journey.py tests/browser/test_node_joint_workspace.py tests/browser/test_node_joint_journey.py tests/browser/test_poc_v1_student_journey.py tests/browser/test_ux_v2_student_journey.py -q`. Require all tests executed and passed, zero unintended skips, browser console clean of uncaught application errors, and identity/topology evidence after save/reload.
- [ ] **5. Run full fresh regression in the implementation worktree.** Execute sequentially: `pytest -q -m 'not browser'`; `pytest tests/browser -q`; `pytest tests/mechanics -q`; `python3 manage.py check`; `python3 manage.py makemigrations --check --dry-run`; `git diff --check`. Record exact pass counts and command exit codes. Check the branch diff against its design+plan start commit: Solver changed = NO, Mechanics changed = NO, Draft schema changed = NO, DB migration = NONE; root original work unchanged and main untouched. A failure blocks completion; diagnose without waiving tests or adding blind waits.
- [ ] **6. Inspect browser visuals, review and commit.** Inspect actual screenshots/browser states against the Spec's Grid prominence, NODE/INT distinction, natural blank-start drawing, unobstructed mini input, stable zoom/pan, intuitive ORTHO and readable four status controls. Record this as engineering inspection, not Product Owner approval. Perform a whole-branch boundary review using the preserved execution method. Commit only integration fixes/tests with `test: cover core drawing journey and regressions`, after fresh GREEN. Hand off commit(s), files, evidence and checks with status **CAD CORE DRAWING V1 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING**, then stop for Product Owner visual review; do not merge/push/deploy.

## Plan self-review and coverage

Spec coverage is complete: authority/state/file boundaries and transform pipeline → Task 1; pending blank start, identity/atomic history/intermediate incidence/crossing guard → Task 2; Grid/ORTHO/Shift/OSNAP, progressive numeric input/status/keyboard → Task 3; zoom/pan, stable pixel presentation/spatial lifecycle/performance → Task 4; public journey/compatibility/full regression/manual acceptance → Task 5. Critical RED cases A–J map to Tasks 1–2, K–N/Q/R/S to Tasks 1–3, O/P/T to Task 4; Task 5 exercises their composition and persistence.

Step scan: each task has explicit failing assertions, a RED command, bounded interface implementation, targeted GREEN, review and commit. Type consistency: all point consumers use Point/CoordinateSpace/SnapResolution; only NODE provides identity, PendingEndpoint becomes EditorEndpoint only at atomic commit, and all view callers use SVG-local field names. Review Focus: each of the five input classes above has a named owning test. Proportion: five independently reviewable tasks, without per-feature approval gates or implementation bodies. No placeholder, unresolved implementation choice, extra Package 2/3 feature, mechanics change, schema change or DB migration is planned.

This plan is submitted for Product Owner review. Production implementation begins only after the plan is approved and the execution method is supplied; this planning turn changes and commits only this document.
