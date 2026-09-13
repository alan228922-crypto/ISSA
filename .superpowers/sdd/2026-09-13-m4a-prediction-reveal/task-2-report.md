# Task 2 — prediction-v1 topology validation

## Changed files

- `learning/services.py` — `PredictionError` and graph-only `validate_prediction_payload`.
- `tests/application/test_prediction.py` — coverage, state/schema, physical-point, and topology tests.

## TDD evidence

- RED: `python3 -m pytest tests/application/test_prediction.py -k 'payload_requires or point_and_path' -v`
  - Result: 2 failed, 2 deselected; both failures were `ModuleNotFoundError: No module named 'learning.services'`.
- GREEN: `python3 -m pytest tests/application/test_prediction.py -k 'payload_requires or point_and_path' -v`
  - Result: 2 passed, 2 deselected.
- Regression check: `python3 -m pytest tests/application/test_prediction.py -v`
  - Result: 4 passed.

## Scope exclusions

- No Solver, member-stress, or mechanics-solving call/import; validation checks only stored physical topology.
- No persistence/completion workflow, `StudentResultReveal`, endpoint, `AnalysisRun`, model, or migration changes.

## Commit

- `feat: validate prediction payload topology`
