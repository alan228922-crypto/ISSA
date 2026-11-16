# AV-01 Phase 2 — Task 3–5 implementation

Date: 2026-11-11 (Asia/Shanghai). Branch: `feat/av01-phase2-visualization`.
Base: `ea359eb535a040cd8c2eb8dd54a0d2592d2bed6a` (verified clean Phase1). Product commits: `fd8e1694b4ba1c0db7444da4e4e0da30e78a8503` Task3; `76329eb346db79fcfc4dbed494657e204421d546` Task4; `4001383c418f96554cb4d19f764d84225fa4c46a` Task5. Follow-up fixes: `30504169679bc2c024fe440f2ccaccbbc6cb10e5` maximum markers; `87e00b6cee193709a8073ff92f05a70dd76091f8` label/notice collision. Review fixes: `87692a47b5bae0c8364c7b4482da51e1029148bb` clear/reset. This is the final tested product-code commit; the following documentation commit changes only this report.

## Scope and authority

Owner authorized original Tasks3–5 only. This scoped authorization supersedes older Phase1-only status prose; MASTER_SPEC v1.12 and approved Spec/Plan engineering contracts are unchanged. Phase1 Projection/API reused without changes. No Solver, mechanics, models, schema, Run, Revision, Draft, Results controller/template, CAD or global Workspace CSS changes.

Approved §11 governs the four controls: 外部荷载 / 支座反力 / 拉压状态 ON; 变形图 AUTO OFF. Original geometry has no off switch; deformation always retains its ghost. This resolves the Owner summary's original-layer-toggle shorthand in favor of the approved contract. Passive numeric disclosure supplies overflow values, not the deferred Task6 selectable object list/Inspector. Local reset/view methods are initial Task3/5 interfaces, not Task7 production Run lifecycle integration.

## Implemented

- **Task3:** saved nodal Rx/Ry, signed horizontal/vertical screen arrows (+Y upward), N units, original-position anchors, one reaction pair per node even with multiple supports. Saved zero has no directional glyph and an explicit zero notice; tiny nonzero remains nonzero, missing/invalid remains unavailable. Six-significant-digit/scientific display plus exact saved values under native disclosure. Snapshot labels reuse unchanged `labels.js`; no raw internal identifiers in copy. Collision fallback has a visible notice and real numeric table, never invented per-support shares.
- **Task4:** display-only x+αux / y+αuy on saved analysis-segment endpoints, including intermediate joints; no curves or whole-member shortcut. AUTO uses supplied same-Run M9 maximum and geometry bounds, never searches for/reclassifies a maximum. α≥1, capped at10000; complete displacement prerequisite, explicit zero/tiny/unavailable and amplified/×1 notices. Original ghost cannot be hidden; force anchors remain original. Explicit Fit includes original+displaced union; ordinary toggles/pan/zoom preserve viewport/α/facts.
- **Task5:** four native keyboard-operable checkboxes, readable disabled reasons, transient per-instance state/reset, no persistence or editor coupling. External loads remain separate saved rows; Fx/Fy point toward original nodes, no implicit sum. Force styles use matching M9 per-segment classifications/values; absent/mismatched evidence produces neutral geometry. MIXED members retain distinct segment facts. All supplied maximum candidates retain markers. Full per-load/reaction/displacement values remain available on demand.

New production files: `analysis-visualization.js`, `analysis-visualization-renderer.js`, `analysis-visualization.css` under `projects/static/projects/workspace/`. Tests: new `av01_harness.py`, `test_av01_reactions.py`, `test_av01_deformation.py`, `test_av01_layers_evidence.py` under `tests/browser/`. This report is the eighth changed file; no existing product file was modified.

## RED → GREEN and fresh QA

| Evidence | Actual result |
|---|---|
| Fresh base Projection/API + Mechanics | 298 passed |
| Fresh base public M9 + KB01 Browser | 31 passed |
| Task3 initial RED | 27 behavior failures / 2 harness setup errors; corrected test-only Django/Playwright threading without async-unsafe bypass; genuine v1/v2 cases then each demonstrated missing-renderer RED |
| Task3 intermediate / final | 28 passed /1 collapsed-details assertion failure corrected by opening actual summary; explicit zero-notice RED; final31 passed |
| Task4 RED / initial GREEN | 29 failed →60 combined passed |
| Task4 visual correction | Actual screenshot exposed collinear ghost occlusion; pixel regression1 failed → ghost-only screen stroke2→5px, unchanged0.45 opacity/no geometry offset; final61 combined passed |
| Task5 RED / correction | 19 failed; first combined79 passed/1 scaling-copy regression, restored wording; supplemental per-load exact-fallback1 failed |
| Task3–5 combined initial GREEN | **81 passed**, 152.45s; no failures/skips |
| Final Spec cross-check corrections | Original-position maximum markers:1 RED→2 targeted GREEN→82 combined PASS94.53s. Crowded force labels hidden by scale notice:1 RED→1 targeted GREEN; reserve notice areas before label placement. Pre-review **83 passed**,86.40s; no failures/skips |
| Final review-fix regression | **86 passed**,159.73s, no failures/skips (`final-components-resumed`); three real review REDs→three targeted GREENs before full affected regression |
| Relevant non-browser | **364 passed**, 25.98s; Projection/API, M9 Run/Reflection, permissions, Mechanics |
| Mechanics | **131 tests included in364**, a subset, not an additional total |
| Existing M9/CAD Browser regression | **128 passed**, 417.70s; no failures/skips |
| Django check / migration dry-run | No issues / no changes detected |
| Independent whole-diff review | 0 Critical,2 Important; both reproduced by3 Browser REDs, fixed, targeted3 GREEN; focused static reinspection: no remaining confirmed Critical/Important/Minor |

