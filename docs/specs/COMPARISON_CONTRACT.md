# Comparison Contract — M4B

## Status and scope

- Status: **CONFIRMED — M4B Gate 1A contract freeze**
- Parent authority: `MASTER_SPEC.md v1.6`
- Schema: `comparison-v1`
- Scope: deterministic derived comparison facts for a completed Prediction and successful AnalysisRun. Compare Core itself creates no UI, Explain text, Reflection flow (deferred to M4C), ORM model, or persisted Comparison aggregate; its separate M4B GET disclosure boundary is specified below.

## Product boundary

The learning paths remain:

```text
Prediction present: Predict → Analyze → Explain → Compare → Reflect
Prediction absent:          Analyze → Explain → Reflect
```

Prediction remains a Soft Gate. `AnalysisRun.prediction = null` is valid: comparison is unavailable with derived reason `NO_PREDICTION`, not an error, and it does not block Analyze, result access, or future Explain.

Comparison is deterministic derived data:

```text
comparison-v1 = f(Prediction, AnalysisRun, ModelRevision, authoritative result_json)
```

It is recomputed from immutable evidence and is not persisted. Future anonymous research metrics require a separate data-governance decision.

## Input eligibility and lineage

Comparison requires all of the following:

1. `AnalysisRun.status = SUCCESS` with authoritative `truss2d-result-v1` numerical data.
2. A non-null, completed `AnalysisRun.prediction` using `prediction-v1`.
3. `Prediction.project_id == AnalysisRun.project_id`.
4. `Prediction.source_draft_version == AnalysisRun.model_revision.source_draft_version`.

Project mismatch is rejected with `COMPARE_PROJECT_MISMATCH`; source-version mismatch is rejected with `COMPARE_SOURCE_MISMATCH`. Matching `model_hash` or `input_hash` never permits a cross-`source_draft_version` comparison. The revision snapshot, not mutable Project authoring data, is the identity source for deterministic mapping.

## Teaching force classification and PhysicalMember projection

The authoritative `truss2d-result-v1.member_results` records **analysis segments**. A single PhysicalMember can be idealized into more than one analysis segment when it has an explicit intermediate Connection. Compare must not assume `PhysicalMember → one axial force`, and must not choose a single segment (including the maximum-absolute-force segment) as a substitute for the PhysicalMember.

The Compare Core first derives a teaching classification from each authoritative **analysis-segment** axial force `N_i` in N. The reference spans every authoritative analysis segment in the successful result:

```text
N_ref = max_j |N_j|
threshold_N = max(1e-6 N, 0.001 * N_ref)
```

If every segment force is zero, `N_ref = 0` and `threshold_N = 1e-6 N`; no division is used. Classification is evaluated in this order:

```text
abs(N_i) <= threshold_N  → ZERO_FORCE
N_i > threshold_N        → TENSION
N_i < -threshold_N       → COMPRESSION
```

This is M4B’s engineering/teaching policy. It does not alter the M1 numerical residual cleanup `ZERO` rule, `abs(N) <= 1e-9 N`, and it does not change `truss2d-result-v1`; every real segment `axial_force_N` remains available to the professional layer. Student-facing wording for `ZERO_FORCE` is **“近似零力构件”**.

Compare then projects the segment classifications onto each PhysicalMember:

| Segment teaching states for one PhysicalMember | Derived `actual_state` |
| --- | --- |
| all `TENSION` | `TENSION` |
| all `COMPRESSION` | `COMPRESSION` |
| all `ZERO_FORCE` | `ZERO_FORCE` |
| two or more distinct states | `MIXED` |

`MIXED` is a Compare-side derived state only. It is not a Prediction choice and is never persisted. The segment evidence must remain available wherever Compare reports its PhysicalMember projection.

## Member comparison semantics

Each Prediction member judgment is compared with the projected PhysicalMember `actual_state`:

| Predicted state | PhysicalMember `actual_state` | `comparison_status` |
| --- | --- | --- |
| `UNSURE` | any state, including `MIXED` | `UNSURE` |
| `TENSION`, `COMPRESSION`, or `ZERO_FORCE` | `MIXED` | `NOT_COMPARABLE` |
| `TENSION`, `COMPRESSION`, or `ZERO_FORCE` | same non-`MIXED` state | `MATCH` |
| `TENSION`, `COMPRESSION`, or `ZERO_FORCE` | different non-`MIXED` state | `MISMATCH` |

`UNSURE` records that the student had not determined a force state. `NOT_COMPARABLE` records that a PhysicalMember had mixed segment evidence while the Prediction schema has no `MIXED` choice. Neither is an error, a mismatch, a wrong answer, a score, a percentage, a rank, a grade, or a pass/fail outcome. For example, `UNSURE` plus actual `COMPRESSION` communicates “分析前未确定；分析结果为受压”.

