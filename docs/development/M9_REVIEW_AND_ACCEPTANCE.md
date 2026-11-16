# M9 review and acceptance handoff

## Current gates

Technical Tasks 1–8 are complete, including fresh regression and closure of the Important findings from the one authorized independent whole-branch review. **M9 IMPLEMENTED — TEACHER REVIEW PENDING. Owner manual product acceptance: PENDING.** No manual acceptance environment has been authorized or started. No merge, push, tag, release or deployment.

### Teacher package preparation — 2026-10-26

**M9 IMPLEMENTED — TEACHER REVIEW READY. Teacher verdict: PENDING. Owner acceptance: PENDING.** READY refers only to preparation of the review materials, not a teacher verdict or a completed live demonstration.

- [简体中文教师简报](M9_TEACHER_REVIEW_BRIEF.md)：约 1–2 页，面向大一至大二竞赛初学者，无需阅读代码。
- [空白教师评审表](M9_TEACHER_REVIEW_FORM.md)：12 项 PASS / NEEDS REVISION / UNCERTAIN 与教师意见，未预填答案。
- [8–12 分钟示范稿与五个案例](M9_TEACHER_DEMO_SCRIPT.md)：A 真实公开分析截图；B 无预测、E 历史分析使用现有真实操作记录，明确无独立截图；C MIXED、D ties 为受控给定事实画面。零值并列只有既有受控验证记录，无独立零值图。不以 A 的画面冒充 B/E，或把受控案例称为自然 Solver outcome。需要补看画面时请教师记录 UNCERTAIN。

No runtime was created in this preparation: no URL, PID, new DB, login credentials or smoke claim. The Owner permits a disposable Teacher Review runtime, but this package uses existing evidence rather than exercising that optional permission. It is not an Owner acceptance environment. Implementation source remains `3eeb50efcabf6ff8385313275f6562e005f59da2`; any preparation commit is docs-only.

Read-only preflight verified feature/main clean at the expected HEADs, protected root diff/DB fingerprints unchanged, grid unchanged and existing on-disk DBs unchanged. No production/test changes, migration, new code review or full regression rerun. Only the three new teacher documents and this necessary handoff update may be committed. Existing genuine synthetic images stay ignored; no credentials or private data copied. R3, dynamic-input overlap and historical Analyze 500 **ROOT CAUSE NOT PROVEN** remain disclosed below; none is labeled fixed by this preparation.

## Teacher task sheet

The teacher should determine whether this is a minimum effective evidence-based activity, not grade a student's answer. Review these five questions against the selected-Run evidence:

1. Which physical members are in tension/compression? Can a student cite the complete relevant analysis segments, including MIXED rather than a largest-force substitute?
2. Where is maximum displacement? Are all tied candidates readable, including valid zero ties, without suggesting a first-row winner?
3. Where do prediction and supplied analysis agree or differ? Is UNSURE a legitimate choice, NOT_COMPARABLE non-binary, and near-zero clearly approximate rather than a correctness score?
4. Which member/node/segment facts support the student's own explanation? Do Level 1 outcome, Level 2 evidence, and collapsed Level 3 exact values/source provide appropriate beginner depth and order?
5. Can students independently state what they want to observe next, using the same Run's optional Reflection without generated answers, design advice, grading or a claimed true force path?

Review segment/candidate volume for beginners while keeping all supplied facts available. Wording/order/disclosure-only feedback can receive bounded tested UX revisions. New safety, buckling, K/I/L, threshold/classification, optimization or true-path requirements require **STOP — MECHANICS / SCOPE DECISION REQUIRED**. O-001 stays OPEN; it is not a prerequisite to reviewing the approved existing-fact presentation.

| Human record | Current value |
| --- | --- |
| Teacher identity/date | PENDING — not supplied |
| Five-question activity feedback | PENDING |
| Level 1/2/3 order/depth | PENDING |
| Complete segments/candidates and uncertainty wording | PENDING |
| Student-owned next observation | PENDING |
| Findings/disposition | PENDING — no Teacher PASS inferred from tests or agent review |
| Owner acceptance | PENDING — after actual Teacher Review |

## Independent whole-branch review

One fresh-context read-only reviewer (`m9_whole_branch_review`, `gpt-6-astra`, high reasoning) inspected `619dd55..6c655c5`, approved spec/plan, full source diff, test evidence and all ledger rulings. It did not dispatch other agents, edit source or touch databases. This is code review, **not Teacher Review**.

| Finding | Grade / disposition | Evidence |
| --- | --- | --- |
| R1: dirty same-version evidence still claimed current-model provenance in Technical/Explain | Important; CLOSED by RED→GREEN and fresh full gates | Real dirty Workspace test failed on `工程详情对应当前模型版本`; live context now updates all panels while values/labels remain selected-snapshot facts |
| R2: obsolete bootstrap `null` became a false error; Save/Analyze continuations could override B | Important; CLOSED by RED→GREEN and fresh full gates | Real held initial-list success and real pending Save/Analyze tests reproduced false error or overwritten selection; continuations now honor epoch/obsolete outcomes |
| R3: switching during a submitted Reflection save says old text was not written, although A's submitted save can finish | Minor, deferred | A receives its explicit saved content correctly and B stays isolated; the persistence notice is overly definite. No silent expansion of the one Important fix pass |