GREEN runs preceded their bounded commits: command metadata records the then-HEAD, with the tested working changes subsequently staged verbatim in the listed commit. Final source fingerprints identify those same production blobs. Later changes were isolated renderer marker/notice and component clear/reset fixes plus report; unrelated backend/public-M9 regression need not be repeated for notice/marker drawing.

All DBs are test-owned: memory SQLite for backend checks; unique private file-SQLite directory for each Browser invocation. Completed-run metadata confirms caffeinate guards released. The first final86-case invocation was interrupted with no result; its PID was confirmed absent and a fresh isolated replacement run was started. The incomplete log is retained and not counted as PASS/FAIL. No Owner DB/service used. No complete Browser/non-browser suite rerun: changed product code is new/unmounted, and relevant public workflows are checked separately. Historical551 Browser/816 non-browser/22 file-SQLite concurrency skips are not fresh results or concurrency PASS.

Independent review was static: its attempted no-server Chromium probe was sandbox-denied, and the approval-blocked retry was interrupted by the parent. It did not independently rerun Browser QA. Parent-run Browser evidence below is distinct. Raw findings/fix disposition: `independent-review.md` in the evidence directory.

## Real Chromium evidence

Actual screenshots come from a test-only isolated carrier importing the production renderer/CSS. They are **not public Results integration or Owner acceptance evidence**. Controlled sign/deformation/MIXED/tie facts are labeled as supplied facts; genuine direct-support-load v1/v2 cases obtain a real saved Run through authenticated API/reveal and render its Phase1 projection (including the support-applied load).

Evidence directory (ignored, retained): `.superpowers/sdd/2026-10-27-av01-analysis-visualization/`. It contains commands/settings/isolated-DB metadata, raw logs, JUnit, result JSON, protection/source fingerprints, screenshot index and visual-calibration before/after evidence.

- Combined layers, actual viewports [1024×768](../../.superpowers/sdd/2026-10-27-av01-analysis-visualization/screenshots/task5-combined-1024x768.png), [1280×800](../../.superpowers/sdd/2026-10-27-av01-analysis-visualization/screenshots/task5-combined-1280x800.png), [1440×900](../../.superpowers/sdd/2026-10-27-av01-analysis-visualization/screenshots/task5-combined-1440x900.png). Inspected wrapping, visible ghost/notice, no horizontal overflow.
- Saved reaction [v1](../../.superpowers/sdd/2026-10-27-av01-analysis-visualization/screenshots/task3-genuine-direct-load-physical-snapshot-v1.png), [v2](../../.superpowers/sdd/2026-10-27-av01-analysis-visualization/screenshots/task3-genuine-direct-load-physical-snapshot-v2.png), actual1280×800.
- `ghost-calibration.json` and `before-ghost-task4-deformation-*` retain the real reason for provisional ghost calibration. Final arrow/label/ghost calibration and full matrix remain Task8/Owner work.

## Protected state and gates

Original12 worktree HEAD/status/binary dirty diffs, original branch refs and9 protected file/DB fingerprints checked unchanged. Root's existing dirty files and original M9 untracked documents remain untouched. Original approved source SHA: Spec `b4fff4cc644bc6d72aa8b7f11ebf1abfea03126599ef710319ddc59b60865da5`; Plan `ebb7e1075f0ff4eff605cf3365cdb715c463690bbeb7fb6a6d51da6edbdd8d98`. Phase1 synchronized tracked files unchanged here: Spec `90f686790cdf989ed3a5258efe4fdfd4e2c6a0144267e6d1146f3a701b92fd52`; Plan `22cdf3ab955ca9607b4f5efd625f31cb2ec5cd63174d22f95f49b76a793dc023`.

Task6 Object Evidence/Hover, Task7 public Results lifecycle/race integration (including W03 keyboard isolation), Task8 full visual/browser matrix, Task9 final whole-AV01 branch review, Task10 Owner package remain pending authorization/completion. This phase review does not replace Task9. No production visualization mount or Owner runtime was created. No merge/push/deploy. M9/CAD Owner Acceptance remains PENDING; Teacher Review DEFERRED. Owner visual calibration and remaining implementation require later decisions.

**AV-01 PHASE 2 — TASK 3–5 IMPLEMENTED, QA VERIFIED, NEXT TASKS PENDING APPROVAL**
