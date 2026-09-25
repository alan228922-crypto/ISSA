# Workspace CAD Interaction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make node placement, support/load targeting, CAD-style multi-selection, and keyboard/panel deletion work as one consistent Truss2D modeling workflow.

**Architecture:** Keep physical-draft-v1 and the current Truss2D idealization. Introduce one pure grid authority and one pure marquee-geometry helper, then adapt the existing canvas state/controller and editor reducer. All deletion entrypoints dispatch one atomic reducer action; node-facing commands resolve internal connections without exposing a separate Connection tool.

**Tech Stack:** Django/Python, plain JavaScript ES modules, SVG, pytest, Playwright browser tests.

**Spec:** `docs/superpowers/specs/2026-09-25-workspace-cad-interaction-design.md`

## Global Constraints

- Canonical mechanics units remain mm/N/MPa/g; no Solver, analysis-snapshot, or report schema change.
- Global-origin logical grid and GRID snap use one `GRID_SPACING = 1` authority. Numeric input preserves decimal coordinates. NODE/INT precedence remains unchanged.
- ORTHO keeps the locked axis exactly, including decimals, and snaps only the moving axis.
- Visual grid uses 1/10/100 mm levels, three SVG patterns and one background rectangle. A level appears at projected spacing of at least 8 CSS pixels; major remains visible at all zoom levels.
- A geometric member crossing is not a joint until a node is explicitly placed there. Internal `Connection` remains the only truss sharing authority; no rigid joints or frame degrees of freedom.
- User-visible support/load targets are nodes. Persisted `target_connection_client_key` and prediction payloads remain unchanged.
- Preserve the existing uncommitted workspace changes and unrelated `README.md` change. Audit staged hunks before every commit; never stage `README.md` for this plan.

## Review Focus

1. A pointer gesture crossing a node must not create a node/member when the marquee completes — Task 3 browser test.
2. A Delete key typed into coordinate, label, or load input must edit text, not topology — Task 4 browser test.
3. A legacy node with two connections must not receive a support/load through an arbitrary connection — Task 2 reducer/browser test.
4. A selected shared joint with one selected and one surviving member must retain the surviving member and its connection — Task 4 reducer test.
5. A visual grid LOD change at fixed world coordinate must not change GRID snap or Fit — Task 1 browser test.

---

## File map

- Create `projects/static/projects/workspace/grid.js`: sole `GRID_SPACING`, grid rounding, and projected-LOD decisions.
- Create `projects/static/projects/workspace/selection-geometry.js`: pure screen-space point/segment-vs-rectangle classification.
- Modify `geometry.js`: call the shared grid rounding authority; retain NODE/INT and ORTHO ordering.
- Modify `canvas-interaction.js`: re-export grid constant for current consumers; implement gesture state and ordered multi-selection.
- Modify `renderer.js`: bounded SVG patterns and selection rectangle/highlighting.
- Modify `editor.js`: node-to-unique-connection resolution and atomic batch deletion.
- Modify `modeling-interaction.js`: clear node feedback and node-first support/load targeting.
- Modify `state.js`, `prediction.js`, `properties.js`: selection compatibility, prediction node adapter, shared panel/keyboard delete.
- Modify `tests/browser/test_workspace.py`, `tests/browser/test_ux_v2_student_journey.py`, `tests/browser/test_poc_v1_student_journey.py`: RED→GREEN interaction, save/reload, and journey regressions.
- Read, but do not modify, `idealization/truss2d.py`, `mechanics/truss2d/model.py`, and existing mechanics benchmarks.

### Task 1: Single 1 mm grid authority and bounded visual grid

**Files:** Create `projects/static/projects/workspace/grid.js`; modify `geometry.js`, `canvas-interaction.js`, `renderer.js`; test `tests/browser/test_workspace.py`.

**Interfaces:** Produces `GRID_SPACING: number`, `gridNearest(value: number): number`, `visibleGridLevels(projectedPixelsPerMm: number): {minor:boolean,medium:boolean,major:true}` from `grid.js`. `canvas-interaction.js` re-exports `GRID_SPACING`; `geometry.js` re-exports `gridNearest` so existing imports remain valid. No later task may introduce another snap/grid constant.

