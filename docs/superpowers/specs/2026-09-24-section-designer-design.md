# Section Designer for POC V1 — Design

## Intent and scope

Students need to see the section they are defining, understand its calculated properties, save it, and assign it to a physical member. The existing rectangle form remains supported. A new editor exposes non-overlapping rectangle components with H/I, T, and box starting layouts plus free placement. This implements the two-stage correction requested after the manual product check.

The student Project owner is the author. Manager and Developer review behavior stays unchanged. The existing section service and pure mechanics engine remain authoritative. Overlapping components remain rejected under open decision O-005. No Euler risk, material-strength decision, new solver behavior, or schema migration is included.

## Student flow

From a Workspace, **管理材料与截面** leads to the owner's section list. **新建矩形截面** opens the existing form with a dimensioned SVG and read-only calculated properties. **新建组合截面** opens a form with a section name and repeatable rectangle rows. Each row has width, height, center X/Y, angle, and density in existing units. Students can add/remove rows, start from H/I, T, or box examples, and adjust every value. A change updates the SVG and sends the definition to the existing `/projects/{id}/sections/preview/` endpoint. The response supplies area, centroid, Ix/Iy, mass per length, and coordinate-axis strong/weak labels. Invalid input clears the previous result and shows an actionable message. Saving returns to the section list; reopening the section restores its components. Workspace reload includes the new section in both the new-member and selected-member choices.

The examples create touching, non-overlapping rectangles. The free editor does not silently merge overlapping areas. On save, the server validates the formset, calls `create_section` or `update_section`, and converts `OVERLAP_UNSUPPORTED` into a student-facing error. Preview and save use the same existing mechanics service; numeric values are never calculated independently in JavaScript.

## Boundaries and interfaces

- `materials/forms.py`: component form and validated formset; decimal fields become the existing `section-definition-v1` composite component shape.
- `materials/views.py`: owner-scoped composite create/edit; dispatch edit by persisted `section_type`; existing rectangle flow remains.
- `templates/materials/`: list, rectangle, and composite editor markup with an accessible preview status and SVG.
- `materials/static/materials/section-designer.js`: input collection, example layouts, repeatable rows, SVG rendering, and preview request. All values are transient until a normal form POST succeeds.
- Existing `projects.views.section_preview`, `materials.services`, and `mechanics.sections` stay unchanged.

## Errors, safety, and accessibility

The server rejects zero/non-finite dimensions, empty component sets, overlap, and unauthorized authors. No invalid definition is persisted. The client clears stale numeric feedback while an edit is incomplete and ignores older preview responses after newer input. Each row has visible labels; buttons have text names; preview messages use `role="status"` or `role="alert"`. The SVG has an accessible label. The graphical preview is supplementary to numeric dimensions and properties.

## Acceptance

1. A rectangle edit shows its shape and authoritative properties, and responds to changed dimensions without saving.
2. H/I, T, and box examples produce non-overlapping component layouts and successful preview responses.
3. A student can create, reopen, edit, and assign a free non-overlapping composite to a member through public controls.
4. Overlap, missing rows, malformed values, and unauthorized access do not save a section and show an actionable state.
5. Existing rectangle and full student-journey tests stay green; solver and mechanics files do not change.
