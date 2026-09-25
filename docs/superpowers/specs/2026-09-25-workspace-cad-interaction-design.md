# Workspace CAD interaction redesign

Date: 2026-09-25

## Intent and scope

Make the existing student Truss2D workspace usable with direct node interaction, CAD-style selection, and keyboard deletion. This is one coordinated interaction change across the canvas controller, editor reducer, renderer, and browser tests. Preserve the canonical mechanics units (mm/N/MPa/g), solver model, analysis snapshots, and the rule that a geometric crossing is not a joint until a student explicitly places a node there.

The current worktree contains uncommitted changes from the previous node/joint implementation. They are the baseline for this design, not a request to discard or overwrite them. The pre-existing README change is unrelated.

## Current defects and boundaries

- `canvas-interaction.js` stores one `selectedObject`. Every left-button pointer drag pans. It has no Delete/Backspace handling or marquee selection.
- `editor.js` blocks member deletion when an automatically created `Connection` references it. The property-panel Delete button and the future keyboard shortcut must share one command.
- The shipped `GRID_SPACING` and `gridNearest` still use 100 mm. That contradicts the approved 1 mm logical grid decision. Changing the constant alone would make the current line-per-cell renderer produce excessive SVG DOM.
- The node tool can silently reuse a nearby existing node or snap multiple clicks to the same 100 mm coordinate. A controlled browser test proves blank-node creation and crossing-node creation can work; the user's exact failed gesture is not yet reproduced. Diagnostics and tests must distinguish click, drag, existing-node hit, read-only/stage state, and grid snap.
- Support and load tools accept only the `Connection` marker. The student-facing target must be a node, while the stored `target_connection_client_key` remains an internal truss compatibility detail.

## Selected approach

Use the existing physical draft schema and idealization seam. Do not migrate stored supports/loads to geometry-node foreign keys and do not add a second snap resolver. Introduce a thin node-to-joint command boundary in the editor; the UI acts on nodes and resolves/creates the internal connection when a node lies on one or more physical members. For selection and deletion, extend the current canvas state and centralize mutation in one transaction-like editor action. Use efficient grid patterns with visual LOD while keeping one 1 mm logical spacing authority.

The alternative of changing the persisted schema to node-targeted supports/loads would require migration of drafts and analysis/report references without improving the immediate student workflow. The alternative of keeping the 100 mm grid and only changing messaging would not satisfy the previously frozen grid decision or the reported inability to place nearby nodes. Neither is selected.

## 1. Selection and gestures

Maintain `selectedObjects` as an ordered set of stable `(kind, clientKey)` identities and `selectedObject` as the primary item for existing property and report consumers. Selection is ephemeral UI state and is never saved in the physical draft. Render all selected objects with a consistent highlight; the property panel shows primary-object details and a selected-count summary for multi-selection. Prediction consumers that currently require a `CONNECTION` selection resolve a selected geometry node to its unique internal connection through one adapter; prediction payload and persisted identifiers remain unchanged.

In SELECT mode only, a left-button drag beyond a small screen-pixel threshold creates a marquee. Drag from right to left means crossing selection: a member is included when its displayed segment intersects the rectangle. Drag from left to right means window selection: both displayed member endpoints must be within the rectangle. Point-like objects (nodes, supports, loads) are included when their screen position lies inside either rectangle. The marquee is a fixed-size overlay and does not mutate topology or pan the viewport. Its selection semantics use screen-space geometry after the current view transform. The visual connection marker maps to its geometry node for student-facing selection, not to a second selectable joint object.

A plain click replaces selection; Shift-click and Shift-marquee add/toggle without duplicates; clicking blank canvas clears selection; Escape clears selection when no drawing command is active. Left dragging in NODE/MEMBER/SUPPORT/LOAD mode is not a selection gesture. Middle-button drag or Space+left-button drag pans in any mode; wheel zoom and Fit retain their existing meanings. Pointer capture and click suppression after a completed drag prevent accidental node/member creation.

## 2. Shared delete command

Delete and Backspace invoke the same batch-delete command as the right-panel button, only in an editable build workspace with nonempty selection. Text, number, select, textarea, and contenteditable focus must keep native editing behavior; shortcuts never delete model objects there. One user command yields one immutable draft update and one dirty transition; this scope does not add undo.

