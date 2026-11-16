# M9 — Results Evidence & Teaching Loop Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended by the skill generally) or superpowers:executing-plans to implement this plan task-by-task. **This plan recommends Native sequential execution with superpowers:executing-plans**, a Run-foundation checkpoint and one independent whole-branch review. Owner must approve this plan and execution method first. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Help a student cite the evidence of one explicitly selected AnalysisRun, compare an optional prediction, and optionally write their own same-Run Reflection.

**Architecture:** Retain Workspace, its four Results tabs, existing Run endpoints and `run-context.js`. Add one bounded, read-only teaching view-model that projects selected-Run facts and snapshot labels, never mechanics. Harden selection/Reflection epochs and disable historical-to-current Canvas linkage where context is not provably identical.

**Tech Stack:** Existing Django 5.2, Python >=3.12, native JavaScript ES modules, pytest/pytest-django and Playwright; no new dependency or framework.

**Spec:** [Owner-approved M9 scope](../specs/2026-10-21-m9-results-teaching-loop-decisions.md). Read it and the existing Comparison, Explanation, Reflection and Report contracts before implementation.

**Status:** **M9 IMPLEMENTED — TEACHER REVIEW PENDING**. Tasks 1–8 technical gates complete; Important whole-branch findings closed by RED→GREEN and fresh full regression. Owner review PENDING; no merge/push/deploy. The original approved planning artifact is preserved byte-for-byte in `7edbc64`; [implementation evidence](../../development/M9_IMPLEMENTATION_EVIDENCE.md) records subsequent execution and the Owner amendment superseding the old Teacher-dependent completion wording below.

## Global Constraints

- M8 stable implementation baseline: `96c335dc1c1d742d4143817c02a51a0fc3961892`.
- M9 starting repository baseline: `main@619dd55fae7307027e449bfd67b99138d38d5d2e`, not the earlier M8 commit.
- Optional Prediction -> Analyze -> Conclusion -> Evidence -> Prediction Comparison -> Explanation -> optional Reflection; no new prerequisite state machine.
- Exactly one selected Run -> linked optional Prediction -> immutable revision/snapshot -> authoritative result/comparison/explanation -> same-Run Reflection. No latest fallback, current Draft/library substitution, coordinate matching or raw-key guessing.
- Canonical units remain mm / N / MPa / g. Backend O-007 remains the only teaching-classification authority; do not rederive tension/compression/ZERO_FORCE/MIXED or displacement maxima/ties in JavaScript.
- MATCH/MISMATCH means 一致/不同, never correctness, pass/fail, ranking or score. UNSURE is a prediction choice. MIXED retains all relevant segments; NOT_COMPARABLE is not a forced binary result.
- Prediction supplies displacement location, not predicted magnitude. No new value field or percentage error. A path is the student's hypothesis, never the Solver's unique true path.
- Stress `N/A` and mass `rho A L` are existing engineering facts, not safety, self-weight, optimization or buckling checks. O-001 stays OPEN — MECHANICS REVIEW REQUIRED: no Euler/K/controlling axis/risk band.
- All levels hide machine codes, client keys, DB IDs, schema, hashes, raw payload and internal mappings from student-visible/accessible copy. Internal transport identifiers remain necessary for scoped requests; do not confuse them with student labels.
- Reflection remains optional, student-authored, three prompts, partial explicit DRAFT save, explicit completion, COMPLETED immutable and governed by existing privacy/lifecycle rules. Navigation never writes or supplies an answer.
- Manager/Developer readonly does not reveal private DRAFT Reflection/Reasoning or allow authoring. FINISHED_GRACE is authorized history read-only; PURGED operational access fails closed. Do not reopen O-003/O-006.
- Expected migration NO; new domain/history model NO; no DesignIteration/CompareRuns, new persisted facts, research tracking, grading or expanded retention.
- Preserve Node-as-Joint, Draft Independence, Delete Impact, validation, M7/M8, historical v1 readers and Solver/Mechanics. No real-data conversion or mutation for testing.
- Future implementation stays isolated; no merge/push/tag/deploy. Root dirty work, grid, existing databases and running platforms are protected.

## Review Focus

1. Unsaved geometry changes with the **same saved draft version** must invalidate Canvas linkage without changing historical evidence: `test_unsaved_same_version_disables_result_linkage` (Task 2).
2. Out-of-order Run-list refreshes and old request failures must not replace a newer selection or its error state: `test_obsolete_refresh_and_error_leave_new_selection_intact` (Task 2).
3. Server explanation templates can contain raw analysis-node identifiers; no level or accessible label may blindly echo them: `test_structured_explain_hides_internal_tokens_at_every_level` (Task 3).
4. Zero magnitude is valid, whereas absent magnitude/provenance is unavailable, not zero: `test_zero_ties_and_missing_displacement_are_distinct` (Task 5).
5. A Reflection save/complete can finish after switching Runs, including A -> B -> A; old callbacks must not repopulate new forms: `test_reflection_aba_and_late_failure_are_selection_scoped` (Task 6).

## A. Verified baseline and safety

Read-only verification on 2026-10-21 found `.worktrees/main-integration` on `main`, HEAD `619dd55fae7307027e449bfd67b99138d38d5d2e`, initially clean. `git merge-base --is-ancestor 96c335dc1c1d742d4143817c02a51a0fc3961892 619dd55fae7307027e449bfd67b99138d38d5d2e` exited 0. Thus M9 must start from `619dd55`, which includes M9-PRE Source-of-Truth synchronization.

This planning operation updates only the five existing scope/status documents and this new plan; HEAD remains unchanged. No baseline regression has been run in this planning operation. Future Task 1 must recheck the baseline and preserve these approved planning artifacts without treating them as unrelated dirty work or discarding them.

## B. Frozen product contract

The five student tasks are: identify tension/compression; locate all maximum-displacement candidates; describe agreement/difference with their prediction; cite member/node/segment facts; state their **own** next observation. Evidence supports an answer but never generates it. Teacher review assesses the activity, not a new mechanics method or a measured learning-effect claim. Scope approval does not authorize implementation until Owner approves this plan/method.

## C. Current implementation gaps — source audit, not runtime claims

