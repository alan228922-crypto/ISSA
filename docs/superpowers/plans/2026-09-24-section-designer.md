# Section Designer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let student owners preview, create, edit, and assign rectangular and non-overlapping composite sections through public controls.

**Architecture:** Keep the existing section service and mechanics engine as the sole source of numeric properties. Add a Django formset for composite rectangle rows and a small browser module for SVG/presets/preview. Persist only through the existing owner-scoped material views.

**Tech Stack:** Django 5.2, Python, Vanilla JavaScript, SVG, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-09-24-section-designer-design.md`

## Global Constraints

- Preserve `section-definition-v1` and `section-properties-v1`.
- Only the Project owner may use the student Section Designer pages.
- Existing `materials.services` and `mechanics.sections` remain authoritative; JavaScript draws geometry but does not calculate section properties.
- Positive-area overlap is rejected under O-005. Edge contact is allowed.
- No migrations, Euler behavior, solver changes, or changed Project ownership policy.

## Review Focus

- A slow preview response for old input must not replace the result for newer input (Task 1 browser test).
- Invalid and overlap input must clear previous numeric results and leave saved sections unchanged (Tasks 1–2 tests).
- Deleting every component must not save an empty section (Task 2 endpoint test).
- An unauthorized viewer must not reach composite create/edit endpoints (Task 2 endpoint test).
- A saved composite must remain selectable after Workspace reload (Task 3 browser test).

---

### Task 1: Rectangle visual and numeric preview

**Files:**
- Create: `materials/static/materials/section-designer.js`
- Modify: `templates/materials/section_form.html`
- Test: `tests/browser/test_section_designer.py`

**Interfaces:**
- Consumes: `POST /projects/{id}/sections/preview/` with the existing rectangle definition.
- Produces: `bindSectionDesigner(root)` behavior keyed by `data-section-designer`, `data-section-preview-svg`, and `data-section-properties`.

- [ ] Write a browser test that opens the real rectangle form, changes width to 2 and height to 6, and sees SVG geometry plus authoritative `A=12`, `Ix=36`, `Iy=4` without saving. Change width to 0 and assert the previous numbers disappear. Name the break: a preview implementation that displays stale or invented properties.
- [ ] Run `pytest tests/browser/test_section_designer.py::test_rectangle_preview_updates_without_saving -q`; expect failure because the preview elements are absent.
- [ ] Add the preview markup and client module. Build a `section-definition-v1` rectangle payload from visible form fields, POST using the form's CSRF token, render the returned numeric properties, draw a dimensioned `<rect>`, clear stale results on incomplete/error input, and ignore obsolete responses using a monotonically increasing request token.
- [ ] Re-run the test; expect PASS. Run `pytest tests/endpoints/test_material_pages.py -q`; expect PASS.
- [ ] Commit: `feat: preview rectangular section geometry and properties`.

### Task 2: Owner-scoped composite form and persistence

**Files:**
- Modify: `materials/forms.py`, `materials/views.py`, `materials/urls.py`
- Modify: `templates/materials/index.html`
- Create: `templates/materials/composite_section_form.html`
- Test: `tests/endpoints/test_material_pages.py`

**Interfaces:**
- Consumes: `CompositeComponentForm` rows of width/height/center X/center Y/angle/density.
- Produces: `section-definition-v1` `{type:"composite",components:[...]}` via `create_section` and `update_section`; same `section_edit` URL restores both RECTANGLE and COMPOSITE.

- [ ] Write endpoint tests for owner create/reopen/edit, overlap rejection, empty component rejection, and unauthorized GET/POST. Name the break: a composite form that saves invalid data or loses components on edit.
- [ ] Run the new tests; expect missing route/form failures.
- [ ] Add the component form and formset, owner-scoped composite create route, and edit dispatch by `section_type`. Feed only validated, non-deleted rows to the existing service. Map `OVERLAP_UNSUPPORTED` to explicit form feedback; do not persist on any error. Add list links for create/edit and a basic formset template with management fields and a row template for browser addition.
- [ ] Re-run endpoint tests and existing section application tests; expect PASS.
- [ ] Commit: `feat: author non-overlapping composite sections`.

### Task 3: Composite examples, preview, and member assignment

**Files:**
- Modify: `materials/static/materials/section-designer.js`, `templates/materials/composite_section_form.html`
- Test: `tests/browser/test_section_designer.py`
- Modify: `docs/specs/POC_V1_KNOWN_ISSUES.md` only if the existing wording needs clarification.

**Interfaces:**
- Consumes: Task 2 formset row names/management form and existing preview endpoint.
- Produces: H/I, T, and box non-overlap starting layouts plus freely editable rows; persisted COMPOSITE appears in Workspace section options after reload.

- [ ] Write browser tests that apply each example, see multiple SVG rectangles and a successful authoritative preview; create a free two-row composite, save it, return to Workspace, and assign it to a member. Test overlap displays an error and does not save. Name the break: a visually convincing designer that cannot persist or assign a section.
- [ ] Run new tests; expect missing example controls and row behavior.
- [ ] Implement row add/remove, example application, composite payload collection, rotated SVG rectangles, preview request/error handling, and numeric display in the shared client module. Keep property values from the server response only.
- [ ] Re-run browser tests; inspect 1024px and 1280px screenshots for clipped controls. Run `pytest -q -m 'not browser'`, `pytest tests/browser -q`, `python3 manage.py check`, `python3 manage.py makemigrations --check --dry-run`, and `git diff --check`; expect all green.
- [ ] Commit: `feat: complete composite section designer journey`.

## Integration

Perform a whole-branch review against the spec and O-005 boundary. Report test evidence and the feature branch. Do not merge or deploy without a separate user instruction for this new feature.