- [ ] **Step 1: Write failing grid behavior tests.** Add browser-evaluated assertions against real ES modules, including `gridNearest(12.4) === 12`, `gridNearest(28.7) === 29`, `GRID_SPACING === 1`, horizontal ORTHO from `(12.4,7.6)` to near `(13.2,7.8)` gives `(13,7.6)`, vertical ORTHO locks `x=12.4`, and grid DOM contains exactly three patterns plus one background rectangle after Fit and zoom. Add a test that captures one pointer world point before/after a visual LOD change and compares the resolver result.

```python
def test_one_mm_grid_snap_and_ortho_preserve_locked_decimals(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {GRID_SPACING, gridNearest} = await import('/static/projects/workspace/grid.js');
      const {resolvePointerPoint} = await import('/static/projects/workspace/geometry.js');
      const run = (point, origin) => resolvePointerPoint({worldPointer:point,
        screenPointer:point,candidates:[],viewTransform:{a:1,b:0,c:0,d:1,e:0,f:0},
        origin,ortho:true,gridEnabled:true,explicitNumeric:false}).point;
      return {spacing:GRID_SPACING,x:gridNearest(12.4),y:gridNearest(28.7),
        horizontal:run({x:13.2,y:7.8},{x:12.4,y:7.6}),
        vertical:run({x:12.6,y:29.2},{x:12.4,y:28.7})};
    }""")
    assert result == {'spacing': 1, 'x': 12, 'y': 29,
                      'horizontal': {'x': 13, 'y': 7.6},
                      'vertical': {'x': 12.4, 'y': 29}}
```

- [ ] **Step 2: Run the new tests RED.** Run `pytest -q tests/browser/test_workspace.py -k 'one_mm_grid or grid_pattern_lod'`. Expected: assertion fails on 100 mm spacing or missing pattern elements, not fixture/setup errors.
- [ ] **Step 3: Implement one authority.** In `grid.js`, export `GRID_SPACING=1`, `gridNearest` with the current positive-tie behavior (`Math.floor(value / GRID_SPACING + .5) * GRID_SPACING`), and `visibleGridLevels` using projected 8 px thresholds. Update `geometry.js` to import/re-export `gridNearest`; update `canvas-interaction.js` to re-export the constant. In `renderer.js`, replace the coordinate loop with three SVG patterns, one world-covering rectangle, and existing independent axes/origin. Avoid constructing a pattern or changing logical snap on pointermove; rebuild only on view redraw.

```javascript
export const GRID_SPACING = 1;
export const gridNearest = value => {
  if (!Number.isFinite(value)) throw new TypeError('INVALID_GRID_VALUE');
  return Math.floor(value / GRID_SPACING + .5) * GRID_SPACING;
};
export const visibleGridLevels = pxPerMm => ({
  minor: pxPerMm >= 8, medium: pxPerMm * 10 >= 8, major: true,
});
```

- [ ] **Step 4: Run GREEN and grid regressions.** Run the new tests plus existing grid/ORTHO/fit tests in `tests/browser/test_workspace.py`; update old 100 mm expectations to the approved 1 mm contract only where the behavior truly changed. Expected: all selected tests pass; no 1 mm-per-line DOM growth.
- [ ] **Step 5: Commit only this task's reviewed hunks.** Stage new `grid.js` and the tested hunks in the three existing files plus tests; inspect `git diff --cached`; commit with `feat: use one millimeter grid with bounded SVG patterns`. Do not include unrelated pre-existing changes.

### Task 2: Reliable node placement and node-facing support/load

**Files:** Modify `editor.js`, `modeling-interaction.js`, `renderer.js`, `prediction.js`, `state.js`; test `tests/browser/test_workspace.py` and `tests/browser/test_ux_v2_student_journey.py`.

