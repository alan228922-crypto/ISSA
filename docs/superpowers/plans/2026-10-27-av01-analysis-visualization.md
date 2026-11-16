# AV-01 — Analysis Visualization TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL upon future implementation authorization: Use superpowers:executing-plans to implement this plan task-by-task. **Approved method: Native Sequential**, with a projection architecture checkpoint and one independent whole-branch review at Task 9. Plan/method approval is separate from implementation approval, which is NOT APPROVED. Steps use checkbox (`- [ ]`) syntax for tracking. Nothing below authorizes execution now.

**Goal:** Add a readonly selected-Run Results Canvas with saved reactions, AUTO straight-segment deformation, independent layers and factual object Evidence, preserving M9 teaching semantics.

**Architecture:** A pure backend projection reads immutable linked Snapshot and saved Solver input/results. A dedicated Results renderer consumes that projection and optional existing M9 facts under the same selection epoch; editable Draft/controller state is never its geometry authority. Visualization starts after successful existing data/reveal disclosure, then loads independently of Comparison/Explanation requests.

**Tech Stack:** Existing Django/Python, native JavaScript ES modules/SVG/CSS, pytest/pytest-django and Playwright. No dependency, model, migration or Solver change.

**Spec:** [AV-01 written specification](../specs/2026-10-27-av01-analysis-visualization.md); read it plus the linked Source-of-Truth contracts before execution.

**Status:** APPROVED — Phase 1 Task 1–2 IMPLEMENTED / QA VERIFIED (2026-11-11); Tasks 3–10 NOT EXECUTED / NOT APPROVED. Estimated full feature size **L**.
**Documentation amendment:** 2026-11-05 (Asia/Shanghai), Owner documentation approval / docs-only update.
**Written Spec approval:** APPROVED.
**TDD Plan approval:** APPROVED.
**Execution method approval:** APPROVED — Native Sequential + Task 9 independent whole-branch review.
**Results Hover Preview Amendment:** APPROVED — Spec §11.1 and Task 6 only.
**Implementation approval:** APPROVED — Task 1–2 ONLY (2026-11-10); Tasks 3–10 NOT APPROVED.
**M9 gates:** UNCHANGED — Teacher/Owner review and merge remain pending; no fresh implementation baseline established by this update.

## Owner Phase 1 authorization — 2026-11-10

This bounded status amendment supersedes older gate/status prose below only; engineering contracts are unchanged. Original approved bytes are preserved in custody commit 59731b0 and AV01_DOCUMENT_CUSTODY.json. Integrated main b5873ecc80996dc0561bba313f7053bf65ad023d has fresh 551 Browser / 816 non-browser +22 skips /131 Mechanics subset GREEN. Owner approved documentation custody/status synchronization and **Task 1–2 ONLY** on feat/av01-phase1-projection; Tasks 3–10 remain NOT APPROVED. Native Sequential and an independent Phase 1 whole-diff review apply; this review does not complete later Task 9 for the full feature.

Teacher Formal Review is DEFERRED until functionality and polish are complete, not PASS and no longer a prerequisite to this authorization. M9 P1-001 formal Owner closure remains PENDING. P2-001 is now explicitly ACCEPTED AS UI POLISH FOLLOW-UP. OA-16 and full M9/CAD Owner Acceptance remain PENDING. Controlled integration before remaining manual acceptance was explicitly approved. No Owner/Teacher PASS or deployment approval is inferred.

W01 file-map addition: projects/workspace.py::_urls() may add visualization_template only. No new router/permissions/domain. Existing selected-Run token/epoch and M9 Results/Reflection remain unchanged in Phase 1; Task 7 frontend visualization lifecycle is not pulled forward. W03 Results keyboard isolation remains future TDD, not verified by Phase 1.

Task 1 is saved-fact characterization (expected GREEN; no manufactured RED). Task 2 new projection/API requires genuine RED→GREEN. Reuse same-SHA controlled-integration full baseline evidence; run fresh relevant baseline/regression tests plus system/migration checks, expanding only on evidence of risk. No unchanged full Browser rerun is required. See AV01_PHASE1_AUTHORIZATION.md for authority, scope and gates.

## Global Constraints

- Canonical units remain mm / N / MPa / g; global +X right, +Y up.
- Readonly selected AnalysisRun → linked immutable Revision/Snapshot + saved solver_input_json/result_json. No current Draft/catalog fallback or coordinate identity guessing.
- No Solver call, new idealization, persisted result/snapshot mutation, Load merge, new mechanics classification, maxima/ties computation in JS or authoring side effects.
- Preserve Master §28.1: the new GET never writes reveal evidence and requires existing same-Project/source-draft owner evidence, except existing Manager/Developer exemption. No numeric view after failed initial data/reveal. This prerequisite resolves the first-disclosure SPEC CONFLICT, not a change to Prediction policy.
- Existing M9 supplies teaching states, MIXED/ZERO_FORCE, comparison and all maximum candidates. A raw postprocess ZERO is not a replacement for teaching ZERO_FORCE.
- Reaction is one Rx/Ry pair per analysis node; no support-row distribution. Exact zero has no arrow; tiny nonzero stays nonzero.
- Deformation is OFF by default, AUTO only, straight analysis segments, original ghost and scale notice always present when ON. Minimum alpha 1; upper bound and target remain calibratable.
- Loads ON, reactions ON, force states ON. Layer settings/selection/Fit reset per Run selection and reload, with no DB/localStorage persistence.
- All student-visible and accessible copy hides machine codes, client keys, DB ids, schemas, hashes, raw payload and internal mappings at every level. `labels.js` remains sole naming authority.
- Owner/Manager/Developer/GRACE read access follows existing permissions. PURGED and expired operational access fail closed. No new private DRAFT Reflection/Reasoning disclosure.
- Existing four M9 tabs, optional Prediction, optional student-authored Reflection, ownership and completion semantics stay unchanged.
- No models/migrations, mechanics/idealization changes, CAD-UX-02, safety/Euler/failure behavior or UI POLISH scope expansion.
- No new branch/worktree until all seven Spec §20 gates hold; no automatic merge/push/tag/deploy. Root dirty work, grid, existing DBs and running servers are protected.

