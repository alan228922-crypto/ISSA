# M9 implementation evidence

## Authority and execution

Owner approved the M9 TDD plan and Native sequential Tasks 1–8, Task 2 architecture checkpoint and one independent whole-branch review. Teacher Review is a human gate before Owner product acceptance, not a technical implementation prerequisite. No manual acceptance environment, merge, push, tag or deploy is authorized.

- M8 stable implementation: `96c335dc1c1d742d4143817c02a51a0fc3961892`.
- M9 repository/feature starting point: `619dd55fae7307027e449bfd67b99138d38d5d2e` (ancestry verified).
- Branch: `feat/results-teaching-loop-m9`; isolated worktree `.worktrees/results-teaching-loop-m9`.

## Planning artifact custody

Before writes, main's complete dirty inventory contained exactly these six approved artifacts. Each was copied individually to the feature and `cmp` returned identical. Original bytes are preserved in the Task 1 commit; approval/amendments are recorded here, without editing the carried originals before that custody check.

| Path | Main status | Source/copy SHA-256 |
| --- | --- | --- |
| `docs/specs/ARCHITECTURE_DECISION_REGISTER.md` | M | `f218cbeef8c1cbfc1294ff9ddf1234c94da4c721070aa3f90470eddcbee490c2` |
| `docs/specs/AUTHORIZATION_AND_EVENT_ARCHITECTURE.md` | M | `27a4e117a1e3d1bbff566f745a4414a7930b65be455b0008e5aba6f8dbfa0c59` |
| `docs/specs/MASTER_SPEC.md` | M | `06ea95525516e16f97e251f6c336e62d71776f1ba2e55818eb65f72999beef4f` |
| `docs/specs/README.md` | M | `e191c544e0c60005b1ddb080b6fcf745979c7904a523aa3a8fd30ae325d1e580` |
| `docs/superpowers/specs/2026-10-21-m9-results-teaching-loop-decisions.md` | M | `f6e2928caa1f898975ba954d38b40018958ef41c363193284b2e838fa1b65018` |
| `docs/superpowers/plans/2026-10-21-m9-results-teaching-loop.md` | ?? | `bc796f9246a4109d79b2bd64fa830bae5c6f51f74de04b3ef52673de3be596e4` |

Feature-commit custody: all six committed blobs in `7edbc64459bd9bd942fc41588e0868ccfc36e6f3` were byte-equal to the original main working copies and hashes above. Only then were the exact five tracked planning docs restored to main `619dd55` and the exact untracked plan working copy removed under Owner preauthorization. The removed working copy is fully recoverable from the feature commit. Main was verified clean at `619dd55`; no whole-directory copy, root changes, stash/reset/clean or real DB mutation.

## Protected initial state

- Root HEAD `84fe5e76a919ede92d831f81a2de79730af33ac7`; exactly the original four dirty paths: README.md, student-shell.js and the v1/v2 student-journey test files.
- Root binary diff SHA-256 `a50343cd33b4f41fd07875f22026a6affb0417c64a8ad98082ffe71bdd5701d3`.
- Root DB SHA-256 `37eff5899edc02514bf6f70cae2df6de3d582e60e96b7ea6b043d16c91a4d17d`.
- Main DB SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Grid HEAD `25aaed76e6ea810ef4e18a8f636ba3896c3da2b9`, clean. Existing root/main/grid worktrees preserved.
- Read-only process/listening inventory found no existing Django/gunicorn/uvicorn/GISWeb server; OS/Chrome/Code listeners were untouched. No acceptance server started.

## Fresh baseline — before production/test edits

| Gate | Actual result | Exit |
| --- | --- | --- |
| `pytest -q -m 'not browser'` | 781 passed, 22 skipped, 313 deselected; 110.31 s | 0 |
| `pytest tests/mechanics -q` | 131 passed; 0.68 s | 0 |
| `python3 manage.py check` | No issues | 0 |
| `python3 manage.py makemigrations --check --dry-run` | No changes detected | 0 |
| `git diff --check` | No errors | 0 |
| Bridge/v1/Node-joint browser subset from Task 1 | 15 passed, 0 skipped; 35.92 s | 0 |