**Interfaces:** Produces `resolveNodeConnection(draft, nodeClientKey): {draft, connectionClientKey}` or throws `EditorActionError('NODE_NOT_ON_MEMBER'|'MULTIPLE_JOINTS_AT_NODE')`. Expose editor actions `{type:'CREATE_SUPPORT_AT_NODE',nodeClientKey,support:{client_key,support_type,restrained_axis}}` and `{type:'CREATE_NODE_LOAD_AT_NODE',nodeClientKey,nodeLoad:{client_key,fx_N,fy_N,label}}`. The reducer inserts `target_connection_client_key` into saved records. Existing saved record fields do not change. Task 3's selection adapter consumes the node→connection lookup.

- [ ] **Step 1: Write failing node and target tests.** Use an existing member with a geometry node and no connection: clicking that node with SUPPORT creates one internal connection and one support; LOAD on the same node reuses that connection. An isolated node yields `NODE_NOT_ON_MEMBER` and unchanged draft. Two legacy connections at one node yield `MULTIPLE_JOINTS_AT_NODE`. Clicking an already connected node with NODE leaves the draft identity/dirty state unchanged and shows an explanatory message. Numeric decimal node and INT node persist through save/reload.

```python
def test_support_and_load_can_target_visible_node(context, workspace_page):
    owner, project, material, section = context
    from modeling.services import save_physical_draft
    from tests.application.test_physical_draft import valid_payload
    draft = valid_payload(material, section)
    draft['connections'] = []
    draft['supports'] = []
    draft['node_loads'] = []
    save_physical_draft(actor=owner, project=project, payload=draft)
    page = workspace_page(user=owner, project=project)
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    assert page.locator('[data-object-kind="Support"]').count() == 1
    page.locator('[data-workspace-tool="LOAD"]').click()
    page.locator('[data-client-key="n1"] circle').click(force=True)
    assert page.locator('[data-object-kind="NodeLoad"]').count() == 1
```

- [ ] **Step 2: Run RED.** Run `pytest -q tests/browser/test_workspace.py -k 'support_and_load_can_target_visible_node or isolated_node or multiple_joints_at_node or existing_node_noop'`. Expected: target tests fail because only `CONNECTION` is accepted; no-op test fails because the draft is marked dirty.
- [ ] **Step 3: Implement the reducer boundary and UI feedback.** Resolve exactly one connection at a node; create one through the existing member-on-segment logic only when needed; reject disconnected and duplicate-connection cases before mutating. Dispatch support/load node actions from `modeling-interaction.js`; map visible joint marker to its geometry node. Ensure NODE no-op does not call `replaceState` as an edit. Adapt prediction selection so a selected node resolves to the unique internal connection without changing submitted payloads. Provide specific visible error messages for read-only, wrong stage, invalid coordinate, isolated node, and legacy duplicate connection.

```javascript
case 'CREATE_SUPPORT_AT_NODE': {
  const resolved = resolveNodeConnection(draft, action.nodeClientKey);
  return createReferenced(resolved.draft, 'SUPPORT', {
    ...action.support, target_connection_client_key: resolved.connectionClientKey,
  });
}
```

- [ ] **Step 4: Run GREEN and save/reload journeys.** Run all Task 2 tests, the existing crossing-node tests, support/load property tests, and the POC student journey. Expected: all pass; no Solver file changes.
- [ ] **Step 5: Commit reviewed Task 2 hunks.** Inspect staged diff and commit `feat: target truss supports and loads through nodes`.

### Task 3: CAD marquee and multi-selection without pan conflicts

**Files:** Create `selection-geometry.js`; modify `canvas-interaction.js`, `renderer.js`, `state.js`, `properties.js`; test `tests/browser/test_workspace.py`.

**Interfaces:** Produces `objectsInMarquee(rect, renderedObjects, mode)` where `rect` is screen-space `{left,right,top,bottom}`, objects are from `renderedObjectsFromSvg`, and `mode` is `'CROSSING'|'WINDOW'`; returns stable `(kind,clientKey)` identities. Produces `selectedObjects` in canvas state while retaining `selectedObject` as primary. Task 4 consumes this selection array.

