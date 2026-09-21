# POC V1 Product Reconciliation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the frozen POC V1 student journey genuinely usable from an empty Project through explicit historical learning/report state using real browser controls.

**Architecture:** Preserve the Django modular monolith and existing pure-Python mechanics authority. Add ordinary owner-scoped Material/Section pages, connect the existing CAD modules to one visible Workspace controller, and introduce one explicit selected-AnalysisRun UI context that drives Results, Compare, Explain, Report, Reasoning, and Reflection without a latest fallback.

**Tech Stack:** Python 3.13, Django 5.2, SQLite, Vanilla JavaScript ES modules, SVG, pytest, pytest-django, Playwright Chromium.

**Spec:** `docs/superpowers/specs/2026-09-21-poc-v1-product-reconciliation-design.md`

## Global Constraints

- P0 analysis remains `TRUSS_2D`: 2D, linear elastic, small displacement, pin-jointed, axial-only, `ux/uy`, nodal `Fx/Fy`.
- Units remain mm / N / MPa / g.
- No mechanics benchmark, sign convention, Roller behavior, or solver authority changes.
- Do not resolve O-001, O-003, O-004, O-005, O-006, T-M6-001, T-M6-002, or T-M6-003.
- Safe Section authoring is rectangular `section-definition-v1`; no overlap-capable composite editor.
- All Project/Material/Section authorization remains server-side and owner-scoped.
- Every historical UI load uses an explicit `AnalysisRun` ID; no latest fallback or cross-run copy-forward.
- Prediction and Reflection remain Soft Gates.
- Student-visible copy is Simplified Chinese; stable program identifiers and machine codes remain English internally.
- Product browser acceptance must use public controls and must not call reducers/private JS functions or inject final state.

## Review Focus

- A Project owner with zero Materials, Sections, members, or fixtures can create a valid first member; another user's IDs are never selectable or accepted.
- Valid numeric input bypasses SNAP while pointer input uses Node/Endpoint > Intersection > Grid exactly once; no intersection creates a Connection.
- Dependency-blocked deletion leaves the draft unchanged and gives an actionable message; allowed deletion persists only after Save.
- Switching between two successful runs never leaks Results, Report, Reasoning, or Reflection and never selects a run merely because it is newest.
- Owner versus assigned reviewer sessions produce correct editable/read-only controls and explanations without weakening server authorization.

---

### Task 1: Entry, identity, and blank-Project foundation

**Files:**
- Create: `materials/forms.py`
- Create: `materials/views.py`
- Create: `materials/urls.py`
- Create: `templates/materials/index.html`
- Create: `templates/materials/material_form.html`
- Create: `templates/materials/section_form.html`
- Create: `templates/shared/product_header.html`
- Modify: `materials/services.py`
- Modify: `config/urls.py`
- Modify: `projects/workspace.py`
- Modify: `templates/accounts/login.html`
- Modify: `templates/accounts/password_change.html`
- Modify: `templates/accounts/event_landing.html`
- Modify: `templates/projects/workspace.html`
- Modify: `projects/static/projects/workspace/modeling-interaction.js`
- Test: `tests/endpoints/test_material_pages.py`
- Test: `tests/endpoints/test_workspace.py`
- Test: `tests/browser/test_student_entry_flow.py`
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Produces: `update_section(*, actor, section, name, definition) -> Section`; owner-scoped routes `materials:index`, `material_create`, `material_edit`, `section_create`, `section_edit`; Workspace bootstrap `access`, `materials`, `sections`; member profile controls with `data-member-material` and `data-member-section`.
- Consumes: existing `create_section`, Material/Section models, `can_view_project`, and `applyEditorAction(CREATE_MEMBER)`.
- Task 2 consumes the member-profile selection and access context.

- [ ] **Step 1: Write endpoint RED tests for safe Material/Section authoring**

  Add tests proving: anonymous redirects; owner can create/edit Material with literal `E=2000`, `density=0.0007`; owner can create/edit a `1×6 mm` rectangular Section and sees computed `A=6`; foreign users receive 404/403 and cannot mutate; invalid/non-finite/non-positive values render form errors; composite overlap input is not offered.

