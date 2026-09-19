# Architecture Specification Set — Truss-first P0 — FINAL

## Current Status

- Source of Truth: `MASTER_SPEC.md v1.8`
- Architecture: `FINAL_FROZEN`
- Current milestone: M5 Gate 0A UX contract frozen; implementation has not started
- Production baseline: M1–M4 learning backend complete
- Open decisions: scoped gates only

## Current Files

1. `MASTER_SPEC.md`
2. `STUDENT_LEARNING_WORKSPACE_UX.md` — current M5 Gate 0A single-workspace UX contract
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
- Roller orientation
- FINISHED_GRACE access
- post-purge account lifecycle
- composite strip overlap if required

These gates do not invalidate MASTER_SPEC v1.0 or the overall final architecture freeze; they block only directly dependent behavior.

## Next Execution Point

The repository can now enter implementation planning/execution using `CODEX_IMPLEMENTATION_PLAN.md`.

Before any task, the implementer must read:

1. `MASTER_SPEC.md`
2. the relevant specialist spec
3. `ARCHITECTURE_FREEZE.md`
4. the matching implementation-plan task

Documentation reconciliation is authorized; M1 execution requires the next explicit user instruction.

## Canonical location

`docs/specs/` is the CURRENT specification set. The original `architecture_round5_final_master_spec_v1/` is preserved locally as historical source and excluded from Git. `docs/codex/` is reserved; execution instructions are delivered directly as user text, so no CODEX prompt files are required.
