# Node as Joint Architecture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the new editable Draft's Connection object with Node-as-Joint topology while preserving historical v1 behavior and numerical results.

**Architecture:** Build an explicit v2 Node/PhysicalMember/incidence graph beside the existing v1 graph, then version snapshots and Idealizer dispatch without changing the solver. Convert eligible projects transactionally through an audited equivalence gate; blocked projects retain read-only legacy recovery. The v2 Canvas authors explicit incidence at confirmed edits, while renderers and the Idealizer never infer topology from geometry.

**Tech Stack:** Django ORM/migrations and JSON services, Python Idealizer and existing Truss2DSolver, browser-native JavaScript/SVG/CSS, pytest/Django test DB, Playwright Chromium.

**Spec:** `docs/superpowers/specs/2026-09-29-node-as-joint-architecture-design.md` at approved commit `bc64228`.

## Global Constraints

- Execute from a new isolated implementation worktree/branch based on `feat/structural-sketch-visual-language` **after this plan commit** (the plan commit descends from `bc64228`); keep the existing feature worktree and `main` intact. No merge, push, tag, or deploy.
- Draft contracts are `physical-draft-v1` and `physical-draft-v2`; Snapshot contracts are `physical-snapshot-v1` and `physical-snapshot-v2`; Prediction contracts are `prediction-v1` and `prediction-v2`. Historical readers dispatch on each artifact's own schema, never the current Project schema.
- New v2 topology authority is Node identity plus member endpoint reference or explicit `MemberJointIncidence`. Normal v2 member-through-Node without participation fails save with `MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE`; only exact audited legacy exemptions pass. Geometric crossing without Node is not connected.
- Preserve `PhysicalMember` identity, independent delete/incomplete-Draft UX, immutable ModelRevision/AnalysisRun/Prediction/Reflection/Reasoning, and v1 historical reader. Do not drop `Connection`/`ConnectionParticipation` tables in this project.
- Solver remains `truss2d-input-v1`; 2D pin-jointed, axial-only, `EA/L`, PINNED/ROLLER global X/Y, signs, and `mm / N / MPa / g` are unchanged. Numerical comparisons use `abs_tol=1e-8`, `rel_tol=1e-8` in canonical units.
- Student UI says 选择、节点、构件、支座、荷载 and “有节点才连接；没有节点，交叉也不连接。” / “节点表示这里的构件真正相连，可以传力。” No student-facing Connection object, ring, key, or Properties panel in v2.
- Each phase follows RED → minimal implementation → targeted GREEN → review → logical commit. A later phase starts only after the previous phase contract is green and reviewed; legacy v1 regression stays green throughout.

## File ownership map

| Responsibility | Create | Modify | Test |
| --- | --- | --- | --- |
| V2 schema, draft I/O, topology validation | `modeling/topology.py`, `modeling/serialization.py`, `modeling/migrations/0004_node_joint_v2_schema.py`, `projects/migrations/0003_project_draft_schema_version.py` | `modeling/models.py`, `modeling/services.py`, `modeling/completeness.py`, `projects/models.py`, `projects/views.py`, `projects/workspace.py` | `tests/application/test_node_joint_draft.py`, `tests/endpoints/test_workspace.py`, existing `test_physical_draft.py`/`test_draft_independence.py` |
| Snapshot and Idealizer v2 | `idealization/truss2d_v2.py` | `modeling/snapshot.py`, `idealization/truss2d.py`, `analysis/orchestration.py` | `tests/idealization/test_node_joint_v2.py`, `tests/application/test_node_joint_analysis.py`, existing mechanics benchmarks |
| Audited conversion/equivalence | `modeling/node_joint_migration.py`, `tests/application/test_node_joint_migration.py` | `modeling/models.py` (audit model already in Phase 1), `projects/services.py`, `projects/workspace.py` | fresh-DB migration tests and existing migration/analysis suites |
| V2 CAD/Canvas | `projects/static/projects/workspace/joint-candidates.js`, `tests/browser/test_node_joint_workspace.py` | `editor.js`, `modeling-interaction.js`, `state.js`, `renderer.js`, `structural-symbols.js`, `canvas-interaction.js`, `properties.js`, `incomplete-objects.js`, `labels.js`, `workflow.js`, `workspace.css`, `templates/projects/workspace.html` | browser tests plus existing workspace/CAD tests |
| Learning, results, reports | `learning/prediction_v2.py` | `learning/services.py`, `learning/comparison.py`, `learning/explanation.py`, `analysis/reporting.py`, `analysis/orchestration.py`, `projects/static/projects/workspace/prediction.js`, `results.js`, `report.js` | `tests/application/test_node_joint_learning.py`, existing prediction/comparison/explanation/report tests |
| Product routes and final acceptance | `projects/migrations/0004_new_projects_default_v2.py`, `tests/browser/test_node_joint_journey.py`, `tests/application/test_node_joint_rollout.py` | `projects/models.py`, `projects/management/commands/seed_demo.py`, v1 test factories/fixtures that directly create `Project` | all domain, endpoint, browser and mechanics regression |