Batch deletion first removes explicitly selected loads and supports, then selected members, then selected nodes that are safe to remove. For each deleted member, remove its ID from participating connections. Remove a connection only when it has no remaining participating members and no surviving load or support. Preserve a shared node/connection when any surviving member depends on it. If deletion would strand a support or load, or would require deleting an unselected member because its endpoint node was selected, reject the whole command with a concrete dependency list; never silently cascade to those objects. A selected node with no dependent member can be deleted together with its now-unused internal connection. This behavior must be deterministic and atomic for multi-selection.

After success, remove deleted identities from selection. After failure, preserve both draft and selection. Saved revisions and existing analysis snapshots remain untouched; user must save the draft to persist deletion.

## 3. Node placement and 1 mm grid

Keep one global-origin 1 mm logical grid authority and reuse the existing GRID snap resolver. Explicit numeric coordinates keep decimals; GRID snap moves coordinates to integer mm only when enabled. NODE and INT snap retain priority and their existing tolerance. ORTHO preserves the locked axis exactly, including decimal starts, and snaps only the moving axis. Fit uses model bounds, not grid spacing.

Replace per-line SVG grid generation with three SVG patterns and one grid background rectangle. Minor/medium/major hierarchy is 1/10/100 mm. Show a level when its spacing projects to at least 8 CSS pixels, except retain the major level at every zoom. Visual LOD never changes logical snap or creates topology. No pointermove may rebuild an SVG element count proportional to the visible millimetres.

NODE click on blank canvas creates a visible geometry node at the resolved point. On an existing node, it explicitly activates its joint when members pass through it and reports that the existing node was used; it must not mark the draft dirty for a no-op. Clicking an intersection creates one node and an internal pin joint for the participating members; merely crossing members creates neither. Duplicate same-coordinate nodes must not be silently layered. When a gesture cannot place a node because of stage, read-only state, invalid coordinate, or object hit, the interface gives a specific reason.

## 4. Supports and loads target nodes

The student clicks a visible geometry node or its joint marker. The command resolves its internal connection (creating one only when at least one physical member geometrically participates), then creates support or load using the existing `target_connection_client_key`. A disconnected node is rejected with an instruction to attach a member first; no invisible load-bearing topology is invented. Existing drafts with explicit connections remain readable and editable. Only one internal connection per geometry node is used for these commands; duplicate legacy connections at one node produce a specific error and no mutation, never an arbitrary target.

Support/load creation and selection remain possible after a new member, save, and reload. Their type/value property controls remain unchanged. Truss idealization still creates shared analysis nodes only from explicit internal connections, and no rigid joint or frame DOF is introduced.

## Verification and acceptance

Write failing tests before each behavioral change. Cover both reducer/geometry behavior and browser gestures:

1. Blank click creates one node; repeated close clicks with 1 mm snap create distinct intended coordinates; existing-node click gives visible feedback without duplicate/dirty mutation; numeric decimal and INT placement persist after save/reload.
2. Crossing members remain disconnected until node placement. Placing that node yields one joint participating in both physical members and the expected idealization segments.
3. Support/load can be placed by clicking a member-attached node; isolated-node attempt gives a clear error; save/reload preserves targets and property editing.
4. Left-to-right window excludes a member with one endpoint outside; right-to-left crossing includes any member segment touching the rectangle. Shift selection, blank click, Escape, zoom, Fit, middle/Space pan, and no accidental click after drag all work.
5. Delete/Backspace and panel Delete invoke equivalent behavior. Input-focused keys do not delete. Single and multi-delete correctly prune auto-joint participation, preserve shared joints, and reject a dependency conflict atomically. Save/reload reflects successful deletions.
6. The 1/10/100 mm visual hierarchy changes with zoom without affecting the same pointer's snap result. A large viewport does not produce line DOM proportional to its millimetre span. Mechanics benchmarks, model check, analyze, and `Intersection != Connection` remain green.

Run targeted browser tests first, then all workspace/browser tests, `pytest -q -m 'not browser'`, `pytest tests/browser -q`, Django system/migration checks, and `git diff --check`. Report any existing failures separately from new regressions. No Solver or mechanics contract changes are authorized.
