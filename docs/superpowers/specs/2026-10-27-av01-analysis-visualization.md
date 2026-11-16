# AV-01 — Analysis Visualization Specification

**Status:** APPROVED — Phase 1 Task 1–2 IMPLEMENTED / QA VERIFIED (2026-11-11); later Tasks pending approval.
**Date:** 2026-10-27 (Asia/Shanghai).
**Documentation amendment:** 2026-11-05 (Asia/Shanghai), Owner documentation approval / docs-only update.
**Written Spec approval:** APPROVED.
**TDD Plan approval:** APPROVED.
**Execution method approval:** APPROVED — Native Sequential + Task 9 independent whole-branch review.
**Results Hover Preview Amendment:** APPROVED — documented in §11.1; Task 6 only.
**Implementation approval:** APPROVED — Task 1–2 ONLY (2026-11-10); Tasks 3–10 NOT APPROVED.
**Implementation gate:** Phase 1 Task 1–2 authorized; later implementation pending separate Owner approval.

## Owner Phase 1 authorization — 2026-11-10

This bounded status amendment supersedes older gate/status prose below only; engineering contracts are unchanged. Original approved bytes are preserved in custody commit 59731b0 and AV01_DOCUMENT_CUSTODY.json. Integrated main b5873ecc80996dc0561bba313f7053bf65ad023d has fresh 551 Browser / 816 non-browser +22 skips /131 Mechanics subset GREEN. Owner approved documentation custody/status synchronization and **Task 1–2 ONLY** on feat/av01-phase1-projection; Tasks 3–10 remain NOT APPROVED. Native Sequential and an independent Phase 1 whole-diff review apply; this review does not complete later Task 9 for the full feature.

Teacher Formal Review is DEFERRED until functionality and polish are complete, not PASS and no longer a prerequisite to this authorization. M9 P1-001 formal Owner closure remains PENDING. P2-001 is now explicitly ACCEPTED AS UI POLISH FOLLOW-UP. OA-16 and full M9/CAD Owner Acceptance remain PENDING. Controlled integration before remaining manual acceptance was explicitly approved. No Owner/Teacher PASS or deployment approval is inferred.

W01 file-map addition: projects/workspace.py::_urls() may add visualization_template only. No new router/permissions/domain. Existing selected-Run token/epoch and M9 Results/Reflection remain unchanged in Phase 1; Task 7 frontend visualization lifecycle is not pulled forward. W03 Results keyboard isolation remains future TDD, not verified by Phase 1.

Task 1 is saved-fact characterization (expected GREEN; no manufactured RED). Task 2 new projection/API requires genuine RED→GREEN. Reuse same-SHA controlled-integration full baseline evidence; run fresh relevant baseline/regression tests plus system/migration checks, expanding only on evidence of risk. No unchanged full Browser rerun is required. See AV01_PHASE1_AUTHORIZATION.md for authority, scope and gates.

## 1. Purpose, learning goal and authority

Show saved mechanics facts on the structure: external loads → reactions → deformation → member force evidence. Students should locate and cite facts before opening existing explanation or writing their own Reflection. This is not proof of teaching effectiveness or a replacement for Teacher review.

This document records the Owner's AV-01 scope and approved read-only API/rendering design. The Owner's 2026-11-05 documentation instruction confirms Written Spec approval, TDD Plan approval and the execution method separately, and approves the bounded Results Hover Preview Amendment. These documentation approvals do not authorize implementation, finalize visual calibration values, or change any M9 Gate.

Source of Truth, in existing precedence:

- [MASTER_SPEC](../../specs/MASTER_SPEC.md), especially O-001 and current M7/M8 decisions.
- [Solver contract](../../specs/TRUSS_SOLVER_CONTRACT.md), [architecture](../../specs/ARCHITECTURE_SPEC.md), [ADR register](../../specs/ARCHITECTURE_DECISION_REGISTER.md).
- [Workspace UX](../../specs/STUDENT_LEARNING_WORKSPACE_UX.md), [Comparison](../../specs/COMPARISON_CONTRACT.md), [Explanation](../../specs/EXPLANATION_CONTRACT.md), [Reflection](../../specs/REFLECTION_AND_RATIONALE_ARCHITECTURE.md).
- [Approved M9 decisions](2026-10-21-m9-results-teaching-loop-decisions.md), [M9 review status](../../development/M9_REVIEW_AND_ACCEPTANCE.md).
- Owner's 2026-10-27 AV-01 scope decisions, recorded below. No Master/ADR status is silently changed.

Planning source: `feat/results-teaching-loop-m9@12cb8debc8bb209385330b8a6c8d43594dd517a2`; current main observed at `619dd55fae7307027e449bfd67b99138d38d5d2e`. These are audit references, NOT the future implementation baseline. M9 Teacher verdict and Owner acceptance remain PENDING. Freeze the actual merged, GREEN M9 main during future Task 1.

## 2. Approved scope and decision register