| Current source | Observed gap | Planned owner |
| --- | --- | --- |
| `results.js::showExplanation/renderExplanation` | Projects mostly `level_1`; loses the distinct Level 2/3 tasks and structured values | Task 3 |
| `results.js::showComparison/renderComparison` | Member-centric; no complete displacement-location comparison; segment expansion mainly MIXED | Tasks 4–5 |
| `results.js::showLevelOne` | Groups raw result states and derives MIXED in JS; M9 must instead project server teaching evidence, without changing server semantics | Task 2 |
| `workspace.html::focusMember` and state subscription | Current-Canvas linkage can use coincident keys; saved-version equality alone misses unsaved geometry edits | Task 2 |
| `run-context.js::selectRun/refreshRuns` | Existing selection token protects many detail responses; list refresh lacks an equivalent ownership guard | Task 2 |
| `reflection.js::save/complete/load`, inline callbacks | Mutable selection and unguarded post-await rendering can install another selection's response | Task 6 |
| Existing public browser journeys | v1 has a full learning loop; Bridge v2 tests drawing/results tabs; the existing v2 prediction test uses an isolated module seam, not the required whole public journey | Task 7 |

Existing backend facts are sufficient: `learning/comparison.py`, `learning/explanation.py`, `analysis/reporting.py`, scoped views, and Reflection services already supply the needed authority. No backend/API/schema change is planned.

## D. Run-authority architecture

`run-context.js` remains the only selection/request owner. Each selection, deselection or invalidating refresh obtains a monotonically increasing epoch; list refresh also has a generation. Clear previous panels, engineering details, path/evidence affordances, report, Reflection form and overlay **before** awaiting new content. Obsolete success **and error** callbacks are ignored. An ordinary refresh must not silently select latest; only an explicit requested Run, including the Run returned by the user's Analyze action, may be selected.

Introduce `teaching-view.js::buildTeachingView({payload, runNumber, workspace}) -> TeachingView`. `workspace` contains only `{projectId, draftVersion, dirty}` for integrity/context/linkage decisions, **not Draft geometry, resource rows or current label maps**. Validate Run IDs across metadata, data, comparison, explanation, report and any Reflection; validate present project/revision/source-version fields against the selected package. A no-Prediction comparison legitimately lacks prediction-specific source fields; validate the fields actually guaranteed by that contract. An absent Reflection is legal. Failed Runs retain the existing no-results state.

`TeachingView` is an immutable presentation object: `{runId, runLabel, sourceDraftVersion, historical, canLinkCanvas, labels, members, explanationBlocks, displacement, comparisonAvailable}`. `runId` is internal routing state, not visible copy. `labels` comes exclusively from `createStudentLabelResolver(payload.report.report.geometry_connectivity)`; segment names use the snapshot's `analysis_member_mapping`. `members` copies `MEMBER_FORCE_STATE.facts.actual_state/segments`, never groups raw Solver states to manufacture a classification. Unsupported/mismatched provenance yields safe unavailable presentation, never fallback data.

`canLinkCanvas(view, workspace) -> boolean` additionally requires selected source version == saved current version **and `dirty === false`**. This is a conservative context gate, not evidence derived from the current Draft. Any later mutation clears the overlay and disables both evidence->Canvas and Canvas->evidence linkage. Historical evidence remains fully readable in its panel, with a historical notice; no new historical Canvas or inferred mapping. Explicit re-selection after a valid save obtains a new package/epoch.

## E. API and presenter interfaces

Reuse the current Project/Run data, comparison, explanation, report, reasoning and reflection URL templates from Workspace bootstrap. `createRunContext(...).selectRun/refreshRuns/state` retains its public signatures; its `onSelect(payload, token)` token becomes the presentation epoch. Retain owner-library and lifecycle service authority unchanged.

`TeachingView.members[]` contains `{key, label, actualState, segments, predictedState, comparisonStatus}`; internal keys never become visible fallback labels. Segment rows contain the snapshot-derived label plus the server-provided state/axial force. `explanationBlocks[]` retains recognized block type, safe subject label, three task-specific messages and structured facts/professional values. Unknown blocks fail to a safe unsupported-evidence note, not arbitrary server text.

`displacement` contains `{available, maximumMm, candidates, predictedLocationLabel, locationMatch, unavailableReason}`. Candidate labels and supplied ux/uy/magnitude come from selected-Run provenance/explanation; no browser vector norm, maximum, tolerance or nearest-node calculation. Prediction points use versioned immutable NODE/CONNECTION/free-endpoint provenance via existing label authority, not coordinates.

In `results.js`, replace the product use of `showLevelOne` with `showLevelOne(view: TeachingView) -> LevelOneView`; update all real call sites and affected focused regression fixtures together, without retaining the old raw-state classification as a hidden fallback. Keep `renderLevelOne`, `renderComparison`, `renderExplanation` as bounded DOM renderers consuming the same TeachingView. Rendering options are `{onFocusMember, onReflect}`; focus obeys `canLinkCanvas`, and `onReflect` only navigates. Keep `showEngineeringDetails/renderEngineeringDetails` reading the same selected package. Retain the four existing tabs and keyboard behavior.

No endpoint extension is currently needed. Owner allows projecting already-existing facts through an existing endpoint, but any newly discovered necessity must first be recorded with the exact field/source and endpoint tests; do not quietly widen this file map. If safe binding would need new persisted facts/domain/history/schema, **STOP — ARCHITECTURE DECISION REQUIRED**.

## F. Progressive disclosure design

| Level | Student task and concrete content | Interaction |
| --- | --- | --- |
| 1 — Conclusion | Supplied member teaching states, supplied maximum magnitude/all candidate locations, neutral available comparison summary; no new “main member” ranking | Existing 结论 default; evidence pointers stay tied to selected Run |
| 2 — Evidence / Explanation | PhysicalMember and complete relevant segment evidence, all maximum candidates, neutral prediction comparison, explicitly labeled student hypothesis, existing `level_2` prompts | Existing 预测对比 / 为什么 panels; labeled member/candidate groups |
| 3 — Professional data / provenance | Existing `level_3` guidance beside actual N/mm/MPa/g values, segment sources, ux/uy, selected human-readable Run and historical context | Existing 技术数据 plus clearly labeled expandable supporting data; engineering tables not initially expanded |