Keep existing large files focused: extract pure spatial candidate/validation logic into `modeling/topology.py` and browser candidate discovery into `joint-candidates.js`; do not restructure unrelated workflows. The `*_v2.py` modules isolate version-specific logic; their public callers dispatch by schema.

Connection retirement is staged: Tasks 1–3 retain v1 editable services/tables while eligible Projects await conversion; Task 4 removes Connection from **v2** editing and presents blocked v1 Projects only in labeled read-only recovery; Task 5 retains historical v1 readers. A future, separately approved cleanup may retire v1 editable code/tables only after every Project is resolved and rollback retention expires. Dropping those tables is not an acceptance condition here.

## Review Focus

1. A member with a missing endpoint cannot be geometry-checked; it remains a savable incomplete Draft and reports the missing endpoint, not a false pass-through error. Test in Phase 1.
2. A long member crossing many Nodes must not trigger an all-Nodes × all-Members scan on each pointermove/render; index candidates by sorted X/bounding box, then strict geometry-check only candidates. Test correctness in Phase 1 and per-frame DOM/performance in Phases 4/6.
3. Two legacy DOFs at identical coordinates, including a nonparticipating member-through-Node pair, must remain separate after migration and be visibly marked; no new v2 edit may extend the exemption. Test in Phases 1/3/4.
4. A stale v1 browser must not restore Connection rows after a Project switches to v2; fail with a schema/version error without changing draft_version or history. Test in Phases 1/3/6.
5. A historical v1 AnalysisRun with a changed current Draft must still render its original report/comparison/explanation from its own Snapshot and Prediction versions. Test in Phase 5.

---

### Task 1: V2 domain and editable-Draft contract

**Files:** Create `modeling/topology.py`, `modeling/serialization.py`, `modeling/migrations/0004_node_joint_v2_schema.py`, `projects/migrations/0003_project_draft_schema_version.py`, `tests/application/test_node_joint_draft.py`; modify `modeling/models.py`, `modeling/services.py`, `modeling/completeness.py`, `projects/models.py`, `projects/views.py`, `projects/workspace.py`; extend `tests/endpoints/test_workspace.py` and existing draft tests. Migration files are **schema-only**: add `Project.draft_schema_version` default `physical-draft-v1`, `MemberJointIncidence`, nullable `Support.target_node`/`NodeLoad.target_node`, and `DraftMigrationAudit`; retain v1 columns/tables and do not convert rows. The final new-Project default changes only in Task 6.

**Interfaces:** `MemberJointIncidence(project, member, node)` has project `related_name="member_joint_incidences"`, `node` FK to `GeometryNode`, and unique `(member,node)`. `modeling.topology.find_unrepresented_passes(*, nodes: dict[str, tuple[float,float]], members: list[dict], incidences: set[tuple[str,str]], exemptions: set[tuple[str,str]]) -> list[tuple[str,str]]` returns sorted `(member_key,node_key)`; its caller includes in `exemptions` only audit pairs whose stored geometry still matches. `modeling.topology.ordered_member_nodes(member: dict, nodes: dict, incidences: set[tuple[str,str]]) -> list[str]` validates the strict v1 cross/t tolerances and returns endpoint/intermediate Node keys in geometric order. `modeling.serialization.serialize_draft_v2(project) -> dict` returns the specified `physical-draft-v2` arrays. `modeling.services.save_physical_draft_v2(*, actor, project, payload) -> dict` uses the existing project lock and version; `save_physical_draft` dispatches on *Project schema plus payload schema*, not payload alone. `DraftMigrationAudit` stores project, source version/hash/payload, old→new mapping, exact legacy exemptions and conversion/blocked reason; exemptions are never accepted from client JSON.