| Decision | Approved rule |
| --- | --- |
| PD-AV-001 | Loads ON, reactions ON, force states ON, deformation OFF. |
| PD-AV-002 | Deformation is opt-in. |
| PD-AV-003 | AUTO only; no manual multiplier or slider. Exact percentages and bounds are visual calibration parameters. |
| PD-AV-004 | Deformation ON always retains a low-weight undeformed ghost and readable scale notice. |
| PD-AV-005 | Reactions are global Rx/Ry components; no resultant/local-axis mode. |
| PD-AV-006 | One reaction vector's components per analysis node; never distribute or duplicate them per support row. |
| PD-AV-007 | Dedicated readonly selected-Run Canvas, using that Run's saved geometry and facts. |
| PD-AV-008 | Results Hover Preview for existing ANALYSIS_NODE/SUPPORT/ANALYSIS_SEGMENT targets only; reuse Task 6 Object Evidence, approximately 400 ms stable-pointer delay as a visual calibration candidate, no new selection type/projection/identity mapping/mechanics. |
| PD-RESULT-001 | Add Structure View to Conclusion; retain names, order and semantics of existing M9 tabs and Reflection. |
| PD-SCOPE-001 | AV-01 visualization only; CAD-UX-02 coordinate/load editing is separate. |

Deliver: selected-Run geometry projection, reactions, straight-segment deformed shape, four layer controls, object → Evidence, existing loads/member-state/maximum-candidate facts and accessible alternatives.

## 3. Out of scope and mechanics invariants

No production changes until all gates in §20. No DB/model/migration, new Solver, idealization changes, CAD editing, Load merge, material/section redesign, new Prediction/Reflection behavior, optimization, true load path or design recommendation.

Mechanics remains 2D linear elastic small-displacement pin-jointed truss: ux/uy, nodal Fx/Fy, axial force only; no bending, shear, rotational DOF, plasticity, geometric nonlinearity or failure progression. Canonical units remain mm / N / MPa / g. Positive x right, positive y up. Tensile axial force positive, compression negative. Display coordinates and widths never enter topology, snapping, lengths, analysis, stress or mass.

O-001 stays **OPEN — MECHANICS REVIEW REQUIRED**. Compression is not buckling danger; successful analysis is not a structural safety verdict. No Euler/risk bands/safety factors/failure load/ultimate/collapse conclusions.

## 4. Existing capabilities and architecture choice

Read-only audit found:

- `AnalysisRun` persists linked Revision, `solver_input_json` and `result_json`.
- `canonical_solver_input()` saves analysis nodes, segment endpoints, supports, loads and segment→PhysicalMember mapping.
- `_result()` saves ux/uy, node reactions, axial forces, stress and mass.
- `analysis_data` exposes results; Report exposes physical snapshot geometry, supports/loads and segment mapping, but not the complete saved analysis-node/segment graph.
- `teaching-view.js` validates selected-Run sources; current editable-Canvas overlay is disabled for historical/dirty Drafts.
- M9 teaching classifications differ from the raw postprocess ZERO classification. Never substitute raw `result.state` for M9 `teaching_state`.

Alternatives considered: (A) overlay the editable Draft Canvas (rejected: historical mismatch/mutation coupling); (B) reconstruct analysis topology in JS (rejected: duplicate idealization/proximity risk); (C) saved-Run numeric projection plus dedicated Results renderer (selected in this approved spec).

No new persisted snapshot or facts. Add an independent GET endpoint so unavailable visualization cannot break the existing data/report/comparison/explanation routes. Reuse coordinate transforms, safe labeling and symbol principles; do not bind the editable Canvas controller to the Results SVG.

## 5. Run authority and provenance

Only this chain is legal:

`requested Project + selected AnalysisRun → linked immutable Revision/Snapshot + saved solver_input_json + saved result_json → projection → selected-Run view`.

- Match Project, Run, Revision and source draft version across projection and existing M9 payloads before joining.
- Read the Run after authorization; never select latest as fallback.
- Historical descriptions come from that Snapshot, not current Draft or catalog.
- No Solver call, database write, new reveal/authoring record, Run/Revision update, backfill or current-Draft idealization in the projection builder/endpoint.
- Deterministic means identical saved Run facts produce identical factual projection, with arrays sorted by immutable transport identity. No current time, current draft version, dirty status, selection epoch or live project name in the factual body.
- Existing M9 disclosure routes keep their existing result-reveal policy; this new endpoint must not bypass broader access policy or create additional disclosure side effects. It returns only the already-authorized mechanics facts, not private learning drafts.
- **SPEC CONFLICT identified and avoided:** a first-disclosure numeric endpoint guarded only by read permission/SUCCESS would violate MASTER_SPEC §28.1 result-reveal integrity. The readonly endpoint therefore requires existing `StudentResultReveal(project, source_draft_version)` evidence for a student owner before returning numeric projection. Missing evidence returns 409 with safe guidance to open the existing result flow, and creates no record. Manager/Developer follow the existing exemption and must not create student reveal evidence. This is a dependency on the established disclosure contract, not a new permission grant or a new reveal-writing path.
- Client starts visualization only after the ordinary existing `analysis_data` request successfully validates the requested Run; that route already records owner reveal before returning results. If data/reveal fails, numeric visualization does not proceed. Later Comparison/Explanation derivation failure may still leave valid numeric visualization available. Direct API access is independently protected by the server's existing-evidence prerequisite, not by client sequencing alone.

## 6. Readonly API / projection contract

### 6.1 Endpoint and interfaces

`GET /projects/<project_id>/analyses/<run_id>/visualization/`

`projects.views.analysis_visualization(request, project_id, run_id)` performs authentication, existing Project read authorization/lifecycle checks, exact Run ownership lookup and SUCCESS check. `analysis.visualization.build_visualization_projection(*, run) -> dict` is pure over the saved JSON/linked Revision; it does not authorize or query current Draft resources.

