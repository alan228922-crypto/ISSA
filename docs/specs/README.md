# Architecture Specification Set — Truss-first P0 — FINAL

## Current Status

- Source of Truth: `MASTER_SPEC.md v1.12`
- Architecture: `FINAL_FROZEN`
- Current milestone: **M8 CLOSED — STABLE ON MAIN**; M7 and M8 complete
- Stable implementation baseline: `main@96c335dc1c1d742d4143817c02a51a0fc3961892` (post-M8; later docs-only commits do not imply a new implementation baseline)
- Learning flow: Build → Check → optional Prediction → Analyze → Compare / Explain → Report → optional Reasoning → optional Reflection → Iterate
- Prediction, Reasoning, and Reflection remain non-blocking; mechanics authority remains `Truss2DSolver`
- M5/M6 merged-main automated acceptance and regression verification: **PASS**
- Current product stage: **CONTROLLED TEACHING / PILOT**, not unattended production deployment
- Current activity: **M9 IMPLEMENTED — TEACHER REVIEW PENDING**; Tasks 1–8 technical gates complete; Owner review PENDING; not merged to main. See [evidence](../development/M9_IMPLEMENTATION_EVIDENCE.md) and [review handoff](../development/M9_REVIEW_AND_ACCEPTANCE.md).
- O-003: **RESOLVED** — FINISHED_GRACE = READ-ONLY HISTORY; PURGED operational access fails closed
- O-006: **RESOLVED — APPROVED SCOPE ONLY** — DRAFT CSV and DRAFT/ACTIVE single CREATE_USER, JOIN_EXISTING, REACTIVATE, DEACTIVATE
- O-004: **OPEN** — User account lifecycle
- O-001: **OPEN — MECHANICS REVIEW REQUIRED** — Euler effective length / controlling-axis policy
- O-005: remains open only if overlap-capable composite sections are proposed

Status synchronization dated 2026-10-21 records already approved decisions, not new authorization semantics. D-M7-001/002/003 and D-M8-001/002/003/004 are **RESOLVED**. See [MASTER_SPEC current status](MASTER_SPEC.md), [decision register](ARCHITECTURE_DECISION_REGISTER.md), [M7 evidence](../development/M7_IMPLEMENTATION_EVIDENCE.md), and [M8 Owner acceptance](../development/M8_IMPLEMENTATION_EVIDENCE.md). Older milestone-stage OPEN / acceptance-pending statements retain historical attribution and do not override this post-M8 status.

O-006 does **not** include ACTIVE CSV, public signup, join codes, Manager assignment/revoke/promotion, administrator password reset, global User recovery, Event transition UI/scheduler, or automatic Project provisioning. Unapproved operations remain fail closed / out of scope; this is not completion of all Event administration.

## Current Files

1. `MASTER_SPEC.md`
2. `STUDENT_LEARNING_WORKSPACE_UX.md` — M5 single-workspace UX contract and authority boundaries
3. `MASTER_SPEC_REVIEW_RECORD.md`
4. `MASTER_SPEC_CONFLICT_CHECK.md`
5. `ARCHITECTURE_FREEZE.md`
6. `ARCHITECTURE_SPEC.md`
7. `DOMAIN_MODEL.md`
8. `DATA_CONTRACT.md`
9. `TRUSS_SOLVER_CONTRACT.md`
10. `AUTHORIZATION_AND_EVENT_ARCHITECTURE.md`
11. `API_AND_APPLICATION_FLOW.md`
12. `TEST_ARCHITECTURE.md`
13. `FRAME_EXTENSION_STRATEGY.md`
14. `ARCHITECTURE_DECISION_REGISTER.md`
15. `CODEX_IMPLEMENTATION_PLAN.md`
16. `IMPLEMENTATION_HANDOFF_CHECKLIST.md`
17. `PREDICTION_AND_REVEAL_ARCHITECTURE.md`
18. `COMPARISON_CONTRACT.md`
19. `EXPLANATION_CONTRACT.md`
20. `REFLECTION_AND_RATIONALE_ARCHITECTURE.md`
21. `CALCULATION_REPORT_ASSISTANCE_SPEC.md` — completed M6 Report contract
22. `POC_V1_KNOWN_ISSUES.md` — deferred manual verification, scope exclusions, and Post-PoC open items

M9 scope: [Results Evidence & Teaching Loop](../superpowers/specs/2026-10-21-m9-results-teaching-loop-decisions.md) — **OWNER SCOPE APPROVED**. [TDD implementation plan](../superpowers/plans/2026-10-21-m9-results-teaching-loop.md) and execution method still require Owner approval; implementation has not started.

## Frozen P0 Direction

- `TRUSS_2D`
- 2D linear elastic ideal truss
- mm / N / MPa / g
- Pinned / Roller
- manual nodal Fx/Fy
- pure Python Mechanics Core
- Physical → Idealization → Analysis separation
- immutable ModelRevision
- AnalysisRun + SolverVersion + InputHash
- deterministic TeachingInsight above mechanics
- server-side authorization
- Event +7 day operational purge
- anonymous derived research metrics only
- Future `FRAME_2D` via a separate mechanics kernel
- no generic FEM / microservice / 3D / nonlinear / optimization scope in P0

## Scoped Open Gates

- Master O-001: Euler K + controlling I / weak-axis policy — `OPEN — MECHANICS REVIEW REQUIRED`; explicit-input formula only, not product screening
- post-purge account lifecycle
- composite strip overlap if required

These gates do not invalidate MASTER_SPEC v1.12 or the overall final architecture freeze; they block only directly dependent behavior. O-003 is no longer an open gate: authorized history remains readable in FINISHED_GRACE, while create, Save, Check, Analyze, Prediction/Reflection/Reasoning authoring and other student mutations are denied. PURGED operational GET/write remains denied, including residual rows.

## Next Execution Point

Review the M9 TDD implementation plan and execution method; scope is approved, but implementation must wait for Owner plan/method approval. Event lifecycle UI/scheduler is not promoted into M9 merely because it remains undelivered. Euler automatic product behavior remains blocked by O-001; the existence of a formula helper does not make screening available.

Historical milestone state (2026-09-23/24): POC V1 frontend reconciliation recorded P1/P2 remaining 0, and POC V1 / UX V2 manual acceptance was pending at those checkpoints. The then-recommended BUG / UX STABILIZATION mode is historical, not the current post-M8 execution point. M8 acceptance does not fabricate separate earlier UX sign-offs.

Before any task, the implementer must read:

1. `MASTER_SPEC.md`
2. the relevant specialist spec
3. `ARCHITECTURE_FREEZE.md`
4. the matching implementation-plan task

Do not begin a new milestone or implement Post-PoC backlog items without explicit authorization.

## Canonical location

`docs/specs/` is the CURRENT specification set. The original `architecture_round5_final_master_spec_v1/` is preserved locally as historical source and excluded from Git. `docs/codex/` is reserved; execution instructions are delivered directly as user text, so no CODEX prompt files are required.