Browser sandbox attempt first had 15 setup errors: OS denied `socket.bind` before any product interaction. Same unchanged subset outside the sandbox passed after authorization. This is environment evidence, not M9 RED or a production fix. The 22 non-browser skips are the existing dedicated file-SQLite exclusions, not claimed concurrency passes.

## Task 1 contract characterizations

New real-v2 HTTP tests check Run/project/source/revision/snapshot authority, legal no-Prediction Explain/results and byte-preservation of numerical input/result/snapshot/Prediction after disclosure. These are characterizations, not fabricated feature RED. `pytest tests/endpoints/test_m9_run_contract.py tests/endpoints/test_compare_explanation_json.py tests/endpoints/test_report_json.py -q`: **32 passed, 0 skipped, exit 0**, 4.13 s. Diff check exit 0.

## Remaining tasks

Tasks 1–8 technically complete, with fresh full gates and Important review findings closed. **M9 IMPLEMENTED — TEACHER REVIEW PENDING.** No Teacher/Owner PASS or acceptance-environment claim. Feature remains isolated; main unchanged.

## Task 2 — foundation, RED evidence and bounded decisions

- First focused run: 7 failed / 6 passed, 22.86 s. Genuine failures: supplied teaching state discarded by the old conclusion signature; list refresh left old presentation visible; obsolete refresh cleared newer selection; obsolete error escaped. Missing-module checks are not counted as independent behavioral RED. Existing detail-response token behavior was already GREEN.
- Real Workspace integration RED exposed two wiring assumptions: bootstrap uses `project.id`, and report mapping is analysis-segment -> PhysicalMember (`analysis/orchestration.py` passes `analysis_member_to_physical` to canonical input). The read-only presenter inverts existing identities for the unchanged `labels.js`; no geometry inference, new mechanics authority, backend or Report change.
- The initial Workspace state omits `dirty` until an edit. Normalize that existing clean/falsy state to an explicit boolean at the adapter boundary, rather than changing state/domain semantics. Existing overlay/focus tests and an added real-Workspace assertion caught the over-conservative linkage regression (11.24 s RED).
- Real UI dirty-same-version RED (10.78 s) proved the need for explicit unsaved/historical context without losing frozen evidence. Dirty linkage now checks live Workspace context in both directions; old overlays clear and original member labels/facts stay readable.
- Nonstandard immutable keys `__proto__` / `constructor` caused a real `.push is not a function` RED (2 failed, 9.28 s). A null-prototype transient identity dictionary fixes the projection without changing stable student naming.
- One additional old signature caller was found in `tests/browser/test_ux_debt_cleanup.py`; its focused fixture was adapted while retaining safe-ID/numerical-value assertions. No production fallback to raw Solver classification was retained.
- Intermediate full targeted run: 179 passed / 3 failed, 328.41 s. Named failures: real package integration, Canvas member -> teaching focus, failed-Run overlay clearing. They corresponded to the mapping/initial dirty adapter defects described above; a fresh fixed-version full rerun is pending, not claimed GREEN.
- Focused run before the key-edge tests: 15 passed, 29.42 s. Fresh fixed-version browser run including all new foundation tests, full Workspace, Node-joint and UX identity modules: **185 passed, 0 skipped, exit 0, 268.31 s**. Fresh non-browser: **784 passed, 22 existing file-SQLite skips, 328 deselected, exit 0, 155.53 s**. Django/migration/diff gates exit 0. No production changes followed that browser run before the Task 2 commit.

### Task 2 internal architecture checkpoint — PASS

| Gate | Evidence / authority |
| --- | --- |
| Every teaching input selected-Run scoped | Metadata/data/comparison/explanation/report/Reflection IDs validated; real v2 HTTP package exercised |
| No current Draft/resource-library substitution | Adapter accepts only Project ID, saved version and dirty boolean; all labels/facts from selected report/explanation |
| Snapshot labels only | Existing labels.js receives immutable snapshot with a transient inversion of supplied segment identities |
| Dirty same-version safety | Real public property edit preserves historical text/values and disables both focus directions/overlay |
| Refresh and response ownership | Generation/selection token protects clearing, list/detail successes and obsolete errors |
| No new mechanics/history/schema authority | Backend, Solver, idealization, domain models and migrations source diff unchanged; classification values copied, not recomputed |
| Protected state | Root diff and DB hashes unchanged; main/grid clean |