Use the existing not-found/denied behavior for wrong Project, unauthorized, inactive or PURGED access; do not introduce a new permission exception. Non-SUCCESS returns 422 with safe existing analysis-not-success wording. After these checks, a student owner without the existing same-Project/source-draft reveal evidence receives 409 (`VISUALIZATION_REVEAL_REQUIRED`, transport only), with `请先打开这次分析的结果，再重试结构视图。` No numeric graph or result is returned. Manager/Developer remain exempt exactly as in the existing disclosure service. Network/server failures use existing safe error presentation, without exception text.

A successful HTTP 200 response may contain READY/PARTIAL/UNAVAILABLE projection. Missing historical data is not a failed analysis. Internal reason enums are transport-only and are mapped to fixed safe text locally. Do not expose raw payload via an error's details field. Response headers: `Cache-Control: private, no-store` for this new authenticated endpoint; no permission-sensitive shared cache.

### 6.2 Field structure

The following is a typed structure, not a fabricated sample result. `TransportId` is a nonempty immutable string; ids/hashes/schema travel internally and are never rendered as student copy, accessible names, tooltips or evidence text. Existing integer route IDs likewise are internal.

```text
{
  ok: true,
  visualization: {
    schema_version: "analysis-visualization-v1",
    status: "READY" | "PARTIAL" | "UNAVAILABLE",
    provenance: {
      project_id: integer,
      analysis_run_id: integer,
      model_revision_id: integer,
      source_draft_version: integer,
      physical_snapshot_schema_version: string,
      input_schema_version: string,
      result_schema_version: string,
      model_hash: string,
      input_hash: string,
      readonly: true
    },
    capabilities: {
      geometry: Capability,
      loads: Capability,
      reactions: Capability,
      axial_forces: Capability,
      deformation: Capability
    },
    label_source: {
      nodes: [{ id: TransportId, label: string, x_mm: finite, y_mm: finite }],
      physical_members: [{ id: TransportId, label: string,
        start_node_id: TransportId, end_node_id: TransportId }],
      connections: [{ id: TransportId, geometry_node_id: TransportId }],
      supports: [{ id: TransportId }],
      node_loads: [{ id: TransportId, label: string }],
      analysis_member_mapping: { physicalMemberId: [analysisSegmentId, ...] }
    },
    nodes: [{
      analysis_node_id: TransportId,
      source_ref: { kind: "NODE" | "CONNECTION" | "MEMBER_ENDPOINT",
        identity: TransportId, endpoint: "START" | "END" | null } | null,
      x_mm: finite, y_mm: finite,
      displacement: { ux_mm: finite, uy_mm: finite } | null,
      support_ids: [TransportId, ...],
      load_ids: [TransportId, ...]
    }],
    segments: [{
      analysis_segment_id: TransportId,
      start_analysis_node_id: TransportId,
      end_analysis_node_id: TransportId,
      physical_member_id: TransportId,
      axial_force_N: finite | null
    }],
    supports: [{
      support_id: TransportId, analysis_node_id: TransportId,
      support_type: "PINNED" | "ROLLER",
      restrained_axis: "X" | "Y" | null
    }],
    loads: [{
      load_id: TransportId, analysis_node_id: TransportId,
      fx_N: finite, fy_N: finite
    }],
    reactions: [{
      analysis_node_id: TransportId,
      rx_N: finite, ry_N: finite,
      support_ids: [TransportId, ...]
    }]
  }
}
Capability = { status: "READY" | "UNAVAILABLE", reason: null | ReasonEnum }
```

`connections` is empty for v2. `label_source` is a minimal Snapshot-derived adapter for the existing `labels.js` resolver; the inverted member map format follows that resolver. This is not a second naming authority.

Run sequence/label comes from the existing run list, not persisted IDs. Snapshot identity is established by linked Revision, model hash and schema; no nonexistent standalone snapshot row is invented.

Display facts remain in the existing M9 payload: `selectedTeachingView.members[].segments`, member `actualState`, `comparisonStatus`, maximum displacement and all candidates. They are joined by validated identities; the new API deliberately does not reclassify or duplicate them. Prediction identifiers remain only existing transport data. Node displacement magnitude may be `hypot(ux, uy)` for presentation; maximum and candidate membership must come from existing M9 authority.

### 6.3 Identity validation without topology inference

- Saved `solver_input_json.nodes` and `.members` are the analysis geometry authority. Require finite non-boolean coordinates, unique ids, existing distinct segment endpoints and nonzero finite segment length.
- Require every saved segment's physical mapping to agree with its saved result mapping and a real Snapshot PhysicalMember when that layer is used. No invented identities or coordinate lookup.
- v2 node provenance: match each exact `node:<snapshot-node-id>` generated from Snapshot identities against the saved node id. Validate its saved coordinates agree with that source; coordinate equality validates a known reference, never chooses one.
- v1 provenance: enumerate exact `connection:<snapshot-connection-id>` and `free:<physical-member-id>:START/END` from explicit Snapshot references. Do not split arbitrary ids on `:` or infer a connection from colocation. Each saved id must have one supported explicit provenance. Ambiguous/unknown historical formats are unavailable.
- Support and Load source refs map through the same identity table. Preserve every original Load row. Compare the saved input relation/multiset with Snapshot-derived identity relations; duplicate support constraints are checked as the union of explicit restrictions, not as a guessed force split.
- Displacement ids must be unique and match the entire saved analysis-node set for deformation. Reject missing/extra/duplicate/nonfinite entries for that layer. Do not insert zero.
- Reaction entries must be unique per analysis node and correspond to saved support nodes; missing/extra/nonfinite entries disable the reaction layer. Never aggregate duplicate reaction result rows as a repair.
- Axial results must match the saved segment set and physical mapping. Do not classify force signs again in projection or JS.
- Emit only finite JSON numbers, no NaN/Infinity or raw malformed values. A malformed shared graph makes the full projection UNAVAILABLE; malformed optional data disables only its dependent layer. No partially drawn complete-looking deformation.