- [ ] **Step 1 — RED tests:** Add `test_v2_round_trip_and_direct_node_targets`, `test_v2_save_rejects_member_through_node_without_incidence`, `test_v2_missing_endpoint_remains_savable`, `test_v2_delete_node_preserves_dependents`, `test_v2_rejects_new_same_coordinate_identity_but_keeps_audited_legacy_pair`, `test_v1_payload_cannot_write_v2_project`, and `test_topology_candidate_filter_matches_bruteforce_on_small_models`. Assert exact v2 collection names, nullable targets, unique incidence, missing-reference codes, `MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE`, unchanged draft_version on rejection, and v1 round-trip still works.

  ```python
  with pytest.raises(DraftSaveError, match="MEMBER_PASSES_THROUGH_NODE_WITHOUT_INCIDENCE"):
      save_physical_draft(actor=owner, project=v2_project, payload=through_node_without_incidence)
  v2_project.refresh_from_db()
  assert v2_project.draft_version == 0
  ```
- [ ] **Step 2 — RED command:** `pytest tests/application/test_node_joint_draft.py tests/endpoints/test_workspace.py -q`; new v2 tests fail for missing schema/model/service, existing v1 tests remain green.
- [ ] **Step 3 — Minimal implementation:** Add schema-only migrations and v2 service/serializer. Use a sorted-X Node index with binary-search over each member's X bounding interval, Y bounding rejection, then the strict geometry predicate; run once per save/check, not on pointermove/render. Reject an unrepresented normal pass; waive only exact audited legacy `(member,node,geometry)` pairs. Keep nullable-reference editing permissive, but reject malformed non-null refs. Add endpoint/target project-owner checks and route `physical-draft-v1` only to unmigrated Projects. Give a new v2 Project no audit/exemptions.
- [ ] **Step 4 — GREEN/review:** `pytest tests/application/test_node_joint_draft.py tests/application/test_physical_draft.py tests/application/test_draft_independence.py tests/endpoints/test_workspace.py -q`; `python3 manage.py makemigrations --check --dry-run`; `git diff --check`. Review schema-only migration SQL/state and confirm Connection remains writable only for v1 Projects. Address failures before moving on.
- [ ] **Step 5 — Commit:** Stage only Task 1 files listed above; run `git commit -m "feat: add versioned node-joint draft contract"`.

### Task 2: Snapshot-v2, Idealizer-v2, and unchanged Solver boundary

**Files:** Create `idealization/truss2d_v2.py`, `tests/idealization/test_node_joint_v2.py`, `tests/application/test_node_joint_analysis.py`; modify `modeling/snapshot.py`, `idealization/truss2d.py`, `analysis/orchestration.py`; extend `tests/contracts/test_idealization_boundary.py` and `tests/application/test_analysis_acceptance.py`.

**Interfaces:** `modeling.snapshot.build_physical_snapshot(project) -> dict` dispatches by Project Draft schema; v2 emits `physical-snapshot-v2` with sorted explicit `{member_id,node_id}` incidences, frozen Material/Section values, direct Node targets. `idealization.truss2d.idealize(snapshot: dict) -> IdealizationResult` dispatches by **snapshot.schema_version**; `idealization.truss2d_v2.idealize_v2(snapshot: dict) -> IdealizationResult` produces the existing `TrussModel('truss2d-input-v1', ...)` and provenance (`node:<key>`, PhysicalMember→segments). `analysis.orchestration` validates v2 Draft before revision/run creation and maps v2 mechanics issues to Node/member; v1 path remains untouched.

- [ ] **Step 1 — RED tests:** Add `test_crossing_without_node_has_no_shared_dof`, `test_endpoint_joint_and_three_member_interior_joint_are_explicit`, `test_one_physical_member_splits_without_identity_loss`, `test_direct_node_support_load_and_units`, `test_v2_idealizer_does_not_infer_from_overlapping_coordinates`, `test_snapshot_rejects_inconsistent_v2_draft`, and `test_v1_snapshot_still_idealizes_identically`. Assert analysis node/segment graph, no inferred segment at unlisted Node, `truss2d-input-v1`, unchanged solver version, and stable frozen numeric properties.

  ```python
  result = idealize(snapshot_with_one_explicit_middle_node)
  assert [m.id for m in result.model.members] == ["m:1", "m:2"]
  assert result.physical_member_to_analysis["m"] == ["m:1", "m:2"]
  assert result.model.schema_version == "truss2d-input-v1"
  ```