Review verdict before fixes: **Changes required**. R1/R2 closure is by named RED→GREEN plus fresh whole-suite verification, not an invented second independent review.

Final technical gates on the corrected source (`058fa0c`): non-browser **784 passed / 22 existing skips / 387 deselected**, browser **387 passed / 0 skipped**, mechanics **131 passed**, M7/M8/permissions **155 passed**, all seven M9 browser modules **74 passed**, endpoint contract **3 passed**. All commands exit 0. Django no issues; migration dry-run no changes; diff check clean. Full details and intermediate failures are preserved in [implementation evidence](M9_IMPLEMENTATION_EVIDENCE.md). Remaining tracked edits are status/evidence documents only.

### Considered-and-set-aside rulings (complete reviewer list)

1. Teacher suitability/disclosure/learning effectiveness: remain a real human gate; do not replace with agent opinion. Cost if wrong: teaching efficacy remains unknown until review.
2. Full-gate outcomes: establish from fresh commands separately; review itself does not certify them. Cost if wrong: regression could be mislabeled GREEN.
3. External protected-state fingerprints: executor verifies them independently; reviewer checked source boundaries only. Cost if wrong: unrelated work could be changed unnoticed.
4. Live Report current-version/staleness: intentional context, not immutable evidence; keep frozen sections pinned. Cost if wrong: historical provenance could be misleading.
5. Earlier approval/status prose: superseded by explicit Owner approval; original artifact preserved, feature status docs advance separately. Cost if wrong: authorization/status ambiguity.
6. Public dynamic-input toggle: supported pointer-only interaction, not a Save/Analyze bypass; pre-existing overlap deferred outside M9. Cost if wrong: a separate CAD interaction issue remains.
7. Existing Report Reasoning error callbacks and completion of previously saved Reflection fields: unchanged existing contracts, not added to M9. Cost if wrong: pre-existing behavior may need a separate audit.
8. Defensive validation of fabricated incomplete segment packages: no ordinary-user failing case shown; backend remains the complete validated fact authority. Cost if wrong: malformed backend data could be presented incompletely; no browser recomputation permitted.
9. File-SQLite suites: conditional, not triggered by unchanged backend dependencies; 22 memory-mode exclusions are not concurrency PASS. Cost if wrong: a newly affected shared dependency would require dedicated file-DB verification before handoff.

## Evidence provenance

The real browser tests in `tests/browser/test_m9_public_teaching_loop.py` use a new browser context and actual login/events/Workspace. Only a synthetic ACTIVE participant, empty v2 Project and catalog are seeded. Canvas actions, Save/reload, Model Check, authored Prediction, successful Analyze, evidence and typed Reflection Save/Complete use public controls and real HTTP/persistence. No fake AnalysisRun or generated Reflection.

Screenshots are retained in the isolated feature worktree under `.superpowers/sdd/2026-10-21-m9-results-teaching-loop/screenshots/`:

- `m9-{1024,1280,1440}-结论.png`, `-预测对比.png`, `-为什么.png`: actual successful public v2 Run.
- `m9-{1024,1280,1440}-evidence.png`, `-level3.png`, `-reflection.png`: complete evidence/professional disclosure and explicitly student-typed Reflection from that same public Run.
- `focused-unsure.png`, `focused-mixed-all-segments.png`, `focused-tied-candidates.png`: controlled supplied-fact presenter cases in a real browser, **not** claims that the public triangle produces those rare numerical states. Test fixtures and literals are inspectable; backend comparison/explanation regressions separately cover their authority.

All names/text are disposable synthetic test content; no real student/private account data or login credentials are retained. Screenshot files are not a running manual environment. Pending teacher evidence is deliberately retained, not discarded with scratch bookkeeping.

## Owner task sheet — not yet scheduled

After Teacher Review and separate environment authorization, prepare one independent v2 runtime/DB/unique host with verified process/branch/HEAD/DB provenance and normal cookie isolation. Provide synthetic credentials only in the handoff response, not repository/evidence/logs.

Owner should build/save/check, optionally predict state/location/path, Analyze, traverse all four Results tabs and three explanation levels, inspect every segment/candidate, navigate to same-Run Reflection without writes, type/save/complete original answers, then select historical A after a changed Draft and Run B. Check no-Prediction, UNSURE/MIXED/ties and Manager/Developer/GRACE readonly, PURGED fail-closed. Record actual observations; no automatic PASS.

## Known boundaries / limitations

- Backend remains the numerical/classification authority; the new TeachingView only projects existing selected-Run facts and snapshot labels.
- No schema, migration, new domain/history model, dependency, persisted numerical fact or M7/M8 service change.
- Current-Draft version/staleness may change in Report provenance; immutable Run snapshot, values and historical identity may not.
- Public pointer-only drawing disables the existing floating numeric inputs through the public toggle. A diagnostic observed the old floating input intercept an endpoint click; CAD behavior is outside M9 and was not changed.
- One intermediate focused race run returned Analyze HTTP 500; root cause was not proven. It is not called fixed. Final named ownership regressions, all 74 M9 cases and the 387-test full browser suite subsequently passed without backend changes or retry/sleep repairs.
- R3 pending-save notice remains a deferred minor; explicit submitted A saves can finish, while B stays isolated. No data loss or cross-Run write is claimed.
- No Teacher/Owner verdict, acceptance server or production readiness claim follows from automated GREEN.
