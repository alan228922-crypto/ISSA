# CAD Interaction Model V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the full beginner-friendly CAD-like 2D drafting interaction contract without altering mechanics or persisted geometry semantics.

**Architecture:** Extend existing Canvas and Modeling controllers as one shared-state orchestration seam. Add local draft history at the existing editor-action boundary. Keep `resolvePointerPoint` the sole snap authority and update only transient presentation DOM on pointermove.

**Tech Stack:** Django templates, vanilla JS ES modules, SVG, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-26-cad-interaction-model-v1-design.md`; authoritative Product Owner brief attached to the 2026-09-26 request.

## Global Constraints

- Mechanics, Solver, canonical mm/N/MPa/g, analysis snapshots, and physical-draft schema unchanged.
- One global-origin `GRID_SPACING = 1` authority; decimal numeric inputs and exact ORTHO locked axis retained.
- `Intersection != Connection`; snap/tracking/preview never mutate topology.
- Student-facing labels in simplified Chinese; no ribbon, layers, UCS, or generic FEM.
- No full workspace rerender, server request, or DOM proportional to visible millimetres on pointermove.
- Preserve pre-existing worktree changes; stage only reviewed feature paths/hunks.

## Review Focus

1. A drawing command with first endpoint survives middle pan and wheel zoom — Batch 1 real-input browser test.
2. An editable input keeps native Space/Enter/Delete/Undo behavior — Batches 1 and 4 browser tests.
3. Shift's temporary ORTHO never modifies the persistent toggle or Shift-select — Batches 1 and 3 tests.
4. Grip drag preserves node/member/connection identities and rejects invalid edits without dirtying — Batch 3 test.
5. Cross-save undo uses the latest draft version and cannot mutate historical runs — Batch 4 test.

---

## File map

- `canvas-interaction.js`: gesture priority, navigation, hover, selection, overlap chooser, grip pointer lifecycle.
- `modeling-interaction.js`: command state, repeat/Esc, temporary ORTHO, snap/tracking/dynamic-input orchestration.
- `renderer.js`: bounded transient snap/tracking/grip presentation and selected/hovered visuals.
- `geometry.js`: existing sole resolver with object-snap enablement supplied by caller.
- `state.js`: history snapshots, undo/redo, save checkpoint and current-version restoration.
- `properties.js`: double-click focus and history-aware property/delete updates.
- `templates/projects/workspace.html`, `workspace.css`, `ux-v2.css`: status controls and pointer-local dynamic input.
- `tests/browser/test_workspace.py`: real pointer/keyboard/wheel acceptance; `docs/specs/STUDENT_LEARNING_WORKSPACE_UX.md`: product contract.

### Task 1: Navigation and command lifecycle

**Interfaces:** Canvas controller supplies `setFitHandler(callback)` and transparent middle-pan; Modeling controller manages last completed tool, command cancellation, and temporary ORTHO. State `cad.ortho` remains persistent; `cad.temporaryOrtho` is transient.

- [ ] Add failing browser tests for wheel zoom, middle pan, double-middle Fit, partial Member preserved across pan, repeat Node/Member, Esc, Enter/Space repeat and focus safety, Shift temporary ORTHO.
- [ ] Run targeted tests RED; failure must be behavioral, not fixture/setup.
- [ ] Implement pointer/keyboard lifecycle through current controllers; avoid changing drawing reducer semantics.
- [ ] Run targeted tests GREEN, inspect in browser, commit `feat: add cad navigation and command lifecycle`.

### Task 2: Precision drafting feedback

**Interfaces:** Existing `resolvePointerPoint` remains the only resolver. `cad` gains `objectSnap`, `tracking`, `dynamicInput`, and independent `gridVisible`; presentation consumes `snapFeedback`, `trackingGuide`, `preview`.

- [ ] Add failing real-input browser tests for 1 mm GRID, NODE/INT, distinct Chinese markers and crossing warning, independent Grid display/Grid Snap/Object Snap toggles, tracking 0°/90°, pointer-local Node X/Y and Member distance/angle, X/Y Tab/Enter, explicit relative ΔX/ΔY, dynamic-input toggle, and visual LOD independence.
- [ ] Run RED; implement status-bar toggles, small transient presentation, focusable dynamic inputs, and coordinate entry without another resolver.
- [ ] Run GREEN; check 500×500, 1000×1000, 2000×1000 mm view DOM/performance; commit `feat: add precision drafting feedback`.

### Task 3: Selection and grip editing

**Interfaces:** Canvas controller owns hover, ordered `selectedObjects`, one overlap chooser, grip preview callbacks. Node release dispatches one `UPDATE_OBJECT` via the shared editor boundary.

- [ ] Add failing browser tests for hover vs selected/result, click/Shift, left-right Window and right-left Crossing with distinct styles, two-click marquee, overlap chooser, node grip and member preview, drag identity/dependency safety, double-click property focus, Delete/Backspace dependency policy.
- [ ] Run RED; implement hover/chooser/grip and property focus, preserving current selection authority.
- [ ] Run GREEN; commit `feat: add cad selection and grip editing`.

### Task 4: Local Undo/Redo and integration

**Interfaces:** `applyWorkspaceEditorAction` records draft snapshots; `undoWorkspaceEdit(state)` and `redoWorkspaceEdit(state)` restore local drafts at current server draft version; `applyWorkspaceSaveSuccess` advances saved checkpoint without discarding local history.

- [ ] Add failing tests for create/delete/move/property/support/load undo/redo, redo invalidation, Save checkpoint and cross-save undo, editable-input shortcut safety, historical AnalysisRun isolation, command+pan and results regressions.
- [ ] Run RED; implement immutable history and keyboard/status controls; ensure one edit is one history step.
- [ ] Run GREEN; commit `feat: add local modeling undo redo`.

### Task 5: Product contract, full verification, and merge gate

- [ ] Update `STUDENT_LEARNING_WORKSPACE_UX.md` with the frozen interaction contract; add any missing real-input regression tests.
- [ ] Run all CAD tests and full UX V2 journey, `pytest -q -m 'not browser'`, `pytest tests/browser -q`, mechanics benchmarks, `python3 manage.py check`, `python3 manage.py makemigrations --check --dry-run`, and `git diff --check`.
- [ ] Inspect actual browser gestures and review diff against every Product Owner exit criterion. Record Critical/Important findings.
- [ ] Only if all criteria pass and no findings remain, clean merge/fast-forward to main, rerun fresh verification, and safely prune worktree/branch. Do not push, tag, or deploy.