- [ ] **Step 2: Run the endpoint tests and verify RED**

  Run: `pytest tests/endpoints/test_material_pages.py -q`

  Expected: FAIL because the routes/forms/templates do not exist.

- [ ] **Step 3: Implement minimum owner-scoped pages and section update service**

  `MaterialForm` exposes `name`, `E_MPa`, `density_g_per_mm3`, strengths, source, and note with units/help text. `RectangleSectionForm` accepts `name`, `width_mm`, `height_mm`, and density, builds this exact definition shape, and delegates calculation:

  ```python
  {
      "schema_version": "section-definition-v1",
      "type": "rectangle",
      "width_mm": float(width),
      "height_mm": float(height),
      "density_g_per_mm3": float(density),
  }
  ```

  `update_section` must call the same canonical/property helpers as `create_section`, authorize Developer or owner using the existing policy, and update all definition/property/hash fields atomically. Do not accept a client-supplied `A_mm2`.

- [ ] **Step 4: Run endpoint tests GREEN**

  Run: `pytest tests/endpoints/test_material_pages.py -q`

  Expected: PASS.

- [ ] **Step 5: Write Workspace bootstrap and read-only RED tests**

  Extend endpoint/browser tests to require owner-only Material/Section choices, event/current-user/owner labels, editable state for the owner, explanatory read-only state for assigned Manager/Developer, Events link, and POST logout. Require an empty Project to show setup guidance rather than relying on an exemplar member.

- [ ] **Step 6: Run focused Workspace tests and verify RED**

  Run: `pytest tests/endpoints/test_workspace.py tests/browser/test_student_entry_flow.py -q -m 'not browser'`

  Expected: endpoint assertions FAIL for missing bootstrap/access context.

- [ ] **Step 7: Implement shared entry shell, access context, and explicit member profile**

  Workspace bootstrap serializes only owner-owned choices:

  ```python
  "access": {
      "current_user": request.user.get_username(),
      "owner": project.owner_user.get_username(),
      "event": project.event.name,
      "editable": request.user.id == project.owner_user_id,
      "read_only_reason": "你正在以只读身份查看此项目。" if request.user.id != project.owner_user_id else "",
  }
  ```

  `modeling-interaction.js` reads the selected profile for every `CREATE_MEMBER`. If either choice is absent, it raises a presentation error and does not mutate. Remove exemplar-member cloning.

- [ ] **Step 8: Add and run real blank-first-member browser RED→GREEN**

  The Playwright test must navigate from Events to an empty Workspace, follow public links to create a Material and Section, return, create two nodes and the first member through visible controls, Save, reload, and assert the member persists. It may use normal browser selectors only.

  Run RED before implementation completion, then GREEN: `pytest tests/browser/test_student_entry_flow.py tests/browser/test_workspace.py -q -m browser`

- [ ] **Step 9: Commit Batch 1**

  ```bash
  git add accounts config materials projects templates tests
  git commit -m "fix: enable blank project student entry"
  ```

- [ ] **Step 10: Task verification**

  Run: `pytest tests/endpoints/test_material_pages.py tests/endpoints/test_workspace.py tests/browser/test_student_entry_flow.py tests/browser/test_workspace.py -q`

  Expected: all selected tests PASS.

---

### Task 2: Complete real CAD interaction, properties, and deletion

**Files:**
- Modify: `templates/projects/workspace.html`
- Modify: `projects/static/projects/workspace/state.js`
- Modify: `projects/static/projects/workspace/canvas-interaction.js`
- Modify: `projects/static/projects/workspace/modeling-interaction.js`
- Modify: `projects/static/projects/workspace/properties.js`
- Modify: `projects/static/projects/workspace/renderer.js`
- Modify: `projects/static/projects/workspace/workspace.css`
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Consumes: Task 1 member profile; existing `parseCadInput`, `transition`, `resolvePointerPoint`, `reduceView`, `applyEditorAction`.
- Produces: one visible CAD controller state (`ortho`, `gridSnap`, `gridVisible`, active command/origin), toolbar controls `data-cad-ortho`, `data-cad-snap`, `data-cad-fit`, numeric input `data-cad-command-input`, and property/delete controls.
- Task 3 consumes stable selection and canvas focus callbacks but no mechanics values.