## Review Focus

1. Complete numeric visualization can exist when M9 teaching projection is unavailable: Task 7 `test_numeric_layers_survive_unavailable_teaching_facts`; show no invented states/maxima.
2. Same-node support records must not multiply reaction arrows/values: Task 3 `test_same_node_supports_share_one_reaction_display`.
3. Legacy identities containing delimiters and colocated distinct nodes must never be mapped by splitting/proximity: Task 2 `test_legacy_delimiter_identity_is_exact_or_unavailable`.
4. Hidden Conclusion or resized viewport must not produce a zero-size Fit or covered labels: Task 8 `test_hidden_then_visible_canvas_refits_without_fact_change`.
5. Delayed success/error or revoked access after A→B→A must not leave old facts under the current heading: Task 7 race/denial tests.

## 0. Custody, baseline and execution policy

Prepared on M9 worktree `feat/results-teaching-loop-m9@12cb8debc8bb209385330b8a6c8d43594dd517a2`; no AV-01 implementation worktree exists. This is not the future baseline. Only this spec and plan are added by the planning operation; no planning commit is authorized or made now.

Before future execution verify documented Teacher disposition, Owner M9 PASS, actual M9 merge, trusted stable main and explicit **AV-01 IMPLEMENTATION APPROVED**. Written Spec, TDD Plan and Native Sequential + Task 9 review method are APPROVED per Owner's 2026-11-05 documentation instruction; preserve those approvals separately from execution authorization. Establish the isolated AV-01 worktree only after all Spec §20 gates hold. If the planning docs remain untracked on the M9 worktree, preserve them and obtain/confirm authorized docs custody in the integration process; never stash/reset/overwrite protected work to make a clean baseline. Do not interpret plan text as a merge authorization.

Baseline failures are diagnosed before any AV-01 RED. A browser skip/unavailable browser is not PASS. Do not run full suites during this planning operation. During implementation test-owned temporary DBs only; disposable manual environments/accounts/migrations require their applicable authorization and must never use existing DBs.

No per-task review-agent fanout is proposed. Task 9 is the one mandatory independent whole-branch review; execution follows the method approved by Owner.

## 1. Exact file map and responsibilities

| Action | Exact path | Responsibility |
| --- | --- | --- |
| MODIFY | `projects/views.py` | Authorized Run-scoped GET adapter |
| MODIFY | `projects/urls.py` | visualization route |
| MODIFY | `projects/workspace.py` | W01: visualization_template bootstrap key only |
| MODIFY | `projects/static/projects/workspace/run-context.js` | Optional visualization requests, epochs, retry |
| MODIFY | `projects/static/projects/workspace/results.js` | Conclusion Structure View mount hook; preserve four tabs |
| MODIFY | `templates/projects/workspace.html` | Selected-Run integration and safe endpoint URL template |
| MODIFY | `projects/static/projects/workspace/workspace.css` | Import new scoped CSS |
| NEW | `analysis/visualization.py` | Pure saved graph/numeric projection |
| NEW | `projects/static/projects/workspace/analysis-visualization.js` | View projection, numeric formatting, calibration, controls/Evidence |
| NEW | `projects/static/projects/workspace/analysis-visualization-renderer.js` | Readonly SVG, label layout, selection, view transforms |
| NEW | `projects/static/projects/workspace/analysis-visualization.css` | Scoped responsive layout/accessibility |
| NEW | `tests/application/test_analysis_visualization.py` | Saved-data/legacy/provenance tests and numeric fixture builder |
| NEW | `tests/endpoints/test_analysis_visualization.py` | Actual GET access/partial/no-write contract |
| NEW | `tests/browser/test_av01_reactions.py` | Reaction labels, directions, aggregation |
| NEW | `tests/browser/test_av01_deformation.py` | Segment positions, alpha, ghost |
| NEW | `tests/browser/test_av01_layers_evidence.py` | Defaults, toggles, Evidence, accessibility |
| NEW | `tests/browser/test_av01_run_integration.py` | Real routes, M9 compatibility, races, lifecycle |
| NEW | `tests/browser/test_av01_visual_matrix.py` | Sizes/cases, screenshots/calibration |
| NEW | `docs/development/AV01_IMPLEMENTATION_EVIDENCE.md` | RED/GREEN, commits, review, calibration truth |
| NEW | `docs/development/AV01_REVIEW_AND_ACCEPTANCE.md` | Owner checklist and known limits; PENDING |

UNCHANGED: `mechanics/**`, `idealization/**`, all models/migrations, `modeling/**`, `learning/**`, Material/Section services, `labels.js`, `teaching-view.js`, editable `renderer.js`, CAD/editor/controller/state modules, Comparison/Explanation/Reflection semantics. Existing tests are not rewritten to make changed semantics pass. If shared-interface change is necessary, stop for scoped file-map/contract review; any mechanics/domain/migration requirement is a hard STOP.