Use supported safe templates plus structured facts. In particular, MAXIMUM_DISPLACEMENT `level_1` can embed raw candidate IDs: rebuild that sentence from the supplied magnitude and snapshot labels rather than print it or perform broad string-redaction. Do not concatenate three strings or expose JSON as “three levels”. Preserve existing safe Report rendering; no Report-export redesign.

## G. Member comparison design

Present the student's predicted state, backend actual teaching state, neutral comparison status and the **complete supplied** segment set in their respective levels. MATCH -> 和预测一致; MISMATCH -> 和预测不同; UNSURE -> 预测时尚不确定; NOT_COMPARABLE -> 当前不能作单一受拉／受压对照, with the existing reason/evidence. ZERO_FORCE includes the existing approximation caveat. MIXED cannot be compressed to the largest-force segment. No comparison or path is manufactured without Prediction. Label path evidence 学生传力假设 and ask 这些结果是否支持你的判断？; never display an inferred true path.

## H. Displacement comparison design

Compare the supplied predicted **location** against the complete server candidate set and supplied `location_match`, beside the actual magnitude in mm. Every tie, including zero-displacement ties, remains visible and equally valid; no first-row winner. No Prediction means a neutral unavailable comparison but still valid actual evidence. Missing values/invalid provenance are an explicit unavailable state distinct from numerical zero. Candidate membership and location agreement are not recomputed in JS. v1 uses its immutable provenance reader; v2 uses NODE provenance, without Connection authoring or real-data conversion.

## I. Reflection handoff

Add 进入反思 to the evidence/explanation context, bound to the selected presentation epoch and Run. It selects the existing Reflection panel only: no POST, create, auto-fill, save, complete or grade. No new prerequisite is added. With no existing Reflection, show the existing explicit 开始反思; student then types their own answers, may save partial DRAFT, and explicitly completes all three prompts. Readonly/completed views never expose authoring actions.

Keep the existing Reflection method names. Extend its selection-owned state with a Run/epoch binding and operation counter: `useReflection(id, reflection, epoch)`, `loadReflection(id)`, `saveReflection(fields)`, `completeReflection()`. Save/complete capture the binding before POST; request targets can never be retargeted by a subsequent selection. A late operation returns `null` when obsolete and never calls onChange, renders an error, or updates workflow progress for the new selection. Serialize authoring for a single binding to avoid save/complete ordering reversals. The inline Workspace callbacks must also guard the captured epoch before rendering success/errors. Switching clears unsaved local form text with a concise notice, never auto-saves or imports it into another Run; do not create a new persisted draft/history aggregate.

## J. Historical and race safeguards

Test A -> changed Draft -> B -> explicit A with different descriptions, loads, catalog values, judgments and Reflection text. A must retain its snapshot labels, true values, comparison, explanation and Reflection. Also test unsaved changes while the saved version is unchanged. Deny unsafe focus/overlay but do not suppress readable historical facts.

Cover slow A / fast B, delayed A failure after B, A -> B -> A, overlapping list refreshes, deselect during load, and pending Reflection save/complete during switch. Detail-token protections already present are characterization tests where they pass; add genuine RED for missing refresh, linkage, view-model or Reflection behavior. Transport interception is allowed only in these isolated race tests, never as the main public-loop proof.

## K. Task-by-task TDD execution — NOT STARTED

All paths below are repository-relative in the **future** isolated worktree. Every feature task follows RED -> minimal implementation -> GREEN -> scoped commit. Existing behavior that already passes is recorded as characterization, not falsely called RED. A baseline failure is diagnosed before feature work and does not count as M9 RED. No task authorizes merge/remote action or changes outside the frozen scope.

### Task 1 — Isolated baseline and authority characterizations

**Goal:** Establish an uncontaminated starting point and preserve approved planning artifacts.

**Files:** NEW `tests/endpoints/test_m9_run_contract.py`, `docs/development/M9_IMPLEMENTATION_EVIDENCE.md`; carry only the six approved planning/status documents listed in Q into the feature. All product files unchanged.

**Interfaces:** Consume real scoped HTTP endpoints and existing v2 save/analyze fixtures. Produce a reproducible fixture/contract characterization for the Run package; no new endpoint or domain factory.

- [ ] Recheck main HEAD `619dd55` and ancestry before writes. After Owner plan/method approval, use `using-git-worktrees` to create `feat/results-teaching-loop-m9` at `.worktrees/results-teaching-loop-m9` **from that exact commit**. Preserve root/grid/runtime/DB fingerprints. Stop on HEAD drift or unrelated dirty changes; do not stash/reset/clean. The known six planning-doc changes are expected: copy only approved bytes into the new worktree, verify hashes, and leave their main-worktree originals untouched; do not copy any root dirty code.
- [ ] Run fresh baseline: `pytest -q -m 'not browser'`; `pytest tests/mechanics -q`; `python3 manage.py check`; `python3 manage.py makemigrations --check --dry-run`; `git diff --check`; `pytest tests/browser/test_bridge_public_journey.py tests/browser/test_poc_v1_student_journey.py tests/browser/test_node_joint_workspace.py -q`. Require no unexpected failure/skip, zero model drift. Record counts/commands/environment, not credentials or free text. No M9 code yet.
- [ ] Add `test_selected_run_endpoints_share_run_and_snapshot_authority`, `test_no_prediction_package_remains_available`, `test_selected_run_reads_do_not_mutate_result_artifacts`: assert selected Run/project/revision/source versions where guaranteed, absent Prediction is legal, labels/geometry derive from report snapshot, and serialized result/snapshot/input/linked Prediction stay byte-identical before/after disclosure. Characterizations are expected GREEN; if not, stop and diagnose, do not force a feature RED or fix mechanics.
- [ ] Run `pytest tests/endpoints/test_m9_run_contract.py tests/endpoints/test_compare_explanation_json.py tests/endpoints/test_report_json.py -q`; require PASS. Document the field contracts and real baseline outcomes.
- [ ] Commit only approved carried documents, characterizations and evidence: `test: characterize selected-run teaching contracts`.

