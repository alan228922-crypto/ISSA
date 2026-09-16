# M4A Prediction and Result-Reveal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add immutable pre-result Prediction evidence and server-authoritative owner result-reveal protection without changing mechanics or adding teaching UI/Compare.

**Architecture:** A `Prediction` JSON aggregate binds `Project + source_draft_version`; a nullable AnalysisRun FK records use. A unique `StudentResultReveal` keyed by the same pair serializes completion and numerical-result disclosure through the Project row lock.

**Tech Stack:** Django 5.2, Django ORM transactions, pytest-django, existing pure-Python idealization.

**Spec:** `docs/specs/PREDICTION_AND_REVEAL_ARCHITECTURE.md`

**Implementation status (2026-09-16):** Tasks 1–6 are complete through M4A Gates 1–4. Task 7 is not started and remains reserved for M4A Final Gate B.

## Global Constraints

- TDD is mandatory: focused RED test, observed expected failure, minimum GREEN code, targeted regression, commit per task.
- JSON errors use English stable codes and zh-CN messages; no traceback; CSRF remains enabled.
- Keep `prediction_id=None` analyzable. Manager/Developer cannot create Prediction or trigger student reveal.
- Do not change Solver numerics, `truss2d-result-v1`, idealization semantics, O-001/O-003/O-004/O-005/O-006/O-007, or add an engineering `ZERO_FORCE` threshold.
- No DRF, Compare, Explain, Reflection, editor/UI, load-path solver, generic audit system, or skip records.

## File Structure

- Create: `learning/models.py`, `learning/services.py`, `learning/views.py`, `learning/urls.py`, `learning/migrations/0001_initial.py`.
- Modify: `config/urls.py`, `analysis/models.py`, migration, `analysis/orchestration.py`, `projects/views.py`.
- Tests: `tests/application/test_prediction.py`, `tests/endpoints/test_prediction_json.py`, plus focused additions to existing analysis/result tests.

### Task 1: Persistence contract

**Files:** Create `learning/models.py`, migration; Test `tests/application/test_prediction.py`.

**Interfaces:** `Prediction`, `Prediction.Status`, `StudentResultReveal`; unique reveal `(project, source_draft_version)`.

- [ ] **Step 1: Write the failing test**

```python
def test_prediction_defaults_draft_and_reveal_is_unique(project, owner, success_run):
    prediction = Prediction.objects.create(project=project, source_draft_version=7,
        created_by=owner, prediction_schema_version='prediction-v1', payload_json={})
    assert prediction.status == Prediction.Status.DRAFT
    StudentResultReveal.objects.create(project=project, source_draft_version=7,
        first_analysis_run=success_run, revealed_to_user=owner)
    with pytest.raises(IntegrityError):
        StudentResultReveal.objects.create(project=project, source_draft_version=7,
            first_analysis_run=success_run, revealed_to_user=owner)
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/application/test_prediction.py::test_prediction_defaults_draft_and_reveal_is_unique -v`
Expected: FAIL because `learning.models` and tables are missing.

- [ ] **Step 3: Write minimal implementation**

Create the exact spec fields: Project-owned `CASCADE`, evidence actor/run `PROTECT`, timestamps, JSON schema/version and the database unique constraint. Do not create child tables.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/application/test_prediction.py::test_prediction_defaults_draft_and_reveal_is_unique -v && python3 manage.py makemigrations --check --dry-run`
Expected: PASS and no migration drift.

- [ ] **Step 5: Commit**

`git add learning tests/application/test_prediction.py && git commit -m "feat: add prediction evidence models"`

### Task 2: `prediction-v1` and topology validation

**Files:** Create `learning/services.py`; Test `tests/application/test_prediction.py`.

**Interfaces:** `validate_prediction_payload(project, payload) -> dict`; `PredictionError(code, status_code)` with `PREDICTION_INVALID_SCHEMA`, `PREDICTION_INCOMPLETE`, `INVALID_PHYSICAL_POINT_REF`, `INVALID_LOAD_PATH`.

- [ ] **Step 1: Write the failing tests**

```python
def test_payload_requires_every_active_member_once(project_with_two_members):
    assert validate_prediction_payload(project_with_two_members, complete_payload())['schema_version'] == 'prediction-v1'
    with pytest.raises(PredictionError, match='PREDICTION_INCOMPLETE'):
        validate_prediction_payload(project_with_two_members, payload_missing_member())