## 2. Interfaces shared between tasks

Backend:

- `build_visualization_projection(*, run) -> dict` in `analysis/visualization.py`; exact Spec §6 payload, deterministic saved data only. No teaching service call. Availability returned in body; programmer/server exception is not silently converted to fabricated READY.
- `analysis_visualization(request, project_id, run_id)` named route `projects:analysis_visualization`; GET and existing auth/read/lifecycle behavior, exact Run lookup, `private, no-store`.

Frontend in `analysis-visualization.js`:

- `VISUAL_CALIBRATION`: Spec §12 candidate values, with documented final calibration.
- `formatVisualizationNumber(value, {exact=false}={}) -> string`: finite-only formatting, units appended by caller; invalid → safe unavailable text.
- `buildAnalysisVisualizationView({projection, teachingView=null, expectedContext}) -> object`: `expectedContext={projectId,runId,revisionId,sourceDraftVersion,modelHash,inputHash,inputSchemaVersion,resultSchemaVersion}` comes from scoped bootstrap + discovered Run metadata + a successful exact-Run `analysis_data` response; match every projection field before joining. Retain valid numeric layers without optional teaching facts; no classification or maxima derivation.
- `deformationDisplayScale({nodes, maximumMm, calibration=VISUAL_CALIBRATION}) -> {available, alpha, reason}`: finite geometry bbox, supplied maximum, zero validation; no node-max search.
- `createAnalysisVisualization({root, onRetry}) -> {setSelection({runId, epoch, metadata}), useProjection(event), useTeachingView(view, epoch), clear(), destroy()}`: readonly UI lifecycle; holds selection/layers/viewport outside Workspace Draft state.

Renderer in `analysis-visualization-renderer.js`:

- `renderAnalysisVisualization(svg, view, {layers, alpha, viewTransform, selected, onSelect}) -> void`.
- `reactionDisplayComponents(reactions, calibration) -> array`: display lengths/directions only; preserve numeric values. Exported for focused browser-module assertions.
- `displacedAnalysisNodes(nodes, alpha) -> array`: saved x/y + scaled saved displacement; no topology mutation.

Run context (Task 7): add optional `urls.visualizationTemplate`, `onVisualization(event=...)` callback and `retryVisualization()` to `createRunContext()`. Events have `{kind: "LOADING"|"READY"|"UNAVAILABLE"|"ERROR"|"DENIED", runId, epoch, metadata, expectedContext?, projection?, message?}`. Metadata is the discovered selected Run, not latest. Construct trusted expectedContext only after `analysis_data` succeeds and matches Run metadata; only then start optional visualization fetch without awaiting it in the subsequent required Comparison/Explanation chain. Before that, no numeric rendering. Retry is same Run/current token with a valid data anchor only. Clear/mount synchronously on selection; if visualization arrives before teaching, retain it under the same epoch. Teaching failure alone is not numeric failure; initial data/reveal failure is a prerequisite failure. Server independently enforces prior reveal evidence on direct requests.

DOM hooks (new, scoped): `[data-av01-root]`, `[data-av01-canvas]`, `[data-av01-status]`, `[data-av01-layer="loads|reactions|forceStates|deformation"]`, `[data-av01-scale]`, `[data-av01-evidence]`, `[data-av01-object-list]`, `[data-av01-retry]`. Use stable ids only as internal attributes, never visible/ARIA copy. Test API/provenance joins, not internal attributes as evidence of student safety.

## Task 1 — Baseline / characterization (AV01-01/03/14 prerequisites)

**Files:** Read all mapped sources and existing M9 tests; create evidence doc and characterization portion of `tests/endpoints/test_analysis_visualization.py` only after gates. No production changes.

**Interfaces:** Consume actual post-M9 stable main and existing Run endpoints. Produce recorded base SHA, source contracts, clean protected inventory and baseline result record.

- [x] Confirm seven gates and isolated worktree; record branch/HEAD, `git status --short`, main ancestry, protected root diff/DB fingerprints without printing sensitive content, grid and running-platform inventory.
- [x] Run fresh baseline commands below BEFORE any production/test edit. Select existing M9 public journey, history permissions and Run-context browser modules as browser baseline.
- [x] If failure, diagnose and stop AV-01 RED attribution. No sleeps/test weakening as a fix.
- [x] Add `test_existing_saved_run_fields_support_visualization` characterization against a real successful test Run: saved nodes/members/supports/loads/mapping and result u/R/N exist; linked Revision remains historical after current Draft/library changes. This test is expected GREEN, not invented RED.
- [x] Record intended RED boundary: missing new `projects:analysis_visualization` endpoint/projection in Task 2. Do not implement ahead of that failure.
- [x] Run characterization and existing M9 subset; record GREEN and browser availability.
- [x] Commit characterization/evidence only: `test: characterize AV-01 saved-run baseline`.

Baseline commands:

```bash
pytest -q -m 'not browser'
pytest tests/mechanics -q
pytest tests/permissions tests/endpoints/test_m9_run_contract.py -q
pytest tests/browser/test_m9_public_teaching_loop.py tests/browser/test_m9_history_permissions.py tests/browser/test_m9_run_context.py -q
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
git diff --check
```

## Task 2 — Visualization Projection Contract (AV01-01..04)

**Files:** NEW application/endpoint test files and `analysis/visualization.py`; MODIFY `projects/views.py`, `projects/urls.py`; evidence doc.

**Interfaces:** Consume saved Run structures. Produce exact backend interfaces in §2 and Spec §6 contract; frontend tasks rely on complete graph plus independent capabilities.