## 7. Availability and composite display facts

Geometry unavailable → empty geometry/selection arrays, all capabilities unavailable, no Results SVG with substitute Draft. Keep legal M9 results/tables outside this feature.

Valid graph with missing displacements → original geometry/loads/reactions can remain usable; deformation unavailable. Missing reaction facts → reaction layer unavailable, independent layers retained. Invalid Snapshot identity relation → dependent glyphs/labels unavailable rather than generic mislabeled geometry. Missing optional descriptions is valid; unresolved identity is not a description omission.

Projection `status`: READY if all five API capabilities ready; PARTIAL if geometry ready but at least one other capability unavailable; UNAVAILABLE if shared graph/provenance invalid. Empty loads is a valid READY empty layer. A complete valid all-zero displacement array is READY.

Client `buildAnalysisVisualizationView({projection, teachingView=null, expectedContext})` validates against a separate trusted selection anchor, NOT fields on an unavailable teaching view. `expectedContext` contains `{projectId, runId, revisionId, sourceDraftVersion, modelHash, inputHash, inputSchemaVersion, resultSchemaVersion}`. Project is the scoped Workspace bootstrap; Run/Revision/version agree between discovered Run metadata and the successful existing `analysis_data` response; hashes/schema come from that exact data response. All corresponding projection provenance must match. No anchor is created after a failed data/reveal request. Existing M9 teaching payloads, when available, must also agree with the anchor before joining.

Valid data/reveal + missing/invalid Comparison/Explanation teaching projection does not globally disable numeric geometry/reaction/load layers. Force-state encoding or maximum highlighting/deformation can independently be unavailable. It never recomputes missing M9 classifications/candidates. This distinction must not be hidden behind a single `teachingView.available` gate; it does not permit bypassing failed initial result disclosure.

## 8. Reaction rendering and numeric formatting

Direction is global sign: +Rx right, -Rx left, +Ry up, -Ry down. Label uses signed value (`Rx = -84 N`) and Inspector includes direction words. One Rx/Ry pair per analysis node regardless of support-row count. Related support records are selectable/listed but carry no invented individual reaction.

Use screen-sized arrows, independent of model mm and zoom; show an anchor marker/leader to the undeformed saved node. Reaction arrows point away from that anchor in the sign direction; force-on-node loads may keep their existing arrowhead-at-anchor convention. Separate arrow styling/legend distinguishes external load and reaction, never reverses force-state colors. Support/load/reaction anchors stay on undeformed geometry even with deformation ON; displaced nodes are visualization, not newly applied forces.

Common Run policy: `Rref = max(abs(rx), abs(ry))` over complete valid reactions, display-only. For each nonzero component `lengthPx = clamp(maxPx * abs(component)/Rref, minPx, maxPx)`. This does not recompute reaction. If all are exactly zero, draw no directional arrows. Candidate min/max: 20/64 CSS px; tune only under §12. Legend: `箭头长度经过显示缩放，请以标示数值为准。`

Numeric formatting for new evidence/labels:

1. Keep raw finite doubles untouched. Exact 0 (including signed -0) displays `0` with no arrow.
2. Default compact labels use up to six significant digits. Nonzero `abs(v)<0.001` or `abs(v)>=1e6` uses scientific notation. If formatting would show zero, use scientific notation instead.
3. Inspector's expanded exact-value text uses a round-trip number representation, with units and sign. Compact text is marked as display precision, never replaces stored precision.
4. NaN/missing is `暂不可用`, never `0`. No reaction near-zero threshold or new physical classification.

Labels use deterministic screen-space candidates, then leaders/stacked label rail. Never silently drop a fact when text cannot fit: provide an explicit `部分标注请在证据面板查看` indicator and the keyboard object list. Pan/zoom/reflow may change label position only. All reaction glyph children are decorative; a node-level hit/list target selects evidence without creating topology.

## 9. Deformation rendering

Per saved analysis node: `p_display = p_saved + alpha * (ux, uy)`. Draw every saved analysis segment as one straight line between its displaced analysis endpoints. A PhysicalMember with intermediate joints becomes multiple straight pieces, never one endpoint shortcut or Bezier/spline/bending curve.

With deformation OFF show undeformed structure. With it ON show low-weight neutral undeformed ghost and primary displaced segments; existing segment force-state style applies to the primary shape if that layer is ON. Preserve intermediate-node markers. Ghost is labeled original structure, not a second model; decorative ghost is not a second selectable copy.

Maximum-candidate markers use all supplied M9 candidates, on the primary node position (original when OFF, displaced when ON), with an original-anchor connector on selection if needed. Evidence always reports original coordinates and actual ux/uy, never displayed coordinates as true geometry. Candidate absence is not a new maximum calculation.

## 10. AUTO scale, viewport and special cases

`D = hypot(saved bbox width, saved bbox height)` over analysis nodes; `Umax` comes from the existing selected-Run authoritative maximum-displacement fact, not JS max. Both must be finite and D>0. Require complete finite displacement data and matching M9 maximum provenance; contradictory zero maximum/nonzero components makes deformation unavailable.

