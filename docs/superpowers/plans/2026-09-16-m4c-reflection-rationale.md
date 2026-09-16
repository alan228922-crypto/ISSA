# M4C Reflection and Rationale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the frozen `reflection-v1` learning-evidence workflow bound one-to-one to `AnalysisRun`, while preserving the Analyze Soft Gate, existing authorization policy, and ordered operational purge boundary.

**Architecture:** Add one `Reflection` ORM aggregate with a unique `analysis_run` foreign key and two-state lifecycle. Keep eligibility, event-status checks, ownership, visibility, and immutability in a thin application service; expose only the HTTP contract frozen at Gate 3A through existing Django JSON conventions. Reflection stores only the three student text fields and minimal provenance; it never copies Compare, Explain, or solver artifacts.

**Tech Stack:** Django 5.2 ORM and migrations, pytest-django, existing `learning.services`, `projects.services`, `competitions.authorization`, `StudentResultReveal`, and Django `JsonResponse`/CSRF conventions.

**Spec:** `docs/specs/REFLECTION_AND_RATIONALE_ARCHITECTURE.md`

## Global Constraints

- `reflection-v1` is the only M4C P0 Reflection schema; `next_iteration_intent` is P0 Design Rationale.
- Reflection is a Soft Gate. Missing or incomplete Reflection never blocks draft save, model editing, Analyze, Compare, Explain, or result access.
- One `AnalysisRun` has at most one Reflection. Reflection identity is `analysis_run`, not `source_draft_version`.
- Creation requires `AnalysisRun.status == SUCCESS` and an existing `StudentResultReveal` for the same Project and `ModelRevision.source_draft_version`; `first_analysis_run` need not equal the Reflection Run.
- Only the student Project owner may create, edit DRAFT, or complete. DRAFT is owner-private; COMPLETED is readable by the owner and existing authorized Manager/Developer readers, but never writable by them.
- Only `DRAFT → COMPLETED` is supported. COMPLETED is immutable; there is no INVALIDATED, STALE, SKIPPED, revision history, or manual DELETE.
- Completion trims all three fields and requires each to be non-empty; each field is at most 2000 characters.
- ACTIVE permits authoring; FINISHED_GRACE authoring is fail-closed; PURGED denies authoring. This narrow rule does not close O-003.
- Raw Reflection text is operational data and must be deleted before AnalysisRun by the supported ordered Project purge. User accounts and research retention policy are unchanged.
- No separate DesignRationale model, DesignIteration domain, comparison/explanation/result snapshot, score, grade, ranking, sentiment/misconception classifier, AI/LLM dependency, mechanics change, idealization change, or Analyze hard gate.
- User-visible prompts/messages are zh-CN; machine error codes are English; no traceback is returned.
- Every task uses strict TDD: write one behavior-focused failing test, observe the expected failure, implement the minimum, run focused and relevant regression tests, then commit.

## File Map

| File | Responsibility in this plan |
|---|---|
| `learning/models.py` | Add the sole `Reflection` model and `DRAFT`/`COMPLETED` choices. |
| `learning/migrations/0002_reflection.py` | Create the Reflection table, constraints, and indexes generated from the model. |
| `learning/services.py` | Add `ReflectionError` and explicit create/update/complete/read application services; no mechanics logic. |
| `projects/services.py` | Include Reflection in the existing ordered operational purge before protected AnalysisRun rows. |
| `learning/views.py` | Add thin JSON handlers only after Gate 3A freezes routes and payloads. |
| `learning/urls.py` | Register only the Gate 3A-frozen explicit routes. |
| `tests/application/test_reflection.py` | Persistence, lifecycle, authorization, event status, eligibility, Soft Gate, and purge service evidence. |
| `tests/endpoints/test_reflection_json.py` | CSRF, JSON mapping, visibility, read-only staff access, and route contract evidence. |
| `docs/specs/REFLECTION_AND_RATIONALE_ARCHITECTURE.md` | Frozen source of truth; no behavior changes are introduced by the plan. |