- [x] Write `test_saved_run_projection_is_deterministic_and_readonly`: two calls equal; Run/Revision/result/input/Snapshot/DB counts unchanged; current Draft/material modifications do not affect output. Use actual `analyze_project` in test setup, not fabricated production Runs.
- [x] Write `test_projection_never_calls_solver_or_idealize`: after creating the genuine Run, make Solver and idealization entry points raise if called during projection/GET; assert successful saved-data projection and no added records.
- [x] Write exact identity tests for v1/v2, delimiter-containing ids, colocated different nodes, intermediate segments, stale/wrong physical mapping, duplicate nodes/endpoints/results, nonfinite/bool values. Valid explicit provenance succeeds; ambiguity yields UNAVAILABLE, never coordinate repair.
- [x] Write `test_missing_layer_does_not_destroy_independent_facts`: remove displacements from an isolated copied test Run → deformation unavailable while valid reactions/loads remain; exact all-zero complete data stays READY. Missing shared graph disables all.
- [x] Write endpoint access matrix: anonymous, wrong Project/Run, inactive authority, Owner, assigned Manager/Developer, GRACE, PURGED residual rows and stale ACTIVE past purge_at. Reuse existing auth semantics; assert non-SUCCESS 422 and new endpoint no-store header.
- [x] Write `test_student_projection_requires_existing_disclosure`: direct first owner GET is409 with no facts/no new reveal; ordinary `/data/` succeeds and establishes existing evidence; subsequent visualization GET is200 with no added records. A reveal-recording failure keeps visualization blocked. Manager/Developer GET does not create reveal evidence. GRACE follows the existing history disclosure contract, not a new exemption.
- [x] Run `pytest tests/application/test_analysis_visualization.py tests/endpoints/test_analysis_visualization.py -q`; confirm real missing API/function RED and save redacted failure evidence.
- [x] Implement the pure projection and guarded GET only, with finite serialization, sorted identities and safe availability. No teaching derivation; no new domain model.
- [x] Rerun targeted tests to GREEN plus existing report/Run contract tests. Compare exact saved numeric values, not rounded approximation for projection copying.
- [x] Architecture checkpoint: graph authority, optional-layer isolation, endpoint read guards, no Solver/write, labels adapter and no teaching classifier. If consistent, continue without Owner pause; new product/schema conflict STOP.
- [x] Commit: `feat: add readonly saved-run visualization projection`.

Representative assertion shape (fixture names defined in the new application test module):

```python
def test_saved_run_projection_is_deterministic_and_readonly(saved_run):
    before = saved_run.result_json.copy()
    first = build_visualization_projection(run=saved_run)
    assert first == build_visualization_projection(run=saved_run)
    assert first['provenance']['analysis_run_id'] == saved_run.id
    saved_run.refresh_from_db()
    assert saved_run.result_json == before
```

Deep-copy/fingerprint all persisted structures and counts in the full test; the fragment above illustrates the builder's return type, not adequate whole-test coverage on its own.

## Task 3 — Reaction visualization (AV01-05..07)

**Files:** NEW `analysis-visualization.js`, renderer, CSS, `tests/browser/test_av01_reactions.py`; evidence doc. Mount isolated component in browser tests until public integration Task 7; label this supplied-fact component evidence, not public Solver evidence.

**Interfaces:** Consume Task 2 nodes/supports/reactions/label source. Produce formatter, reaction component display function and initial readonly component interfaces in §2. No deformation yet.

- [ ] Write parameterized `test_reaction_components_match_saved_sign_and_value`: (+84,0), (-84,0), (0,+326), (0,-326), (+84,-326) yield correct screen arrow directions under Y inversion and signed exact label values. Inspect SVG endpoints and rendered text.
- [ ] Write `test_zero_tiny_and_numeric_formatting`: 0/-0 have no directional glyph; ±1e-12 have nonzero scientific labels/minimum arrow; 1e9, missing and nonfinite distinguish true numbers/unavailable. Assert same Run normalization and bounded candidate 20..64 px, including extreme finite ranges.
- [ ] Write `test_same_node_supports_share_one_reaction_display`: two support rows, one saved reaction → two related support names, exactly one Rx/Ry pair. Never assert an invented per-support share.
- [ ] Write `test_support_direct_load_uses_saved_reaction`: analyze genuine benchmark-style test input with load directly on a restrained node; compare display to saved reaction including that load, not `-sum(other loads)`.
- [ ] Run `pytest tests/browser/test_av01_reactions.py -q` and observe behavior RED before implementing render/formatter.
- [ ] Implement reactions/anchor marker/legend/labels, safe Snapshot resolver and explicit collision overflow indicator; no editable hit controller. Preserve all raw numbers.
- [ ] Run targeted GREEN; browser inspect representative sign cases at 1280×800 and note provisional collision/arrow calibration.
- [ ] Commit: `feat: visualize saved nodal support reactions`.

## Task 4 — Deformed shape (AV01-08..09)

**Files:** MODIFY two new visualization JS modules/CSS; NEW `tests/browser/test_av01_deformation.py`; evidence doc.

**Interfaces:** Consume complete saved node displacements/segment endpoints plus supplied M9 maximum. Produce `deformationDisplayScale`, `displacedAnalysisNodes`, ghost and scale notice. No frontend maximum search.

