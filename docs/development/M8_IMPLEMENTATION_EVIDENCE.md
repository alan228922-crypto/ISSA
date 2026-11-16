# M8 — implementation and verification evidence

Status: **M8 OWNER MANUAL PRODUCT ACCEPTANCE: PASS** — Owner decision dated **2026-10-20, Asia/Shanghai**. Accepted implementation HEAD: `5eea16eff337ca458dd5f2a8803571f08c8d2de0`. Local integration and fresh post-merge verification are separate gates, not claimed complete by this acceptance record. Earlier implementation-stage entries below retain their historical attribution.

## Contract and isolation

Baseline main `fa9c000ddbff89adc41a34711bf44a0b509d19fe`; isolated branch `feat/event-participant-management-m8`.
Owner approved native sequential Tasks1–9, with Task4 credential checkpoint, Task6 SQLite checkpoint, and Task9 one independent whole-branch review. Binding decisions: [M8 contract](../superpowers/specs/2026-10-18-m8-event-participant-management-decisions.md); [approved amended plan](../superpowers/plans/2026-10-18-m8-event-participant-management.md).

The original main planning artifact and isolated feature copy both SHA-256 `9e062694843d86ce847ac848184e244866ae927dc590802ccb23635bf32dc5bc`, cmp exit0. Only after verification was the original untracked main copy removed. Main remains at the baseline, clean. Root original four dirty files, root DB and grid were not used or changed.

Root binary diff SHA-256 `a50343cd33b4f41fd07875f22026a6affb0417c64a8ad98082ffe71bdd5701d3`; root DB SHA-256 `37eff5899edc02514bf6f70cae2df6de3d582e60e96b7ea6b043d16c91a4d17d`. Grid HEAD `25aaed76e6ea810ef4e18a8f636ba3896c3da2b9`, clean. No real DB migration, demo seed, acceptance-server startup or real account operation.

## Fresh baseline before production/tests

| Gate | Result |
| --- | --- |
| Non-browser | 640 passed,7 skipped,308 deselected,34.06s |
| Permissions/landing/reasoning/provisioning | 45 passed,9.47s |
| Mechanics | 131 passed,0.55s |
| Entry/M7 browser | 5 passed,11.51s |
| Exact three Workspace browser nodes | 3 passed,6.48s |
| Django/migration dry-run/diff | exit0 |

Default concurrency skips are intentional in-memory exclusions, not claimed concurrency evidence. Dedicated file-SQLite runs below execute every collected case without skips.

## Sequential implementation record

| Task | Commit | RED / GREEN evidence |
| --- | --- | --- |
|1 contract/baseline | f5d7bcd | docs-only; no fake RED; fresh baseline above |
|2 central authority |632a471 |8 behavioral failures;24 targeted,122 broader,78 completion PASS |
|3 audit field |db60956 |22 failures for missing approved field/validator/migration;22 PASS incl forward/reverse and legacy preservation |
|4 opaque preview |0bfd7f3 |32 failures/2 PASS, then34/75 PASS; expired-after-close RED1→GREEN;76 expanded and62 completion PASS;706 non-browser PASS |
|5 lifecycle |a39a628 |22 missing-service failures;104 targeted PASS;78 M7/readonly/resource PASS; genuine successful v2 Run preserved |
|6 concurrency |b346516 |staged4 missing-API failures before Task5, not claimed as race reproduction; three independent15/15 file runs,0 skip; M7 7/7,0 skip |
|7 SSR |a9172bd |HTTP11 failures and real browser missing-entry RED1;108 targeted,50 completion PASS; browser GREEN1; named NOOP copy RED→GREEN |
|8 public journey |e1441dc |public Manager→Student forced-password-change→M7 create/resources/model/save/check/analyze;5 new browser PASS;13 new/old completion PASS37.43s |
|9 independent review/final regression |8797dc2 fix; this evidence commit |ABA and CSV safe-boundary named RED→GREEN6/6; affected112 PASS; affected browser5 PASS; fresh full browser313 PASS |

## Checkpoints and security evidence

Task4 PASS: one default-DB Session row per opaque preview; no auth impersonation keys. Only server preview/User contains Django password hash. Credential canaries absent from response, HTML, logs and audit. No signed credential-bearing token compatibility path remains. CSV UTF-8/BOM, byte/row/column/number bounds and normalized1/01 duplication covered; two-row failure is all-or-nothing. Consumed preview is hash-free, same-reference retry returns the existing receipt. Invalid, unauthorized, malformed, cross-bound, expired and role-conflict attempts produce no BulkImportBatch business receipt.

