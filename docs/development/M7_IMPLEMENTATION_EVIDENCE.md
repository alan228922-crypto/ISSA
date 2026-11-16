# M7 — implementation and verification evidence

Owner decisions D-M7-001/002/003 and the three execution amendments are frozen in the [implementation plan](../superpowers/plans/2026-10-17-m7-project-creation-event-provisioning.md).

Branch: `feat/project-creation-m7`.
Base: `main@8dc11a1c095b5a350299296f555952af3268c946`.
Estimated size: L. Execution: native Task 1 → Task 8, one final independent whole-branch review.

## Delivered boundaries

- Existing authenticated active USER + exact active Event PARTICIPANT may self-create only in ACTIVE before `purge_at`.
- Application create-or-open serializes before cardinality reads; one valid existing Project is returned unchanged. Legacy multiples are preserved without latest choice.
- Landing distinguishes no Project / sole Project / multiple legacy Projects; only eligible empty ownership has a Create CTA.
- New Project is TRUSS_2D, physical-draft-v2, empty version 0. No resources, Run, Snapshot or learning evidence precreated.
- GRACE preserves authorized history reads and existing minimal disclosure receipts, but denies authoring, Save, Check and Analyze.
- PURGED operational access fails closed on residual rows, including direct Prediction discovery and cached Event objects.
- Resource mutation services protect direct and Material → Strip → Section references from GRACE/PURGED indirect writes. No copying or Draft/deletion semantic changes.
- O-006 remains OPEN / FAIL CLOSED; ACTIVE account provisioning is still rejected for Manager and Developer.

## Fresh baseline before production/test edits

| Command / selection | Result |
| --- | --- |
| `pytest -q -m 'not browser'` | 537 passed, 306 deselected |
| Permissions + Event landing + reasoning endpoints | 25 passed |
| `pytest tests/mechanics -q` | 131 passed |
| Existing student entry + Workspace lifecycle subset | 5 passed |
| Django / migrations / diff | PASS / no changes / PASS |

## RED → GREEN record

- Task 2: 18 real failures before implementing GRACE/PURGED gates; then 36 targeted and 71 related tests passed.
- Task 3: missing create service produced 26 failures; implemented service passed 27 cases including rollback characterization.
- Task 4: all 7 real file-SQLite cases failed before serialization/revalidation/retry; all passed in three independent processes, then again at the checkpoint and final targeted verification.
- Task 5 / initial Task 7 browser RED: 23 endpoint and 2 browser cases failed before the route, form and presentation states existed. Targeted HTTP/provisioning/password regression: 40 passed.
- Task 6: 21 failures before the service-level resource guard and context gate. Then 64 resource/readonly tests and 17 Draft Independence/revision tests passed.
- Task 7: continuous real-browser public journey created resources and a triangle, saved/reloaded, passed Check, authored optional draft Prediction, normally analyzed successfully, exercised duplicate POST and GRACE history. Combined M7/entry/bridge subset: 17 passed.
- Visual inspection found readonly owner incorrectly labeled non-owner: one explicit HTTP RED preceded the template fix; targeted endpoint/workspace suite: 25 passed.
- Final review found direct Prediction discovery could bypass residual-read protection. Three direct-service tests failed before its guard; related permissions/Prediction/readonly suite then passed 109 tests.

One browser subset invocation could not bind its temporary live-server socket in the sandbox. It was rerun with explicit escalation and passed; this was not counted as product RED. A pre-review full browser run was intentionally interrupted to rerun against the final service fix, not reported as PASS.

## Final fresh regression

Post-review fresh non-browser: **640 passed, 7 skipped, 308 deselected**. Dedicated file-SQLite concurrency: **7 passed, no skips**. Mechanics: **131 passed**. Django check PASS; migration check reports no changes; diff check PASS. Final fresh browser run: **308 passed in 502.44s**. No manual acceptance PASS is claimed.

Browser stability disclosure: the preceding full run had **307 passed / 1 failed** in 528.66s. `test_poc_v1_full_student_journey_uses_public_controls` timed out at its final second-Reflection textarea; captured HTTP logs included Forbidden and a missing Reflection, not the earlier Workspace-404 incident. Its unchanged independent rerun passed (11.20s); failure-only HTTP/authorization tracing was then added without changing assertions, injecting DOM state, or adding sleeps. Standalone diagnostic run passed (9.44s), predecessor Workspace + journey subset passed (11 tests, 27.66s), and the next full run passed all 308. **ROOT CAUSE NOT YET PROVEN** for that single full-run failure; no production fix or false “flake fixed” claim is made. The final test retains failure diagnostics for future reproduction.