## Gate 1 — Reflection Persistence Contract

### Task 1: Add the Reflection model and migration

**Files:**
- Modify: `learning/models.py` after `StudentResultReveal`
- Create: `learning/migrations/0002_reflection.py` via `makemigrations`
- Test: `tests/application/test_reflection.py`

**Interfaces:**
- Consumes: existing `analysis.models.AnalysisRun`, `accounts.User`, and Django model constraints.
- Produces: `Reflection`, `Reflection.Status.DRAFT`, `Reflection.Status.COMPLETED`; fields `analysis_run`, `created_by`, `status`, `original_reasoning`, `unexpected_results`, `next_iteration_intent`, `reflection_schema_version`, `created_at`, `updated_at`, `completed_at`.
- Database invariant: `analysis_run` is a `PROTECT` foreign key with a unique constraint, so one Run can have at most one Reflection and a Reflection cannot outlive its historical Run accidentally.

- [ ] **Step 1: Write the failing tests**

Add these independent tests with real ORM objects:

```python
def test_reflection_defaults_to_draft_and_uses_reflection_v1(success_run, owner):
    reflection = Reflection.objects.create(analysis_run=success_run, created_by=owner)
    assert reflection.status == Reflection.Status.DRAFT
    assert reflection.reflection_schema_version == "reflection-v1"
    assert reflection.completed_at is None

def test_one_analysis_run_allows_at_most_one_reflection(success_run, owner):
    Reflection.objects.create(analysis_run=success_run, created_by=owner)
    with pytest.raises(IntegrityError):
        Reflection.objects.create(analysis_run=success_run, created_by=owner)

def test_reflection_text_columns_enforce_2000_character_contract(success_run, owner):
    reflection = Reflection.objects.create(
        analysis_run=success_run,
        created_by=owner,
        original_reasoning="x" * 2001,
    )
    with pytest.raises(ValidationError):
        reflection.full_clean()

def test_only_draft_and_completed_statuses_are_valid(success_run, owner):
    reflection = Reflection.objects.create(analysis_run=success_run, created_by=owner)
    reflection.status = "INVALIDATED"
    with pytest.raises(ValidationError):
        reflection.full_clean()
```

- [ ] **Step 2: Run the focused tests to verify RED**

Run: `python3 -m pytest tests/application/test_reflection.py -k 'defaults_to_draft or at_most_one or text_columns or statuses' -v`

Expected: FAIL because `Reflection` and its migration/table do not exist.

- [ ] **Step 3: Implement the minimum persistence layer**

Add the model with these exact database-facing choices:

```python
class Reflection(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        COMPLETED = "COMPLETED", "Completed"

    analysis_run = models.OneToOneField(
        AnalysisRun, on_delete=models.PROTECT, related_name="reflection",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="reflections",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    original_reasoning = models.CharField(max_length=2000, blank=True, default="")
    unexpected_results = models.CharField(max_length=2000, blank=True, default="")
    next_iteration_intent = models.CharField(max_length=2000, blank=True, default="")
    reflection_schema_version = models.CharField(max_length=64, default="reflection-v1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
```

Use a database check constraint restricting `status` to `DRAFT` or `COMPLETED`; do not add a DesignRationale or DesignIteration model. Generate the migration and run `makemigrations --check --dry-run` after applying it in the test database.

- [ ] **Step 4: Run focused and migration verification**

Run: `python3 -m pytest tests/application/test_reflection.py -k 'defaults_to_draft or at_most_one or text_columns or statuses' -v`

Expected: PASS with four tests. Then run: `python3 manage.py makemigrations --check --dry-run`; expected: `No changes detected`.

- [ ] **Step 5: Commit the persistence contract**

```bash
git add learning/models.py learning/migrations/0002_reflection.py tests/application/test_reflection.py
git commit -m "feat: add reflection persistence contract"
```

### Task 2: Extend the supported purge graph

**Files:**
- Modify: `projects/services.py` in `purge_project_operational_data`
- Modify: `tests/application/test_reflection.py`
- Modify: `tests/application/test_prediction.py` only if its shared purge fixture needs an explicit Reflection assertion

