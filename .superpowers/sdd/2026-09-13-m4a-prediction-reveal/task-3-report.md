# Task 3 — Prediction lifecycle and completion service

## Changed files

- `learning/services.py` — added `create_prediction` and `complete_prediction`, owner-participant authorization, Project-row serialization, stale DRAFT invalidation, reveal exclusion, and server-owned completion fields.
- `tests/application/test_prediction.py` — added lifecycle evidence for current-draft binding, owner-only active participant authorization, Developer denial, PURGED blocking, validation rollback, stale invalidation, completed-history preservation, reveal blocking, and no reveal creation during completion.

## TDD evidence

### RED

Command:

```sh
python3 -m pytest tests/application/test_prediction.py::test_owner_completes_current_draft_once -v
```

Result: failed as expected with `ImportError: cannot import name 'complete_prediction' from 'learning.services'` before either lifecycle interface existed.

### GREEN

Commands:

```sh
python3 -m pytest tests/application/test_prediction.py -k 'owner_completes or immutable or stale or manager or developer or other_user' -v
python3 -m pytest tests/application/test_prediction.py -v
python3 -m pytest -v
```

Results: focused command passed (`1 passed`); prediction suite passed (`31 passed`); full repository suite passed (`232 passed`).

## Self-review

- Both lifecycle paths lock the Project row in `transaction.atomic()` and re-read its version.
- Prediction authorization is deliberately stricter than `can_modify_project`: actor must be Project owner and have an active PARTICIPANT membership. Developers and managers are denied.
- Completion only completes a current DRAFT before an existing result reveal, validates through `validate_prediction_payload`, and controls status, binding, creator, and timestamps on the server.
- A stale DRAFT is persisted as `INVALIDATED` before `PREDICTION_STALE_DRAFT` is returned; COMPLETED records are left unchanged.
- Invalid or incomplete payloads produce no state transition; completion does not create reveal records.

## Scope exclusions

No runtime reveal service, endpoints, Task4 `AnalysisRun.prediction` foreign key, compare/UI behavior, mechanics behavior, zero-force classification policy, or FINISHED_GRACE policy was added.

## Follow-up review fix — privileged owner-participants

Review found that a Manager or Developer account which was itself the Project owner and held an active PARTICIPANT membership could pass the original owner-membership predicate. `_authorize_student_owner` now explicitly denies `MANAGER` and `DEVELOPER` roles before allowing either lifecycle operation.

### Follow-up RED

```sh
python3 -m pytest tests/application/test_prediction.py -k 'privileged_owner_participant' -v
```

Result: all four new real lifecycle cases failed as expected (`DID NOT RAISE PredictionError`): Manager and Developer owner-participants could both create and complete predictions before the role check existed.

### Follow-up GREEN

```sh
python3 -m pytest tests/application/test_prediction.py -k 'privileged_owner_participant' -v
python3 -m pytest tests/application/test_prediction.py -v
```

Results: privileged-owner focused tests passed (`4 passed`); full prediction suite passed (`35 passed`). The create tests assert no Prediction is created; the complete tests assert the existing Prediction remains DRAFT with empty payload and no completion timestamp.
