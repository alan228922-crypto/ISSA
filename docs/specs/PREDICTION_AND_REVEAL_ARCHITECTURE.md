# Prediction and Result-Reveal Architecture — M4A

## Status and scope

- Status: **CONFIRMED for M4A implementation planning**
- Parent authority: `MASTER_SPEC.md v1.4`
- Scope: Prediction persistence and integrity only; no Compare, Explain, Reflection, visual editor, visualization, or teaching-result UI.

## Confirmed product boundary

Prediction is a **Soft Gate**. A student owner may analyze with `prediction_id = null`; a completed Prediction is never Solver input. A Prediction is valid only when completed before that Project owner has received a successful numerical/classified result for the same `source_draft_version`. Manager and Developer reads do not reveal a result to the student owner.

## Prediction aggregate and lifecycle

```text
Prediction
- project FK (CASCADE)
- source_draft_version
- status: DRAFT | COMPLETED | INVALIDATED
- created_by FK (PROTECT)
- created_at / completed_at nullable / invalidated_at nullable
- invalidation_code nullable
- prediction_schema_version = prediction-v1
- payload_json
```

There are no P0 member/displacement/load-path child tables. `COMPLETED` records are immutable. A completed record from an older draft remains historical evidence but is derived `STALE` for the current draft; `STALE` is not stored. A DRAFT whose source version is no longer current becomes `INVALIDATED` with a stable server-owned code. Skip creates neither a Prediction nor a skip event.

`AnalysisRun.prediction` is a nullable FK (`0..1` per Run, `0..N` Runs per Prediction). Repeated Analyze calls for the same source draft may reuse one completed Prediction.

## Revision lineage at the prediction/reveal boundary

`ModelRevision` reuse is limited to `(Project, source_draft_version, model_hash)`. A new authoring draft creates a new immutable revision even if physical content, `model_hash`, numerical `input_hash`, and eventual result are identical. This keeps revision lineage aligned with Prediction and StudentResultReveal, both of which are authoritative by `Project + source_draft_version`; hash values remain content/numerical identities and do not substitute for the draft-version boundary.

## `prediction-v1` payload

```json
{
  "schema_version": "prediction-v1",
  "member_judgments": [{"physical_member_client_key": "m1", "predicted_state": "TENSION", "display": {"member_label": "主杆"}}],
  "max_displacement_location": {"kind": "CONNECTION", "connection_client_key": "c1", "display": {"geometry_node_client_key": "n1", "geometry_node_label": "荷载点"}},
  "representative_load_path": [
    {"kind": "CONNECTION", "connection_client_key": "c1"},
    {"kind": "PHYSICAL_MEMBER", "physical_member_client_key": "m1"},
    {"kind": "CONNECTION", "connection_client_key": "c2"}
  ]
}
```

All active PhysicalMembers appear exactly once with `TENSION`, `COMPRESSION`, `ZERO_FORCE`, or `UNSURE`. `ZERO_FORCE` is a confirmed student choice, not an analysis classification. The path is one representative hypothesis: it alternates Connection/PhysicalMember, starts/ends with Connection, and adjacent entities must be physically incident. Validation must never call the Solver or claim mechanical correctness.

## PhysicalPointRef

Only this restricted tagged union is allowed:

```json
{"kind": "CONNECTION", "connection_client_key": "c1"}
{"kind": "MEMBER_ENDPOINT", "physical_member_client_key": "m3", "endpoint": "START"}
```

`endpoint` is `START|END`. GeometryNode-only references, ORM PKs, coordinates, and analysis-node IDs are forbidden. An endpoint represented by an explicit participating Connection must normalize to `CONNECTION`; unconnected same-coordinate endpoints remain distinct member-endpoint references.

The completed payload may retain only keys and labels needed for history: Connection key plus GeometryNode key/label, or member key/label plus endpoint and GeometryNode key/label. It must not duplicate coordinates, topology, material/section data, snapshots, or solver data.

Future Compare can deterministic-idealize the linked immutable ModelRevision and map `connection:<key>` or `free:<member>:START|END` to an analysis node. Actual maximum displacement is a future candidate set by displacement magnitude; a mapped prediction matches if it belongs to that set. M4A stores the seam and does not implement Compare.

## Student result reveal

```text
StudentResultReveal
- project FK (CASCADE)
- source_draft_version
- first_analysis_run FK (PROTECT)
- revealed_to_user FK (PROTECT)
- first_revealed_at
Unique(project, source_draft_version)
```

It stores no result, force, geometry, or snapshot and follows Project operational data on purge. Authority is `Project + source_draft_version`, not a Run, Revision, or model hash. On `GET /projects/<project_id>/analyses/<run_id>/data/`, only a successful Run read by that Project's student owner creates the record. Analyze metadata, failed Runs, Model Check, Section Preview, Manager reads, Developer reads, and status-only reads do not.

Every future owner response exposing numerical/classified answers must call the same reveal service before returning content. `SUCCESS` metadata alone is not disclosure.

## Operational purge boundary

The supported single-Project boundary is `purge_project_operational_data(project_id, actor_id=None)`. Raw `Project.delete()` is intentionally unsupported when protected historical relationships exist. Preserve all `PROTECT` references, including Run → ModelRevision, Run → Prediction, and Reveal → first AnalysisRun.

The internal application service locks Project and deletes in one transaction: StudentResultReveal, ValidationLog, AnalysisRun, Prediction, ModelRevision, then physical draft children (Support/NodeLoad, Connection and participation rows, PhysicalMember, GeometryNode), and Project last. User, Material, Section, SolverVersion, and Event are retained. Calling orchestration owns purge eligibility/authorization; this boundary adds no Event scheduler, Event status transition, or HTTP endpoint.

The same transaction persists `ProjectOperationalPurgeAudit`: unique primitive `project_id`, primitive `event_id`, `purged_at`, `deletion_counts_json`, and optional primitive `actor_id`. It contains no raw payload and no foreign key to deleted operational data. Repeating a completed purge returns the original audit; an unknown ID without an audit is rejected. Any deletion or audit failure rolls back the whole purge.

## Transaction invariants

Completion and owner result reveal serialize on `select_for_update()` of the same Project row.

Completion: authorize owner; lock Project; re-read draft version; check DRAFT/source version; validate payload/point/path; verify no reveal; then set `COMPLETED` with server timestamp.

Reveal: authorize and verify Project/Run scope and `SUCCESS`; lock Project; `get_or_create` the unique reveal record; commit before returning numerical result. Two tabs are idempotent. If reveal wins, later completion is rejected/invalidated; if completion wins, it is valid pre-reveal evidence.

## Authorization and open decisions

Only the student owner may create, save, or complete Prediction. Manager and Developer may read results under existing policy but cannot enter student learning evidence. PURGED blocks writes; FINISHED_GRACE remains Master O-003 Open.

O-001, O-003, O-004, O-005, O-006 remain unchanged. O-007 — **Engineering Zero-Force Classification Policy** — is **OPEN / MECHANICS REVIEW REQUIRED**. M4A must not add a threshold or equate existing numerical `ZERO` with Prediction `ZERO_FORCE`.