**Interfaces:**
- Consumes: `Reflection.objects.filter(analysis_run__project_id=project_id)` and the existing transaction/Project lock.
- Produces: raw Reflection deletion before `AnalysisRun` deletion; no change to user-account retention or purge audit shape.

- [ ] **Step 1: Write the failing purge test**

```python
def test_supported_project_purge_removes_reflection_and_preserves_user(project, owner, success_run):
    Reflection.objects.create(analysis_run=success_run, created_by=owner)
    purge_project_operational_data(project_id=project.id, actor_id=owner.id)
    assert not Reflection.objects.filter(analysis_run_id=success_run.id).exists()
    assert User.objects.filter(pk=owner.id).exists()
```

- [ ] **Step 2: Run RED**

Run: `python3 -m pytest tests/application/test_reflection.py::test_supported_project_purge_removes_reflection_and_preserves_user -v`

Expected: FAIL because the current purge loop does not delete Reflection before the protected AnalysisRun.

- [ ] **Step 3: Implement the minimum purge change**

Import `Reflection` in the local purge imports and add it as the first learning-evidence deletion before `StudentResultReveal`, `ValidationLog`, and `AnalysisRun`. Filter it by `analysis_run__project_id=project_id` because Reflection is Run-bound. Leave `User`, `Material`, `Section`, `SolverVersion`, Event orchestration, audit schema, and all raw research retention behavior unchanged.

- [ ] **Step 4: Run purge regressions**

Run: `python3 -m pytest tests/application/test_reflection.py::test_supported_project_purge_removes_reflection_and_preserves_user tests/application/test_prediction.py -q`

Expected: PASS with no protected-FK regression and unchanged account retention.

- [ ] **Step 5: Commit the purge boundary**

```bash
git add projects/services.py tests/application/test_reflection.py tests/application/test_prediction.py
git commit -m "feat: purge reflection operational evidence"
```

## Gate 2 — Lifecycle and Authorization

### Task 3: Implement Reflection eligibility and authoring lifecycle

**Files:**
- Modify: `learning/services.py` after the existing reveal service
- Test: `tests/application/test_reflection.py`

**Interfaces:**
- Consumes: `AnalysisRun`, `ModelRevision.source_draft_version`, `StudentResultReveal`, `Project.event.status`, `projects.services.can_view_project`, `accounts.User`, and `EventMembership` participant ownership semantics.
- Produces exact services:
  - `create_reflection(*, run: AnalysisRun, actor: User) -> Reflection`
  - `update_reflection(*, reflection: Reflection, actor: User, fields: dict[str, str]) -> Reflection`
  - `complete_reflection(*, reflection: Reflection, actor: User) -> Reflection`
  - `get_reflection_for_read(*, reflection: Reflection, actor: User) -> Reflection`
  - `ReflectionError(code: str, status_code: int)`

Use stable codes: `REFLECTION_NOT_ELIGIBLE`, `REFLECTION_NOT_FOUND`, `REFLECTION_WRITE_DENIED`, `REFLECTION_READ_DENIED`, `REFLECTION_ALREADY_COMPLETED`, `REFLECTION_INVALID_FIELDS`, `REFLECTION_NOT_DRAFT`, `REFLECTION_EVENT_NOT_ACTIVE`, and `REFLECTION_RUN_NOT_SUCCESS`. Human messages belong to the HTTP layer and must be zh-CN.

- [ ] **Step 1: Write failing lifecycle/eligibility tests**

