# Architecture Specification Set — Truss-first P0 — FINAL

## Current Status

- Source of Truth: `MASTER_SPEC.md v1.11`
- Architecture: `FINAL_FROZEN`
- Current milestone: M5 Student Learning Workspace — **COMPLETE**
- Production baseline: M1–M4 learning backend complete; M5 Workspace merged into `main`
- Learning flow: Build → Check → optional Prediction → Analyze → Compare / Explain → Engineering Details → optional Reflection → Iterate
- Prediction and Reflection remain Soft Gates
- M5 merged-main acceptance and regression verification: **PASS**
- Next milestone: M6 Calculation Report Assistance
- M6 status: **FROZEN — implementation not started**
- Open decisions: O-001, O-003, O-004, O-005, O-006

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
21. `CALCULATION_REPORT_ASSISTANCE_SPEC.md` — frozen M6 Report contract

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

- Master O-001: Euler K + controlling I / weak-axis policy — `MECHANICS REVIEW REQUIRED`
- FINISHED_GRACE access
- post-purge account lifecycle
- composite strip overlap if required

These gates do not invalidate MASTER_SPEC v1.11 or the overall final architecture freeze; they block only directly dependent behavior.

## Next Execution Point

M5 Student Learning Workspace implementation is complete. M6 Calculation Report Assistance is frozen as the next milestone; implementation has not started.

Before any task, the implementer must read:

1. `MASTER_SPEC.md`
2. the relevant specialist spec
3. `ARCHITECTURE_FREEZE.md`
4. the matching implementation-plan task

Documentation reconciliation is authorized; M6 implementation must begin at Gate 1 only after the frozen Gate 0 contract is reviewed against the repository.

## Canonical location

`docs/specs/` is the CURRENT specification set. The original `architecture_round5_final_master_spec_v1/` is preserved locally as historical source and excluded from Git. `docs/codex/` is reserved; execution instructions are delivered directly as user text, so no CODEX prompt files are required.