- [ ] Write `test_deformation_uses_saved_segment_endpoints`: for alpha=2, saved (10,20), u=(0.5,-0.25) displays (11,19.5), while source remains (10,20)/(0.5,-0.25). Parameterize ux-only/uy-only/combined and y-axis inversion.
- [ ] Write `test_intermediate_joint_remains_piecewise_straight`: two saved segments through intermediate node render as two independent straight lines using all three displaced nodes; no Bezier/spline or whole-member shortcut.
- [ ] Write `test_deformation_scale_cases`: D=1000 and Umax=1 gives candidate alpha=50; Umax=100 gives alpha=1; Umax=1e-12 caps at10000; all-zero gives1; missing/bool/nonfinite/zero-D/contradictory maximum or absent M9 maximum → unavailable. Use exported calibration values in bound assertions, plus separately pin chosen defaults while provisional.
- [ ] Write ghost/notice tests: cannot hide ghost independently; nonzero tiny does not say0; ×1 notice distinct; any alpha>1 never rounds to1; pan/zoom does not change alpha or saved values. Huge finite coordinates/scale arithmetic cannot emit invalid SVG numbers.
- [ ] Run `pytest tests/browser/test_av01_deformation.py -q` to real RED.
- [ ] Implement only saved-geometry display math, bounded AUTO, always-on ghost and notice, Fit union with padding and explicit unavailable states.
- [ ] Run targeted GREEN and reaction regression; real browser inspect ghost/notice at all three required dimensions as preliminary evidence.
- [ ] Commit: `feat: add amplified straight-segment deformation view`.

## Task 5 — Layer controls (AV01-10)

**Files:** MODIFY visualization component/CSS; NEW `tests/browser/test_av01_layers_evidence.py` layer tests; evidence doc.

**Interfaces:** Consume readonly view and render functions. Produce transient four-layer controls without Workspace editor coupling.

- [ ] Write `test_layer_defaults_toggles_and_reset_are_transient`: defaults loads/reactions/forceStates true and deformation false; toggling one leaves others unchanged; explicit Run reselection/reload resets; no localStorage writes.
- [ ] Assert on/off cycles, unavailable disabled-with-reason, zero-load READY, force-state data absence neutral geometry, and ghost fixed when deformation ON. No HTTP POST, Draft dirty/history/version/selection mutation.
- [ ] Write keyboard Tab/Space tests for all toggles with visible focus and stable label/notice. Toggling hidden Conclusion must not focus-steal from another M9 tab.
- [ ] Run `pytest tests/browser/test_av01_layers_evidence.py -k 'layer or toggle' -q` to RED.
- [ ] Implement controls; reset in `setSelection`, rerender selected view only. No persistence or new keyboard CAD handlers.
- [ ] Run same command GREEN plus Task 3/4 tests; inspect control wrapping at 1024×768.
- [ ] Commit: `feat: add independent readonly results layers`.

## Task 6 — Object Evidence (AV01-11/15/18)

**Files:** MODIFY visualization modules/CSS; extend layers/evidence test file; evidence doc.

**Interfaces:** Consume Snapshot labels and matching M9 member/candidate/comparison facts. Produce ANALYSIS_NODE/SUPPORT/ANALYSIS_SEGMENT selection and equivalent accessible object list/table.

**Approved Results Hover Preview Amendment:** Consume the same Object Evidence projection, safe labels, availability and number formatting for the existing three target types (Spec §11.1 / AV01-18). No second projection, identity mapping, Results selection state machine or mechanics. Only component-local target reference, screen anchor and pending timer owned by the existing Run/epoch lifecycle are needed. The approximately 400 ms stable-pointer delay is a visual calibration candidate in the existing calibration export. Clicking retains complete Inspector selection; keyboard/touch retain the existing equivalent entries. Do not add CAD-UX-02 behavior to this task.