- [ ] **Step 1: Write failing pure/browser selection tests.** A segment from `(0,50)` to `(100,50)` intersects a rectangle `[40,60]×[40,60]`: CROSSING includes it, WINDOW excludes it. A contained segment is included by both. A point outside is excluded. In browser, left→right and right→left gestures select the expected rendered members; Shift adds; blank click and Escape clear; middle/Space drag pans; dragging never invokes the drawing click handler.

```python
def test_cad_window_and_crossing_selection(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {objectsInMarquee} = await import('/static/projects/workspace/selection-geometry.js');
      const objects=[{kind:'PHYSICAL_MEMBER',clientKey:'m1',
        hit:{type:'SEGMENT',start:{x:0,y:50},end:{x:100,y:50}}}];
      const rect={left:40,right:60,top:40,bottom:60};
      return {crossing:objectsInMarquee(rect,objects,'CROSSING'),
        window:objectsInMarquee(rect,objects,'WINDOW')};
    }""")
    assert result == {'crossing':[{'kind':'PHYSICAL_MEMBER','clientKey':'m1'}], 'window':[]}
```

- [ ] **Step 2: Run RED.** Run `pytest -q tests/browser/test_workspace.py -k 'cad_window_and_crossing_selection or marquee_gesture or multi_selection_pan'`. Expected: missing module/incorrect left-drag pan behavior.
- [ ] **Step 3: Implement geometry and gestures.** Use screen-space segment-rectangle intersection and endpoint containment in `selection-geometry.js`. In `canvas-interaction.js`, start a gesture at pointerdown; after a 4 CSS pixel threshold, SELECT+left becomes marquee, middle or Space+left becomes pan; pointerup commits selection and suppresses the synthetic click. Use pointer capture and release/cancel handling. Render a single marquee overlay and selected highlights from `selectedObjects`. Keep `selectedObject` in sync as the primary selection for legacy consumers. Map visible connection markers to their node identity for multi-selection. Do not mutate the draft during selection.

```javascript
export function objectsInMarquee(rect, renderedObjects, mode) {
  return renderedObjects.filter(object => object.hit?.type === 'POINT'
    ? pointInside(rect, object.hit.point)
    : mode === 'WINDOW'
      ? pointInside(rect, object.hit.start) && pointInside(rect, object.hit.end)
      : segmentIntersectsRect(rect, object.hit.start, object.hit.end))
    .map(({kind, clientKey}) => ({kind, clientKey}));
}
```

- [ ] **Step 4: Run GREEN and viewport regressions.** Run Task 3 tests plus existing `pickAt`, zoom, pan, Fit, node, member, support, load, and keyboard accessibility tests. Expected: no accidental model creation after dragging, no selection loss after redraw, and unchanged wheel zoom.
- [ ] **Step 5: Commit reviewed Task 3 hunks.** Inspect staged diff and commit `feat: add CAD window and crossing selection`.

### Task 4: Atomic batch delete, keyboard Delete, and panel parity

**Files:** Modify `editor.js`, `canvas-interaction.js`, `properties.js`, `state.js`; test `tests/browser/test_workspace.py` and `tests/browser/test_ux_v2_student_journey.py`.

**Interfaces:** Consumes `selectedObjects` from Task 3. Produces `applyEditorAction(draft,{type:'DELETE_OBJECTS',targets:[{kind,clientKey},...]})` with all-or-nothing behavior, returning a new draft or `EditorActionError('EDITOR_DEPENDENCY_CONFLICT')`. Both keyboard and panel invoke this action through one UI command.

- [ ] **Step 1: Write failing deletion tests.** Cover member deletion with two auto-generated endpoint connections; shared joint preserving the surviving member; explicit selected load/support deletion followed by member deletion; conflict when a surviving load/support would be stranded; node-only deletion with an unselected attached member rejected atomically; two selected members deleted in one draft update; Delete/Backspace focused in coordinate/label/load input does not alter draft; keyboard and panel produce the same resulting collections.