**STOP:** Baseline drift/failure, unexpected protected-state changes, required schema/new history facts, or inability to preserve approved documents safely. Task 1 is setup/characterization, not a fabricated failing-feature cycle.

### Task 2 — Selected-Run view-model, race and historical foundation

**Goal:** All subsequent presenters receive the same validated Run/snapshot facts; unsafe Canvas linkage and obsolete callbacks cannot escape.

**Files:** NEW `projects/static/projects/workspace/teaching-view.js`, `tests/browser/test_m9_run_context.py`; MODIFY `projects/static/projects/workspace/run-context.js`, `projects/static/projects/workspace/results.js`, `templates/projects/workspace.html`; update affected existing call-site fixtures in `tests/browser/test_workspace.py` only where the explicit `showLevelOne` interface changes.

**Interfaces:** Implement `buildTeachingView({payload, runNumber, workspace}) -> TeachingView` and `canLinkCanvas(view, workspace) -> boolean` from D/E. Retain `createRunContext` external methods and `onSelect(payload, token)`. `showLevelOne(view)` consumes server evidence, never current Draft or raw Solver-state grouping.

Core assertions in the arranged A/B fixture (server teaching state deliberately differs from raw result state):

```python
assert observed["actualState"] == "ZERO_FORCE"  # supplied backend evidence
assert observed["label"] == "旧上弦杆 · 构件 M4"  # A snapshot, not current description
assert observed["dirtySameVersionCanLink"] is False
assert observed["selectedAfterLateA"] == run_b.id
```

- [ ] Add named tests `test_selected_run_evidence_never_uses_current_draft` (RED-1), `test_run_switch_clears_all_derived_presentation` (RED-2), `test_late_run_response_cannot_replace_new_selection` (RED-3), `test_historical_labels_use_selected_snapshot` (RED-4), `test_server_classification_and_result_bytes_are_not_recomputed` (RED-22), plus both Review Focus 1/2 tests. Assert a deliberately conflicting raw result cannot override server teaching state; missing authoritative state is unavailable, not reclassified. Assert changed/dirty current Canvas cannot focus historical keys, including reverse linkage; invalid Run provenance fails safely; A/B late failures/list refreshes cannot reset B.
- [ ] Run `pytest tests/browser/test_m9_run_context.py -q`; require genuine failures for missing view-model/dirty-linkage/refresh guards. Record already-GREEN detail-token cases separately; import or environment failures alone do not count as behavioral RED.
- [ ] Implement the bounded projection, integrity checks and generation ownership. Wire all panel clearing and focus/overlay invalidation into Workspace; no API/backend modification. Keep current snapshot labels and source facts immutable; no raw-ID fallback. Update old focused fixtures to supply real explanation facts rather than preserve a second classification path.
- [ ] Run `pytest tests/browser/test_m9_run_context.py tests/browser/test_workspace.py tests/browser/test_node_joint_workspace.py -q` and Task 1 contract tests; require PASS.
- [ ] Commit `feat: bind teaching evidence to selected analysis runs`; record an **internal architecture checkpoint**: inspect every evidence input, both focus directions, dirty/version gate, request generation and source-file diff. Continue only if no current-Draft substitution, new history/schema or new mechanics authority exists. No Owner wait needed for a passing approved-design checkpoint.

**STOP:** Safe binding requires new history/schema or unapproved provenance inference; existing v1/v2 immutable contract cannot supply required facts.

### Task 3 — Three distinct Explain levels and safe provenance

**Goal:** Complete explanation disclosure as student tasks, not a raw-text/data dump.

**Files:** MODIFY `teaching-view.js`, `results.js`, `projects/static/projects/workspace/ux-v2.css`, `templates/projects/workspace.html`; NEW `tests/browser/test_m9_explanation.py`.

**Interfaces:** `renderExplanation(root, view, {onFocusMember, onReflect})` renders recognized `explanationBlocks` into task-labeled levels; `renderLevelOne(root, showLevelOne(view), options)` and existing engineering view retain separate responsibilities. Use existing `renderResultActions` tabs and keyboard navigation.

- [ ] Add `test_explain_levels_serve_conclusion_evidence_and_professional_tasks` (RED-5) and `test_structured_explain_hides_internal_tokens_at_every_level` (RED-6, Review Focus 3). Assert Level 1 supplies an interpretable outcome, Level 2 names relevant labeled segment/candidate evidence and prompt, Level 3 shows exact server values/units and readable Run/historical context. Seed distinct internal ID/hash/schema sentinel strings, including within backend MAX `level_1`; they must not appear in visible/accessibility copy, tooltips or errors. Add `test_four_result_tabs_and_disclosure_are_keyboard_accessible` at 1024/1280/1440 widths.

  Use semantic sections with `data-teaching-level="1|2|3"` for test/disclosure hooks, not raw-result dumps. Assert, for the arranged segment fact, `assert "12.5 N" in level3_text`; `assert "分析段 2" in level2_text`; `assert all(token not in student_text for token in internal_sentinels)`. Labels and values must come from that selected package.
- [ ] Run `pytest tests/browser/test_m9_explanation.py -q`; expect missing Level 2/3 and safe structured presentation assertions to fail before changes.
- [ ] Project existing level messages/facts into the three tasks. Format recognized templates safely with snapshot labels; unknown block/error -> safe unavailable/next-action note. Keep engineering tables behind disclosure, preserve real stress/mass and assumptions, avoid any safety/path-authority language. Do not change backend templates or generic Report schemas.
- [ ] Run `pytest tests/browser/test_m9_explanation.py tests/browser/test_modeling_ux_bridge.py tests/browser/test_ux_debt_cleanup.py -q`; require PASS.
- [ ] Commit `feat: present structured explanation at three teaching levels`.

**STOP:** Required explanation needs a new causal mechanics method, novel safety interpretation, or new framework rather than existing facts.

### Task 4 — Neutral member comparison and hypothesis evidence

**Goal:** Compare prediction and actual state without grading or discarding segment facts.

**Files:** MODIFY `teaching-view.js`, `results.js`; NEW `tests/browser/test_m9_member_evidence.py`.

