# Draft Object Independence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permit independent deletion and incomplete current drafts while keeping analysis snapshots strict and historical runs immutable.

**Architecture:** Nullable draft FKs and explicit nullable Connection participation slots are the sole reference authority. A resource deletion service updates all affected current drafts and their versions atomically. Shared completeness preflight sits before strict snapshot/revision/Solver.

**Tech Stack:** Django 5.2, SQLite/PostgreSQL-compatible ORM migrations, vanilla ES modules, pytest and Playwright.

**Spec:** `docs/superpowers/specs/2026-09-27-draft-independence-design.md`

## Global Constraints

- Preserve `physical-draft-v1`, `physical-snapshot-v1`, canonical mm/N/MPa/g and existing solver code.
- Never mutate ModelRevision, AnalysisRun, Report, Prediction, Reflection or Reasoning on resource deletion.
- Keep owner/project permission and optimistic `draft_version` contracts.
- Use Simplified Chinese student-facing feedback; machine codes stay stable.

## Review Focus

- Simultaneous deletion of a Node and its Member: only surviving objects get null references; one undo restores both.
- Rebinding a null slot to a Member in a different Project must be rejected atomically.
- Resource deletion while another Project saves: locks and stale-version detection prevent lost updates.
- An incomplete object without canvas geometry remains selectable from Properties.
- Existing complete snapshots and historical revisions remain byte-for-byte unchanged.

---

### Task 1: Draft schema and participation migration

**Files:** `modeling/models.py`, `materials/models.py`, `modeling/migrations/0003_*.py`, `materials/migrations/0003_*.py`, `tests/application/test_draft_independence.py`.

**Interfaces:** Produces `ConnectionParticipation(connection, member, position)` and nullable draft refs. Existing `Connection.participating_members` manager remains readable for complete drafts.

- [ ] Write RED tests: direct Node/Member/Connection/Material/Section deletion preserves surviving draft entities and nulls only their links; deleted Member leaves one null participation slot; Strip survives Material deletion.
- [ ] Run `pytest -q tests/application/test_draft_independence.py`; expect failures from CASCADE/PROTECT/missing model.
- [ ] Alter editable FKs; add through model with `(connection, position)` uniqueness and project membership validation; generate migration with data copy from implicit M2M.
- [ ] Rerun targeted tests and `python3 manage.py makemigrations --check --dry-run`; expect green and no changes.

### Task 2: Save, reload and strict completeness boundary

**Files:** `modeling/services.py`, `projects/workspace.py`, `modeling/completeness.py` (new), `analysis/orchestration.py`, `modeling/snapshot.py` (only if strict guard needed), `tests/application/test_draft_independence.py`, `tests/endpoints/test_workspace.py`.

**Interfaces:** Produces `draft_completeness_issues(project) -> list[dict]`; issue dict has `code`, `severity`, `stage`, `entity_refs`, `human_message`, `physical_object`.

- [ ] RED: save/reload null refs and participation slots; rebind them; Model Check yields all requested codes and does not call snapshot; Analyze rejects before Revision/Run/Solver; historical snapshot remains unchanged.
- [ ] Run targeted tests; expect null rejection/dereference failures.
- [ ] Make save resolve nulls without accepting unknown non-null keys, serialize nulls, preflight Check/Analyze under Project lock, and keep snapshot strict.
- [ ] Run targeted and existing draft/analysis tests; expect green.

### Task 3: Shared Material/Section deletion

**Files:** `materials/services.py`, `materials/models.py`, `materials/migrations/0003_*.py`, `materials/views.py`, `materials/urls.py`, `templates/materials/index.html`, `templates/materials/delete_confirm.html` (new), `tests/application/test_draft_independence.py`, `tests/endpoints/test_material_pages.py`.

**Interfaces:** Produces `delete_resource(*, actor, resource) -> receipt`; receipt records resource identity, affected Project IDs, Member/Strip counts. POST delete route invokes it after owner authorization.

- [ ] RED: multi-project Material/Section deletion nulls every current Member/Strip, bumps each affected Project once, writes receipt, preserves historical snapshots, denies foreign actor and GET mutation.
- [ ] Run targeted tests; expect failure from PROTECT/missing service/routes.
- [ ] Implement transaction and deterministic Project locks; clear refs, bump versions, audit, delete; add impact confirmation and POST route.
- [ ] Show retained Strips with “未指定” material and provide an owner-scoped material rebind form.
- [ ] Run targeted and material-page tests; expect green.

### Task 4: CAD atomic delete, rebind and feedback

**Files:** `projects/static/projects/workspace/editor.js`, `properties.js`, `renderer.js`, `modeling-interaction.js` (only null safety), `tests/browser/test_workspace.py`.

**Interfaces:** `DELETE_OBJECTS` nulls refs on surviving objects, preserving null participation array positions; `UPDATE_OBJECT` can rebind each nullable relation. Both keyboard and button use one deletion path.

- [ ] RED browser tests: delete with dependents, confirm impact, Undo identity/relations, save/reload, select incomplete via object list, rebind Member/Connection/Support/Load and Material/Section.
- [ ] Run targeted browser tests; expect old dependency conflict and missing controls.
- [ ] Implement pure editor transformations, Properties choices and object list, nonblocking confirmation/feedback, and null-safe canvas behavior.
- [ ] Run targeted browser tests and existing workspace browser suite; expect green.

### Task 5: Full regression and review

**Files:** Any narrow fixes evidenced by failing tests; no mechanics changes.

- [ ] Run `pytest -q -m 'not browser'`, `pytest tests/browser -q`, `python3 manage.py check`, `python3 manage.py makemigrations --check --dry-run`, `git diff --check`.
- [ ] Compare complete snapshot before/after and check no changes under `mechanics/`; review migration reversibility and data-copy behavior.
- [ ] Obtain independent whole-branch review, fix Important/Critical findings RED→GREEN, rerun suites and report files/commits/status.
