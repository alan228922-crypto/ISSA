# Structural Sketch Visual Language V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing student Canvas read like a structural-mechanics textbook sketch while preserving all Draft, CAD, and mechanics contracts.

**Architecture:** `renderer.js` retains layer ordering and state orchestration; a new `structural-symbols.js` creates read-only screen-sized SVG symbols and shared definitions. Existing selectable wrappers and CAD hit-routing remain the sole interaction authority; student-facing Support/Load controls map to existing codes.

**Tech Stack:** Django templates, browser-native JavaScript/SVG/CSS, pytest + Playwright browser tests.

**Spec:** `docs/superpowers/specs/2026-09-28-structural-sketch-visual-language-design.md` and the Product Owner's attached Structural Sketch Visual Language V1 brief.

## Global Constraints

- Base `main` HEAD is `d2e2308ad42322e985c0e5cef48b908a9b760444`; work only in `feat/structural-sketch-visual-language` and its isolated worktree.
- No changes to Solver, mechanics, support/load semantics, Physical Draft domain, ModelRevision, or AnalysisRun.
- Preserve Intersection != Connection and 1 mm logical Grid/Snap authority.
- All visible student terminology is simplified Chinese; do not show internal identity in primary Canvas labels.
- Decorative SVG children use `pointer-events="none"`; retain one hit target per selectable object.
- No analyzable fixed support, distributed load, or moment objects.
- Do not merge, push, tag, or deploy; stop at owner visual review.

## Review Focus

1. A Member with one missing endpoint renders only a truthful known-end fragment or inventory entry, never a fabricated endpoint; pin this in Task 2.
2. A Support/Load whose Connection exists but has no geometry node stays selectable from the incomplete inventory and does not crash rendering; pin this in Task 3.
3. A combined positive/negative Fx/Fy load produces two correctly oriented arrows whose arrowheads share the true anchor and whose absolute-magnitude labels do not cover nodes/supports, without changing saved values; pin this in Task 4.
4. Selection and hover while a result overlay is active leave the body force-state color/dash intact; pin this in Task 5.
5. At far zoom and small responsive viewports, symbols remain readable while secondary labels may hide and hit regions remain stable; pin this in Task 6.

---

### Task 1: Isolate the structural symbol seam

**Files:**
- Create: `projects/static/projects/workspace/structural-symbols.js`
- Modify: `projects/static/projects/workspace/renderer.js`
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Produces `structuralSymbolDefs() -> SVGElement` and `renderNode(node, point, unit, visualState)`, `renderMember(member, start, end, unit, visualState)`, `renderConnection(connection, point, unit, visualState)`, `renderSupport(support, point, unit, visualState)`, `renderLoad(load, point, unit, visualState)` returning child SVG groups or shapes.
- `renderer.js` owns the existing `selectable()` wrapper, world transform, student labels, and layer order; symbol helpers never mutate Draft or create a second point resolver.

- [ ] **Step 1: Write RED tests** asserting helper-backed symbol groups exist, are anchored at the existing world coordinates, use a single shared defs subtree, and keep `data-object-kind`/`data-client-key` wrappers.
- [ ] **Step 2: Run** `pytest tests/browser/test_workspace.py -q -k structural_symbol_seam` and confirm expected failures.
- [ ] **Step 3: Extract symbol construction** behind the named functions without changing appearance or Canvas behavior; keep grid/CAD presentation in `renderer.js`.
- [ ] **Step 4: Rerun targeted tests** and existing renderer/CAD tests until green.
- [ ] **Step 5: Commit** `refactor: isolate structural sketch symbol renderer`.

### Task 2: Node, Member, Connection grammar

**Files:**
- Modify: `projects/static/projects/workspace/structural-symbols.js`
- Modify: `projects/static/projects/workspace/renderer.js`
- Modify: `projects/static/projects/workspace/workspace.css`
- Modify: `templates/projects/workspace.html` (remove inline universal selection styling)
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Consumes Task 1 helpers and the existing `screenUnit()` conversion; result overlay remains read-only presentation input.
- Produces hollow node, dark member body, explicit connection ring, and independent hit/hover/selection layers.

- [ ] **Step 1: Write RED tests** for 14 px hollow node, initial roughly 3 px member, center-to-center endpoints, explicit marker only, crossing without marker, and incomplete Member with a missing endpoint. At visual review compare the clean line with a thin outlined bar; neither visual width may affect geometry, snap, or mechanics.
- [ ] **Step 2: Run** `pytest tests/browser/test_workspace.py -q -k structural_node_member_connection` and confirm failures.
- [ ] **Step 3: Implement** the symbols with screen-aware units; keep unresolved objects in Properties when no truthful Canvas position exists.
- [ ] **Step 4: Run targeted tests** plus node/member/connection selection and intersection tests.
- [ ] **Step 5: Commit** `feat: draw textbook nodes members and connections`.

### Task 3: Pinned and global-axis roller supports