def test_point_and_path_are_physical_not_solver_rules(project_with_connection_and_free_endpoint):
    validate_prediction_payload(project_with_connection_and_free_endpoint, valid_free_endpoint_payload())
    with pytest.raises(PredictionError, match='INVALID_PHYSICAL_POINT_REF'):
        validate_prediction_payload(project_with_connection_and_free_endpoint, connected_endpoint_as_free_payload())
    with pytest.raises(PredictionError, match='INVALID_LOAD_PATH'):
        validate_prediction_payload(project_with_connection_and_free_endpoint, broken_path_payload())
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/application/test_prediction.py -k 'payload_requires or point_and_path' -v`
Expected: FAIL because validator is missing.

- [ ] **Step 3: Write minimal implementation**

Validate only `prediction-v1`, exact active-member keys and four states, Connection/free-endpoint union normalization, alternating incidence path and duplicate/disconnected rejection. Include same-coordinate unconnected endpoint and cross-Project cases. Do not call Solver.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/application/test_prediction.py -k 'payload_requires or point_and_path' -v`
Expected: PASS.

- [ ] **Step 5: Commit**

`git add learning/services.py tests/application/test_prediction.py && git commit -m "feat: validate prediction payload topology"`

### Task 3: Lifecycle and completion service

**Files:** Modify `learning/services.py`; Test `tests/application/test_prediction.py`.

**Interfaces:** `create_prediction(project, actor, expected_draft_version)` and `complete_prediction(prediction, actor, expected_draft_version, payload)`.

- [ ] **Step 1: Write the failing test**

```python
def test_owner_completes_current_draft_once(project, owner):
    prediction = create_prediction(project=project, actor=owner, expected_draft_version=project.draft_version)
    complete_prediction(prediction=prediction, actor=owner, expected_draft_version=project.draft_version, payload=complete_payload())
    prediction.refresh_from_db()
    assert prediction.status == Prediction.Status.COMPLETED
    with pytest.raises(PredictionError, match='PREDICTION_ALREADY_COMPLETED'):
        complete_prediction(prediction=prediction, actor=owner, expected_draft_version=project.draft_version, payload=complete_payload())
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/application/test_prediction.py::test_owner_completes_current_draft_once -v`
Expected: FAIL because lifecycle functions are missing.

- [ ] **Step 3: Write minimal implementation**

Authorize only owner participant; in an atomic Project lock re-read version, check DRAFT/source, validate payload and absence of reveal, then server-set `COMPLETED`. Use `PREDICTION_STALE_DRAFT`, `PREDICTION_AFTER_RESULT_REVEAL`, `PREDICTION_ALREADY_COMPLETED`, `PREDICTION_INVALIDATED`; stale DRAFT invalidates but completed history never mutates.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/application/test_prediction.py -k 'owner_completes or immutable or stale or manager or developer or other_user' -v`
Expected: PASS for all authorization, completeness, immutability and changed-draft cases.

- [ ] **Step 5: Commit**

`git add learning/services.py tests/application/test_prediction.py && git commit -m "feat: add prediction completion lifecycle"`

### Task 4: AnalysisRun nullable Prediction link

**Files:** Modify `analysis/models.py`, migration, `analysis/orchestration.py`; Test `tests/application/test_analysis_acceptance.py`.

**Interfaces:** `analyze_project(..., prediction_id=None)` persists eligible completed Prediction.

- [ ] **Step 1: Write the failing test**

```python
def test_analyze_accepts_none_and_reuses_completed_prediction(context):
    plain = analyze_project(project=context.project, actor=context.owner, expected_draft_version=1, prediction_id=None)
    prediction = completed_prediction_for(context.project, context.owner, 1)
    first = analyze_project(project=context.project, actor=context.owner, expected_draft_version=1, prediction_id=prediction.id)
    second = analyze_project(project=context.project, actor=context.owner, expected_draft_version=1, prediction_id=prediction.id)
    assert plain.prediction_id is None
    assert first.prediction_id == second.prediction_id == prediction.id
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/application/test_analysis_acceptance.py -k 'reuses_completed_prediction' -v`
Expected: FAIL because AnalysisRun has no relation.

- [ ] **Step 3: Write minimal implementation**

Add nullable `PROTECT` FK; reject cross-project/not-found as `PREDICTION_NOT_FOUND` 404, DRAFT/INVALIDATED as `PREDICTION_NOT_ELIGIBLE` 409, and old source as `PREDICTION_STALE_DRAFT` 409 before run creation. Preserve null behavior.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/application/test_analysis_acceptance.py -k prediction -v && python3 manage.py makemigrations --check --dry-run`
Expected: PASS, no migration drift.

- [ ] **Step 5: Commit**

`git add analysis learning tests/application/test_analysis_acceptance.py && git commit -m "feat: link analysis runs to predictions"`

### Task 5: Reveal service and race invariant

**Files:** Modify `learning/services.py`; Test `tests/application/test_prediction.py`.

**Interfaces:** `record_student_result_reveal(project, run, actor) -> StudentResultReveal | None`.