```python
def test_delete_member_prunes_only_unused_auto_joints(context, workspace_page):
    page = workspace_page(user=context[0], project=context[1])
    result = page.evaluate("""async () => {
      const {applyEditorAction} = await import('/static/projects/workspace/editor.js');
      const draft={schema_version:'physical-draft-v1',version:0,
        nodes:[{client_key:'n1',x_mm:0,y_mm:0,label:''},
               {client_key:'n2',x_mm:100,y_mm:0,label:''}],
        physical_members:[{client_key:'m1',start_node_client_key:'n1',
          end_node_client_key:'n2',material_id:1,section_id:1,label:'',is_active:true}],
        connections:[{client_key:'c1',geometry_node_client_key:'n1',participating_member_client_keys:['m1']},
                     {client_key:'c2',geometry_node_client_key:'n2',participating_member_client_keys:['m1']}],
        supports:[],node_loads:[]};
      const next=applyEditorAction(draft,{type:'DELETE_OBJECTS',
        targets:[{kind:'PHYSICAL_MEMBER',clientKey:'m1'}]});
      return {members:next.physical_members.length,joints:next.connections.length,nodes:next.nodes.length};
    }""")
    assert result == {'members':0,'joints':0,'nodes':2}
```

- [ ] **Step 2: Run RED.** Run `pytest -q tests/browser/test_workspace.py -k 'delete_member_prunes_only_unused_auto_joints or batch_delete or delete_key'`. Expected: unknown `DELETE_OBJECTS` action or blocked dependency.
- [ ] **Step 3: Implement one delete command.** Validate all targets, compute the entire survivor graph before mutation, reject if any unselected dependent member/support/load would be removed or stranded, then construct new arrays for all five collections. Remove member IDs from connections and drop only empty unreferenced connections. Normalize/dedupe selected identities. The right-panel button calls the same command with current `selectedObjects`, and canvas/document keydown handles Delete/Backspace only when focus is not editable and the workspace is editable/build stage. On success clear removed selections and set dirty once; on failure leave state untouched and show concrete dependencies.

```javascript
case 'DELETE_OBJECTS': return deleteObjectsAtomically(draft, action.targets);
case 'DELETE_OBJECT': return deleteObjectsAtomically(draft, [action.target]);
```

- [ ] **Step 4: Run GREEN and save/reload.** Run Task 4 tests plus existing editor immutability/dependency tests; update legacy assertions only where the approved delete contract changes. Browser-save a deletion and reload to prove persistence; run model check on surviving structure.
- [ ] **Step 5: Commit reviewed Task 4 hunks.** Inspect staged diff and commit `feat: delete selected model objects with dependency safety`.

### Task 5: Integrated acceptance and final review

**Files:** Test `tests/browser/test_workspace.py`; adjust other browser tests only when an explicit contract in the spec supersedes their old expectations. No solver/analysis code changes.

**Interfaces:** Consumes Tasks 1–4. Produces verification evidence and a final report; no new runtime API.

- [ ] **Step 1: Add one end-to-end browser journey.** In `test_cad_integrated_journey`, use the existing blank-project `context` and `workspace_page` fixtures. Select material/section; place triangle nodes `(0,0)`, `(1000,0)`, `(500,500)` through numeric input, create its three members, then place temporary nodes `(0,250)` and `(1000,250)` and connect them with a fourth member. Assert no joint appears at `(250,250)` or `(750,250)`, the two visual crossings; the separate Task 2 test covers intentional crossing-node creation. Place PINNED support at `(0,0)`, ROLLER_Y at `(1000,0)`, and a downward load at `(500,500)` by clicking nodes/joint markers. Use a left-to-right window marquee to select the temporary fourth member and its two temporary nodes, press Delete, save/reload, and assert only the three-member triangle remains. Run model check and analyze; assert success and stable support/load target IDs. Verify the crossing member's removal did not delete triangle joints or mechanics data.