- [ ] **Step 2 — RED command:** `pytest tests/idealization/test_node_joint_v2.py tests/application/test_node_joint_analysis.py -q`; fail because v2 snapshot/Idealizer dispatch does not exist.
- [ ] **Step 3 — Minimal implementation:** Add a v2-only Idealizer that consumes `ordered_member_nodes`/explicit incidences, never discovers new ones; keep v1 implementation callable for old snapshots. Snapshot requires Model Check/pass-through validation first, freezes only explicit graph, and never repairs. Update analyze/check dispatch and exact issue mapping without changing anything under `mechanics/` or the solver input schema.
- [ ] **Step 4 — GREEN/review:** `pytest tests/idealization tests/application/test_node_joint_analysis.py tests/application/test_analysis_acceptance.py tests/contracts/test_idealization_boundary.py tests/mechanics -q`; `git diff --check`. Inspect solver input/result diffs and confirm v1 immutable fixture hashes and v2 provenance are correct.
- [ ] **Step 5 — Commit:** Stage only Task 2 files listed above; run `git commit -m "feat: idealize explicit node-joint snapshots"`.

### Task 3: Audited per-Project migration and numerical-equivalence gate

**Files:** Create `modeling/node_joint_migration.py`, `tests/application/test_node_joint_migration.py`; modify `projects/services.py`, `projects/workspace.py`, `modeling/models.py` only if the Phase 1 audit fields need a schema-only follow-up migration; extend `tests/application/test_draft_independence_migration.py`, `tests/application/test_analysis_acceptance.py`. Do **not** put data conversion inside a Django `migration.py`.

**Interfaces:** `build_migration_proposal(project) -> MigrationProposal` is read-only and partitions old analysis DOFs into deterministic Node identity classes, incidence pairs, target mapping, and exact legacy nonparticipating-pass exemptions; its fields are `source_hash: str`, `source_version: int`, `draft_v2: dict`, `node_mapping: dict[str,str]`, and `exceptions: set[tuple[str,str]]`. `compare_legacy_v2(*, v1_snapshot, v2_snapshot, mapping) -> EquivalenceReport` returns `equivalent: bool` and `discrepancies: tuple[str,...]` after normalized graph/numeric comparison with `1e-8` absolute/relative tolerance. `convert_project(*, project_id, expected_draft_version, actor) -> DraftMigrationAudit` locks Project, rechecks source hash/version, audits attempt, runs equivalence, atomically replaces current editable rows and flips schema only on success; mismatch/ambiguity blocks Project and retains v1 rows. `restore_v1_from_audit(*, project_id, expected_draft_version, actor)` refuses if post-conversion v2 edits exist, retaining the newer Draft for explicit owner disposition.

- [ ] **Step 1 — RED tests:** Add `test_complete_v1_conversion_preserves_normalized_graph_and_numbers`, `test_legacy_free_endpoints_same_coordinate_remain_distinct`, `test_legacy_nonparticipating_pass_is_audited_not_connected`, `test_ambiguous_null_participant_blocks_only_its_project`, `test_stale_v1_tab_cannot_overwrite_converted_project`, `test_equivalence_mismatch_rolls_back_conversion`, `test_fresh_database_schema_then_v1_convert_then_v2`, `test_rollback_refuses_after_v2_edits`, and `test_purge_counts_new_incidence_and_audit`. Assert unchanged history hashes/rows, exact source payload/audit mapping, blocked reason, deterministic retry, one draft-version increment, and zero partial rows on failure.

  ```python
  proposal = build_migration_proposal(legacy_project)
  report = compare_legacy_v2(v1_snapshot=old_snapshot, v2_snapshot=proposal_snapshot, mapping=proposal.node_mapping)
  assert report.equivalent is True
  assert report.discrepancies == ()
  ```
