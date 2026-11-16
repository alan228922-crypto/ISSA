# AV-01 Phase 1 implementation evidence

Owner authorization 2026-11-10: Task 1–2 only. Baseline main b5873ecc80996dc0561bba313f7053bf65ad023d; isolated feat/av01-phase1-projection. No renderer/Hover UI/Task7 implementation.

Original approved Spec/Plan custody: 59731b0; status synchronization: a5e2679. Original M9 files retain approved SHA/untracked state. Custody manifest preserves provenance. Engineering contracts unchanged.

## Task 1

Fresh baseline: permissions / M9 run contract / report / mechanics: 175 passed (9.19s). Real Chromium public teaching loop / history permissions / Run context: 29 passed (92.68s), fresh test-owned fileSQLite. Existing full integration QA at the same base remains historical evidence for this Sprint, not relabeled fresh.

New v1/v2 characterization asserts saved graph/supports/loads, ux/uy, Rx/Ry, axial force, segment mapping and immutable linked Revision after genuine new Draft/library edits and Run B. Initial characterization: 2 failed/5 passed, due exact hand-derived -100 versus saved -99.99999999999999; corrected analytic expectation to approx, no product change. These are not manufactured feature RED. New projection tests will require exact saved-value preservation.

Task 1 GREEN: 7 passed, includes 4 new characterization cases and 3 existing M9 contract tests. Saved-fact characterization is expected GREEN by the approved plan. Task2 RED boundary is missing visualization builder/endpoint/bootstrap; no Task2 production code yet.

Raw commands/JUnit/logs are retained in ignored .superpowers/sdd/2026-10-27-av01-analysis-visualization/. Existing DBs and Owner runtimes are not used.

## Task 2 — first implementation / architecture checkpoint

Initial RED: 117 failed /4 existing characterization passed (14.20s); missing builder/route/bootstrap. Supplementary exact identity tests: 2 failed, then restricted to the applicable fixture rather than keeping two artificial applicability skips. First implementation: 122 passed /1 stale test Project setup failed; refreshed the intermediate-joint fixture only. Defensive RED: 10 failed /5 passed (malformed endpoint type, unit/schema checks and specific missing-data reason), followed by minimal validation fixes. Final targeted projection/endpoint + existing M9/report: **147 passed (9.70s)**.

Architecture checkpoint: canonical saved graph + exact Snapshot identity enumeration; no topology reconstruction, Solver or current Draft reads; layer-local availability and exact numeric copy; same-node support union only validates saved constraints, never distributes reaction; per-row loads preserved. Linked Revision/project checked. New GET reuses read authorization + existing lifecycle cutoff, exact Run lookup, existing owner reveal prerequisite and Manager/Developer exemption; no reveal creation, DB write or new permission mechanism. Every response private/no-store. W01 only adds visualization_template. No frontend controller/epoch/renderer change; existing M9 race tests remain the authority until Task7.

New API returns data only; no student UI/arrow/ghost/hover/grip change. Missing displacements remain null, no fake zero, malformed shared graph empty/unavailable; programmer exceptions are not converted to READY. Full non-browser and expanded M9/KB01 Browser gates are executing on the frozen source, with test-owned DBs. Later Tasks remain pending.

## 2026-11-11 resumed QA / independent review

Owner confirmed shutdown yesterday. Previous long QA processes/temp settings disappeared; their logs have no final JUnit or exit result, and are INCOMPLETE. The original runner also incorrectly matched `browser` inside `nonbrowser`, selecting the same test-owned fileSQLite as Browser during concurrent runs. This runner isolation bug is a plausible source of setup E, not a confirmed product defect; raw incomplete logs retained. Resume uses a new0700 directory and explicit --file-sqlite flag; memory nonbrowser is separate. No existing Owner DB was involved; original Owner temporary runtime DB is now absent after shutdown, not recreated.

Fresh full nonbrowser diagnostic (-x) reached 667 passed /1 failed (157.48s), with no setup E: tests/endpoints/test_workspace.py exact key/value assertions lacked the Owner-approved W01 visualization_template. Added only the key and precise path, preserving every old assertion; this corresponding W01 test adjustment is not changed permissions or weakened coverage.

One successful independent whole-diff review of b5873ec..8cf2aed by a fresh read-only reviewer: no Critical, 1 Important (missing/invalid required hash still READY), 1 Minor (integer-coordinate difference overflow). Earlier quota failure produced no review. Executor regraded the overflow as the required malformed-data correctness boundary and included both in one bounded fix pass. 30 genuine RED cases (28 hash-format/provenance, 2 integer overflow; 4.11s) → validate existing hash representation only, no recomputation; invalid shared provenance returns UNAVAILABLE/empty facts with unusable hash anchors null; catch only OverflowError around length validation. No Solver, thresholds or saved value changes.

Review-fix targeted GREEN: 168 passed (13.21s), including all AV01 application/endpoint tests and exact Workspace bootstrap contract. Final full nonbrowser /128 M9+KB Browser and system/migration gates run next on frozen commit. New visualization races/rendering/keyboard isolation remain unimplemented/unverified Task7+ work, not claimed complete.

## Final Phase 1 GREEN — 2026-11-11

Frozen code commit80ecee9: full non-browser **983 passed/22 skipped/551 deselected (226.39s)**; all M9+KB01 relevant real Chromium **128 passed (469.96s)**; Mechanics **131 passed (1.27s)** is a non-browser subset. System check0 issues; migration dry-runNo changes; no model/schema changes. Review fixes targeted168 passed (13.21s) is also a subset, not additive. New AV01 cases total167 are within983. All completed commands exit0, JUnit retained. 22 concurrency skips listed individually, not concurrency PASS. Original full551 Browser integration QA is historical; unchanged full Browser was not rerun under Phase1 authorization.

Independent findings closed by real30-caseRED→GREEN and final suites, not an invented second reviewer verdict. No deferred minor remains: integer overflow was treated as a correctness-boundary fix. The review only covered Phase1; no Task3+/full-feature acceptance claimed. Original source/custody hashes and old worktree state remain protected; Owner's old temp runtime DB disappeared after acknowledged shutdown, not restored or tested. Report and fingerprint evidence identify both original and amended documentation versions.