- [ ] Write `test_selected_object_evidence_is_snapshot_bound`: node displays original x/y, actual ux/uy, displacement magnitude; support displays aggregate node reaction plus related rows; segment displays mapped member, force, all sibling segment evidence and optional existing comparison. Display positions never masquerade as geometry values.
- [ ] Write `test_no_internal_identity_in_visible_or_accessible_copy`: include standard, UUID, delimiter and legacy ids; inspect rendered text, title/tooltips and accessible names at all levels, including expanded values. Description plus stable code comes only from `labels.js` over Snapshot source.
- [ ] Test same immutable object labels survive filtering/order changes, no Prediction still works, all tied candidate markers/list entries retained, MIXED keeps per-segment facts and no recomputation.
- [ ] Extend existing keyboard/touch equivalence checks: list/keyboard and touch selection show the same complete Evidence as pointer; Hover never takes focus or becomes a required entry point. Decorative ghost/arrows do not create duplicate objects; readonly selection cannot dispatch delete/grip/drawing/editor events.
- [ ] In the same document with editable Workspace SVG, assert Results SVG resource ids are scoped and selecting/deleting an Evidence item never changes Draft selection/history or either Canvas's unrelated markers/patterns.
- [ ] Write `test_hover_preview_reuses_object_evidence`: each existing ANALYSIS_NODE/SUPPORT/ANALYSIS_SEGMENT target shows its safe name and 2–4 principal Evidence items after approximately 400 ms stable hover, using identical values/units/formatting to the Inspector. Hover does not change selected object or Inspector. Pointer movement restarts the delay; assert no new fetch, whole Evidence projection rebuild or full Canvas redraw on pointermove.
- [ ] Write `test_hover_preview_does_not_intercept_canvas_actions`: the entire preview has `pointer-events: none`, no buttons/editor fields/focus target or pointer capture. Existing click selection, pan, wheel zoom and Fit work with pending/visible Preview, cancel it and leave Draft/history unchanged.
- [ ] Write `test_hover_preview_cancel_and_dismiss`: exercise Hover pending, Visible, Cancelled and Dismissed; pointer leave/target change/pointerdown/pan/wheel zoom/Fit/Canvas hidden/Results tab leave/pointercancel/target removal/destroy clear timer, Tooltip and anchor. Escape dismisses until pointer leaves/re-enters without changing existing CAD/Results command-cancellation semantics. Use controlled timers/events and observable state, not test sleeps.
- [ ] Write `test_hover_preview_cannot_survive_run_epoch_change`: existing component selection lifecycle clears pending/visible Preview synchronously on Run/epoch changes, same-Run reselection and A→B→A; release old callbacks after the change and assert no stale Tooltip/anchor. Reuse the Task 7 epoch interface; do not build a second Run controller or selection state machine.
- [ ] Write `test_hover_preview_uses_safe_availability_and_labels`: assert `暂不可用` for missing/invalid values and `未设置` only for unset descriptions; exact saved zero is preserved, tiny nonzero never becomes zero. Inspect visible/accessible text for raw IDs/hashes/client keys; historical facts never come from current Draft/catalog. Preserve node aggregate reaction and segment force, with no support distribution, segment averaging, mechanics recomputation or MIXED/ZERO_FORCE reclassification; unresolved identity/provenance creates no fallback target.
- [ ] Run `pytest tests/browser/test_av01_layers_evidence.py -q` to RED for new evidence tests.
- [ ] Implement Evidence/table/list and hit targets; use DOM textContent and existing safe resolver, do not modify naming authority or learning services.
- [ ] Implement only the Spec §11.1 transient Preview presentation/lifecycle over that same Evidence, using the existing component `setSelection/clear/destroy` lifecycle and Task 7 epoch ownership. Render 2–4 items in a noninteractive Engineering Inspector Tooltip within the visible Canvas, with low decoration/thin border/small radius, no obstruction of primary operations and Simplified Chinese copy. Do not add another selection state machine or rebuild/redraw the full projection/Canvas on pointermove.
- [ ] Run GREEN, inspect keyboard-only flow, scale announcement and non-color legend in a real browser.
- [ ] Commit: `feat: connect results objects to historical evidence`.

## Task 7 — M9 integration / races (AV01-03/04/12..14/17)

**Files:** MODIFY `run-context.js`, `results.js`, `templates/projects/workspace.html`, `workspace.css`; extend visualization component; NEW `tests/browser/test_av01_run_integration.py`; evidence doc.

**Interfaces:** Consume §2 optional request callback/retry and component lifecycle; retain original M9 onSelect contract. Produce mounted public Conclusion Structure View with independent numeric/teaching availability and token ownership.

- [ ] Write public-route `test_visualization_keeps_m9_navigation_and_reflection_contract`: use real v2 public drawing/Save/Check/Analyze routes and genuine SUCCESS result. All four tabs remain available; Reflection stays same-Run optional/student-authored. No synthetic AnalysisRun insert in the primary journey.
- [ ] Write no-Prediction, UNSURE, NOT_COMPARABLE, MIXED/ZERO and all-tie cases. Controlled supplied-fact browser cases remain explicitly labeled; never claim triangle Solver naturally produced MIXED/ties.
- [ ] Write `test_projection_late_success_error_and_aba_are_discarded`: delay only projection GET responses/failures; A→B and A→B→A keep new epoch Canvas/labels/scale/Evidence. No test sleep as synchronization; use request interception barriers and visible state conditions.
- [ ] Write `test_numeric_layers_survive_unavailable_teaching_facts`: successful ordinary data/reveal plus valid selected-Run numeric projection and missing later teaching payload → geometry/reactions/loads remain, force-state/max marker/deformation requiring supplied maximum unavailable; do not invent replacements. Optional API failure leaves valid M9 text/tables.
- [ ] Write `test_numeric_layers_require_data_anchor_not_teaching_availability`: unavailable teachingView has no trusted metadata, so use separately validated data anchor; mismatched Project/Revision/hash and failed initial data/reveal prohibit rendering even with a plausible projection. A late data response cannot establish a new epoch's anchor.
- [ ] Write `test_denial_clears_view_but_network_failure_is_isolated`: permission denied during retry clears protected selected surfaces; network outage shows safe same-Run retry only. Stale old denial cannot clear new authorized selection.
- [ ] Genuine Run A → change Draft/material/load → genuine Run B → select A: saved A geometry, values, labels, loads and Evidence persist; never read Draft B. Current editable Canvas/hotkeys untouched; selected-Run controls do not Save.
- [ ] Write readonly Manager/Developer/GRACE and PURGED residual endpoint/UI cases. Check private DRAFT Reflection remains governed by existing routes, not projection.
- [ ] Run `pytest tests/browser/test_av01_run_integration.py -q` to RED; retain exact failure evidence.
- [ ] Implement optional projection request/callback/clear/retry ownership and dedicated Conclusion root. Allow numeric view after successful data/reveal but before/without full teaching view. Guard independent context before combining; do not await optional request inside the subsequent required teaching chain.
- [ ] Run new integration GREEN; rerun existing M9 public teaching/history/run-context modules plus all AV-01 modules. Investigate regressions without changing teaching semantics.
- [ ] Commit: `feat: integrate selected-run visualization without changing M9 semantics`.

## Task 8 — Real browser / visual acceptance (AV01-15..16)

**Files:** NEW `tests/browser/test_av01_visual_matrix.py`; optional visual-only adjustments to new visualization modules/CSS; evidence doc.