## Maximum-displacement comparison

For every authoritative analysis-node displacement `(ux_mm, uy_mm)`, Compare derives:

```text
d_i_mm = sqrt(ux_mm^2 + uy_mm^2)
d_max_mm = max_i d_i_mm
tie_tolerance_mm = max(1e-9 mm, 1e-9 * d_max_mm)
maximum candidates = { i | d_max_mm - d_i_mm <= tie_tolerance_mm }
```

This produces a deterministic candidate set, including the all-zero case. The Prediction’s `PhysicalPointRef` is mapped through the linked immutable ModelRevision snapshot and deterministic idealization: an explicit Connection maps by connection identity; a free `MEMBER_ENDPOINT` maps by physical member identity plus `START|END`. An endpoint normalized by an explicit Connection must map as that Connection. Coordinates, ORM primary keys, and proximity guesses are forbidden.

`location_match = true` only when the mapped analysis node belongs to the maximum candidate set. An unmappable prediction reference is a comparison-contract failure, not a coordinate fallback.

## Load-path evidence overlay

The representative Prediction load path is a student hypothesis, never Solver truth. Compare must not create an `actual_load_path`, a unique “real path”, a correctness boolean, or a path score. For each PhysicalMember explicitly named in the student’s alternating path, the overlay exposes the projected `actual_state` and its complete segment evidence. It must not fabricate a single PhysicalMember `axial_force_N` when multiple segments exist. Each segment entry reuses the stable authoritative `analysis_member_id` from `truss2d-result-v1`, plus that segment’s `axial_force_N` and teaching state; it never uses an ORM identity.

## `comparison-v1` output

The derived output contains only the minimum teaching facts:

```json
{
  "schema_version": "comparison-v1",
  "comparison_available": true,
  "reason": null,
  "project_id": 1,
  "prediction_id": 2,
  "analysis_run_id": 3,
  "source_draft_version": 7,
  "member_comparisons": [
    {
      "physical_member_client_key": "m1",
      "predicted_state": "UNSURE",
      "actual": {
        "actual_state": "COMPRESSION",
        "segments": [
          {"analysis_member_id": "m1:1", "axial_force_N": -12.5, "teaching_state": "COMPRESSION"}
        ]
      },
      "comparison_status": "UNSURE"
    }
  ],
  "maximum_displacement": {
    "maximum_displacement_mm": 0.42,
    "tie_tolerance_mm": 1e-9,
    "predicted_point": {"kind": "CONNECTION", "connection_client_key": "c1"},
    "candidate_analysis_node_ids": ["n1"],
    "location_match": true
  },
  "load_path_evidence": [
    {
      "physical_member_client_key": "m1",
      "actual_state": "COMPRESSION",
      "segments": [
        {"analysis_member_id": "m1:1", "axial_force_N": -12.5, "teaching_state": "COMPRESSION"}
      ]
    }
  ]
}
```

With no linked Prediction, output is limited to `schema_version`, `comparison_available: false`, `reason: "NO_PREDICTION"`, and safe Project/Run identifiers. Comparison must not copy the full physical snapshot, solver input, material/section database records, or full result payload.

## HTTP disclosure boundary

The M4B Compare HTTP boundary is `GET /projects/<project_id>/analyses/<run_id>/comparison/`, specified in `API_AND_APPLICATION_FLOW.md`. It uses the existing M3 `ok` success envelope with one nested `comparison-v1` value. It is a result-disclosure boundary: after scoped Project/Run read authorization and successful deterministic derivation, the existing StudentResultReveal service must persist the student-owner reveal before the response returns. Manager/Developer reads use the same authorization path but create no student reveal. No Prediction remains HTTP 200 with this contract’s `NO_PREDICTION` unavailable value.

## Explain and mechanics boundaries

Compare Core returns facts only. Future Explain consumes these facts but is responsible for teaching prose; Compare does not generate recommendations, structural-quality assessments, long-form explanation, or AI output.

Compare must not modify Solver, reaction, displacement, axial force, stress, mass, ModelRevision reuse, `model_hash`, `input_hash`, idealization, or result schema. It derives only from their immutable outputs.

## Gate 1A self-review

- Cross-draft comparison is forbidden independently of matching hashes.
- Teaching `ZERO_FORCE` is classified at analysis-segment level, then projected without losing segment evidence; it is independent of M1 numerical `ZERO`.
- `UNSURE` and `NOT_COMPARABLE` are non-error evidence.
- Load path has no Solver-truth or score semantics.
- No-Prediction remains a legal product flow.
- No score, ranking, grade, or Comparison persistence is introduced.