**Interfaces:** `renderComparison(root, view, {onFocusMember, onReflect})` consumes `members`, `comparisonAvailable` and recognized path blocks. Member states/statuses come directly from selected-Run backend evidence; label mapping remains exclusively in `labels.js`.

- [ ] Add parameterized `test_member_match_mismatch_wording_is_neutral` (RED-7), `test_unsure_is_legal_non_scoring_prediction` (RED-8), `test_mixed_retains_every_segment_fact` (RED-9), `test_not_comparable_has_no_binary_verdict` (RED-10), `test_student_path_is_hypothesis_not_solver_truth` (RED-14), and `test_zero_force_retains_approximation_caveat`. Assert predicted/actual labels, true segment forces/labels and non-scoring text; use a multi-segment member with a deliberately larger segment to prove it is not chosen as sole truth. No Prediction produces no path. Verify input payload unchanged.

  Core assertions: `assert displayed_forces == [segment["axial_force_N"] for segment in server_segments]`; `assert "和预测不同" in mismatch_text`; `assert "学生传力假设" in path_text`; `assert "正确" not in mismatch_text and "错误" not in mismatch_text`. Never reduce the segment list to one row.
- [ ] Run `pytest tests/browser/test_m9_member_evidence.py -q`; capture genuine incomplete state/evidence failures; keep already-neutral text checks as characterizations.
- [ ] Extend the shared view and comparison renderer to expose all supplied segments and safe hypothesis prompts. Use backend statuses exactly; no maximum-force rule, threshold, force recovery or new enum.
- [ ] Run `pytest tests/browser/test_m9_member_evidence.py tests/browser/test_m9_explanation.py -q` and `pytest tests/application/test_comparison.py tests/application/test_explanation.py -q`; require PASS.
- [ ] Commit `feat: expose neutral member prediction evidence`.

**STOP:** Proposed comparison needs new mechanics/classification, a path correctness verdict or scoring.

### Task 5 — Complete displacement-location evidence

**Goal:** Show the student's predicted location against all supplied maximum candidates and actual magnitude.

**Files:** MODIFY `teaching-view.js`, `results.js`; NEW `tests/browser/test_m9_displacement.py`.

**Interfaces:** Populate `TeachingView.displacement` from selected comparison/MAXIMUM_DISPLACEMENT facts and professional candidate rows. Existing comparison/conclusion/explanation renderers consume this single projection; there is no second displacement resolver.

- [ ] Add `test_displacement_comparison_uses_server_candidates_and_match` (RED-11), `test_ties_display_all_candidates_without_winner` (RED-12), `test_zero_ties_and_missing_displacement_are_distinct` (Review Focus 4), `test_displacement_prediction_has_location_not_magnitude_or_percent`, `test_invalid_candidate_provenance_is_unavailable_not_coordinate_matched`. Include v2 NODE and existing v1 provenance forms; raw displacement rows designed to tempt JS recomputation must not replace supplied candidates/maximum/match. Preserve every zero-tie candidate; absent/invalid facts never turn into 0 mm. Unresolvable identities do not print raw keys or guess nearest coordinates.

  Core assertions: `assert displayed_candidate_labels == ["节点 N2", "节点 N3"]` for the arranged tied server set; `assert view["maximumMm"] == 0.0` for valid all-zero data; `assert missing_view["available"] is False`; `assert "%" not in comparison_text`. Agreement must equal the supplied boolean even when isolated raw rows would tempt a different browser-derived answer.
- [ ] Run `pytest tests/browser/test_m9_displacement.py -q`; expect missing location comparison/candidate rendering to fail before implementation.
- [ ] Implement candidate labels from immutable provenance and existing label authority; render predicted location, full actual set, magnitude and neutral server match outcome. No Prediction retains actual evidence and an unavailable-comparison explanation. No predicted value, vector norm, tolerance computation or arbitrary winner.
- [ ] Run `pytest tests/browser/test_m9_displacement.py tests/browser/test_m9_member_evidence.py tests/browser/test_m9_run_context.py -q` and `pytest tests/application/test_node_joint_learning.py tests/application/test_comparison.py tests/application/test_explanation.py -q`; require PASS.
- [ ] Commit `feat: complete maximum displacement location comparison`.

**STOP:** Existing immutable provenance cannot label candidates safely, or a new predicted magnitude/classification/history field is proposed.

### Task 6 — Evidence-to-Reflection navigation and async ownership

**Goal:** Let a student navigate, explicitly save and complete their own same-Run Reflection without cross-selection writes/presentation.

**Files:** MODIFY `projects/static/projects/workspace/reflection.js`, `templates/projects/workspace.html`, `results.js`; NEW `tests/browser/test_m9_reflection_handoff.py`.

**Interfaces:** Implement I's selection/operation binding on the existing Reflection workspace. Presenter `onReflect` checks the selected epoch before selecting the existing Reflection panel. Response `null` means obsolete, not empty/created Reflection; callers do not render it. Keep `workflow.js` service request semantics unchanged.

- [ ] Add `test_evidence_handoff_targets_same_run` (RED-15), `test_reflection_navigation_never_writes_or_fills_answers` (RED-16), `test_readonly_viewer_cannot_author_reflection` (RED-17), `test_reflection_aba_and_late_failure_are_selection_scoped` (Review Focus 5), `test_partial_save_and_explicit_completion_keep_existing_contract`. Assert zero navigation POSTs/row changes, empty student fields until typed, captured Run-specific request URLs, ignored late success/errors/progress and unsaved form text not crossing Runs. Complete may follow explicit saved input, never button navigation; completed text remains immutable. Include Manager and Developer/private DRAFT denial.

  Core assertions: `assert navigation_posts == []`; `assert Reflection.objects.count() == before_count`; `assert all(value == "" for value in initial_student_fields)`; `assert late_operation_return is None`; `assert rendered_run_id == run_b.id`. A submitted A save may finish on A, but never update B's form/progress/error or target B's endpoint.