Starting calibration: target fraction 0.05, minimum amplification 1, maximum 10000. For Umax>0: `alpha = clamp(targetFraction * D / Umax, minAlpha, maxAlpha)`. Avoid overflow through bounded ratio evaluation; if a finite meaningful scale/display geometry cannot be produced, mark unavailable, never emit infinite SVG coordinates.

- Umax=0 with all components exactly zero: alpha=1; shapes coincide; `本次节点位移均为 0 mm。` Keep all legitimate zero-tie candidates.
- Tiny nonzero: cap alpha; if maximum projected offset remains under 1 CSS px, say `变形已达到显示放大上限，仍不易辨认；请查看实际位移数值。` Do not label it zero. The 1 px readability trigger is calibration, not mechanics.
- Candidate automatic alpha<1: use 1. No downscaling to hide large displacement and no safety inference.
- Missing ux/uy, unsupported graph or invalid display math: deformation unavailable, not zero-filled.
- While ON always show `变形显示已放大 {alpha}×；数值仍为实际分析位移。`; alpha=1 uses `变形显示倍率 ×1。` Formatting must not round >1 to 1; expose exact scale on expansion.

Scale depends on Run facts/calibration, not pointermove or ordinary zoom/pan. Fit uses union of original/display geometry with screen-symbol padding. Toggle does not automatically move the viewport; explicit Fit updates it. Initial per-Run Fit occurs when that Results Canvas has usable dimensions. Editable Workspace Fit, grid and view transform are untouched.

## 11. Layer controls, selection and accessible alternatives

Four native keyboard-operable checkbox controls: `外部荷载` ON, `支座反力` ON, `拉压状态` ON, `变形图 AUTO` OFF. Ghost has no off switch. Unavailable controls are disabled with readable reasons. No stress heatmap, reaction resultant, animation, failure or editing controls.

Approved transient view policy: reset defaults, selection and Fit on every explicit Run selection and reload; no localStorage/DB persistence. The same Run selected again is a fresh selection epoch. Toggling layers/pan/zoom/Fit never creates Undo entries, dirty state, Save or server mutations.

Dedicated selection types: ANALYSIS_NODE, SUPPORT, ANALYSIS_SEGMENT. A reaction hit target selects its analysis node and related support group; clicking a specific support/list row selects that record but still shows the node's aggregate reaction. A segment includes its mapped member and all sibling segment evidence, especially MIXED. Keyboard object list supports equivalent selection. No editable node grips, drawing, delete or keyboard Draft shortcuts.

Evidence:

- Node: Snapshot x/y, saved ux/uy, presentation displacement magnitude, supplied maximum-candidate status (or unavailable), original Load rows, support relations.
- Support: historical safe support/node names, type/restriction, node's Rx/Ry once and all related supports; no force sharing.
- Segment: safe analysis-segment label via `labels.js`, mapped member, saved axial force, existing M9 teaching state, complete member segment list and optional existing comparison status. No Prediction is a legal state.

`labels.js` stays the single student naming authority; use Snapshot `label_source`. No raw ids, schema, hashes, internal refs or machine codes in any visual/accessible level, including professional values. Description is not identity. Use textContent, not raw HTML, for labels. Preserve existing tension red solid/compression blue dashed/near-zero gray/MIXED meaning with non-color line/label/legend alternatives. Never paint every MIXED segment a single tension/compression color.

Native layer controls, object list, factual table alternatives, visible focus and readable scale announcements are required. Arrows alone are insufficient. Keep all existing M9 tabs and Reflection positions/order. Add Results SVG/Evidence within Conclusion; hidden Conclusion does not hijack focus from other tabs.

Scope SVG defs/resource ids to the Results instance so the editable Workspace's markers/patterns cannot collide. Reusing a symbol function is allowed only without importing its editable hit behavior or duplicate global ids. Historical selection must never trigger current Draft selection, deletion or grips.

### 11.1 AV-01 — Results Hover Preview Amendment

Owner documentation approval, 2026-11-05: Hover Preview is a transient preview of Task 6 Object Evidence for existing selectable ANALYSIS_NODE, SUPPORT and ANALYSIS_SEGMENT targets only. Reuse the same validated selected-AnalysisRun Evidence projection, identity references, availability, safe labels and §8 number formatting. No second historical dataset, projection, identity mapping, Results selection state machine or mechanics authority is introduced. Hover never changes selected object state, Inspector content or Draft state, and makes no data request or write.

After the pointer remains stable over the same eligible target for approximately 400 ms, show the safe object name and 2–4 principal engineering information items, with engineering symbols and units. The delay is a visual calibration candidate, not a mechanics constant or a final calibrated value. Example field priorities drawn from existing Evidence: Node original X/Y and actual ux/uy; Support related node/type/restriction and that node's aggregate Rx/Ry; Segment mapped member, saved segment axial force and existing teaching state. Full relations, sibling segments and exact-value detail remain in the existing Evidence Inspector on selection; keyboard/touch use the existing Task 6 equivalent entries. All student-visible copy is Simplified Chinese.

Use Engineering Inspector Tooltip styling: low decoration, thin border, small corner radius, readable compact rows; position within the visible Canvas and away from the target/main operation area. It contains no buttons, editor fields or new interactive state. The complete Tooltip subtree has `pointer-events: none`; it never captures pointer, takes focus or adds a hit target. Clicking still selects through the existing Results path and opens complete Evidence. No native title may act as an independent competing factual preview.

