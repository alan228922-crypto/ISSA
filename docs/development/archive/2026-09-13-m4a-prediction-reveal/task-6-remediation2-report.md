# Task 6 remediation round 2 report

## Status

Implemented the final-review correction for the Analyze JSON boundary only. Task 7 was not started.

## Root cause

`projects.views.analyze` forwarded the new optional `prediction_id` to `analyze_project`, but its exception adapter handled only `KeyError` and `AnalysisError`. An unexpected service or ORM failure therefore escaped to Django's default 500 handler, producing HTML and, with `DEBUG=True`, disclosing exception text and internal paths.

## RED

Added the genuine HTTP regression `test_analyze_http_maps_unexpected_prediction_service_failure_to_safe_json`. It sends an authenticated Analyze request with an explicit `prediction_id`, injects an unexpected `analyze_project` failure containing a private path, database secret, and result-field names, and requires the stable safe JSON envelope.

Command:

```text
python3 -m pytest -q tests/endpoints/test_project_json.py::test_analyze_http_maps_unexpected_prediction_service_failure_to_safe_json
```

Observed before the production change:

```text
FAILED ... assert response.headers['Content-Type'].startswith('application/json')
Content-Type: text/html; charset=utf-8
1 failed in 0.97s
```

The traceback showed the injected failure escaping from `projects/views.py` at the `analyze_project` call.

## GREEN

Minimum boundary fix:

- Added the existing M3-convention `INTERNAL_ERROR` message to the Projects boundary.
- Added `except Exception` after the existing `AnalysisError` handler in `analyze`, returning HTTP 500 through `_error`.
- Kept all expected `AnalysisError` status/code mappings unchanged.
- The exact response assertion permits no exception text, internal path, numerical result, or other result data.

Commands and results:

```text
python3 -m pytest -q tests/endpoints/test_project_json.py::test_analyze_http_maps_unexpected_prediction_service_failure_to_safe_json
1 passed in 0.83s

python3 -m pytest -q tests/endpoints/test_project_json.py tests/endpoints/test_prediction_json.py tests/application/test_analysis_acceptance.py
62 passed in 3.77s

python3 manage.py check
System check identified no issues (0 silenced).

python3 manage.py makemigrations --check --dry-run
No changes detected

python3 -m pytest tests/permissions -v
6 passed in 7.63s

python3 -m pytest tests/application -v
118 passed in 6.51s

python3 -m pytest tests/contracts -v
5 passed in 0.37s

python3 -m pytest tests/idealization -v
3 passed in 0.09s

python3 -m pytest tests/mechanics -v
131 passed in 0.65s

python3 -m pytest -q
304 passed in 14.78s

git diff --check
exit 0
```

## Files

- `projects/views.py`
- `tests/endpoints/test_project_json.py`
- `.superpowers/sdd/2026-09-13-m4a-prediction-reveal/task-6-remediation2-report.md`

No service, model, migration, mechanics, domain, or Task 7 file changed.

## Commit

This report is included in the remediation commit with subject `fix: contain unexpected analyze failures` (the final commit hash is reported after commit creation because a commit cannot contain its own hash).

## Concerns

None within the authorized correction. This deliberately hardens only the Task 6 Analyze service integration identified by the final review; it does not broaden error handling for unrelated pre-existing endpoints.
