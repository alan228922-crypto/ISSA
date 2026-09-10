# MASTER_SPEC_CONFLICT_CHECK.md

## 0. Status

**Result:** `COMPLETE — MASTER_SPEC.md v1.0 ESTABLISHED AND RECONCILED`

The project previously had no `MASTER_SPEC.md`. A first Source of Truth has now been created from the latest confirmed Truss-first direction and reviewed against the current architecture specs.

---

## 1. Reconciliation Rule

Current authority order:

```text
MASTER_SPEC.md
    ↓
Current specialist specs
    ↓
Architecture Decision Register
    ↓
Implementation Plan
    ↓
Code / Tests / Migrations
```

Historical Frame-first documents remain reference material only where they conflict with the current master.

---

## 2. Reconciliation Matrix

| Area | MASTER_SPEC v1.0 | Architecture specs | Result |
|---|---|---|---|
| P0 analysis | `TRUSS_2D` | `TRUSS_2D` | PASS |
| Frame | Stage 2 | Separate Frame extension seam | PASS |
| Units | mm/N/MPa/g | Same | PASS |
| Support | Pinned/Roller; orientation open | Same | PASS |
| P0 load | manual nodal Fx/Fy | Same | PASS |
| Self Weight | deferred P0.x/P1 | Same | PASS |
| Physical vs Analysis | separated | separated | PASS |
| Intersection | not automatic connection | same invariant | PASS |
| PhysicalMember | not AnalysisElement | same invariant | PASS |
| Mechanics | pure Python | same dependency boundary | PASS |
| Solver authority | displacement/reaction/N | same kernel contract | PASS |
| Postprocess | stress/mass/Euler | same pure postprocess boundary | PASS |
| Teaching | explanation, no result mutation | same | PASS |
| Revision | immutable | same | PASS |
| Analysis traceability | Revision + SolverVersion + InputHash | same | PASS |
| Authorization | server-side | same | PASS |
| Purge | Event +7 day operational purge | same | PASS |
| Research retention | anonymous derived metrics only | same | PASS |
| Generic FEM | prohibited in P0 | same | PASS |

---

## 3. Historical SPEC CONFLICTS

### SC-01 — Frame-first research plan vs Truss-first P0

**Resolution:** `RESOLVED`

Frame learning/benchmark content is Stage 2.

### SC-02 — Raw research snapshot vs purge

**Resolution:** `RESOLVED`

Raw operational model data is purged; anonymous derived metrics only may survive.

### SC-03 — MASTER_SPEC absent

**Resolution:** `RESOLVED`

`MASTER_SPEC.md v1.0` has now been established.

---

## 4. Open Decisions Are Not Spec Conflicts

The following remain open but are represented consistently across the master and specialist specs:

- Master O-001: Euler K + controlling I / weak-axis policy
- Roller orientation
- FINISHED_GRACE user access
- post-purge account lifecycle
- composite strip overlap if required

They should be handled through the decision register, not treated as hidden inconsistencies.

---

## 5. Final Result

No blocking architecture conflict remains between `MASTER_SPEC.md v1.0` and the current Truss-first architecture set.

Architecture may move from:

```text
CONDITIONAL_FREEZE
```

to:

```text
FINAL_FROZEN
```

with scoped feature gates remaining active for the open decisions.

## Approved readiness-audit reconciliation

The Product Owner authorized these corrections directly in the Codex handoff:

- FINISHED_GRACE access remains Master O-003 Open; read-only is recommended only. No permanent edit/analyze allow/deny assertions before confirmation, including in the API flow.
- Mutable authoring uses physical-draft-v1; immutable ModelRevision canonical snapshots use physical-snapshot-v1. Task 10 is corrected.
- Account lifecycle gates reference Master O-004; no automatic deletion or disabling. Confirmed Project Operational Data purge remains independent.
- Master O-001 explicitly includes controlling I / weak-axis policy alongside K and final risk behavior.
- Prediction is a teaching step; blocking Analyze remains open.

MASTER_SPEC remains v1.0 / CURRENT; architecture remains FINAL_FROZEN. This reconciliation does not close any Open Decision or start production implementation.