Add these tests with explicit fixtures and concrete assertions. `test_create_requires_success_run_and_same_draft_reveal` calls `reveal_for(success_run)` then `create_reflection` and asserts the returned `analysis_run_id`. `test_create_rejects_success_run_without_reveal` asserts `ReflectionError.code == "REFLECTION_NOT_ELIGIBLE"`. `test_create_rejects_failed_run_even_if_revealed` asserts `REFLECTION_RUN_NOT_SUCCESS`. `test_create_allows_second_success_run_after_same_draft_reveal` and `test_first_reveal_run_need_not_equal_reflection_run` create two SUCCESS Runs for one draft, reveal the first, create on the second, and assert the Reflection points at the second while the reveal’s first Run remains the first. `test_create_does_not_require_compare_or_explain_read` creates directly after reveal and asserts DRAFT. `test_draft_allows_partial_and_clearable_fields` updates one field, asserts the exact submitted value, then updates it to `""` and asserts empty storage. `test_draft_update_accepts_only_three_known_text_fields` submits `status` and asserts `REFLECTION_INVALID_FIELDS`. `test_completion_trims_and_requires_three_nonempty_fields` fills all three fields with surrounding whitespace, completes, and asserts COMPLETED plus non-null `completed_at`. `test_each_reflection_field_rejects_more_than_2000_characters` submits 2001 characters and asserts `REFLECTION_INVALID_FIELDS`. `test_completed_reflection_is_immutable` completes a record, attempts an update, and asserts `REFLECTION_ALREADY_COMPLETED`. Every assertion checks a returned status or exact `ReflectionError.code`, never implementation internals; these tests do not authorize another lifecycle state.

- [ ] **Step 2: Run RED**

Run: `python3 -m pytest tests/application/test_reflection.py -k 'create_requires or without_reveal or failed_run or second_success or first_reveal or compare_or_explain or draft_ or completion or 2000 or immutable' -v`

Expected: FAIL because the four Reflection services and `ReflectionError` do not exist.

- [ ] **Step 3: Implement the minimum application service**

Implement the following order in each service:

1. Re-fetch the Run/Reflection with the related Project, Event, ModelRevision, and owner identity under a Project `select_for_update()` transaction where a state transition occurs.
2. Authoring actor must be the Project owner, have an active participant membership, and not be Manager/Developer.
3. Require `event.status == ACTIVE` for create/update/complete. Return `REFLECTION_EVENT_NOT_ACTIVE` for DRAFT, FINISHED_GRACE, and PURGED; do not change O-003.
4. For create, require Run `SUCCESS`, then require `StudentResultReveal(project=run.project, source_draft_version=run.model_revision.source_draft_version)`. Do not compare `first_analysis_run_id` and do not call Compare/Explain.
5. For update, require DRAFT and validate only the three text fields, allowing omission to retain the existing value and `""` to clear it. Reject unknown fields, non-string values, and values over 2000 characters.
6. For complete, require DRAFT, trim each value for the non-empty check, preserve the intended submitted text, set `COMPLETED` and `completed_at` atomically, and never permit a second transition.
7. For read, owner can read either status; Manager/Developer can read only COMPLETED through existing Project read authorization; other users and staff reading DRAFT receive `REFLECTION_READ_DENIED`.

Do not add a delete function, auto-completion, snapshot builder, score, or event-wide policy helper.

- [ ] **Step 4: Run GREEN and regression verification**

Run: `python3 -m pytest tests/application/test_reflection.py -q` and `python3 -m pytest tests/application/test_prediction.py tests/application/test_analysis_acceptance.py -q`.

Expected: all Reflection lifecycle tests pass and existing Prediction/AnalysisRun reveal invariants remain green.

- [ ] **Step 5: Commit lifecycle and authorization**

```bash
git add learning/services.py tests/application/test_reflection.py
git commit -m "feat: add reflection lifecycle service"
```

### Task 4: Complete application-level authorization and Soft Gate evidence

**Files:**
- Modify: `tests/application/test_reflection.py`
- Modify: `tests/application/test_analysis_acceptance.py` only for a focused no-Reflection Analyze regression if the shared fixture does not already prove it

**Interfaces:**
- Consumes: Task 3 services and existing `analyze_project`.
- Produces: executable evidence that Reflection is never an Analyze prerequisite and that role/event boundaries are not widened.

- [ ] **Step 1: Write failing tests for role, visibility, and Soft Gate**