Presentation lifecycle only (not another Results selection state machine):

| State | Rule |
| --- | --- |
| Hover pending | Hold only the existing target reference, screen anchor and pending timer under the current Run/epoch. Pointer movement restarts the stable-pointer delay; it must not rebuild Evidence or redraw the full Canvas. Revalidate target and Run/epoch before display. |
| Visible | Render the 2–4-item preview from the same Evidence. It does not alter selection, layers, focus or complete Inspector content. |
| Cancelled | Cancel timer and remove preview/anchor when pointer leaves, target changes, pointerdown, pan, wheel zoom, Fit, Canvas hidden or Results tab leaves. A fresh stable hover is required after the operation. Also clean up on pointercancel, target removal or component destroy. |
| Dismissed | Escape closes the preview and clears timer/anchor; do not immediately reopen on the same target until pointer leaves and re-enters. Do not change or consume existing CAD/Results command-cancellation semantics. |

Run/epoch change, including A→B→A or selecting the same Run again, synchronously clears Tooltip, anchor and pending timer. Old callbacks cannot render under the new epoch. Reuse the existing component lifecycle and Task 7 selection ownership; do not create a parallel Run/selection controller. Do not rebuild the entire Evidence projection or redraw the full Canvas on pointermove.

Safe data rules are unchanged: every value is from the same validated selected AnalysisRun; never fill history from current Draft/catalog, recalculate mechanics or reclassify MIXED/ZERO_FORCE. Support Preview describes the node's aggregate reaction, never support-specific force sharing; Segment Preview reports that segment, never an average or a fabricated whole-member force. Missing/invalid values display `暂不可用`, never zero; an unset description may display `未设置`. Exact saved zero remains zero under §8. Unresolved identity/provenance does not create a fallback target. Raw IDs, hashes and client keys are forbidden in visible or accessible Tooltip copy.

## 12. Fixed rules versus calibration

Fixed: provenance, units, sign, no false zero, aggregate node reaction, all analysis segments, exact saved facts, minimum alpha=1/no downscaling, bounded AUTO, ghost/notice, independent controls and no mutation.

Calibration parameters in one `analysis-visualization.js::VISUAL_CALIBRATION` export: reaction min/max 20/64 px, deformation target 0.05, max alpha 10000, label offsets (starting 12 px with 4 px rail gap), tiny-visible trigger 1 px. These are starting values, not domain/mechanics constants. Min alpha is explicitly recorded alongside them but must remain 1 under the approved no-downscaling rule; changing that rule requires Owner approval.

Results Hover Preview stable-pointer delay: approximately 400 ms, recorded in the same calibration export. It is a visual calibration candidate; changes require the same visual evidence process, not a change to engineering data or classification.

Tune only after 1024×768, 1280×800, 1440×900 real browser inspection. Record parameter, before/after screenshots, viewport/case, reason (overlap/readability/hierarchy), affected assertions and proof raw facts did not change. No undocumented magic numbers or "looks better" alone. Final accepted constants freeze in the acceptance record, not Solver contract.

## 13. Historical, permissions and race rules

Owner, assigned Manager, Developer and FINISHED_GRACE view only as existing read permission allows. Readonly status must not hide visualization. No private DRAFT Reflection/Reasoning added to projection. PURGED/stale ACTIVE after purge deadline/inactive authority follow existing fail-closed policy; do not create new lifecycle rules.

Use M9 selection token plus exact requested Run. Clear old Canvas/Evidence synchronously on selection, load visualization independently of required M9 payloads, and discard late success/error for old epochs, including A→B→A. A network error must not remove otherwise valid selected-Run text results. No old scale/selection/labels may remain under the new Run heading. An authoritative access denial clears the selected Run's protected result surfaces; do not continue showing an already-rendered visualization after that denial. Network failures are distinguished from access denial.

## 14. Error / fallback copy

| State | Safe student behavior |
| --- | --- |
| Loading | `正在载入所选分析的结构视图…` clear old view |
| Historical geometry missing | `该历史分析缺少完整的可视化几何记录。仍可查看已有结果。` |
| Partial data | Name unavailable layer; keep independent valid layers and tables |
| Projection invalid | `这次分析的结构视图暂不可用，请查看已有数值资料。` |
| Access revoked | Clear protected view; existing safe authorization notice |
| Network failure | `结构视图暂时无法载入，请重试。` explicit retry same selected Run |

Never raw exception, fake zero, silent latest/current fallback, automatic Analyze/Save or history repair. API reason codes stay internal.

## 15. Wireframes (concept only)

```text
结论 | 预测对比 | 为什么 | 技术数据
第 2 次分析 · 历史模型
[✓外部荷载] [✓支座反力] [✓拉压状态] [□变形图 AUTO]
┌────────── Results Structure View ──────────┬─ 所选分析证据 ─┐
│                 ↓ 外部荷载                 │ 支座 S1 · 节点 N1│
│                 ○                         │ Rx = -84 N  ←   │
│                / \                        │ Ry = 326 N  ↑   │
│               ○───○                       │ 此节点合计反力   │
│               ↑   ↑ 支座反力              │ [相关支座记录]   │
│ 淡灰原形 + 主要变形线（开启时）             │ [完整数值]       │
└───────────────────────────────────────────┴─────────────────┘
变形显示已放大 42×；数值仍为实际分析位移。
[可用键盘选择的节点/支座/分析段列表] [数值表格]
```