- [ ] Run `pytest tests/browser/test_m9_reflection_handoff.py -q`; expect missing handoff and late-response protection to fail. Permission/completion invariants may already be GREEN; do not weaken them to manufacture failure.
- [ ] Add navigation only and bind all load/save/complete successes/errors/inline callbacks to captured Run+selection epoch, with same-binding operations serialized. Clear old forms; no generated answer, autosave, new authoring authority or new persistence. Disable submit actions during that binding's operation without blocking unrelated Run selection.
- [ ] Run `pytest tests/browser/test_m9_reflection_handoff.py tests/browser/test_m9_run_context.py -q`; `pytest tests/application/test_reflection.py tests/endpoints/test_reflection_json.py tests/permissions -q`; require PASS.
- [ ] Commit `feat: keep reflection handoff and requests run scoped`.

**STOP:** New Reflection/history model, changed privacy/lifecycle/reveal eligibility or auto-authored student content would be needed.

### Task 7 — Real public v2 loop, history and lifecycle proof

**Goal:** Prove actual public controls/HTTP/persistence complete the activity; focused presenters are not the acceptance substitute.

**Files:** NEW `tests/browser/test_m9_public_teaching_loop.py`, `tests/browser/test_m9_history_permissions.py`; MODIFY `tests/endpoints/test_m9_run_contract.py`, `docs/development/M9_IMPLEMENTATION_EVIDENCE.md`. Product changes only as a bounded correction to Tasks 2–6 with a separate failing test.

**Interfaces:** Use actual login, `/events/`, Project/Workspace, Save/Check/Prediction/Analyze and Run endpoints, existing service fixtures only for synthetic setup. Build public-control helpers locally in the new journey module; do not use `workspace_page`/`entry_page` force-login cookies as a substitute for the required login step. Assertions may read DB and endpoint responses; no page-state injection or direct JS controller/renderer calls.

- [ ] Add `test_public_v2_prediction_to_self_authored_reflection` (RED-20): synthetic active student/Event/empty v2 Project/catalog only -> browser login -> Project -> Canvas members/supports/load -> Save -> Check PASS -> author/complete real Prediction incl location/path -> Analyze -> assert actual new SUCCESS Run links that Prediction -> four tabs, evidence and all three levels -> navigate Reflection without writes -> student types original answers -> partial Save -> all fields Save -> explicit Complete -> reload and immutable completed text. Assert named labels, server segment values, candidate set, units and comparison semantics, not just non-empty panels. Capture real response statuses and relevant console errors.

  Core persistence assertions after public controls: `assert run.status == "SUCCESS"`; `assert run.prediction_id == prediction.id`; `assert reflection.analysis_run_id == run.id`; `assert reflection.status == "COMPLETED"`; `assert reflection.next_iteration_intent == student_typed_next_observation`. The final value is the test student's typed text, never generated or pre-seeded Reflection.
- [ ] Add `test_public_v2_no_prediction_keeps_explain_and_reflection_legal` (RED-13), `test_historical_run_a_survives_b_and_changed_draft` (RED-21), `test_grace_is_history_only` (RED-18), `test_purged_residual_run_access_fails_closed` (RED-19). History creates A and B through normal public Save/Analyze; modifies descriptions/catalog/load/Prediction and distinct Reflection, returns to A, verifies snapshot facts and no current overlay. GRACE/readonly preserve history and deny authoring; PURGED checks public GET/write denial with residual artifacts, never production data.
- [ ] Run `pytest tests/browser/test_m9_public_teaching_loop.py tests/browser/test_m9_history_permissions.py -q`. Capture any unmet integrated behavior as genuine RED. If prior tasks already satisfy the journey, record integration GREEN rather than fabricating RED; underlying feature RED evidence remains in Tasks 2–6. No fixed waits as a repair, mocked transport, fake AnalysisRun or precomputed-result injection in the public proof.
- [ ] Apply only minimal wiring corrections proven by the failure. Complete the alternate-case matrix in L using focused real endpoint fixtures where a rare numerical case is impractical in a manual public drawing; focused mocks never replace the primary public loop.
- [ ] Rerun both browser modules and `pytest tests/endpoints/test_m9_run_contract.py tests/endpoints/test_m7_read_only.py tests/application/test_node_joint_learning.py -q`; require PASS, no required journey skipped. Record redacted screenshots at 1024/1280/1440 for conclusion/evidence/comparison/Level 3/Reflection, Run/draft provenance, commands and counts.
- [ ] Commit `test: prove the public v2 evidence and reflection journey`.

**STOP:** Public journey fails outside a bounded approved correction; missing immutable facts/role conflict; test browser unavailable means NOT VERIFIED, not PASS. Do not bypass permissions/Check or seed successful results.

### Task 8 — Fresh regression, independent review and teaching handoff

**Goal:** Deliver an evidenced implementation for Teacher review and later Owner acceptance, not an integration or an acceptance claim.

**Files:** MODIFY `docs/development/M9_IMPLEMENTATION_EVIDENCE.md`; NEW `docs/development/M9_REVIEW_AND_ACCEPTANCE.md`. Any review correction must stay in Q's implementation map and carry its own RED/GREEN before a scoped fix commit.

**Interfaces:** Consume all preceding task results and selected-Run screenshots; produce review findings, regression evidence and a teacher/Owner checklist with explicit PENDING/PASS/FAIL outcomes supplied by the responsible human.

- [ ] Run N's full gates; require GREEN. Inspect source diff against `619dd55`, verify only approved files changed, no migration/new dependency, unchanged mechanics and numerical artifact authority. These are verification gates, not artificial feature RED tests.
- [ ] Request **one fresh independent whole-branch reviewer** after Owner has approved this execution method. Review spec+plan+diff+test evidence with O's checklist. Do not start a per-task agent swarm. Any finding: write the failing regression first, make the bounded fix, rerun targeted tests, obtain finding closure and then repeat the fresh full gates. No production/test editing during this planning operation.
- [ ] Prepare Teacher Review Gate M with the genuine evidence, complete segment/candidate disclosure and uncertainty cases. Obtain an actual teacher's feedback before final Owner product acceptance; do not label an agent review or browser GREEN “Teacher PASS”. Wording/order/disclosure-only feedback permits bounded UX revisions with tests. Mechanics/safety/classification requests STOP for a new decision.
- [ ] Prepare a single isolated v2 manual environment only when authorized, using synthetic accounts/DB and real public Analyze, without touching existing servers or DBs. Confirm process/branch/HEAD/DB/host provenance and normal cookie isolation before handoff. Do not persist credentials in repo/evidence. If no environment authorization/Teacher outcome is available, leave those steps PENDING, do not improvise acceptance.
- [ ] Commit evidence/checklist only after factual verification: `docs: record M9 verification and review handoff`. End **M9 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING** when implementation/review gates pass; explicitly identify pending Teacher Review if applicable. No merge/push/tag/deploy, cleanup of protected worktrees, or Owner PASS claim.

