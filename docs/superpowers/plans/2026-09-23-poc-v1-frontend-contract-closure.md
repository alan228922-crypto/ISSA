# POC V1 Frontend Contract Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the five confirmed P1 and two confirmed P2 frontend contract gaps without changing mechanics, topology semantics, persistence models, or unresolved policy.

**Architecture:** Keep the existing authoritative workspace state and snap resolver. Add transient CAD presentation fields to that state, a single student-label resolver, selection observers for teaching-panel focus, and a pure workflow projection from persisted bootstrap/API facts. Implement in three independently testable batches, then reconcile documentation only after all gates pass.

**Tech Stack:** Django 5, server-rendered templates, Vanilla JavaScript ES modules, SVG, pytest, pytest-django, Playwright Chromium.

**Spec:** `docs/specs/STUDENT_LEARNING_WORKSPACE_UX.md` plus the approved request “POC V1 FRONTEND CONTRACT CLOSURE”.

## Global Constraints

- Scope is exactly P1-01 through P1-05 and P2-01 through P2-02 from the approved closure request.
- Mechanics changed = NO; do not modify `Truss2DSolver`, idealization, Connection semantics, units, supports, or numerical results.
- `Intersection != Connection`; transient preview and markers never mutate draft topology.
- Student-facing default copy is Simplified Chinese; use “预测” and “近似零力”.
- Internal client keys remain valid for state, DOM data attributes, and APIs but not primary student copy.
- Prediction and Reflection remain soft gates.
- O-001 remains open; do not implement Euler behavior.
- No push, tag, latest-run fallback, or new persistence.

## Review Focus

- Pointer leaves the SVG or a view redraw occurs during a partial member: transient visuals must clear or redraw without becoming topology.
- A snapped intersection coincident with an explicit Connection must not show the unconnected-crossing warning.
- Repeated panel/canvas focusing must not recursively emit selection changes.
- Historical successful runs must not mark current-draft analysis complete when their source version is stale.
- Read-only workspaces and projects with no prediction/run must still project exactly one current stage and preserve soft-gate wording.

---

### Task 1: CAD transient visual contract and unified Esc

**Files:**
- Modify: `projects/static/projects/workspace/state.js`
- Modify: `projects/static/projects/workspace/renderer.js`
- Modify: `projects/static/projects/workspace/modeling-interaction.js`
- Modify: `projects/static/projects/workspace/workspace.css`
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Consumes: existing `resolvePointerPoint(...)`, `canvasController.replaceState(state)`, and canonical draft objects.
- Produces: `state.cad.preview`, `state.cad.snapFeedback`, and one `cancelCommand()` path used by every Esc handler.

- [ ] Add Playwright tests that select a member start, move the pointer, and assert `[data-cad-member-preview]` exists while member count is unchanged; assert NODE/INT/GRID marker text and position; assert the INT warning and unchanged Connection count.
- [ ] Add Esc regression tests for coordinate Node input and partial Member input; after Esc assert SELECT is active, transient layers are absent, and a real canvas click creates nothing.
- [ ] Run the new tests and confirm failures are caused by absent preview/markers and inconsistent coordinate-field Esc.
- [ ] Extend the existing CAD state with immutable transient presentation data and render a non-interactive SVG overlay (`pointer-events="none"`) after the world geometry.
- [ ] Reuse the resolver result from pointer movement to populate preview and marker; derive the warning only from an `INT` result whose location has no explicit Connection.
- [ ] Centralize cancellation so it clears inputs, member start, preview, snap feedback, CAD origin, active command, and selects `SELECT`.
- [ ] Run targeted browser tests, inspect at 1024×768, 1280×800, and 1440×900, then commit Batch A.

### Task 2: Teaching presentation, labels, and two-way focus

**Files:**
- Create: `projects/static/projects/workspace/labels.js`
- Modify: `projects/static/projects/workspace/renderer.js`
- Modify: `projects/static/projects/workspace/results.js`
- Modify: `projects/static/projects/workspace/prediction.js`
- Modify: `projects/static/projects/workspace/canvas-interaction.js`
- Modify: `templates/projects/workspace.html`
- Modify: `projects/static/projects/workspace/workspace.css`
- Test: `tests/browser/test_workspace.py`
- Test: `tests/browser/test_poc_v1_student_journey.py`