Reflection authoring asynchronous ownership remains explicitly Task 6, not claimed fixed by this Run-context checkpoint. Continue Task 3 without another Owner approval, as authorized.

## Task 3 — three-level explanation

- Observed pre-implementation RED: no Level 1/2/3 sections (`dict_keys([])`), 1 failed in 2.75 s; initial full new module 5 failed in 98.16 s.
- Minimal presenter now separates conclusion, complete segment/candidate evidence, and collapsed professional values/source. Existing structured message levels are used only through safe copy projection; raw candidate IDs are replaced with snapshot-derived names. True forces/ux/uy/magnitudes remain supplied values; no mechanics calculation.
- First implementation: 4 passed / 1 failed. Playwright showed the test's appended component was behind the existing Workspace footer; fixed only the focused fixture mounting location (actual visible Results panel), not assertions or production layout. No force click or added sleep.
- Fresh required Explain + Bridge + UX identity browser command: **50 passed, 0 skipped, exit 0, 209.88 s**. Fresh non-browser: **784 passed, 22 existing concurrency skips, 335 deselected, exit 0, 301.97 s**. Diff and syntax checks pass.
- Backend/mechanics/domain/migration source diff unchanged; main/grid still clean. No acceptance environment or Teacher/Owner PASS claim.

## Task 4 — member prediction evidence

- RED: a selected-Run TeachingView was incorrectly shown as no Prediction, instead of the supplied MATCH state (1 failed, 3.11 s).
- Minimal projection copies backend predicted state/status and complete segment evidence, validating consistency with the same selected package. No JS force/state/threshold/match calculation. UI uses 一致/不同, preserves UNSURE and NOT_COMPARABLE, shows all segments including a deliberately larger opposite-sign segment, and names path evidence 学生传力假设.
- Named browser + Explain + legacy MIXED fixture regression: **14 passed, 0 skipped, exit 0, 22.50 s**. Existing backend Comparison/Explanation: **40 passed, exit 0, 0.20 s**. Fresh non-browser: **784 passed, 22 existing concurrency skips, 343 deselected, exit 0, 138.14 s**.
- Template and the existing focused MIXED fixture were adapted to the approved shared TeachingView renderer interface; no raw-result classification fallback retained. Conclusion adds a neutral supplied-status summary, not a score or ranking.

## Task 5 — displacement location comparison

- RED: predicted location was null instead of the server's Node N2 (3.89 s), and a missing authoritative result incorrectly remained available (2.55 s).
- Projection now preserves complete server candidate IDs/values and supplied match boolean, checks same-package consistency, and resolves NODE / legacy CONNECTION / MEMBER_ENDPOINT through immutable snapshot identity and labels.js. No browser maximum, norm, tie tolerance or location-match calculation. Missing/invalid facts are unavailable, not 0 mm; valid zero ties remain visible. No predicted magnitude/percentage field.
- Required displacement/member/Run browser regression: **37 passed, 0 skipped, exit 0, 53.42 s**. Node-joint learning/Comparison/Explanation: **46 passed, exit 0, 3.73 s**. Fresh non-browser: **784 passed, 22 existing concurrency skips, 355 deselected, exit 0, 132.50 s**. Diff and protected backend source checks pass.

## Task 6 — same-Run Reflection ownership

- RED: no evidence-to-Reflection navigation (8.77 s); an old A response replaced B rather than returning null (4.21 s).
- Navigation now selects the existing same-Run Reflection panel without POST/save/auto-fill/complete. Authoring captures an immutable selection binding and queues operations per binding, not across Runs. Obsolete load/save/complete success/errors and inline UI callbacks cannot alter the new form/progress/error; completed server policy remains unchanged. Unsaved local text is cleared with an explicit notice, never silently saved or carried to B.
- Initial targeted run: 35 passed / 2 failed. Read-only diagnosis proved two fixture issues: direct ORM under the Playwright loop needs a test-only worker thread; authoring in the inherited DRAFT Event correctly returned `REFLECTION_EVENT_NOT_ACTIVE` (not CSRF). The authoring fixture now uses ACTIVE; first Reflection creation correctly expects existing HTTP 201. No production authorization, CSRF or service change.
- Fixed targeted Reflection/Run/legacy browser run: **37 passed, 0 skipped, exit 0, 38.37 s**. Additional genuine HTTP tests for unsaved-text isolation and delayed A-save/B-local-text preservation: **2 passed, 6.17 s**. Explicit persisted private-DRAFT Manager/Developer checks: **2 passed, 6.58 s**, no raw text/authoring controls exposed.
- Application Reflection / HTTP / permissions: **63 passed, exit 0, 15.73 s**. Fresh non-browser: **784 passed, 22 existing concurrency skips, 373 deselected, exit 0, 144.85 s** (before the two additional browser-only cases). Source boundaries/diff pass.