- [ ] **Step 2 — RED command:** `pytest tests/application/test_node_joint_migration.py -q`; fail for absent proposal/conversion/equivalence services.
- [ ] **Step 3 — Minimal implementation:** Separate schema creation (Task 1), read-only preflight, per-Project conversion, equivalence, schema switch, and future legacy cleanup. Lock the Project as save/analyze do; compare current hash/version inside the lock. Preserve every old `free:<member>:START/END` DOF, including equal-coordinate duplicates; preserve old Connection DOFs and attach only their explicit participants. Audit each exempt legacy pass-through identity/geometry and visually mark it later. Ambiguous incomplete Connection or any topology/numeric mismatch records a block without deleting meaningful data. Add the bounded rollback/export seam and update purge dependency order; leave Connection tables and v1 readers in place.
- [ ] **Step 4 — GREEN/review:** `pytest tests/application/test_node_joint_migration.py tests/application/test_draft_independence_migration.py tests/application/test_analysis_acceptance.py -q`; run the new fresh test-DB old-v1→convert→v2 and brand-new v2 fixtures; `git diff --check`. Review audits, lock ordering, rollback/blocked behavior and no production DB mutation.
- [ ] **Step 5 — Commit:** Stage only Task 3 files listed above; run `git commit -m "feat: gate legacy node-joint migration on equivalence"`.

### Task 4: Workspace/CAD Node-as-Joint editing and Structural Sketch

**Files:** Create `projects/static/projects/workspace/joint-candidates.js`, `tests/browser/test_node_joint_workspace.py`; modify `projects/static/projects/workspace/editor.js`, `modeling-interaction.js`, `state.js`, `renderer.js`, `structural-symbols.js`, `canvas-interaction.js`, `properties.js`, `incomplete-objects.js`, `labels.js`, `workflow.js`, `workspace.css`, `templates/projects/workspace.html`, and `projects/workspace.py`; retain legacy recovery view. Targeted extraction only; keep Grid/Snap/ORTHO authority unchanged.

**Interfaces:** `joint-candidates.js` exports `candidateMembersAtNode(draft, point) -> string[]` and `nodesOnMember(draft, start, end) -> string[]`, using cached spatial discovery plus the same strict geometry predicate; neither mutates topology or runs per pointermove over all node/member pairs. `editor.js` actions `PLACE_JOINT_NODE`, `CREATE_MEMBER_WITH_ENDPOINT`, `CREATE_SUPPORT_AT_NODE`, `CREATE_NODE_LOAD_AT_NODE`, `UPDATE_OBJECT`, and `DELETE_OBJECTS` produce v2 endpoint/incidence/target changes atomically. Renderer reads state only; v2 `selectedObject` kinds exclude CONNECTION. Legacy recovery is explicitly read-only with identity warnings.

- [ ] **Step 1 — RED tests:** In `test_node_joint_workspace.py`, add real-pointer cases `test_crossing_without_node_does_not_connect`, `test_click_node_at_two_member_crossing_authors_both_incidences`, `test_three_member_crossing_authors_all_incidences`, `test_new_member_through_existing_node_authors_incidence`, `test_node_on_single_member_authors_incidence`, `test_support_and_load_target_node`, `test_invalid_node_move_rejects_without_detach`, `test_delete_undo_redo_and_reload_preserve_independent_objects`, `test_legacy_duplicate_and_unjoined_pass_show_chooser_warning`, and `test_pointermove_does_not_rebuild_grid_or_scan_all_pairs`. Assert Draft JSON after save/reload, selection behavior, no Connection tool/ring/Properties, and truthful Canvas symbols.

  ```python
  assert page.locator('[data-object-kind="Connection"]').count() == 0
  assert {(row.member.client_key, row.node.client_key) for row in migrated_project.member_joint_incidences.all()} == {("m1", "n_cross"), ("m2", "n_cross")}
  ```