**Interfaces:**
- Consumes: canonical draft order and existing `selectedObject` state.
- Produces: `createStudentLabelResolver(draft)` and additive `canvasController.subscribeStateChange(handler)`; result items expose `data-teaching-member` for focus.

- [ ] Add failing browser/module tests for stable labels `节点 N1 / 构件 M1 / 连接 C1 / 支座 S1 / 荷载 L1`, “近似零力”, Chinese “预测”, and the exact stale-result consequence/next action.
- [ ] Add a failing MIXED rendering test with two segment evidence rows and the frozen beginner explanation.
- [ ] Add a failing selection test: canvas member selection focuses/scrolls the corresponding Result, Compare, or Explain item; repeated selection emits no loop.
- [ ] Implement one stable-order label resolver and use it in renderer, Prediction, Level One, Compare, Explain, and relevant accessibility labels.
- [ ] Render `actual.actual_state === "MIXED"` with segment labels, student state labels, and force evidence while preserving backend comparison truth.
- [ ] Replace the single canvas state-change handler slot with additive subscribers; keep property rendering and add a teaching-panel subscriber that only focuses existing items and never writes selection.
- [ ] Run targeted tests and the full student journey, inspect panel focus behavior at all three viewports, then commit Batch B.

### Task 3: Keyboard navigation and persisted workflow projection

**Files:**
- Modify: `templates/projects/workspace.html`
- Modify: `projects/static/projects/workspace/canvas-interaction.js`
- Modify: `projects/static/projects/workspace/workflow-progress.js`
- Modify: `projects/static/projects/workspace/run-context.js`
- Modify: `projects/workspace.py` only if an already-authoritative persisted fact must be exposed in bootstrap
- Modify: `projects/static/projects/workspace/workspace.css`
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Consumes: persisted draft existence/version, loaded Prediction state, explicit AnalysisRun metadata/source draft version, and Reflection state.
- Produces: `projectWorkflow({draft, prediction, runs, selectedRun, reflection})` returning all five display states with no event-history dependence.

- [ ] Add failing keyboard tests for Zoom In/Out buttons, arrow-key pan on the canvas, keyboard-reachable Fit, and semantic status announcements.
- [ ] Add failing projection tests for blank, saved, prediction, current successful run, stale-only run, and reflection states; assert at most one `aria-current="step"` after reload.
- [ ] Wire named keyboard controls to existing `dispatchViewEvent`; give the canvas an explicit keyboard-pan label and status regions appropriate `role="status"`/`aria-live` semantics.
- [ ] Replace event-history setters with one pure projection function and re-project whenever Prediction, run list/selection, or Reflection authoritative state changes.
- [ ] Keep optional stages visibly optional/available rather than hard prerequisites and never treat stale historical runs as current analysis completion.
- [ ] Run targeted browser tests and viewport inspections, then commit Batch C code.

### Task 4: Governance, review, verification, and integration

**Files:**
- Modify: `README.md`
- Modify: `docs/specs/README.md`
- Modify: `docs/specs/MASTER_SPEC.md`
- Modify: implementation status documentation directly related to this closure
- Test: all required suites

**Interfaces:**
- Consumes: verified code/test results and unchanged O-001 status.
- Produces: one consistent status: `POC V1 FRONTEND CONTRACT COMPLETE — MANUAL PRODUCT ACCEPTANCE PENDING`.

- [ ] Record Euler success-criterion blocking as `SPEC_CONFLICT` under O-001 without changing O-001 or implementing Euler.
- [ ] Update all status surfaces only after targeted tests are green; commit documentation reconciliation.
- [ ] Run `pytest -q -m 'not browser'`, `pytest tests/browser -q`, `python3 manage.py check`, `python3 manage.py makemigrations --check --dry-run`, and `git diff --check`.
- [ ] Generate a whole-branch review package and perform a fresh review against all seven gaps; fix every Critical/Important finding with RED→GREEN tests.
- [ ] Re-run the full verification on the feature branch.
- [ ] If and only if all gates pass, merge to `main`, re-run fresh full verification on merged `main`, remove the worktree, prune, and delete the feature branch with `git branch -d`.