Add `test_owner_can_author_active_reflection`, asserting DRAFT after a same-draft reveal; `test_other_user_cannot_author_or_read`, asserting `REFLECTION_WRITE_DENIED` on create and `REFLECTION_READ_DENIED` on read; `test_manager_cannot_author_but_reads_completed` and `test_developer_cannot_author_but_reads_completed`, asserting write denial and successful completed read; `test_manager_and_developer_cannot_read_draft`, asserting `REFLECTION_READ_DENIED`; `test_finished_grace_rejects_create_update_complete` and `test_purged_rejects_create_update_complete`, asserting `REFLECTION_EVENT_NOT_ACTIVE` for all three service calls; and `test_analyze_succeeds_without_reflection`, which builds a valid model, calls `analyze_project(project=context.project, actor=context.owner, expected_draft_version=1, prediction_id=None)`, and asserts SUCCESS. Use a real assigned `EventMembership` for Manager and `User.Role.DEVELOPER` for Developer; assert exact error codes.

- [ ] **Step 2: Run RED**

Run: `python3 -m pytest tests/application/test_reflection.py -k 'owner_can or other_user or manager or developer or draft or finished_grace or purged or without_reflection' -v`

Expected: FAIL only where the authorization and event assertions are not yet enforced; no test should fail because of a fixture or import error.

- [ ] **Step 3: Implement only missing policy checks**

Keep all checks in the existing Reflection application service. Reuse `can_view_project` for Project-read scope and `can_modify_project` only as a supporting policy check; add the explicit ACTIVE requirement and completed-only staff visibility locally to Reflection. Do not change global authorization helpers or Analyze orchestration.

- [ ] **Step 4: Run GREEN and full relevant application regression**

Run: `python3 -m pytest tests/application/test_reflection.py tests/application/test_analysis_acceptance.py -q`.

Expected: PASS, including the existing Prediction Soft Gate tests and no new Reflection hard gate.

- [ ] **Step 5: Commit authorization evidence**

```bash
git add tests/application/test_reflection.py tests/application/test_analysis_acceptance.py
git commit -m "test: lock reflection authorization and soft gate"
```

## Gate 3 — HTTP Boundary

### Task 5: Gate 3A — Freeze the Reflection HTTP contract

**Files:**
- Modify: `docs/specs/API_AND_APPLICATION_FLOW.md` only after the decision below is made
- Create or modify: `docs/specs/REFLECTION_AND_RATIONALE_ARCHITECTURE.md` only if the frozen route/payload decision needs a one-line cross-reference

**Interfaces:**
- Consumes: Task 3 service signatures and the existing `projects/` + `learning/` URL convention.
- Produces: one exact, reviewed route and envelope contract for read, create, DRAFT update, and completion; no implementation.

The single decision required before Gate 3B is the resource identity in the URL:

- Option A: Reflection resource routes use `project_id + reflection_id`, matching existing Prediction create/detail/complete routes:
  - `GET /projects/<project_id>/reflections/<reflection_id>/`
  - `POST /projects/<project_id>/reflections/`
  - `POST /projects/<project_id>/reflections/<reflection_id>/update/`
  - `POST /projects/<project_id>/reflections/<reflection_id>/complete/`
- Option B: Reflection is exposed through its required AnalysisRun binding:
  - `GET /projects/<project_id>/analyses/<run_id>/reflection/`
  - `POST /projects/<project_id>/analyses/<run_id>/reflection/`
  - `POST /projects/<project_id>/analyses/<run_id>/reflection/update/`
  - `POST /projects/<project_id>/analyses/<run_id>/reflection/complete/`

Product Owner must choose exactly one option before implementation. The contract must also freeze: `POST` methods retain CSRF; create accepts no fields beyond `analysis_run_id` if Option A or no identity field if Option B; update accepts only the three text fields; complete accepts the three text fields or uses persisted DRAFT values according to the chosen contract; read returns only Reflection metadata/text and safe Run/source-draft provenance, never result/Compare/Explain snapshots. Errors use English codes, zh-CN messages, 400 malformed JSON, 403/404 scoped authorization/not-found, 409 immutable/lifecycle conflict, 422 field/eligibility validation, and safe 500 unexpected failure.