- [ ] **Step 2 — RED command:** `pytest tests/browser/test_node_joint_workspace.py -q`; fail on old editor/renderer and absent v2 UI.
- [ ] **Step 3 — Minimal implementation:** Route converted/new v2 Projects to new actions and direct Node targeting, retaining read-only v1 recovery. At a confirmed Node placement, attach **all** strict passing members; at new Member commit, attach every existing normal Node it passes; preview list/count and confirmation precede the atomic action. Reject moves that break or create unrepresented passes. Remove v2 Connection ring, selectable layer, inventory category and student terminology; keep hollow Node, member, support, load glyphs and decorative `pointer-events: none`. Use one pure candidate seam with cache invalidated on Draft edit, not visual LOD/pointermove; do not create a second topology authority. Keep Delete/Backspace, marquee, Shift, Undo/Redo, incomplete inventory, numerical coordinates, pan/zoom/fit and 1 mm Grid/Snap contracts.
- [ ] **Step 4 — GREEN/review:** `pytest tests/browser/test_node_joint_workspace.py tests/browser/test_workspace.py tests/browser/test_incomplete_draft_ux.py tests/browser/test_ux_v2_student_journey.py -q`; update active-student v1 interaction cases to v2 equivalents and keep separate v1 historical/recovery assertions, rather than deleting either coverage. `git diff --check`. Inspect real browser screenshots at normal/close/far zoom and review the mismatch between visual Node and persisted incidence; reject any hidden inferred topology.
- [ ] **Step 5 — Commit:** Stage only Task 4 files listed above; run `git commit -m "feat: make workspace nodes the only visible joints"`.

### Task 5: Prediction-v2 and historical result/report compatibility

**Files:** Create `learning/prediction_v2.py`, `tests/application/test_node_joint_learning.py`; modify `learning/services.py`, `learning/comparison.py`, `learning/explanation.py`, `analysis/reporting.py`, `analysis/orchestration.py`, `projects/static/projects/workspace/prediction.js`, `results.js`, `report.js`; extend `tests/application/test_prediction.py`, `test_comparison.py`, `test_explanation.py`, `test_report_package.py`, `tests/endpoints/test_prediction_json.py`, `test_compare_explanation_json.py`, and `test_report_json.py`.

**Interfaces:** `learning.prediction_v2.validate_prediction_v2(project, payload: dict) -> dict` validates Node refs and alternating adjacent Node–PhysicalMember path using explicit ordered incidence. `learning.services.validate_prediction_payload(project, payload)` dispatches by current Draft schema for new authoring; `learning.comparison.build_comparison(run)` and `learning.explanation.build_explanation(run, ...)` dispatch using `run.model_revision.physical_snapshot_json['schema_version']` plus `run.prediction.prediction_schema_version`. `analysis.reporting.build_report_package(run, ...)` does likewise; historical v1 presentation remains unchanged. `analysis.orchestration` accepts current v2 completed Prediction only for a v2 Draft/version.

- [ ] **Step 1 — RED tests:** Add `test_prediction_v2_references_node_and_adjacent_member_path`, `test_prediction_v2_rejects_geometry_only_path`, `test_v2_comparison_and_result_overlay_use_node_provenance`, `test_v2_report_has_nodes_without_explicit_connection_count`, `test_v1_run_remains_readable_after_current_project_converts_and_changes`, `test_v1_prediction_reflection_reasoning_payloads_are_unchanged`, and `test_mixed_schema_prediction_is_ineligible_for_analysis`. Assert no reader consults current Draft for historical topology and no solver call during report generation.

  ```python
  package = build_report_package(run=v2_run, actor=owner)
  assert package["geometry_connectivity"]["nodes"]
  assert "connections" not in package["geometry_connectivity"]
  assert build_report_package(run=old_v1_run, actor=owner)["geometry_connectivity"]["connections"]
  ```
- [ ] **Step 2 — RED command:** `pytest tests/application/test_node_joint_learning.py tests/application/test_report_package.py -q`; new v2 tests fail, old v1 tests still pass.
- [ ] **Step 3 — Minimal implementation:** Add v2 prediction validation/authored payload; dispatch comparison/explanation/report/result overlay from frozen artifact versions. Keep v1 parsers, provenance and stored payload JSON unchanged. Hide Connection terminology only in v2 product surfaces; old historical report may truthfully say “显式连接”. Preserve existing result disclosure and permission checks.
- [ ] **Step 4 — GREEN/review:** `pytest tests/application/test_node_joint_learning.py tests/application/test_prediction.py tests/application/test_comparison.py tests/application/test_explanation.py tests/application/test_report_package.py tests/endpoints/test_prediction_json.py tests/endpoints/test_compare_explanation_json.py tests/endpoints/test_report_json.py -q`; `git diff --check`. Review a v1 historical run after a v2 current-Draft edit and a new v2 run side by side.
- [ ] **Step 5 — Commit:** Stage only Task 5 files listed above; run `git commit -m "feat: version node-joint learning and report readers"`.