**Files:**
- Modify: `projects/static/projects/workspace/structural-symbols.js`
- Modify: `projects/static/projects/workspace/renderer.js`
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Consumes existing `support_type` and `restrained_axis`; `PINNED` means both axes restrained, `ROLLER`+`Y` ground roller, `ROLLER`+`X` 90° wall roller.
- Produces shared hatch defs, triangle/base/wheels/wall glyphs, and independent selection hit region.

- [ ] **Step 1: Write RED tests** for pinned textbook triangle/hatch, Roller Y two wheels and ground, Roller X vertical wall, one shared hatch definition, pointer-events isolation, a click on a Roller wheel not selecting/creating a Node, and missing target-node safety.
- [ ] **Step 2: Run** `pytest tests/browser/test_workspace.py -q -k structural_support_symbol` and confirm failures.
- [ ] **Step 3: Implement** anchored, screen-sized support glyphs using reusable defs; ensure the node symbol remains visible over the support.
- [ ] **Step 4: Rerun targeted tests** and existing support semantics tests.
- [ ] **Step 5: Commit** `feat: draw pinned and roller support symbols`.

### Task 4: Concentrated load grammar and previews

**Files:**
- Modify: `projects/static/projects/workspace/structural-symbols.js`
- Modify: `projects/static/projects/workspace/renderer.js`
- Modify: `projects/static/projects/workspace/modeling-interaction.js`
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Consumes current `fx_N`/`fy_N` and CAD transient state; no new Draft action or load type.
- Produces separate red Fx/Fy arrows, absolute value + `N` labels, and temporary Load-tool pointer preview that never enters Draft/save/solver.

- [ ] **Step 1: Write RED tests** for each sign of Fx/Fy, arrowheads at the true target anchor, combined components with non-overlapping labels, `20 N` label, zero-component behavior, immediate property-edit rerender, and preview disappearing on cancel/leave without a Draft mutation.
- [ ] **Step 2: Run** `pytest tests/browser/test_workspace.py -q -k structural_load_symbol` and confirm failures.
- [ ] **Step 3: Implement** load symbols/offset labels and render the pointer preview only in CAD presentation state.
- [ ] **Step 4: Rerun targeted tests** and existing load/save/undo tests.
- [ ] **Step 5: Commit** `feat: draw component load arrows and previews`.

### Task 5: Student controls, hover, selection, and hit regions

**Files:**
- Modify: `templates/projects/workspace.html`
- Modify: `projects/static/projects/workspace/modeling-interaction.js`
- Modify: `projects/static/projects/workspace/properties.js`
- Modify: `projects/static/projects/workspace/workspace.css`
- Modify: `projects/static/projects/workspace/structural-symbols.js`
- Test: `tests/browser/test_workspace.py`

**Interfaces:**
- Three illustrated Support choices map to existing `PINNED`, `ROLLER_Y`, `ROLLER_X` data; Load choice remains concentrated force with explained Fx/Fy inputs.
- Hover and selected overlays are independent from member result body color/dash; transparent hit targets remain in each existing selectable wrapper.

- [ ] **Step 1: Write RED tests** for student labels and code mapping, 22–28 px Node/comfortable Member hit target, hover vs selected, result overlay unchanged during selection, and decorative pointer-event isolation.
- [ ] **Step 2: Run** `pytest tests/browser/test_workspace.py -q -k structural_palette_selection` and confirm failures.
- [ ] **Step 3: Implement** illustrated cards, explanatory property labels, and overlay CSS/SVG while retaining keyboard and CAD routing.
- [ ] **Step 4: Rerun targeted tests** and selection/Delete/Undo/Redo regressions.
- [ ] **Step 5: Commit** `feat: refine structural tool palette and selection`.

### Task 6: Visual acceptance, performance, and full regression

**Files:**
- Modify: `tests/browser/test_workspace.py`
- Modify: `docs/superpowers/specs/2026-09-28-structural-sketch-visual-language-design.md` only if implementation decisions require clarification.

**Interfaces:**
- Produces browser demo coverage for 1024×768, 1280×800, 1440×900 and near/mid/far zoom, screenshots/visual inspection notes, and test evidence.

- [ ] **Step 1: Add RED acceptance tests** for a simple truss with pinned left, Roller Y right, Roller X against a wall, downward/upward/horizontal ±/combined loads with clear true-anchor arrowheads and labels away from nodes/supports, selected Node/Member/Support, explicit Connection versus mere crossing, incomplete items, and far-zoom hit regions.
- [ ] **Step 2: Run targeted browser acceptance**; inspect the real browser image at all three viewport sizes and adjust symbol spacing/label LOD until legible.
- [ ] **Step 3: Check performance** with many repeated supports/loads: hatch/marker defs count stays fixed and pointer move does not rebuild full Workspace DOM.
- [ ] **Step 4: Run** `pytest -q -m 'not browser'`, `pytest tests/browser -q`, `python3 manage.py check`, `python3 manage.py makemigrations --check --dry-run`, and `git diff --check`; confirm no mechanics/domain files changed.
- [ ] **Step 5: Commit** `test: add structural sketch browser acceptance`; leave branch unmerged and unpushed for Product Owner visual review.