TTL600 is **SERVICE ACCESS CUTOFF**, not automatic physical deletion. An encountered expired owned preview is deleted before refusal, including after Event closure; cleanup commits instead of rolling back with the refusal. Tests prove abandoned expired Session rows are physically removed by Django `clearsessions`. Existing maintenance must run that command for abandoned rows; no scheduler/worker/preview model was introduced.

Task6 PASS: Event no-op UPDATE is the first database operation in mutation transaction. Independent SQLite connections verify fresh actor/Event/target after waiting, active role+exact active Membership, stale opposing preview protection, one-effect/one-receipt replay, controlled busy retry5 attempts and exhaustion, rollback of candidate mutation/audit/consumption, and M7 waiting create observing deactivation. Task9 independent review found the additional ABA cycle case; named dual-direction RED→GREEN now binds pending expected state to the existing latest successful mutating qualification receipt. NOOP/unrelated-target receipts do not invalidate a preview; consumed historical replay never repeats a mutation. No schema was added for this marker.

Task6 dedicated DBs: `/private/tmp/isaa-m8-gate1-UQDidj/m8.sqlite3`15 PASS6.44s; `/private/tmp/isaa-m8gate2-qRMEyh/m8.sqlite3`15 PASS6.33s; `/private/tmp/isaa-m8gate3-ebYDeC/m8.sqlite3`15 PASS6.53s. M7 `/private/tmp/isaa-m7gate-FUL0tk/m7.sqlite3`7 PASS2.49s. Task6 completion fresh fourth process15 PASS6.40s.

## Scope and rollout

Only migration: `competitions/0003_bulkimportbatch_operation_details.py`, one AddField JSONField(default=dict,blank=True). Legacy batches retain `{}` with no fabricated details. Apply only to a separately authorized target environment; no real DB migration was performed here.

M7 `projects/creation.py`, User/EventMembership/Project schemas, Draft, Node-as-Joint, Delete Impact, resources, historical snapshots, Solver/Mechanics/units remain unchanged. M8 creates User/Membership only, never Project/resources/revision/Run/snapshot. Existing credentials/global flags and other Event Memberships are preserved. GRACE is read-only; PURGED operational access fails closed.

O-004 remains OPEN. Following formal Owner acceptance on 2026-10-20, O-006 is **RESOLVED — APPROVED SCOPE ONLY**: DRAFT CSV and DRAFT/ACTIVE single CREATE_USER, JOIN_EXISTING, REACTIVATE and DEACTIVATE. ACTIVE CSV, public signup/join codes, Manager assignment/revoke/participant-to-manager promotion, impersonation, administrator password reset, global User recovery, Event transitions/scheduler and automatic Project provisioning remain denied/out of scope. This is not completion of all Event administration.

## Visual evidence

Screenshots contain synthetic test accounts only, no password inputs, cookies, raw payload, hashes or hidden preview references. Representative screenshots were opened and inspected; this is engineering inspection, not Owner manual PASS.

- [New-team confirmation](evidence/m8/screenshots/manager-confirm-new.png)
- [Non-destructive deactivation](evidence/m8/screenshots/manager-confirm-deactivation.png)
- [GRACE read-only roster](evidence/m8/screenshots/manager-grace-readonly.png)
- [Safe CSV preview](evidence/m8/screenshots/draft-csv-safe-preview.png)
- [Restored genuine historical result](evidence/m8/screenshots/student-history-restored.png)

## Execution rulings

1. Explicit feature worktree despite isolated main: Owner requires feature isolation; cost: one disposable worktree.
2. Active-only mixed Membership conflicts: Owner amendment1 supersedes old wording; cost: inactive historical rows no longer block legitimate authority, as intended.
3. Internal CSV dispatch remains DRAFT_CSV_CREATE; business receipt uses CREATE_USER and SUCCESS/NOOP only: amendment2 vocabulary; cost: channel is not a distinct persisted business operation.
4. O-006 not prematurely marked RESOLVED: latest Owner gate requires acceptance; cost: conservatively open tracking.
5. Workspace denial in new test is exact404, not403: existing anti-enumeration contract; JSON denial stays403. Cost: new regression is status-specific, no production change.
6. One bounded credential-free Event/outcome notice uses existing auth Session: MessageMiddleware is absent; no global settings expansion. Cost: another tab can replace the presentation notice, not business state. Credential preview/consumption stays separate and atomic.
7. One shared management_base.html reuses header/CSS rather than copying it: cost one local template, no framework/domain change.
8. New browser tests assert actual asynchronous UI completion (default Playwright expect), not immediate select.value/is_visible: source+HTTP200+pending screenshot proved selection precedes six requests/render. Cost normal5-second assertion deadline; no fixed sleep, production fix or claim to resolve the historical Reflection transient.
9. Re-grade handler-origin CSV traceback/ref exposure Important: explicit safe-error contract; cost bounded safe-handler protection and regression tests, no global settings expansion.
10. Keep pre-existing global DEBUG/CSRF pre-view malformed-request handling outside the bounded CSV handler fix: a CSRF-enforced diagnostic proved parsing occurs in middleware before the handler. Cost development technical400 remains possible; no plaintext credential canary leak proved. Disclose this framework-hardening Minor rather than claiming it fixed.
11. Keep broader pre-existing M7 Project-role helpers: Owner freezes them; cost existing policy debt remains, not silently redefined by participant management.
12. Certify default transactional SQLite application paths only: approved guarantee; cost non-SQLite/multiple databases remain uncertified.