At 1024 width the evidence panel may stack below the Canvas; controls wrap without page overflow. No forced three-column layout. Current Draft editing stays in 建模, not in this SVG.

## 16. Acceptance criteria and test ownership

| AC | Requirement | Future RED tests / task |
| --- | --- | --- |
| AV01-01 | Exact Run/Revision/Snapshot saved graph; deterministic/no writes/no Solver; prior reveal required | `test_saved_run_projection_is_deterministic_and_readonly`, `test_projection_never_calls_solver_or_idealize`, `test_student_projection_requires_existing_disclosure` / 2 |
| AV01-02 | Exact identities; v1/v2 supported only with provable refs | `test_v1_v2_explicit_identity_mapping`, `test_bad_graph_or_identity_is_unavailable` / 2 |
| AV01-03 | Wrong project/auth/lifecycle denied | `test_visualization_access_matrix` / 2, 7 |
| AV01-04 | Partial/legacy failure isolated; no zero substitution | `test_missing_layer_does_not_destroy_independent_facts` / 2, 7 |
| AV01-05 | Signed reaction directions and true values | `test_reaction_components_match_saved_sign_and_value` / 3 |
| AV01-06 | Zero/tiny; no rounding nonzero to zero | `test_zero_tiny_and_numeric_formatting`, `test_support_direct_load_uses_saved_reaction` / 3 |
| AV01-07 | Multi-support node not duplicated/distributed | `test_same_node_supports_share_one_reaction_display` / 3 |
| AV01-08 | Deformation uses every saved segment and ux/uy | `test_deformation_uses_saved_segment_endpoints`, `test_intermediate_joint_remains_piecewise_straight` / 4 |
| AV01-09 | Bounded AUTO/zero/invalid/ghost/notice | `test_deformation_scale_cases`, `test_ghost_and_scale_notice_are_always_present_when_on` / 4 |
| AV01-10 | Independent controls/defaults/reset/no mutation | `test_layer_defaults_toggles_and_reset_are_transient` / 5 |
| AV01-11 | Selected object evidence and stable safe names | `test_selected_object_evidence_is_snapshot_bound`, `test_no_internal_identity_in_visible_or_accessible_copy` / 6 |
| AV01-12 | Existing MIXED/ZERO/UNSURE/NOT_COMPARABLE/ties/no Prediction retained | `test_existing_teaching_facts_are_not_reclassified` / 7 |
| AV01-13 | A/B and ABA race; late errors cannot overwrite new selection | `test_projection_late_success_error_and_aba_are_discarded` / 7 |
| AV01-14 | M9 tabs/Reflection unchanged, historical current-Draft isolation | `test_visualization_keeps_m9_navigation_and_reflection_contract` / 7 |
| AV01-15 | Keyboard/list/table equivalent, readonly and no overflow | `test_visualization_keyboard_and_role_matrix` / 6–8 |
| AV01-16 | Real visual matrix and calibration evidence | Task 8 records, Task 10 Owner checklist (never automated Owner PASS) |
| AV01-17 | Access denial clears protected view, optional outage isolated, trusted context independent of teachingView | `test_denial_clears_view_but_network_failure_is_isolated`, `test_numeric_layers_require_data_anchor_not_teaching_availability` / 7 |
| AV01-18 | Results Hover Preview reuses Task 6 Evidence; non-interception, lifecycle/epoch cleanup, safe availability/labels | `test_hover_preview_reuses_object_evidence`, `test_hover_preview_does_not_intercept_canvas_actions`, `test_hover_preview_cancel_and_dismiss`, `test_hover_preview_cannot_survive_run_epoch_change`, `test_hover_preview_uses_safe_availability_and_labels`; extend existing keyboard/touch equivalence / 6 |

Test files and executable commands are in the [TDD plan](../plans/2026-10-27-av01-analysis-visualization.md). Existing mechanics/M9 suites remain unchanged unless a compatible new assertion is explicitly needed; baseline failures are not RED.

## 17. Exact expected file impact

MODIFY (future implementation only):

- `projects/views.py` — guarded visualization GET view.
- `projects/urls.py` — one exact Run-scoped route.
- `projects/static/projects/workspace/run-context.js` — optional visualization lifecycle/epoch, preserve required M9 requests.
- `projects/static/projects/workspace/results.js` — mount/unmount compatible Conclusion view, preserve tab contract.
- `templates/projects/workspace.html` — selected-Run integration callbacks, no CAD changes.
- `projects/static/projects/workspace/workspace.css` — scope import/reference for new visualization CSS.

NEW (future implementation):

- `analysis/visualization.py` — saved numeric graph/provenance validation, no teaching classifier.
- `projects/static/projects/workspace/analysis-visualization.js` — composite view, formatting, calibration, controls/evidence lifecycle.
- `projects/static/projects/workspace/analysis-visualization-renderer.js` — dedicated readonly SVG, labels/collisions/selection, pan/zoom/Fit.
- `projects/static/projects/workspace/analysis-visualization.css` — scoped layout/focus/legend.
- `tests/application/test_analysis_visualization.py`.
- `tests/endpoints/test_analysis_visualization.py`.
- `tests/browser/test_av01_reactions.py`.
- `tests/browser/test_av01_deformation.py`.
- `tests/browser/test_av01_layers_evidence.py`.
- `tests/browser/test_av01_run_integration.py`.
- `tests/browser/test_av01_visual_matrix.py`.
- `docs/development/AV01_IMPLEMENTATION_EVIDENCE.md` and `AV01_REVIEW_AND_ACCEPTANCE.md`.