- [ ] **Step 1: Write genuine UI RED tests for CAD controls**

  Add Playwright tests that click the visible SNAP/ORTHO toggles, click Fit and observe a transform change, type `1000,500`, `@1000,0`, and `1000<30` in legal command contexts, use Tab/Enter/Escape, and assert resulting world coordinates. Tests must not import CAD modules.

- [ ] **Step 2: Run CAD UI tests and verify RED**

  Run: `pytest tests/browser/test_workspace.py -q -m browser -k 'visible_cad_controls or numeric_modeling'`

  Expected: FAIL because the controls/wiring do not exist.

- [ ] **Step 3: Wire one controller to existing CAD authorities**

  Pointer events collect candidates from the current draft, call `resolvePointerPoint` once, and render the returned `NODE`/`INT`/`GRID` indicator. Complete numeric input calls `parseCadInput` and passes `explicitNumeric:true`. ORTHO/Grid state is presentation/drawing state only. Fit dispatches the existing `FIT_VIEW` event with `workspaceWorldBounds`.

- [ ] **Step 4: Run CAD UI tests GREEN and existing CAD module regressions**

  Run: `pytest tests/browser/test_workspace.py -q -m browser -k 'cad or snap or grid or canvas or numeric'`

  Expected: PASS.

- [ ] **Step 5: Write property/delete RED tests**

  Through public controls edit Node `x_mm/y_mm/label`, Member `material_id/section_id/label/is_active`, inspect immutable Connection membership, edit Support and Load, reject dependency-blocked deletion with a Chinese next action, delete an unreferenced object, Save, reload, and verify persistence.

- [ ] **Step 6: Run property/delete tests and verify RED**

  Run: `pytest tests/browser/test_workspace.py -q -m browser -k 'property or delete'`

  Expected: new Node/Member/delete assertions FAIL.

- [ ] **Step 7: Implement complete frozen property controls and safe Delete**

  Every edit dispatches the existing `UPDATE_OBJECT` whitelist. Connection shows node and participating members read-only. Delete dispatches `DELETE_OBJECT`; map `EDITOR_DEPENDENCY_CONFLICT` to “请先删除或调整依赖该对象的构件、连接、支座或荷载。” No cascade is added.

- [ ] **Step 8: Run property/delete GREEN and Save/reload regression**

  Run: `pytest tests/browser/test_workspace.py -q -m browser -k 'modeling or property or delete or save'`

  Expected: PASS.

- [ ] **Step 9: Commit Batch 2**

  ```bash
  git add projects/static/projects/workspace templates/projects/workspace.html tests/browser/test_workspace.py
  git commit -m "fix: complete beginner cad modeling workflow"
  ```

- [ ] **Step 10: Task verification**

  Run: `pytest tests/browser/test_workspace.py tests/application/test_physical_draft.py -q`

  Expected: all selected tests PASS.

---

### Task 3: Wire the explicit-run learning journey and historical restore

**Files:**
- Modify: `templates/projects/workspace.html`
- Modify: `projects/static/projects/workspace/results.js`
- Modify: `projects/static/projects/workspace/workflow.js`
- Modify: `projects/static/projects/workspace/reflection.js`
- Modify: `projects/static/projects/workspace/report.js`
- Modify: `projects/static/projects/workspace/report-reasoning.js`
- Create: `projects/static/projects/workspace/run-context.js`
- Modify: `projects/static/projects/workspace/workspace.css`
- Test: `tests/browser/test_workspace.py`
- Test: `tests/endpoints/test_workspace.py`
- Test: `tests/endpoints/test_report_json.py`
- Test: `tests/endpoints/test_reasoning_json.py`
- Test: `tests/endpoints/test_reflection_json.py`

**Interfaces:**
- Produces: `createRunContext({urls,...})` with `refreshRuns({selectRunId})`, `selectRun(runId)`, and immutable `state()`; public controls `#workspace-run-select`, `data-result-compare`, `data-result-explain`, `data-result-report`.
- Consumes: explicit `analysis_run_id` from Analyze and existing run-scoped endpoints. It never consumes an implicit latest identifier.
- Task 4 consumes these public controls for the full journey.