The default test run skips seven concurrency tests that deliberately require a file SQLite DB. They are separately executed **without skips** using:

```bash
PYTHONPATH=tests M7_TEST_DB_PATH=/private/tmp/<allocated-dir>/m7.sqlite3 pytest --ds=m7_concurrency_settings tests/application/test_project_creation_concurrency.py -q
```

The dedicated settings alter only pytest's TEST database path, not the application DB or production transaction mode.

## Architecture checkpoints

Task 4: PASS. Event no-op UPDATE obtains SQLite write serialization before current User/Membership/time/cardinality reads; bounded whole-transaction retries; no unique migration, latest selection or altered Event timestamps.

Task 6: PASS. `assert_resource_mutable()` is service-level authority. Existing update_section/delete_resource/rebind_strip_material and the encapsulated Material edit path are covered directly. Additional standalone owner-library HTTP/Strip CRUD endpoints: NOT APPLICABLE (none exist); no new endpoint was added.

## Independent review and deferred minors

Fresh read-only reviewer: gpt-6-astra; reviewed `8dc11a1..5bded68`. No Critical findings. One Important finding (direct Prediction discovery) received RED → GREEN repair. No second review is claimed; fixes are verified by regression.

Deferred Minor 1: strict create-field validation currently checks POST text but not uploaded `request.FILES`; an unsupported multipart attachment is ignored rather than rejected. Forged fields are not assigned and files are not persisted by this endpoint. The normal form has no upload field.

Deferred Minor 2: a sole BLOCKED v1 Project still receives the landing “继续建模” wording; Workspace remains read-only/export-capable, create-or-open rejects reuse, and no new Create CTA is offered. Unavailable-editing wording remains a follow-up.

The reviewer did not independently rerun supplied tests or claim full browser/manual acceptance; it did not promise PostgreSQL/raw-ORM uniqueness, reopen superseded O-003 decisions, or treat pure internal derivation functions as new public access boundaries. The executor retains those scope limits.

## Execution rulings

1. Create an explicit feature worktree despite the skill's existing-linked-worktree shortcut: protects main; no product cost.
2. HTTP tests inspect readonly/history contracts; real browser checks JS-rendered Results tabs rather than demanding tabs in SSR HTML. Risk if wrong: missing browser coverage; the actual four-tab journey ran.
3. Silent `git diff --check` needed a nonempty HEAD evidence line for the skill's completion script. No product impact.
4. Encapsulate existing MaterialForm editing in `update_material(actor, material, fields)`: required for one service mutation authority, not a new user entry point. Rollback would be a bounded adapter change, no migration.
5. Keep new resource tests in focused `test_m7_resource_guards.py`: same contract/commands, no product cost.
6. Combine duplicate/GRACE/history checks in one continuous public creation journey rather than seeding separate models: preserves evidence continuity, no product cost.
7. Defer reviewer Minor findings rather than adding polish to the final Important/Critical fix pass. Cost: the two documented low-severity behaviors remain for Owner review.
8. Respect the review's declined areas: no cross-database/raw-ORM guarantees or manual PASS. Cost: no assurance outside the frozen SQLite application boundary.
9. Retain failure-only diagnostics in the existing v1 browser journey after one unreproduced full-run failure; keep every assertion and timing behavior unchanged. Cost: extra diagnostic code, and no proven root cause for the earlier failure despite the fresh full GREEN run.

## Real browser evidence

Synthetic test account only; no real student data, screenshots are not mockups.

- [Empty new v2 Workspace](evidence/m7/new-empty-workspace.png)
- [Successful public analysis](evidence/m7/successful-results.png)
- [GRACE read-only historical Results](evidence/m7/grace-history.png)
- [Safe legacy multiple-Project conflict](evidence/m7/safe-create-conflict.png)

## Protected work and non-actions

- Root original four dirty files preserved; diff SHA-256: `a50343cd33b4f41fd07875f22026a6affb0417c64a8ad98082ffe71bdd5701d3`.
- Root DB unchanged SHA-256: `37eff5899edc02514bf6f70cae2df6de3d582e60e96b7ea6b043d16c91a4d17d`.
- Main remains `8dc11a1`; its original untracked planning document is preserved. Grid worktree clean and untouched.
- No model/schema/migration/Mechanics/Solver changes, real Project conversion, demo reseeding or fake AnalysisRun.
- No main merge, push, tag, deploy, or existing acceptance-server restart.

Owner manual product acceptance remains pending. No new Owner acceptance environment was provisioned in this implementation run.