UNCHANGED: `mechanics/**`, `idealization/**`, every `models.py` and `migrations/**`, `modeling/**`, material/section services, editable renderer/controller/state/CAD modules, `labels.js` naming authority, `teaching-view.js` classifications, `learning/**`, existing Prediction/Comparison/Explanation/Reflection domain contracts. No M7/M8 changes. Reuse these through existing interfaces; necessary expansion triggers a scoped file-map review, and any domain/Solver/migration change triggers STOP.

Planning operation creates only this spec and its linked plan in the existing M9 worktree, uncommitted. It does not amend Master/M9 acceptance status or create the future evidence files.

## 18. Risks, open issues and UI POLISH integration

The initial first-disclosure design conflict with Master §28.1 is explicitly addressed in §5–6 by a readonly existing-evidence prerequisite and normal data-route sequencing; it is not silently merged away. No new reveal writes, exemption or Prediction semantics are introduced. The API shape, this dependency and transient layer reset policy are covered by the approved Written Spec; implementation remains NOT APPROVED. If preserving the existing-evidence prerequisite proves impossible without domain/policy changes, STOP rather than bypass it.

Open calibration: constants in §12 await real visual evidence. Open dependency: final M9 Teacher/Owner decisions, merged baseline and UI POLISH 01 exact file plan. The current feature tree did not contain a separately identifiable UI POLISH plan; do not claim collision-free integration until re-audited. Share styling containers/tokens only: Results Canvas, Evidence Inspector and layer controls belong behaviorally to AV-01; Material/Section polish does not.

Risks: duplicate support semantics, v1 identity ambiguity, large graph/labels, changed hidden-container dimensions, clipping of exaggerated geometry, async data mixing, disclosure side effects and accidental reuse of editable shortcuts. No per-pointermove full graph/projection rebuild. Label layout updates on viewport/selection changes, not data mutation. Any Source-of-Truth conflict must be labeled SPEC CONFLICT, not silently reconciled.

Planning builder check (2026-10-27): one independent read-only reviewer identified (1) first-disclosure bypass and (2) missing trusted provenance when teachingView is unavailable. Both were corrected in §5–7 and the plan's interfaces/Tasks 2/7. Targeted recheck found no remaining contradiction in those two items and confirmed the label adapter shape against `labels.js`. This is a spec buildability check, not Task 9 whole-branch review, Teacher verdict, Owner acceptance, production verification or implementation approval.

## 19. Future handoffs — record only

**CAD-UX-02:** Modeling Node/Member/Support/NodeLoad Hover; NODE active direct absolute `X,Y`; existing XY/parsers/commit reuse; Enter, Esc cancel entry and remain NODE; pointermove protection for the complete input pair; editable/IME isolation; preserve v2 Node-as-Joint identity and topology confirmation; one-row Fx/Fy editor plus multi-row ΣFx/ΣFy summary by target Node identity, not coordinate equality; no automatic row merge. No AV-01 Task 6 scope/code/tests for these behaviors.

**FAILURE / CAPACITY SCREENING:** FUTURE — MECHANICS / PRODUCT DECISION REQUIRED; no implementation. Need tested/estimated/allowable/ultimate strength semantics and reliability, Snapshot persistence, missing-data policy, K/effective length/control axis/I/restraint, physical segmentation, glue/joint limitations, wording and historical authority. Do not repurpose amplification or compression color as a failure verdict.

## 20. Execution gates and stop conditions

All are mandatory: (1) M9 Teacher review handled, (2) M9 Owner acceptance complete, (3) M9 merged to stable main, (4) fresh stable baseline GREEN, (5) this spec approved, (6) TDD plan approved, (7) Owner explicitly says **AV-01 IMPLEMENTATION APPROVED**. Only then create an isolated feature branch/worktree.

Documentation-state synchronization (2026-11-05): gates (5) and (6) are APPROVED, as is Native Sequential + Task 9 independent whole-branch review. This amendment does not close or change M9 gates (1)–(3), does not establish fresh baseline gate (4), and does not grant implementation gate (7), which remains NOT APPROVED. This docs-only update runs no tests, creates no branch/worktree and makes no commit/merge/push/tag/deploy.

STOP for Solver/idealization/domain/migration requirements, unprovable identity, current Draft/catalog fallback, new classification/max/tie semantics, force-sharing invention, failure policy, new permission exception or unresolved Teacher/Owner conflict. No new feature work during gate waiting. Future execution uses Task 1–10 and at least one independent whole-branch review; no automatic merge/push/tag/deploy or Owner PASS.

**AV-01 SPEC + TDD PLAN APPROVED — RESULTS HOVER AMENDMENT DOCUMENTED — IMPLEMENTATION GATE PENDING**


2026-11-11 Phase 1 completion record: Task 1–2 only implemented and independently reviewed. Final code 80ecee9; 983 non-browser passed/22 existing concurrency skips; 128 relevant M9/KB01 Browser passed; 131 Mechanics passed (subset); checks/dry-run/diff clean. Original approved engineering text retained; Task1 gate/baseline checkboxes reflect the explicit limited Owner exception and retained same-base full integration evidence, not a Teacher/Owner PASS. Full later Task9 not completed by the Phase1 review. See docs/development/AV01_PHASE1_IMPLEMENTATION_REPORT.md.