**STOP:** High-severity independent finding unresolved; any failed gate; absent Teacher review blocks final Owner product acceptance; new mechanics/schema/product decision needed. A pending human gate is not a claimed completed gate.

## L. Required browser/alternate matrix and named RED coverage

| Requirement | Named test / task | Proof |
| --- | --- | --- |
| RED-1 / RED-2 / RED-3 / RED-4 | Selected evidence / switch clearing / late response / historical labels — Task 2 exact names above | Focused selection tests plus public history |
| RED-5 / RED-6 | Three-task Explain / internal-token test — Task 3 | Visible and accessible DOM at all levels |
| RED-7 / RED-8 / RED-9 / RED-10 | Neutral comparison / UNSURE / MIXED / NOT_COMPARABLE — Task 4 | Focused parameterized evidence, backend comparison regressions |
| RED-11 / RED-12 | Server candidates/match / all ties — Task 5 | Single, multiple and all-zero candidates; actual endpoint contract |
| RED-13 | `test_public_v2_no_prediction_keeps_explain_and_reflection_legal` — Task 7 | Real Analyze and optional own Reflection without fake Comparison/path |
| RED-14 | `test_student_path_is_hypothesis_not_solver_truth` — Task 4 | Positive hypothesis label; no true-path assertion |
| RED-15 / RED-16 / RED-17 | Same-Run handoff / navigation no write / readonly no author — Task 6 | Request/DB assertions; Manager and Developer |
| RED-18 / RED-19 | GRACE history-only / PURGED fail closed — Task 7 | Real public routes and guarded controls |
| RED-20 | `test_public_v2_prediction_to_self_authored_reflection` — Task 7 | Actual login, modeling, Prediction, Analyze, evidence and Save/Complete |
| RED-21 | `test_historical_run_a_survives_b_and_changed_draft` — Task 7 | A/B differing snapshot labels/values/Prediction/Reflection |
| RED-22 | `test_server_classification_and_result_bytes_are_not_recomputed` — Task 2 plus Task 1 artifact test | Server states preserved, frontend has no classification/max algorithm, serialized immutable artifacts unchanged |

ZERO_FORCE is explicitly exercised by Task 4's approximation test; invalid/missing result/provenance by Tasks 2/5; v1 historical readers remain covered by existing node-joint learning and full v1 journey. Isolated edge/race fixtures may use controlled payloads. The primary public journey must never mock transport, skip login or synthesize a successful AnalysisRun. Collect behavioral RED messages separately from already-GREEN invariants and infrastructure failures.

## M. Teacher Review Gate — before Owner product acceptance

Provide a task sheet and genuine screenshots/live selected-Run evidence, including no-Prediction, UNSURE, MIXED and displacement ties. Ask the teacher to review: (1) whether the five questions are a minimum effective activity; (2) Level 1/2/3 order/depth; (3) segment/candidate volume for beginners, with all facts still available; (4) non-misleading uncertainty wording; (5) whether students can cite facts and independently propose their next observation. Record actual reviewer/date/findings/disposition without student private text. Do not require O-001 to design or implement the approved existing-fact presentation. New K/I/L/safety/true-path/classification demands require **STOP — MECHANICS / SCOPE DECISION REQUIRED**; no silent acceptance as “copy”.

## N. Full regression gates

After the final code change and review correction, in the feature worktree:

```bash
pytest -q -m 'not browser'
pytest tests/browser -q
pytest tests/mechanics -q
pytest tests/permissions tests/endpoints/test_event_landing.py tests/endpoints/test_m7_read_only.py tests/endpoints/test_participant_management.py tests/application/test_m7_resource_guards.py tests/application/test_participant_management.py -q
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
git diff --check
```

Require all applicable tests GREEN, Django no issues, no model changes/migration files, no whitespace errors; record counts and any existing skips explicitly. Required M9 public browser tests cannot be skipped. Also run all seven new `tests/browser/test_m9_*.py` modules and the new endpoint contract module explicitly to make collection visible; the full browser suite protects M7/M8, Workspace Save/Check/Analyze, Report, Prediction/Reflection, history and existing interactions. Migration dry-run is diagnostic only; no migration generation/application to existing DBs.

Dedicated file-SQLite M7/M8 tests are **conditional**: run them if a correction touches shared authorization/resource/transaction/provisioning dependencies, or later closeout policy requires them. Otherwise record NOT REQUIRED — no affected dependency; do not count memory-DB skips as file-SQLite PASS. If triggered, use the existing `tests/m7_concurrency_settings.py` / `tests/m8_concurrency_settings.py` and their documented fresh disposable file-DB commands; never root/main/acceptance DBs. This is not permission to change concurrency services.

When triggered, allocate a fresh directory and run (these test settings select only the new test DB paths):

```bash
m9_sqlite_dir=$(mktemp -d /private/tmp/isaa-m9-sqlite.XXXXXX)
PYTHONPATH=tests M7_TEST_DB_PATH="$m9_sqlite_dir/m7.sqlite3" pytest --ds=m7_concurrency_settings tests/application/test_project_creation_concurrency.py -q
PYTHONPATH=tests M8_TEST_DB_PATH="$m9_sqlite_dir/m8.sqlite3" pytest --ds=m8_concurrency_settings tests/application/test_participant_management_concurrency.py -q
```

Require zero skips in both dedicated runs; record the validated disposable paths. Any additional repetition requirement comes from the applicable closeout policy, not from a claim that one in-memory run proves concurrency.

## O. Independent whole-branch review gate