- [ ] **Step 1: Record the selected contract**

Update the API flow document with the selected exact URLs, request field sets, success envelope, safe response fields, and status/code mapping. Do not add a generic CRUD route, DELETE route, bulk route, DRF serializer, or a future UI contract.

- [ ] **Step 2: Run contract-only verification**

Run: `git diff --check` and inspect the API flow diff for exactly one selected route shape, the four explicit methods, CSRF retention, safe envelope, and no incidental URL.

- [ ] **Step 3: Commit the HTTP contract freeze**

```bash
git add docs/specs/API_AND_APPLICATION_FLOW.md
git commit -m "docs: freeze M4C reflection http contract"
```

### Task 6: Gate 3B — Implement thin Reflection HTTP boundary

**Files:**
- Modify: `learning/views.py`
- Modify: `learning/urls.py`
- Test: `tests/endpoints/test_reflection_json.py`
- Test: `tests/contracts/test_reflection_contract.py`

**Interfaces:**
- Consumes: the single Gate 3A route decision, `create_reflection`, `update_reflection`, `complete_reflection`, `get_reflection_for_read`, `ReflectionError`, and `_json_body`/error-envelope conventions.
- Produces: thin authenticated JSON views; all lifecycle, eligibility, event, role, and immutability rules remain in `learning.services`.

- [ ] **Step 1: Write failing endpoint tests**

Cover each selected route with these concrete tests: `test_reflection_post_requires_authentication_and_csrf` uses anonymous and `Client(enforce_csrf_checks=True)` clients and asserts 302 then 403 without a token; `test_owner_creates_updates_and_completes_reflection` asserts 201 create, 200 update, and 200 COMPLETED; `test_malformed_json_and_unknown_fields_are_safe_json_errors` asserts 400 with `MALFORMED_JSON` and `INVALID_REQUEST`; `test_owner_reads_draft_and_completed_reflection` asserts both read states; `test_other_user_is_denied_without_cross_project_leak` asserts 403/404 and no Reflection facts; `test_manager_developer_read_completed_but_cannot_write` asserts 200 read and 403 POST; `test_manager_developer_cannot_read_draft` asserts 403; `test_failed_run_or_missing_reveal_maps_to_domain_error` asserts the frozen 409/422 machine code; and `test_response_does_not_leak_result_or_snapshot_data` asserts the serialized response excludes `result_json`, `solver_input_json`, `comparison-v1`, `explanation-v1`, and `physical_snapshot`. Every POST uses a real CSRF token with `Client(enforce_csrf_checks=True)`.

- [ ] **Step 2: Run RED**

Run: `python3 -m pytest tests/endpoints/test_reflection_json.py -q`

Expected: FAIL because the selected routes and view functions are not registered.

- [ ] **Step 3: Implement thin views and explicit URL patterns**

Each view may only authenticate, parse JSON, perform scoped Project/Run/Reflection lookup, call one application service, map `ReflectionError`, and return `JsonResponse`. Use `@login_required`, `@require_GET` or `@require_POST`; never use `@csrf_exempt`. Scope every Reflection lookup through the URL Project and, when Option B is selected, the URL AnalysisRun. Do not instantiate or mutate Reflection directly in a view and do not duplicate eligibility or completion rules.

- [ ] **Step 4: Run GREEN and endpoint regression**

Run: `python3 -m pytest tests/endpoints/test_reflection_json.py tests/endpoints/test_prediction_json.py tests/endpoints/test_project_json.py -q`.

Expected: PASS with existing CSRF, Prediction, result-reveal, and Project JSON conventions unchanged.

- [ ] **Step 5: Commit the HTTP boundary**

```bash
git add learning/views.py learning/urls.py tests/endpoints/test_reflection_json.py tests/contracts/test_reflection_contract.py
git commit -m "feat: expose reflection json boundary"
```