## Task 7 — real public v2 teaching loop and history

- Synthetic setup supplies only an ACTIVE participant, empty v2 Project and owner catalog. New browser context logs in through the real form/events link. Actual Canvas pointer actions create the triangle/supports/load; public Save/reload/Check, authored Prediction (members/location/path), Analyze, selected evidence and self-authored partial-save/complete Reflection all persist normally. No seeded AnalysisRun, transport mock, state injection, force-login cookie or direct renderer/controller call in either primary journey.
- Initial fixture errors: password label includes punctuation (use the real named input); the floating numeric overlay intercepted a third-member endpoint (use the existing public dynamic-input toggle for this pointer-only journey); an extra Reflection request field was rejected before lifecycle authorization. These are test setup corrections, not M9 production changes. The existing dynamic-input overlap is noted for later CAD consideration, not silently fixed here.
- Initial integrated history assertion compared the entire Report envelope. Its live current-version/staleness and completeness indicators legitimately change. The corrected assertion pins every immutable report section and immutable provenance field while explicitly requiring the historical warning; no numerical/history contract changed.
- Final public browser modules: **5 passed, 0 skipped, exit 0, 24.48 s**. Required endpoint/M7-readonly/Node-joint-learning command: **33 passed, 0 skipped, exit 0, 3.90 s**. Integration is already GREEN after Tasks 2–6, not fabricated feature RED.
- Both Prediction/no-Prediction journeys create genuine successful Runs and complete typed Reflection. History creates A and B via public controls, changes member description, material E, load and Prediction/Reflection, returns to A and checks all original immutable HTTP facts and no current Canvas overlay. GRACE reads selected history but denies valid authoring requests; PURGED residual Run reads/writes fail closed.
- Genuine screenshots retained under this plan's ignored `screenshots/`: conclusion/comparison/Explain/evidence/Level 3/Reflection at 1024/1280/1440. Screenshots contain disposable synthetic data only. Teacher Review and Owner acceptance remain PENDING; no manual environment started.

## Task 8 — independent review and bounded fix pass

- Exactly one fresh-context read-only whole-branch review inspected `619dd55..6c655c5`: no Critical findings; R1/R2 Important and R3 Minor. Full findings/considered-and-set-aside rulings are recorded in `M9_REVIEW_AND_ACCEPTANCE.md`. No independent re-review or Teacher PASS fabricated.
- R1 genuine RED: after a real unsaved property change Technical Data still said it corresponded to the current model. R2 genuine RED: obsolete initial list success produced a false error, and pending Save/Analyze replaced explicitly selected B. First R1/bootstrap run: 3 failures (two behavior failures and one test route/response timeout), 52.52 s. Pending operations: 2 behavior failures, 18.22 s.
- One bounded fix pass updates live context notices across selected evidence panels, preserving immutable values/labels; render-on-demand uses current compatibility only. Bootstrap ignores obsolete null; Save/Analyze keep server operations legitimate but do not clear/replace B's selected presentation, stage or error. Current non-obsolete errors remain visible. No backend/request/schema change.
- First corrected core set: 5 passed, 17.56 s. Expanded actual caller cases cover late success/error for both Save/Analyze. A test could intercept the previous document's unfinished initial list before reload; it now waits on actual first-document discovery before installing the reload interceptor. B's evidence must be fully loaded before releasing A's request. These are request-ownership conditions, not fixed sleep or production retries.
- An intermediate wiring run had one unexpected real Analyze HTTP 500 (1 failed / 24 passed, 42.38 s); cause was not proven and no backend fix claimed. Another had one old-document response timeout (1 failed / 24 passed, 80.40 s). The final owned-request core is **7 passed, 17 deselected, exit 0, 17.71 s**. Fresh full regression remains the completion gate.
- First full browser regression: **379 passed / 1 failed, 725.69 s**, named `test_analysis_opens_conclusions_then_evidence_tabs`. Its old no-Prediction sentence was no longer a substring; bounded copy retains it plus the new availability explanation. Its next assertion required visible axial-force evidence context, now explicitly introduced in Level 2 while exact values remain collapsed in Level 3. No existing assertion weakened. Subsequent wiring run passed that legacy journey; fresh complete rerun is in progress.
- Controlled UNSURE/MIXED/tie screenshots are explicitly labeled focused supplied-fact cases, not public Solver outcomes. Public triangle screenshots remain actual public Analyze evidence.
- Initial whole-branch non-browser: **784 passed, 22 existing file-SQLite skips, 380 deselected, 177.08 s**. Post-fix fresh non-browser: **784 passed, 22 existing skips, 387 deselected, exit 0, 152.46 s**. Post-fix mechanics **131 passed, 0 skipped, exit 0, 0.95 s**; M7/M8/permissions command **155 passed, 0 skipped, exit 0, 80.18 s**. Dedicated file-SQLite is NOT REQUIRED — no affected authorization/resource/transaction/provisioning dependency; skipped memory-mode tests are not claimed concurrency PASS.