### Task 6: Product rollout, browser acceptance, and full regression

**Files:** Create `projects/migrations/0004_new_projects_default_v2.py`, `tests/browser/test_node_joint_journey.py`, `tests/application/test_node_joint_rollout.py`; modify `projects/models.py` to default new rows to `physical-draft-v2`, `projects/management/commands/seed_demo.py` to create new demo Projects as v2, and direct-ORM legacy fixtures in `tests/application/test_physical_draft.py`, `test_prediction.py`, `tests/browser/test_workspace.py`, `tests/endpoints/test_project_json.py`, and `test_workspace.py` so their retained v1 contract tests explicitly request v1. Current production project creation is `seed_demo.py`; no user-facing Project-create route exists in this codebase. The default switch leaves existing v1 rows unchanged.

**Interfaces:** New Projects start in v2 with an empty v2 Workspace and no Connection rows; existing Projects remain v1 until equivalence-gated conversion. Blocked legacy Projects serve read-only recovery plus audit reason/export; a stale v1 POST is rejected. The owner-review endpoint is **`NODE AS JOINT IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING`**, not automatic product acceptance.

- [ ] **Step 1 — RED tests:** Add fresh new-v2 Project creation, old-v1→preflight→migrate→v2, ambiguous-blocked Project, stale browser, rollback refusal after v2 edits, and a sparse 2,000-Node/1,000-Member pass-through case that executes fewer than 100,000 strict candidate checks (versus 2,000,000 all-pairs checks). Add a real-pointer browser journey: no Connection tool; crossing alone no joint; Node click creates all-member joint; new member through Node connects; Support/Load directly target Node; legacy warning and historical report remain accessible. Assert pointermove does not invoke the full Draft validator or grow Grid DOM with visible millimeters, and save/reload/Model Check/Analyze remain correct.

  ```python
  project = Project.objects.create(event=event, owner_user=owner, name="新桁架")
  assert project.draft_schema_version == "physical-draft-v2"
  response = client.get(reverse("projects:workspace", kwargs={"project_id": project.id}))
  assert _bootstrap(response)["draft"]["schema_version"] == "physical-draft-v2"
  ```
- [ ] **Step 2 — RED command:** `pytest tests/application/test_node_joint_rollout.py tests/browser/test_node_joint_journey.py -q`; fail on new-Project routing or end-to-end gaps.
- [ ] **Step 3 — Minimal implementation:** Alter only the model/default for new Project rows to v2; existing rows retain their explicit v1 marker. Update the seed command and legacy test fixtures, then complete only missing bootstrap/error-routing, blocked recovery and stale-client handling. Do not add new mechanics or silently resolve blocked data. Use a fresh test DB for migration tests; never run conversion against the user's live `db.sqlite3` without a separate future approval/rollout.
- [ ] **Step 4 — GREEN/review:** Run targeted domain/migration/Idealizer/learning/report suites and `pytest tests/browser/test_node_joint_workspace.py tests/browser/test_node_joint_journey.py -q`. Then run `pytest -q -m 'not browser'`, `pytest tests/browser -q`, `python3 manage.py check`, `python3 manage.py makemigrations --check --dry-run`, and `git diff --check`; require zero failures/skips that conceal browser coverage. Re-run unchanged `tests/mechanics` benchmarks, compare solver source diff against base, and inspect actual browser screenshots/real-pointer behavior. Review old-v1, converted-v2, new-v2 and blocked-legacy routes separately.
- [ ] **Step 5 — Commit:** Stage only Task 6 files listed above; run `git commit -m "feat: default new projects to node-joint v2"`. Record verification evidence, migration/blocked counts from **test data**, and screenshots. Stop with **manual Product Owner browser acceptance pending**; no merge/push/deploy/legacy-table drop.

## Execution handoff

The six phases form one dependent architecture path, so an execution worker reads this plan and the approved spec before starting. The worker creates the isolated worktree at the plan commit, runs each RED/GREEN/review/commit sequence in order, and stops on semantic conflict, ambiguous migration, numerical mismatch, or mechanics diff. Product Owner review of this plan and choice of execution method are required before Task 1 begins.