**Interfaces:** Consume public integration; produce genuine screenshots and recorded calibration values. Browser verification is a deliverable, not DOM-only approval or Owner PASS.

- [ ] Add parametrized responsive test `test_visualization_keyboard_and_role_matrix` at 1024×768,1280×800,1440×900; inspect actual screenshots and keyboard behavior, not just element existence. Add `test_hidden_then_visible_canvas_refits_without_fact_change`.
- [ ] Execute cases A–K in the matrix below. For real Solver cases use public setup/edit/Save/Check/Analyze or genuine saved test Runs; mark controlled fixtures unmistakably. Never change real Projects or claim controlled facts are naturally solved cases.
- [ ] Record before screenshots with exact Run/case, dimensions and calibration; identify overlap/readability/clipping failures. If an actual visual defect exists, add the meaningful failing geometric/accessibility assertion before fixing it.
- [ ] Tune only visual parameters; record before/after value, concrete reason, screenshots, affected tests and saved input/result/Snapshot unchanged. Constants are not mechanics thresholds. If already acceptable, record no tuning, not artificial RED.
- [ ] Run `pytest tests/browser/test_av01_visual_matrix.py -q` and all AV-01 browser modules GREEN; inspect pointer pan/zoom/Fit, load/reaction anchors and Evidence at every size.
- [ ] Freeze proposed final calibration in evidence for Owner review; do not mark Owner visual acceptance PASS.
- [ ] Commit: `test: verify AV-01 responsive visual evidence` (include any justified visual-only fix).

### Required real browser matrix

Every row is checked at each of the three dimensions. K is denied access, so no legitimate geometry/labels are expected; verify no protected render instead.

| Case | Fixture | Inspect |
| --- | --- | --- |
| A | Simple triangle, genuine public Analyze | direction, true labels, force states, ghost/notice |
| B | Larger truss | collision rails, visibility, pan/zoom/Fit, overflow/performance |
| C | Multiple support rows/nodes | one reaction/node, clear related supports |
| D | Multiple Load rows | saved vectors retained, no silent merge or hidden fact |
| E | Tiny nonzero displacement | upper bound, nonzero formatting/readability notice |
| F | Large relative displacement | alpha=1, no safety inference, Fit union |
| G | Intermediate Joint / multiple segments | piecewise straight, no shortcut/curve, MIXED evidence |
| H | Historical A vs Draft B | all geometry/facts belong to A |
| I | Manager/Developer readonly | full allowed visualization, no edits/private learning draft |
| J | FINISHED_GRACE | history visualization usable, no student writes |
| K | PURGED access rejection | denied, no stale rendered content |

Each legitimate row: label collision, layer overlap, arrow direction, member visibility, ghost, scale notice, Evidence, pan/zoom/Fit and document horizontal overflow. Record graph size and practical interaction observations; no performance PASS inferred just from a small triangle or DOM count.

## Task 9 — Independent whole-branch review and regression

**Files:** Review complete base..feature diff; any fixes only in the approved file map; evidence doc.

**Interfaces:** Consume GREEN feature and evidence; produce findings by Critical/Important/Minor and resolved review record. At least one independent whole-branch review; no substitute for Teacher/Owner.

- [ ] Verify feature scope/diff and baseline gates still hold. Request one fresh independent reviewer for projection authority, numerical display vs mechanics, optional failures, identity/labels, readonly/lifecycle, async ABA and actual visual evidence.
- [ ] Record findings. Critical/Important → add real RED regression, minimal fix, targeted GREEN. Re-review affected findings until closed; Minor may be explicitly deferred with reason/acceptance impact.
- [ ] Execute fresh final commands below after the last relevant fix; inspect complete outputs and exact skip reasons. New required browser tests cannot be silently skipped. Mechanics numbers must remain unchanged.
- [ ] Verify no model/migration files changed and no runtime DB/credentials/sensitive screenshots staged. No `migrate` on existing DB; migration command is check/dry-run only.
- [ ] Commit only reviewed fixes/evidence: `fix: close AV-01 review findings` if needed; no empty ceremonial fix commit.

```bash
pytest tests/application/test_analysis_visualization.py tests/endpoints/test_analysis_visualization.py -q
pytest tests/browser/test_av01_reactions.py tests/browser/test_av01_deformation.py tests/browser/test_av01_layers_evidence.py tests/browser/test_av01_run_integration.py tests/browser/test_av01_visual_matrix.py -q
pytest -q -m 'not browser'
pytest tests/browser -q
pytest tests/mechanics -q
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
git diff --check
```

## Task 10 — Owner acceptance package (no acceptance claim)

**Files:** NEW `docs/development/AV01_REVIEW_AND_ACCEPTANCE.md`; finalize evidence doc. No new product feature.

**Interfaces:** Consume actual test/review/screenshots/calibration results. Produce reviewable bounded handoff, known limits and explicit Owner checklist PENDING.

- [ ] Prepare before/after genuine screenshots showing the same case/Run where possible; distinguish real public analysis from supplied-fact cases. No fake result, screenshot or Teacher/Owner answer. Retain redacted evidence outside tracked source under existing evidence practice.
- [ ] Include branch/HEAD/base, test commands/counts/skips, projection examples with secrets removed, final calibration values, review dispositions and known limits.
- [ ] Owner checklist: load/reaction signs; zero/tiny; deform ON/OFF/ghost/notice; segment Joint; historical A/B; keyboard Evidence; readonly/GRACE; no CAD/teaching regression. Keep all outcomes unfilled/PENDING until actual Owner feedback.
- [ ] Describe manual runtime/account requirements separately; do not seed/migrate/start a new acceptance environment without the applicable authorization. No credentials in repo/evidence/logs. Never substitute private existing data.
- [ ] Recheck protected work, production file boundaries, links and `git diff --check`. Commit docs: `docs: prepare AV-01 owner visual acceptance`.
- [ ] Stop at `AV-01 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING` only after actual implementation/gates are complete. Never merge/push/tag/deploy automatically.