- [ ] **Step 1: Write the failing test**

```python
def test_owner_success_reveal_is_idempotent_and_blocks_late_completion(success_run, owner):
    first = record_student_result_reveal(project=success_run.project, run=success_run, actor=owner)
    assert record_student_result_reveal(project=success_run.project, run=success_run, actor=owner).id == first.id
    with pytest.raises(PredictionError, match='PREDICTION_AFTER_RESULT_REVEAL'):
        complete_prediction(prediction=draft_prediction(success_run.project, owner), actor=owner,
                            expected_draft_version=success_run.model_revision.source_draft_version, payload=complete_payload())
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/application/test_prediction.py::test_owner_success_reveal_is_idempotent_and_blocks_late_completion -v`
Expected: FAIL because reveal service is absent.

- [ ] **Step 3: Write minimal implementation**

Return `None` for non-owner/non-SUCCESS; otherwise share completion’s Project lock and `get_or_create` unique evidence. Cover duplicate tabs, failed run, Manager/Developer non-reveal, draft-8 eligibility, and both lock orders.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/application/test_prediction.py -k reveal -v`
Expected: PASS.

- [ ] **Step 5: Commit**

`git add learning/services.py tests/application/test_prediction.py && git commit -m "feat: record student result reveal evidence"`

### Task 6: JSON boundaries and result integration

**Files:** Create `learning/views.py`, `learning/urls.py`; modify `config/urls.py`, `projects/views.py`; Test `tests/endpoints/test_prediction_json.py`, `tests/endpoints/test_project_json.py`.

**Interfaces:** `POST /projects/<id>/predictions/`, `POST /projects/<id>/predictions/<prediction_id>/complete/`, `GET /projects/<id>/predictions/<prediction_id>/`; result-data automatically calls reveal service.

- [ ] **Step 1: Write the failing tests**

```python
def test_owner_prediction_flow_uses_csrf_and_result_read_reveals(client, owner, project, success_run):
    client.force_login(owner)
    assert post_json_with_csrf(client, create_url(project), {'expected_draft_version': project.draft_version}).status_code == 201
    assert post_json_with_csrf(client, complete_url(project, 1), complete_payload()).status_code == 200
    assert client.get(result_data_url(project, success_run)).status_code == 200
    assert StudentResultReveal.objects.filter(project=project).exists()
```

- [ ] **Step 2: Verify RED**

Run: `python3 -m pytest tests/endpoints/test_prediction_json.py::test_owner_prediction_flow_uses_csrf_and_result_read_reveals -v`
Expected: FAIL with missing URLs/views.

- [ ] **Step 3: Write minimal implementation**

Use thin session/CSRF JSON views. Map malformed 400, authorization/no-IDOR 403/404, lifecycle stale 409, schema/topology 422, and unexpected 500 with zh-CN text. Result view calls reveal only after authorization, Project/run scope, and SUCCESS check, before returning numerical JSON; no mark-revealed endpoint.

- [ ] **Step 4: Verify GREEN**

Run: `python3 -m pytest tests/endpoints/test_prediction_json.py tests/endpoints/test_project_json.py -v`
Expected: PASS for CSRF, malformed JSON, owner/other/Manager/Developer policy, null/valid/stale Analyze, owner-only successful reveal and all non-reveal boundaries.

- [ ] **Step 5: Commit**

`git add learning config projects tests/endpoints && git commit -m "feat: add prediction and reveal application flow"`

### Task 7: Full regression and traceability gate

**Files:** Documentation only if a demonstrated contract mismatch requires it; Test all suites.

- [ ] **Step 1: Run focused suites**

Run: `python3 -m pytest tests/application/test_prediction.py tests/endpoints/test_prediction_json.py tests/application/test_analysis_acceptance.py tests/endpoints/test_project_json.py -v`
Expected: PASS.

- [ ] **Step 2: Run boundaries and migration checks**

Run: `python3 manage.py check && python3 manage.py makemigrations --check --dry-run && python3 -m pytest tests/contracts tests/idealization tests/mechanics -v`
Expected: no Django/migration error; mechanics/idealization unchanged.

- [ ] **Step 3: Run fresh full verification**

Run: `python3 -m pytest -v && git diff --check && git status --short`
Expected: full green suite, no whitespace errors, intended tracked changes only.

- [ ] **Step 4: Commit**

`git add docs tests && git commit -m "test: verify prediction reveal integrity"`

## Self-review

- Every confirmed M4A item maps to Tasks 1–6.
- No task implements Compare, Reflection, result UI, load-path solver, or O-007 classification.
- Interfaces consistently use `source_draft_version`, `prediction-v1`, nullable `AnalysisRun.prediction`, and Project-lock serialization.