- [ ] **Step 1: Write Compare/Explain reachability RED test**

  Use real buttons after Analyze. Assert Compare renders normal no-prediction or member comparison states and Explain renders backend blocks. The test must fail if helper functions exist but buttons are absent.

- [ ] **Step 2: Run and verify RED**

  Run: `pytest tests/browser/test_workspace.py -q -m browser -k 'compare_explain_reachable'`

  Expected: FAIL for missing controls.

- [ ] **Step 3: Implement result actions and renderers**

  Add render functions that create focusable rows from `comparison-v1` and `explanation-v1`, preserve `NO_PREDICTION` as normal, and focus the referenced PhysicalMember through the existing selection controller. No frontend mechanics classification is added.

- [ ] **Step 4: Run Compare/Explain GREEN**

  Run: `pytest tests/browser/test_workspace.py -q -m browser -k 'compare_explain'`

  Expected: PASS.

- [ ] **Step 5: Write explicit-run refresh and two-run historical RED tests**

  Test Analyze → returned Run immediately appears/selects without reload. Create Run #1 and Run #2 with distinct Reflection/Reasoning text; reload; explicitly select each and assert its Results, Report, Reasoning, and Reflection. Assert changing current draft marks older runs stale but does not alter their data. Assert no UI/API request omits a run ID.

- [ ] **Step 6: Run and verify RED**

  Run: `pytest tests/browser/test_workspace.py tests/endpoints/test_report_json.py tests/endpoints/test_reasoning_json.py tests/endpoints/test_reflection_json.py -q -k 'historical or explicit or refresh'`

  Expected: browser historical/refresh assertions FAIL while endpoint isolation remains GREEN.

- [ ] **Step 7: Implement shared explicit run context**

  `refreshRuns({selectRunId})` repopulates discovery and selects only the supplied ID when present. `selectRun(runId)` concurrently requests run data, Compare, Explain, Report, owner Reasoning, and Reflection for that exact ID, discarding stale responses by selection token. A failed/non-success run shows safe metadata and does not substitute another run.

- [ ] **Step 8: Run historical GREEN and backend isolation regressions**

  Run: `pytest tests/browser/test_workspace.py tests/endpoints/test_report_json.py tests/endpoints/test_reasoning_json.py tests/endpoints/test_reflection_json.py -q`

  Expected: PASS.

- [ ] **Step 9: Commit Batch 3**

  ```bash
  git add projects/static/projects/workspace templates/projects/workspace.html tests
  git commit -m "fix: connect explicit run learning journey"
  ```

- [ ] **Step 10: Task verification**

  Run: `pytest tests/browser/test_workspace.py tests/endpoints/test_report_json.py tests/endpoints/test_reasoning_json.py tests/endpoints/test_reflection_json.py -q`

  Expected: all selected tests PASS.

---

### Task 4: Beginner presentation, genuine full journey, reconciliation docs

**Files:**
- Modify: `projects/static/projects/workspace/results.js`
- Modify: `projects/static/projects/workspace/errors.js`
- Modify: `templates/projects/workspace.html`
- Modify: `projects/static/projects/workspace/workspace.css`
- Modify: `tests/browser/test_workspace.py`
- Create: `tests/browser/test_poc_v1_student_journey.py`
- Modify: `projects/management/commands/seed_demo.py`
- Modify: `docs/development/demo_setup.md`
- Modify: `docs/specs/MASTER_SPEC.md`
- Modify: `docs/specs/STUDENT_LEARNING_WORKSPACE_UX.md`
- Modify: `docs/specs/CALCULATION_REPORT_ASSISTANCE_SPEC.md`
- Modify: `docs/specs/CODEX_IMPLEMENTATION_PLAN.md`
- Modify: `docs/specs/POC_V1_KNOWN_ISSUES.md`
- Create: `README.md`

**Interfaces:**
- Consumes all Tasks 1–3 public controls and explicit-run context.
- Produces the authoritative real-browser POC V1 journey and verified product-state documentation.