## Final Gate — Reconciliation and Full Verification

### Task 7: Reconcile M4C implementation, Spec, and tests

**Files:**
- Modify only documentation if a verified implementation/spec drift exists: `docs/specs/REFLECTION_AND_RATIONALE_ARCHITECTURE.md`, `docs/specs/API_AND_APPLICATION_FLOW.md`, `docs/specs/MASTER_SPEC.md`, `docs/specs/DOMAIN_MODEL.md`, `docs/specs/DATA_CONTRACT.md`, `docs/specs/AUTHORIZATION_AND_EVENT_ARCHITECTURE.md`, `docs/specs/ARCHITECTURE_DECISION_REGISTER.md`
- Test evidence: all existing M4C application/contract/endpoint tests; do not rewrite them in Final Gate

**Interfaces:**
- Consumes: all Gate 1–3 services, model/migration, purge behavior, HTTP contract, and role/event fixtures.
- Produces: no new product behavior; a clean, reconciled branch ready for release verification.

- [ ] **Step 1: Perform targeted reconciliation review**

Check each frozen invariant against implementation and executable tests: Soft Gate; one-to-zero/one Run binding; SUCCESS plus same-source reveal; no first-run equality; no Compare/Explain prerequisite; DRAFT/COMPLETED lifecycle; three-field/2000-character completion; owner-private DRAFT; completed staff read-only; no delete; no snapshots; ordered raw purge; FINISHED_GRACE fail-closed with O-003 open; no scoring or AI.

- [ ] **Step 2: Run fresh verification**

Run exactly:

```bash
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
python3 -m pytest tests/permissions -q
python3 -m pytest tests/application -q
python3 -m pytest tests/contracts -q
python3 -m pytest tests/idealization -q
python3 -m pytest tests/mechanics -q
python3 -m pytest -q
git diff --check
git status
```

Expected: all commands exit 0, no migration drift, full suite passes, and the worktree is clean. If any command fails, classify it as `TEST_FIXTURE_ERROR`, `PRODUCTION_DEFECT`, `SPEC_GAP`, or `POLICY_GAP` and stop without scope expansion.

- [ ] **Step 3: Commit only verified documentation drift**

If reconciliation found no drift, create no verification commit. If a documentation-only correction is necessary, use:

```bash
git add docs/specs
git commit -m "docs: reconcile M4C reflection implementation state"
```

### Task 8: Final branch verification handoff

**Files:**
- No production or test changes.

**Interfaces:**
- Consumes: the verified M4C branch and the accepted implementation plan.
- Produces: a status report only; no merge, push, UI, or M4D work.

- [ ] **Step 1: Confirm branch scope**

Run: `git diff --name-only main...HEAD` and `git diff --stat main...HEAD`. Confirm only the approved Reflection model/service/HTTP/purge files, tests, migrations, plan/spec updates, and no mechanics, idealization, Compare/Explain semantics, AI, or unrelated API framework changes.

- [ ] **Step 2: Report readiness**

Report the final HEAD, test evidence, migration status, purge/Soft-Gate evidence, open decisions, and whether the branch is ready for the next release gate. Do not merge or start another M4C gate in this plan task.

## Plan Self-Review

- Spec coverage: every Gate 0A invariant has a persistence, lifecycle, HTTP, purge, or final-reconciliation task; no independent DesignRationale or DesignIteration path exists.
- Placeholder scan: the only intentional decision checkpoint is Gate 3A’s explicit Product Owner choice between two concrete route shapes; no TODO, TBD, or unspecified “appropriate tests” step is used.
- Interface consistency: all lifecycle services accept explicit keyword arguments and return `Reflection`; HTTP views consume those exact services; purge consumes the model through `analysis_run__project_id` before AnalysisRun deletion.
- Scope check: no task modifies mechanics, idealization, Analyze eligibility, Prediction lifecycle, Compare/Explain core semantics, global O-003 policy, user account lifecycle, research raw-text retention, or introduces a second aggregate.
