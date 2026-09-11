# ARCHITECTURE_FREEZE.md

## 0. Freeze State

**Architecture state:** `FINAL_FROZEN`\
**Source of Truth:** MASTER_SPEC.md v1.3\
**Freeze date:** 2026-09-10

Meaning:

- P0 product scope and architecture boundaries are stable enough for implementation.
- The current specialist specs have been reconciled with MASTER_SPEC v1.0.
- Open mechanics/product decisions remain explicit scoped gates.
- No developer, Codex worker or AI may silently resolve an open decision.

---

## 1. Frozen Baseline

### F-01 — Overall architecture

```text
Django Modular Monolith
        ↓
Application Services
        ↓
Physical Snapshot
        ↓
Idealization
        ↓
Pure Python Mechanics Core
```

### F-02 — P0 analysis

Only:

```text
TRUSS_2D
```

### F-03 — Physical / Analysis separation

```text
Physical Structure ≠ Analysis Model
Intersection ≠ Connection
PhysicalMember ≠ AnalysisElement
```

### F-04 — Mechanics authority

`Truss2DSolver` kernel owns:

- node displacement
- support reaction
- member axial force

Pure postprocess/stability owns:

- axial stress
- tension/compression numerical classification
- mass
- explicit-K Euler calculation

Teaching Layer only interprets source metrics.

### F-05 — Traceability

```text
Project
→ immutable ModelRevision
→ AnalysisRun
→ SolverVersion
→ InputHash
```

### F-06 — Authorization

Role / Event / Project ownership must be verified server-side.

### F-07 — P0 loads

Manual nodal Fx/Fy only.

Self Weight remains P0.x/P1.

### F-08 — Research retention

Raw operational student project/model/revision data is deleted by Event purge policy.

Only approved anonymous derived metrics may survive.

### F-09 — Frame seam

Future Frame uses:

```text
FrameModel → Frame2DSolver
```

Do not expand the Truss kernel with Frame conditionals.

### F-10 — YAGNI

P0 does not require:

- microservices
- repository pattern everywhere
- generic FEM framework
- CQRS
- event sourcing
- Redis/Celery
- WebSocket
- SPA/API-first rewrite
- 3D
- nonlinear mechanics
- optimization

---

## 2. Frozen Specification Set

1. `MASTER_SPEC.md`
2. `ARCHITECTURE_SPEC.md`
3. `DOMAIN_MODEL.md`
4. `DATA_CONTRACT.md`
5. `TRUSS_SOLVER_CONTRACT.md`
6. `AUTHORIZATION_AND_EVENT_ARCHITECTURE.md`
7. `API_AND_APPLICATION_FLOW.md`
8. `TEST_ARCHITECTURE.md`
9. `FRAME_EXTENSION_STRATEGY.md`
10. `ARCHITECTURE_DECISION_REGISTER.md`
11. `MASTER_SPEC_CONFLICT_CHECK.md`
12. `MASTER_SPEC_REVIEW_RECORD.md`
13. `ARCHITECTURE_FREEZE.md`

`CODEX_IMPLEMENTATION_PLAN.md` is an execution plan, not the Source of Truth.

---

## 3. Scoped Open Gates

### G-01 — Master O-001: Euler K / controlling I / weak-axis policy

**Status:** `MECHANICS REVIEW REQUIRED`

Blocks:

- automatic K default/inference
- automatic controlling I / weak-axis selection policy
- final buckling risk bands
- final risk wording tied to K policy

Does not block:

- explicit-K Euler formula unit tests
- Truss solver
- section engine
- other P0 workflow

### G-03 — FINISHED_GRACE access

Blocks final Event UX permission behavior only.

Master O-003 remains open. Read-only is a recommendation only; do not establish permanent allow/deny edit/analyze assertions before confirmation.

### G-04 — Account lifecycle after purge

Project operational purge is confirmed.

Do not auto-delete/disable User until Master O-004 is confirmed. Project Operational Data purge is not blocked by this decision.

### G-05 — Composite overlap

Blocks only overlap-capable free composite section behavior if needed.

---

## 4. Change Control

### May change without Product Owner re-approval

- internal helper names
- test fixture organization
- refactoring preserving public/domain contracts
- performance changes preserving validated mechanics results

### Requires architecture/spec review

- new Django app
- new core persistent entity
- ownership/lifecycle changes
- ModelRevision mutability changes
- solver contract changes
- sign convention changes
- new P0 load/support/analysis type
- purge-retention changes
- AI entering mechanics authority
- Frame mechanics entering Truss kernel

### Requires Product Owner / teacher decision

- mechanics assumption changes
- Euler K policy
- competition-rule interpretation
- P0 scope expansion
- research-retention expansion

---

## 5. Implementation Gate

### Planning

`OPEN`

### P0 production implementation

`OPEN WITH SCOPED GATES`

Implementation may proceed against MASTER_SPEC v1.0 and the specialist specs.

When reaching a scoped open gate, stop only that task/behavior and continue unrelated work where dependencies permit.

### Frame implementation

`CLOSED — STAGE 2`

### Euler automatic product behavior

`CLOSED UNTIL G-01 RESOLVED`

---

## 6. Definition of Architecture Compliance

An implementation is architecture-compliant only if:

1. Mechanics runs independently of Django.
2. Physical/Analysis identity is not collapsed.
3. AnalysisRun traces to immutable ModelRevision + SolverVersion + InputHash.
4. Teaching does not overwrite numerical results.
5. authorization tests enforce server-side ownership.
6. purge is idempotent and raw operational project data does not survive.
7. mechanics changes pass benchmark gates.
8. no hidden Frame/3D/optimization scope enters P0.
9. scoped open decisions are not silently defaulted.