## Independent review and fix pass

Genuine fresh-context review by `/root/m8_independent_final_review` (`gpt-6-astra`) of fa9c000..e1441dc. Critical0; Important1 ABA stale-state defect; reviewer Minor1 CSV exception boundary, re-graded handler-origin portion Important under explicit safe-error contract. See [full findings/disposition](evidence/m8/INDEPENDENT_REVIEW.md).

One bounded fix pass, commit `8797dc2`: four reproduced failures/two passing characterizations before implementation, six PASS11.15s after. Affected service/HTTP112 PASS108.01s and five public browser journeys PASS32.38s. No second review claimed or requested; fixes verified by named RED→GREEN and fresh regression. Pre-view middleware technical400 in DEBUG remains separately disclosed, not falsely covered by a view decorator.

## Post-fix fresh regression (2026-10-20)

| Gate | Result |
| --- | --- |
| Targeted Tasks2–7 |148 passed140.75s, exit0 |
| Non-browser |781 passed,22 skipped,313 deselected199.60s, exit0 |
| Full browser |313 passed568.61s, exit0 |
| Mechanics |131 passed0.76s, exit0 |
| M8 dedicated file-SQLite |three independent15/15 PASS,0 skip,14.60/14.88/13.84s |
| M7 dedicated file-SQLite |7/7 PASS,0 skip,5.20s |
| Django / migration dry-run / diff |exit0 |

Post-fix dedicated DBs: `/private/tmp/isaa-postfix-m8-1-rnDa7S/m8.sqlite3`, `/private/tmp/isaa-postfix-m8-2-I4zDY3/m8.sqlite3`, `/private/tmp/isaa-postfix-m8-3-ZJKVcF/m8.sqlite3`; M7 `/private/tmp/isaa-postfix-m7-RvgsKZ/m7.sqlite3`. The22 default skips are exactly the15 M8 +7 M7 in-memory concurrency exclusions, independently executed above with0skip. The pre-fix interrupted full browser run is not counted as completed evidence.

Durable command output: [full browser](evidence/m8/verification/final-browser.log), [non-browser](evidence/m8/verification/final-non-browser.log), [targeted](evidence/m8/verification/final-targeted.log). [Execution ledger](evidence/m8/EXECUTION_LEDGER.md) preserves task evidence and every ruling. Protected source diff for M7 creation/User/Project/modeling/analysis/materials/mechanics/idealization is empty; root fingerprints and main/grid clean state reverified. No unresolved Critical/Important implementation finding remains; the bounded fixes were verified by tests, not an unperformed second independent review.

## Owner manual acceptance record — 2026-10-20, Asia/Shanghai

**M8 OWNER MANUAL PRODUCT ACCEPTANCE: PASS.** This is the Product Owner's explicit final decision, not an agent-generated acceptance declaration.

Formal disposable environment: `m8-owner-icmp4a9c.localhost:8022`, feature at accepted implementation HEAD above. Normal application cookie-name contract, host-only cookies and unique hostname isolation; no diagnostic middleware. Only existing repository migrations were applied to the separately authorized new disposable DB. No real DB or old Project was migrated.