- [ ] **Step 1: Write beginner result/error and 1024px RED tests**

  Assert Level 1 contains load/support/force-transfer guidance, rounded student values, localized object labels, tension/compression/zero summaries, and no `connection:`/raw hash. Trigger unstable/dependency/stale errors and assert what/why/next-action; machine codes appear only inside collapsed technical detail. At 1024×900 assert `document.documentElement.scrollWidth <= window.innerWidth`, key actions are visible, and report tables scroll/wrap within their panel.

- [ ] **Step 2: Run and verify RED**

  Run: `pytest tests/browser/test_workspace.py -q -m browser -k 'beginner or error or desktop_1024'`

  Expected: FAIL on current identifiers, error code placement, and report overflow.

- [ ] **Step 3: Implement label resolver, cautious teaching summaries, technical disclosure, and desktop layout**

  Keep source values untouched. Format only presentation, use object labels when present, and use consistent localized fallbacks. Error messages never diagnose a unique mechanism; singular/unstable guidance says to inspect supports, connections, isolated nodes, and overall stability.

- [ ] **Step 4: Run presentation tests GREEN**

  Run: `pytest tests/browser/test_workspace.py -q -m browser -k 'result or error or desktop_1024'`

  Expected: PASS.

- [ ] **Step 5: Write the real POC V1 journey RED test**

  `test_poc_v1_full_student_journey_uses_public_controls` performs Login → Events → empty Project → Material → Section → first model → numeric/SNAP/ORTHO → Support/Load → Save/reload → Check → Prediction → Analyze → Results → Compare → Explain → Report → Reasoning → Reflection → second run → reload/historical switching. It uses only Playwright locators, typing, clicking, selection, and reload; no `page.evaluate` except read-only layout measurements, no JS imports, no direct service/reducer calls.

- [ ] **Step 6: Run and verify RED**

  Run: `pytest tests/browser/test_poc_v1_student_journey.py -q -m browser`

  Expected: FAIL until all public flow details are complete.

- [ ] **Step 7: Close journey defects and make the test GREEN**

  Fix only defects exposed by the public journey. Keep mechanics, authorization, and run binding authoritative on the server.

- [ ] **Step 8: Strengthen deterministic demo setup**

  Keep `seed_demo --confirm` development-only and idempotent. Ensure its output documents login, Events entry, blank-project option, and manual acceptance steps. Do not fabricate production provisioning.

- [ ] **Step 9: Update docs with verified facts only**

  Record resolved Gap Matrix items, manual commands, explicit run behavior, remaining policy/open/out-of-scope items, and recommended tag `poc-v1`; remove the deferred read-only issue only after owner/reviewer browser evidence exists.

- [ ] **Step 10: Run targeted and full verification**

  Run in order:

  ```bash
  pytest tests/browser/test_poc_v1_student_journey.py -q -m browser
  pytest -q -m 'not browser'
  pytest tests/browser -q -m browser
  python3 manage.py check
  python3 manage.py makemigrations --check --dry-run
  python3 manage.py migrate --plan
  git diff --check
  ```

  Expected: all tests PASS; checks exit 0; no unexpected migration.

- [ ] **Step 11: Commit Batch 4**

  ```bash
  git add README.md docs projects tests templates
  git commit -m "test: reconcile poc v1 student product journey"
  ```

- [ ] **Step 12: Task verification**

  Run: `pytest -q`

  Expected: all non-browser default tests PASS; browser suite has already passed explicitly.

---

## Final branch review and merge

- Build a whole-branch review package from `65926249c95627696e39a26e3eda5d50bdd0bdea` to final HEAD.
- Review product gaps as well as code: P0=0; P1=0 or explicit policy-open only; browser blockers=0; Critical=0; Important=0.
- Fix Critical/Important findings in one RED→GREEN pass and rerun full verification.
- If all exit criteria remain green, fast-forward or clean-merge `stabilize/poc-v1-product-reconciliation` into `main`, run the full verification again on main, remove only this worktree, prune, and delete the stabilization branch with `git branch -d`.
- Do not push, tag, deploy, force-delete, or resolve semantic conflicts with whole-file ours/theirs.