```python
def test_cad_integrated_journey(context, workspace_page):
    owner, project, material, section = context
    page = workspace_page(user=owner, project=project)
    page.locator('[data-member-material]').select_option(str(material.id))
    page.locator('[data-member-section]').select_option(str(section.id))
    page.locator('.ux-precision summary').click()
    page.locator('[data-workspace-tool="NODE"]').click()
    command = page.locator('[data-cad-command-input]')
    for coordinate in ('0,0', '1000,0', '500,500', '0,250', '1000,250'):
        command.fill(coordinate)
        command.press('Enter')
    page.locator('[data-cad-fit]').click()
    page.locator('[data-workspace-tool="MEMBER"]').click()
    for start, end in (('node-1','node-2'), ('connection-1','node-3'),
                       ('connection-2','connection-3'), ('node-4','node-5')):
        page.locator(f'[data-client-key="{start}"]').click(force=True)
        page.locator(f'[data-client-key="{end}"]').click(force=True)
    assert page.locator('[data-object-kind="Connection"]').count() == 5
    page.locator('[data-workspace-tool="SUPPORT"]').click()
    page.locator('[data-client-key="connection-1"] rect').click(force=True)
    page.locator('[data-client-key="connection-2"] rect').click(force=True)
    page.locator('[data-client-key="support-2"]').focus()
    page.keyboard.press('Enter')
    page.locator('[data-property-support-type]').select_option('ROLLER_Y')
    page.locator('[data-workspace-tool="LOAD"]').click()
    page.locator('[data-client-key="connection-3"] rect').click(force=True)
    page.locator('[data-workspace-tool="SELECT"]').click()
    box = page.evaluate("""() => {
      const matrix=document.querySelector('[data-world-layer]').getScreenCTM();
      const a=new DOMPoint(-10,260).matrixTransform(matrix);
      const b=new DOMPoint(1010,240).matrixTransform(matrix);
      return {left:Math.min(a.x,b.x),right:Math.max(a.x,b.x),
        top:Math.min(a.y,b.y),bottom:Math.max(a.y,b.y)};
    }""")
    page.mouse.move(box['left'], box['top'])
    page.mouse.down()
    page.mouse.move(box['right'], box['bottom'])
    page.mouse.up()
    page.keyboard.press('Delete')
    assert page.locator('[data-object-kind="PhysicalMember"]').count() == 3
    page.locator('#workspace-save').click()
    page.wait_for_function("document.querySelector('#workspace-save-status').textContent.includes('无')")
    page.reload()
    saved = page.evaluate("JSON.parse(document.querySelector('#workspace-bootstrap').textContent).draft")
    assert len(saved['physical_members']) == 3
    assert len(saved['supports']) == 2 and len(saved['node_loads']) == 1
    assert {item['target_connection_client_key'] for item in saved['supports']} == {'connection-1','connection-2'}
    assert saved['node_loads'][0]['target_connection_client_key'] == 'connection-3'
    page.locator('[data-ux-stage-target="check"]').click()
    page.locator('#workspace-model-check').click()
    page.wait_for_function("document.querySelector('#workspace-check-issues').textContent.trim().length > 0")
    assert '模型检查通过' in page.locator('#workspace-check-issues').inner_text()
    page.locator('[data-ux-stage-target="analyze"]').click()
    page.locator('#workspace-analyze').click()
    page.wait_for_function("document.querySelector('#workspace-run-select').value !== ''")
```

- [ ] **Step 2: Run the integrated journey.** Run `pytest -q tests/browser/test_workspace.py -k 'cad_integrated_journey'`. Expected: PASS after Tasks 1–4; if it fails, identify which owning interface broke and add a focused failing test there before correction.
- [ ] **Step 3: Run full verification.** Run `pytest -q -m 'not browser'`, `pytest tests/browser -q`, `python3 manage.py check`, `python3 manage.py makemigrations --check --dry-run`, and `git diff --check`. Expected: zero failures/issues/migration changes/whitespace errors. Run the mechanics benchmark tests by their existing pytest selection and confirm no Solver/mechanics files changed.
- [ ] **Step 4: Inspect and report.** Review the full diff against the spec, confirm user-owned `README.md` remained untouched, report changed files, exact pass/fail counts, any unaddressed browser-only caveat, commit IDs, and the local platform URL if a server is running. Do not claim complete unless all four behavior groups and all required checks pass.
