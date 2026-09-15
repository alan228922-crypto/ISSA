# ARCHITECTURE_DECISION_REGISTER.md

| ID | Topic | Status | Current decision / next action |
|---|---|---|---|
| ADR-01 | P0 analysis type | Confirmed | `TRUSS_2D` only |
| ADR-02 | Overall architecture | Final baseline | Django Modular Monolith + Idealization + Pure Mechanics |
| ADR-03 | Research stage | Confirmed | Truss metrics P0; Frame metrics Stage 2 |
| ADR-04 | Purge retention | Confirmed | Retain anonymous derived metrics only |
| ADR-05 | P0 loads | Confirmed | Manual nodal Fx/Fy only |
| ADR-06 | Self Weight | Confirmed deferred | P0.x/P1 |
| ADR-07 | Initial password | Confirmed | Captain student ID; hash only; forced change |
| ADR-08 | Euler K + controlling I / weak-axis policy | MECHANICS REVIEW REQUIRED | Master O-001: no default/automatic K, controlling-axis selection, final risk bands or related wording until review; explicit-input formula only |
| ADR-09 | Roller orientation | Confirmed | Master O-002 resolved: P0 ROLLER restrains global X or Y only; arbitrary-angle support is out of scope |
| ADR-10 | FINISHED_GRACE user access | Open Decision | Master O-003: read-only recommended only; edit/analyze allow/deny remains open |
| ADR-11 | Account lifecycle after purge | Open Decision | Master O-004: do not auto-delete/disable until confirmed; Project Operational Data purge proceeds independently |
| ADR-12 | Composite strip overlap | Open if feature requires | Define before overlap-capable free-composite implementation |
| ADR-13 | MASTER_SPEC | Resolved | `MASTER_SPEC.md v1.0` established as Source of Truth |
| ADR-14 | Architecture freeze state | Final Frozen | P0 implementation may proceed with scoped gates |
| ADR-15 | Implementation sequencing | Current baseline | M0 complete → M1 Mechanics → M2 Secure Skeleton → M3 Analysis → M4 Teaching → M5 Purge/Research |
| ADR-16 | Solver/postprocess authority | Confirmed | Solver kernel: u/R/N; pure postprocess: stress/mass/Euler; Teaching: explanation only |
| ADR-17 | Payload schema distinction | Confirmed | Mutable authoring: physical-draft-v1; immutable ModelRevision canonical snapshot: physical-snapshot-v1 |
| ADR-18 | Platform Language | Confirmed | Simplified Chinese (zh-CN) for user-facing copy and Chinese comments/docstrings; program identifiers and mechanics machine codes remain English; P0 has no i18n framework |
| ADR-19 | ACTIVE Event Team Provisioning | Open Decision | Master O-006. Current safe implementation is fail-closed with PROVISIONING_STATUS_POLICY_GAP; this temporary behavior is not final product policy |
| ADR-20 | Prediction and result reveal evidence | Confirmed | M4A hybrid `prediction-v1`, Project+draft binding, immutable completed records, nullable Run FK, PhysicalPointRef, and unique owner-only StudentResultReveal; no Prediction UI/Compare in M4A |
| ADR-21 | Engineering zero-force classification | MECHANICS REVIEW REQUIRED | Master O-007: Prediction `ZERO_FORCE` is allowed, but existing numerical `ZERO` must not become a teaching classification; threshold/reference policy is unapproved |
| ADR-22 | Project operational purge boundary | Confirmed — Task 5 Option 1 | Preserve all PROTECT FKs; raw Project.delete is unsupported with protected history. Use atomic ordered `purge_project_operational_data`, Project last, durable minimal unique ProjectOperationalPurgeAudit, deterministic repeat; no User deletion. Event orchestration remains outside M4A. |
| ADR-23 | ModelRevision reuse identity | Confirmed — M4A Gate 3 refinement | Reuse only for `(Project, source_draft_version, model_hash)`. A changed authoring draft always gets a new immutable revision even if snapshot/content hash, numerical input hash, and result match. `model_hash` remains content identity; `input_hash` remains numerical-input identity. |