One reviewer, independent of implementation context, examines approved spec/plan, complete diff and actual RED/GREEN/browser evidence before manual acceptance. Mandatory topics: every Run input/provenance, no current-Draft/resource substitutions, no frontend mechanics engine, all segment/candidate facts, safe labels/internal disclosure, no-Prediction/uncertainty language, late success/error/Reflection writes, permissions/GRACE/PURGED, genuine public v2 proof and protected-state/source boundaries. Report severity/file/line/evidence; unresolved blockers prevent handoff. This planned review is not dispatched now and is not a substitute for Teacher or Owner review.

## P. Owner manual acceptance plan

After Teacher review, hand off one verified v2 environment/URL and synthetic credentials through the response only. Owner: model/save/check; optionally predict member state/location/path; Analyze; inspect conclusion and every member/candidate; compare predicted location/all maxima and neutral member outcomes; open Explain levels; use evidence->same-Run Reflection; type/save/complete their own three answers; select historical A after changed Draft/B; inspect readonly/no-Prediction cases. Ask whether each of the five questions can be answered with concrete evidence, not whether tabs merely exist. Record actual Owner observations and PASS/FAIL/PENDING; never infer acceptance. No merge is included in this plan.

## Q. Exact file map

**Planning operation — MODIFY only (status/approved-scope clarification):**

- `docs/superpowers/specs/2026-10-21-m9-results-teaching-loop-decisions.md`
- `docs/specs/README.md`
- `docs/specs/MASTER_SPEC.md`
- `docs/specs/AUTHORIZATION_AND_EVENT_ARCHITECTURE.md`
- `docs/specs/ARCHITECTURE_DECISION_REGISTER.md`

**Planning operation — NEW:** this plan, `docs/superpowers/plans/2026-10-21-m9-results-teaching-loop.md`. No planning commit is made; do not discard these documents when creating the future isolated branch.

**Future implementation — MODIFY:**

- `projects/static/projects/workspace/run-context.js` — selection/refresh ownership.
- `projects/static/projects/workspace/results.js` — server-fact conclusion, comparison and three-level evidence renderers.
- `projects/static/projects/workspace/reflection.js` — Run/epoch-scoped asynchronous authoring presentation.
- `templates/projects/workspace.html` — narrow wiring, clearing, guarded Canvas focus/overlay and Reflection navigation.
- `projects/static/projects/workspace/ux-v2.css` — bounded responsive disclosure styling only.
- `tests/browser/test_workspace.py` — only existing focused call-site fixtures affected by `showLevelOne`'s contract; never weaken real public assertions.

**Future implementation — NEW:**

- `projects/static/projects/workspace/teaching-view.js` — read-only selected-Run projection, no mechanics or persistence.
- `tests/endpoints/test_m9_run_contract.py` — real public package/source/artifact characterization.
- `tests/browser/test_m9_run_context.py`
- `tests/browser/test_m9_explanation.py`
- `tests/browser/test_m9_member_evidence.py`
- `tests/browser/test_m9_displacement.py`
- `tests/browser/test_m9_reflection_handoff.py`
- `tests/browser/test_m9_public_teaching_loop.py`
- `tests/browser/test_m9_history_permissions.py`
- `docs/development/M9_IMPLEMENTATION_EVIDENCE.md`
- `docs/development/M9_REVIEW_AND_ACCEPTANCE.md`

**UNCHANGED:** `mechanics/`, `idealization/`, `analysis/` including orchestration/postprocess/reporting, `learning/` including comparison/explanation/services/models, `projects/views.py` and URL contracts, all models/migrations, permissions/event/provisioning services, Material/Section services, `labels.js` sole naming authority, `workflow.js` request semantics, `report.js`, Prediction schema/editor, Canvas geometry/snap/1 mm grid/resolver, Node-as-Joint, Draft/Delete Impact domain, dependencies, root/grid worktrees and existing DB/runtime. If an existing endpoint projection is proven necessary under E, stop to document/review that bounded exact-file amendment before editing; no silent scope expansion.

## R. Schema and migration impact

EXPECTED MIGRATION: **NO**. EXPECTED NEW DOMAIN MODEL: **NO**. EXPECTED NEW PERSISTED FACTS: **NO**. Existing AnalysisRun/ModelRevision/snapshot/Prediction/Reflection remain sufficient. A presentation epoch/view-model is transient state, not a new history model. `makemigrations --check --dry-run` is a guard; any unexpected model drift is a STOP, not authorization to generate a migration.

## S. Risks and STOP conditions

Main HEAD drift; protected state change; baseline failure; inability to prove selected-Run binding using existing facts; new schema/history/persisted facts; unresolvable historical identity; new mechanics, thresholds, ranking, safety or path truth; changed role/lifecycle/privacy; required public test unavailable; unresolved independent review finding. Stop with evidence and the smallest needed decision, do not substitute latest/current Draft or invent an answer. Missing Teacher/Owner feedback remains explicitly pending, not automatically passed. Teacher wording/order/depth revisions stay bounded and tested; other requests need a new scope decision.

## T. Estimated size and execution recommendation

**L** — cross-panel selected-Run safety, async Reflection ownership, a genuine public v2 teaching loop and history/lifecycle evidence make this larger than the original scope-only M estimate. This is not new feature scope. Recommend **Native sequential Tasks 1–8 + internal architecture checkpoint after Task 2 + one independent whole-branch review before manual acceptance**. Shared presenter/selection interfaces favor sequential ownership. Teacher Review remains a separate human gate. No automatic agent/worktree/task launch.

## U. Historical readiness and planning self-review

Read-only audit found no architecture blocker and no need for schema/history/API expansion. All 22 requested RED obligations map to named tests, all five Review Focus cases map to owning tasks, interfaces use one TeachingView and selection epoch, and each implementation task has exact files, RED/minimal/GREEN/commit/STOP boundaries. Characterizations and verification-only tasks are explicitly distinguished from real failing feature tests. Required public loop, independent review, Teacher gate and full regression are planned, **not executed**.

Historical planning handoff (superseded by the Owner's subsequent plan/method approval): no implementation occurred during preparation of this plan. Execution and fresh gate outcomes are recorded separately in the linked implementation evidence; no remote action is authorized.

**M9 OWNER SCOPE APPROVED**

**OWNER PLAN / NATIVE SEQUENTIAL EXECUTION APPROVED — TEACHER / OWNER REVIEW PENDING**
