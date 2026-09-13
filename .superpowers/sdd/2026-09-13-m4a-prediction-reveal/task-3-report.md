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