| Acceptance behavior | Result / attribution |
| --- | --- |
| A1 editable student with resources: Member, two Canvas points, Save HTTP 200, reload persistence | PASS; real public browser pre-handoff, saved v1 |
| A2 without Material/Section | PASS; editable and understandable resource prerequisite guidance |
| Assigned Manager viewing student Project | PASS; readonly, modeling unavailable |
| Developer viewing student Project | PASS; existing readonly contract preserved |
| Deactivate -> next student request denied -> reactivate -> same Project/modeling restored | PASS; real management UI, saved v1 preserved while inactive, public Save/reload v2 after restoration |
| GRACE participant management | PASS; readonly |
| PURGED participant operations | PASS; fail closed |
| Owner F: forced password change, ACTIVE Event visible, M7 self-create, Material/Section, Member/Save/Reload, Model Check | **OWNER MANUAL PASS — F JOURNEY**, all six confirmed by Owner |
| DRAFT CSV real file upload and Preview | PASS; HTTP 200, exactly one safe account shown, opaque reference field, no legacy credential-bearing token |
| DRAFT CSV Confirm | PASS; HTTP 302 to successful participant list HTTP 200 |
| DRAFT CSV User and exact active PARTICIPANT | PASS; active USER, forced first change; Project precreated **NO** |
| Audit contract | PASS; approved participant-operation-audit-v1 allowlist validated, no credential/payload leakage |
| Result/list refresh idempotence | PASS; User/Membership/Project/audit counts unchanged after refresh |
| ACTIVE CSV | **FAIL CLOSED — PASS**, HTTP 403 |

CSV counts before -> confirm -> refresh: Users 7 -> 8 -> 8; Memberships 10 -> 11 -> 11; Projects 4 -> 4 -> 4; business audit receipts 3 -> 4 -> 4. No direct service/ORM creation substituted for public upload/confirm. No additional replayed-POST/concurrency suite is claimed by this refresh smoke. No passwords, cookies, sessions, CSRF values, preview references, raw CSV or disposable DB are part of repository evidence.

**ORIGINAL MODELING FAILURE: ROOT CAUSE NOT PROVEN.** **NOT REPRODUCED IN CONTROLLED PRODUCTION-EQUIVALENT M8 ACCEPTANCE ENVIRONMENT.** Do not infer that the original unidentified incident was fixed or attribute it to user error/cache.

The separate 8020 Save 403 was **ACCEPTANCE ENVIRONMENT FALSE NEGATIVE**: an acceptance-only custom CSRF cookie name disagreed with the normal frontend cookie contract. The same accepted implementation under normal cookie settings and isolated hostname passed Member/Save/reload. No production CSRF fix was made or implied. Redacted diagnosis is retained separately; credentials/DBs are excluded.

D-M8-001, D-M8-002, D-M8-003 and D-M8-004: **RESOLVED**. O-006: **RESOLVED — APPROVED SCOPE ONLY**, exactly as listed above. O-004: **OPEN**.

Before local integration, Owner-authorized removal of only two temporary root README login notes restored the original protected dirty diff fingerprint exactly. No credential text was printed, archived or copied into evidence. The other three protected dirty files and root DB stayed unchanged; the drifted fingerprint was not adopted as a new baseline.

## Known debt / remaining gates

- Implementation gates and explicit Owner acceptance are complete; fresh local post-merge verification, main browser smoke, evidence preservation and bounded cleanup remain mandatory closeout gates.
- Deferred framework Minor: with DEBUG=True, malformed requests rejected by global CSRF parsing before the handler may show Django technical400. The bounded CSV fix covers handler-origin parsing/rendering, not middleware/global settings. No plaintext credential leak proved.
- Owner authorized a disposable acceptance environment and explicitly declared PASS; account credentials are not repository or archive artifacts.
- Abandoned expired previews require existing Django clearsessions maintenance;600 sec does not imply physical row deletion on a timer.
- Certified concurrency scope is default transactional SQLite application paths only; other DB backends remain uncertified.
- Credential-free Event/outcome notices use the existing auth Session; another tab can replace a presentation notice without changing business state.
- ACTIVE CSV remains fail closed; Manager assignment/revoke/promotion is outside M8. O-004 remains OPEN; the original historical modeling incident remains ROOT CAUSE NOT PROVEN.
- Previously accepted M7 Minors remain: unsupported create-form file attachment is ignored rather than rejected; sole BLOCKED v1 Project landing wording still says continue though Workspace is read-only. Historical Reflection transient root cause remains NOT PROVEN / NOT CLAIMED FIXED.
- Local closeout is separately Owner-authorized; no push, tag, release or deploy.

## Handoff

Owner-approved local closeout starts from main `fa9c000ddbff89adc41a34711bf44a0b509d19fe`. This docs-only acceptance commit is the feature closeout HEAD; resolve its actual Git hash separately from accepted implementation `5eea16e`. The final stable main must use that actual closeout hash, only after ff-only integration and fresh main gates. No push/tag/release/deploy or real-data conversion is authorized. Do not start another milestone.