## Acceptance-to-RED coverage map

| Spec AC | Task | Test / evidence |
| --- | --- | --- |
| 01 | 2 | saved_run_projection_is_deterministic_and_readonly; projection_never_calls_solver_or_idealize; student_projection_requires_existing_disclosure |
| 02 | 2 | v1_v2_explicit_identity_mapping; legacy_delimiter_identity_is_exact_or_unavailable; bad_graph_or_identity_is_unavailable |
| 03 | 2/7 | visualization_access_matrix; readonly/GRACE/PURGED integration |
| 04 | 2/7 | missing_layer_does_not_destroy_independent_facts; numeric_layers_survive_unavailable_teaching_facts |
| 05 | 3 | reaction_components_match_saved_sign_and_value |
| 06 | 3 | zero_tiny_and_numeric_formatting; support_direct_load_uses_saved_reaction |
| 07 | 3 | same_node_supports_share_one_reaction_display |
| 08 | 4 | deformation_uses_saved_segment_endpoints; intermediate_joint_remains_piecewise_straight |
| 09 | 4 | deformation_scale_cases; ghost_and_scale_notice_are_always_present_when_on |
| 10 | 5 | layer_defaults_toggles_and_reset_are_transient |
| 11 | 6 | selected_object_evidence_is_snapshot_bound; no_internal_identity_in_visible_or_accessible_copy |
| 12 | 7 | existing_teaching_facts_are_not_reclassified |
| 13 | 7 | projection_late_success_error_and_aba_are_discarded |
| 14 | 7 | visualization_keeps_m9_navigation_and_reflection_contract; genuine historical A/B |
| 15 | 6/8 | visualization_keyboard_and_role_matrix; object-list equivalence |
| 16 | 8/10 | 3-size × A–K screenshots/calibration records and PENDING Owner checklist |
| 17 | 7 | denial_clears_view_but_network_failure_is_isolated; numeric_layers_require_data_anchor_not_teaching_availability |
| 18 | 6 | hover_preview_reuses_object_evidence; hover_preview_does_not_intercept_canvas_actions; hover_preview_cancel_and_dismiss; hover_preview_cannot_survive_run_epoch_change; hover_preview_uses_safe_availability_and_labels; extend existing keyboard/touch equivalence |

Test names above have `test_` prefixes in actual modules. Every named behavior is added in its owning task before its implementation, except existing-behavior characterization and visual observations that are explicitly not claimed RED. No test body is executed repeatedly to manufacture reliability evidence.

## Handoffs and final planning state

M9 is still Teacher/Owner PENDING and not merged. UI POLISH exact plan needs read-only file-map reconciliation before AV-01 execution; no scope transfer. CAD-UX-02 and Failure handoffs are Spec §19 notes only, with no tests/code here. Failure remains unapproved and O-001 OPEN.

Approved plan does not authorize feature creation or Task 1 execution. Written Spec, TDD Plan and Native Sequential + Task 9 independent whole-branch review are separately APPROVED; AV-01 Implementation remains NOT APPROVED. Spec §20 gates (5)/(6) are satisfied by documentation approval only; M9 gates (1)–(3), fresh baseline gate (4) and explicit implementation gate (7) are not closed by this update. No new Task checkbox is completed.

Planning checks: spec received one independent read-only builder check; first-disclosure and independent-provenance questions were resolved and rechecked. Plan self-review matched Spec AV01-01..17 to Tasks 2–8, checked shared interface names and preserved separate characterization, implementation, visual tuning and acceptance gates. No baseline/regression/RED was executed in this planning phase; no Task checkbox is complete.

2026-11-05 docs-only amendment: before editing, verified M9 HEAD `12cb8debc8bb209385330b8a6c8d43594dd517a2` and both untracked file fingerprints against the reconciled copies: Spec SHA-256 `1747d3068c54935798bf2bcc355fbfa0c2335610f96c8712d22d8247239b478b`; Plan SHA-256 `029e660856195300b2ce301784b528d53ea7b05e9a584b9e0316767991e2dbe3`. Added AV01-18 coverage exclusively to Task 6 and the existing keyboard/touch checks; no production/test file or data/identity/mechanics contract changes, no test execution, no branch/worktree creation and no commit/merge/push/tag/deploy. Preserve both files untracked for Owner custody; no reset/stash/move. M9 Gate and CAD-UX-02 boundaries remain unchanged.

**AV-01 SPEC + TDD PLAN APPROVED — RESULTS HOVER AMENDMENT DOCUMENTED — IMPLEMENTATION GATE PENDING**


2026-11-11 Phase 1 completion record: Task 1–2 only implemented and independently reviewed. Final code 80ecee9; 983 non-browser passed/22 existing concurrency skips; 128 relevant M9/KB01 Browser passed; 131 Mechanics passed (subset); checks/dry-run/diff clean. Original approved engineering text retained; Task1 gate/baseline checkboxes reflect the explicit limited Owner exception and retained same-base full integration evidence, not a Teacher/Owner PASS. Full later Task9 not completed by the Phase1 review. See docs/development/AV01_PHASE1_IMPLEMENTATION_REPORT.md.
