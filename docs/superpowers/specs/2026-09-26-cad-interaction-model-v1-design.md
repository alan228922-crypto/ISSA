# CAD Interaction Model V1 design

The Product Owner's 2026-09-26 CAD Interaction Model V1 brief is the authoritative behavior contract. This technical design implements it in the existing Django, vanilla-JavaScript, SVG workspace. The goal is beginner-friendly CAD-like precision interaction, not an AutoCAD clone. Mechanics, canonical units (mm/N/MPa/g), physical-draft schema, analysis revisions, and `Intersection != Connection` remain unchanged.

## Existing base and boundaries

`feat/workspace-cad-interaction` contains the current student workspace, 1 mm grid authority, node-facing support/load commands, and selection/delete. A distinct `feat/grid-1mm` worktree remains, but the current branch already has the 1 mm grid and bounded SVG patterns. Existing unrelated dirty files are preserved. No merge or reset is needed as a prerequisite.

The single pointer orchestration seam remains `bindCanvasInteractions`: it owns gesture priority, view navigation, hit testing, hover, selection, grip drag, overlap choice, and keyboard navigation. `bindModelingInteractions` owns command lifecycle, pointer resolution, transient drafting feedback, dynamic input, and tool toggles. Both share one workspace state and one `resolvePointerPoint` authority. Existing `applyWorkspaceEditorAction` is the only local draft mutation boundary; it gains local history. No large SPA rewrite or new server API is introduced.

## Interaction priority and command lifecycle

Input priority is middle-button/Space navigation, active grip, active modeling command, selection/hit-test, then empty canvas. Pan and wheel are transparent to a partially completed member command. Esc cancels transient interaction and returns to SELECT without deleting committed geometry. Completed Node/Member placements leave their tool active. After a completed drawing action, Enter or Space outside editable controls repeats the last tool. Text inputs and browser-reserved keys retain native behavior. Shift temporarily inverts ORTHO only while drawing; it remains additive selection in SELECT.

## Precision drafting

Logical 1 mm GRID Snap and visual grid display are independent booleans. NODE/INT object snap can be toggled separately from GRID, but all resolution still runs through `resolvePointerPoint`; disabled candidate classes are filtered before resolution. ORTHO locks the original axis exactly, including decimals, and GRID snaps only the moving axis. Three existing 1/10/100 mm SVG patterns remain bounded and zoom-aware.

Pointer-local dynamic input shows Node X/Y or Member length/angle, with keyboard focusable X/Y and distance/angle fields. The precision area also offers explicit relative ΔX/ΔY fields; `@dx,dy` remains an optional shortcut. NODE, INT, GRID markers and tooltips are Chinese and visually distinct; INT without a Connection warns that the crossing is not yet connected. Acquired NODE/INT points can show 0°/90° visual tracking lines. Preview/marker/tracking layers are pointer-transparent and never mutate topology. Pointermove updates only the small CAD presentation layer, not the entire workspace.

## Selection and editing

Existing click, Shift-click, two-click marquee, and held-drag marquee remain. Window selection fully contains; Crossing selection touches. Their visual styles differ. Hover is a visual-only preselection state. When more than one eligible object is under a pointer, a small student-readable chooser resolves the ambiguity before selection; it does not invent a second selection state. A selected node gets a grip. Grip drag previews attached member geometry, then commits one `UPDATE_OBJECT` node-coordinate action on release. No endpoint, identity, or Connection is created. Property double-click opens and focuses the right panel. Delete/Backspace continue to use the shared dependency-safe reducer action.

## Local history and save boundary

Every successful modeling reducer action records one local draft snapshot; no-op and navigation actions do not. Undo/Redo operate only on the current browser editing session's draft, not AnalysisRun/ModelRevision/Report. Save updates the checkpoint and draft version but retains local undo history; a cross-save undo restores geometry into the current draft version and marks it dirty, so a subsequent Save creates a new revision rather than rolling back a server revision. New editing after undo clears redo. Selection is pruned when its object no longer exists. Undo shortcuts are disabled in editable controls. Status text exposes unsaved changes.

## Acceptance

Four independently testable batches: (1) navigation and command state; (2) precision controls, feedback, tracking, dynamic input; (3) hover, selection, chooser, grip, property focus; (4) history and integration. Each batch uses failing real-input Playwright tests before implementation, then targeted tests and a logical commit. Final verification includes all browser journeys, nonbrowser tests, Django and migration checks, mechanics benchmarks, diff check, and hands-on browser inspection. Merge to main is permitted only with all exit criteria green and no Critical/Important review findings.