## Final regression and handoff

| Fresh corrected-source gate | Result | Exit |
| --- | --- | --- |
| `pytest -q -m 'not browser'` | 784 passed, 22 existing skips, 387 deselected; 152.46 s | 0 |
| `pytest tests/browser -q` | 387 passed, 0 skipped; 614.12 s | 0 |
| `pytest tests/mechanics -q` | 131 passed, 0 skipped; 0.95 s | 0 |
| N's M7/M8/permissions command | 155 passed, 0 skipped; 80.18 s | 0 |
| Explicit seven M9 browser modules | 74 passed, 0 skipped; 145.28 s | 0 |
| `pytest tests/endpoints/test_m9_run_contract.py -q` | 3 passed; 4.50 s | 0 |
| `python3 manage.py check` | No issues | 0 |
| `python3 manage.py makemigrations --check --dry-run` | No changes detected | 0 |
| `git diff --check` | No whitespace errors | 0 |

All final production/test edits belong to `058fa0c`; later handoff edits are documentation only. A combined early browser+endpoint invocation selected browser markers and deselected the 3 endpoint tests; they were explicitly rerun separately as shown, never counted as skipped verification. Full split suite totals 1,171 passed plus 22 existing conditional file-SQLite skips, with no browser skip.

| Task | Commit / outcome |
| --- | --- |
| 1 | `7edbc64` custody/baseline/characterization |
| 2 | `984559c` selected-Run projection/races; internal architecture checkpoint PASS |
| 3 | `08bf749` three distinct explanation levels |
| 4 | `a28b6e3` neutral complete member evidence |
| 5 | `41a7bc2` supplied displacement candidates/location comparison |
| 6 | `8582267` same-Run Reflection/ABA/late-response protection |
| 7 | `6c655c5` genuine public v2, history/lifecycle proof |
| 8 | `058fa0c` single bounded Important-finding fix pass, followed by the docs-only handoff commit containing this table |

R1/R2 are CLOSED by real failing regressions, corrected targeted GREEN and final 387-test browser GREEN. R3 is a deferred minor; no second agent review or Teacher outcome inferred. Teacher task sheet, all considered-and-set-aside rulings, known limitations and genuine screenshot provenance are in [review and acceptance](M9_REVIEW_AND_ACCEPTANCE.md). 24 screenshot artifacts include the named public and controlled cases; the diagnostic image is not acceptance evidence.

Protected-state final check: root remains exactly the original four dirty files; aggregate diff `a50343cd33b4f41fd07875f22026a6affb0417c64a8ad98082ffe71bdd5701d3`, root DB `37eff5899edc02514bf6f70cae2df6de3d582e60e96b7ea6b043d16c91a4d17d`. Main remains clean at `619dd55`, grid clean at `25aaed7`; main and feature on-disk DBs remain empty SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. No existing DB/server changed; no manual environment created. Solver/mechanics/idealization/analysis/learning/domain/permissions/M7/M8/material services/labels/workflow/report/grid/dependencies source diff is unchanged. Schema/migration/new model/new persisted facts: NO. No merge/push/tag/deploy; keep feature worktree/branch and ignored genuine evidence for the pending human review.
