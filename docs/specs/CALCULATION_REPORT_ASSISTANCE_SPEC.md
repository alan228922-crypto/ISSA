# Calculation Report Assistance — M6 Product Contract

## Status and authority

- Status: **CURRENT / FROZEN — M6 COMPLETE; First POC V1 automated acceptance passed**
- Parent authority: `MASTER_SPEC.md v1.12`
- Scope: online calculation-report assistance for one authoritative successful `AnalysisRun`
- Presentation: online Report / Calculation Report Data Package only
- Deferred: PDF, DOCX, and Excel export

M6 organizes authoritative engineering facts so a student can prepare a calculation report. It does not write the student's engineering argument, select a best design, or replace the mechanics authority.

### D-M6-011 — Reasoning visibility

In M6 P0, raw `CalculationReportReasoning` is visible and editable only to the Project owner/student author. Managers and Developers do not receive raw reasoning visibility, review, publication, or teacher-review states.

### D-M6-012 — No completion lifecycle in P0

Reasoning has no completed, locked, submitted, or published state. It is optional saved student text that remains editable until the existing Project/Event read-only lifecycle or purge.

### D-M6-013 — Seven optional student-authored sections

Modeling, material/section, support/load, result interpretation, design-change, scheme-comparison, and final-conclusion reasoning are all optional in M6 P0. Empty fields do not change technical completeness, block Report/Analyze/Prediction/Reflection, or imply quality judgment.

### D-M6-007 — Failed AnalysisRun Report Policy

Only a successful `AnalysisRun` may produce a Calculation Report Package. If the explicitly selected Run has status `VALIDATION_FAILED` or `SOLVER_FAILED`, the Report endpoint returns `REPORT_ANALYSIS_NOT_SUCCESS` and does not produce a package.

The error response includes the safe details `analysis_run_id` and `analysis_status`, and may include the existing safe `failure_code` where the public error contract permits it. It never exposes a traceback, filesystem path, raw stack detail, or a substitute result. The Report layer does not re-analyze, choose another Run, select `latest`, or create a second diagnostics engine.

## 1. Goal and user story

After a successful Analyze, a student can open **计算书资料** and:

1. identify exactly which `AnalysisRun` and model revision the material represents;
2. inspect the frozen assumptions, physical model, inputs, and authoritative results;
3. see provenance and missing/unavailable items;
4. use the organized facts while writing their own engineering reasoning;
5. return to the Workspace and continue the learning loop.

## 2. Frozen authority boundary

```text
Report
→ AnalysisRun
→ ModelRevision
→ Physical Snapshot
→ SolverVersion
→ InputHash
```

`Report ≠ Mechanics Engine`.

The Report layer may only organize and present existing authoritative data. It must not:

- reassemble stiffness;
- recompute displacement, reaction, axial force, stress, or mass;
- perform frontend mechanics calculations;
- modify Solver results;
- use AI to generate engineering conclusions or rationale.

Mechanics authority remains the `TRUSS_2D` Solver and authoritative postprocess.

## 3. Version and historical behavior

Every Report is bound to one explicit `AnalysisRun`. It must not automatically select `latest`, overwrite a historical run, or recalculate an old Report from the current Draft.

When the student edits the Draft after a Report's source run:

- the historical Report remains viewable under existing authorization;
- it is marked `STALE`;
- `STALE` means it belongs to an earlier Draft / AnalysisRun, not that its result is erroneous;
- it is not automatically deleted, recomputed, or replaced.

## 4. Platform and student responsibility

### Platform may provide

- Project and Event metadata;
- AnalysisRun, ModelRevision, model hash, SolverVersion, and InputHash;
- frozen mechanics assumptions;
- geometry, explicit Connections, PhysicalMembers, Materials, Sections, Supports, and Loads;
- node displacement and support reaction;
- member axial force, tension/compression/zero state, stress, and mass;
- ValidationLog and limitations;
- provenance and completeness/missing-item status.

### Student must provide

- why the structure system was chosen;
- why materials and sections were selected;
- why supports and loads were simplified as they were;
- engineering interpretation of results;
- design-change reasons;
- scheme trade-offs;
- final design conclusion.

The platform must not automatically generate a best design, final conclusion, modification reason, scheme ranking, or design argument.

## 5. Report Data Contract

This is a conceptual product contract, not a database schema.

| Block | Required | Authority | Student editable |
|---|---:|---|---:|
| Metadata | YES | Application / Analysis | NO |
| Assumptions | YES | Frozen Mechanics contract | NO |
| Materials / Sections | Where applicable | ModelRevision Physical Snapshot | NO |
| Geometry / Connectivity | YES | Physical Snapshot + Idealization mapping | NO |
| Supports / Loads | YES | Physical Snapshot + canonical solver input | NO |
| Results Summary | Successful Run only | AnalysisRun result / postprocess | NO |
| Node Results | Successful Run only | `AnalysisRun.result_json` | NO |
| Member Results | Successful Run only | `AnalysisRun.result_json` / postprocess | NO |
| Validation / Limitations | YES | AnalysisRun + ValidationLog + capability boundary | NO |
| Student-authored Reasoning | Contract placeholders | Student | YES |

### Metadata

Includes Project, Event context, generated timestamp, explicit AnalysisRun, ModelRevision, source draft version, model hash, SolverVersion, and InputHash.

### Assumptions

Only the frozen P0 assumptions are listed: `TRUSS_2D`, 2D linear elastic, small displacement, pin-jointed, axial-only, `ux/uy`, nodal `Fx/Fy`, and units mm/N/MPa/g.

### Materials / Sections

Includes identity, authoritative numeric properties, section properties, and definition hash where available, sourced from the immutable Physical Snapshot.

### Geometry / Connectivity

Includes GeometryNode, PhysicalMember, explicit Connection, and relevant PhysicalMember → AnalysisMember/segment mapping. `Intersection ≠ Connection` and `PhysicalMember ≠ AnalysisElement` remain explicit boundaries.

### Supports / Loads

Includes support type, restrained global axis, load target, and `Fx/Fy` from the physical snapshot and canonical solver input.

### Results

For a successful AnalysisRun, includes maximum displacement, authoritative tension/compression/zero summary where available, total mass, node displacements, support reactions, member axial force, member state, stress, mass, and applicable result schema/version. No result is recomputed by the Report layer.

### Validation / Limitations

Includes AnalysisRun status, relevant ValidationLog, unavailable capabilities, model/analysis limitations, and the statement that the package is not professional code-compliance review or formal engineering sign-off.

Euler / Stability automatic reporting is `UNAVAILABLE` in M6 P0 while O-001 remains open. The package may display that limitation but may not infer K, choose a controlling axis, or generate an Euler risk level.

### Student-authored reasoning

The contract preserves placeholders for modeling rationale, material/section rationale, support/load simplification rationale, design-change rationale, scheme comparison, and final conclusion. These are student-owned and are not auto-filled by AI. Reflection may be referenced as learning evidence but does not automatically replace a complete design argument.

## 6. Completeness contract

M6 uses **Calculation Report Readiness / Completeness**, not a quality score. Allowed states are:

- `READY`
- `MISSING`
- `NOT_APPLICABLE`
- `UNAVAILABLE`

The checks may cover successful AnalysisRun, valid ModelRevision, material/section evidence, supports, loads, results, provenance, and any student-authored fields later marked required by Teacher Review.

Completeness must not produce a numeric score, grade, quality judgment, best-design judgment, or Reflection correctness judgment. Reflection remains a Soft Gate and is not required to view or produce the basic engineering package.

## 7. M6 P0 non-goals

- AI-generated full calculation reports or engineering arguments;
- automatic design conclusions, best schemes, or modification advice;
- grading, ranking, or quality scoring;
- professional code review or automatic sign-off;
- advanced PDF/DOCX/Excel export;
- complex formula editor;
- collaborative editing;
- Frame or 3D results;
- Euler automatic risk UX;
- any duplicated mechanics engine.

## 8. Open-decision impact

| Decision | M6 impact | Status |
|---|---|---|
| O-001 Euler K / buckling axis | Related but not blocking base M6; blocks any Euler report block | POST-POC / OPEN |
| O-003 FINISHED_GRACE access | Related but not blocking base package; later affects historical Report access | POST-POC / OPEN |
| O-004 account lifecycle after purge | Related but not blocking base package; affects post-purge account boundary | POST-POC / OPEN |
| O-005 composite overlap | Unrelated for base M6; relevant only to overlap-capable section reporting | POST-POC / OPEN |
| O-006 ACTIVE provisioning | Unrelated for base M6; concerns event provisioning | POST-POC / OPEN |

## 9. Teacher review items

- `T-M6-001` — **POST-POC / OPEN**: confirm the minimum competition calculation-report engineering content;
- `T-M6-002` — **POST-POC / OPEN**: confirm which student-authored sections are required versus optional;
- `T-M6-003` — **POST-POC / OPEN**: confirm that Euler / Stability remains outside M6 P0 until O-001 is resolved.

These do not block the core authoritative package architecture but must be resolved before dependent presentation/completeness behavior is finalized.

## 10. M6 implementation gates

### Gate 0 — Report Contract Freeze — COMPLETE

Freeze this contract and the high-level M6 boundary.

### Gate 1 — Authoritative Report Package — COMPLETE

Assemble a read-only package from one explicit AnalysisRun and preserve provenance without mechanics recomputation.

### Gate 2 — Completeness + Limitation — COMPLETE

Expose readiness, missing items, and unavailable capabilities without quality scoring.

### Gate 3 — Report Workspace — COMPLETE

Present the online package in the existing Workspace with progressive disclosure.

### Gate 4 — Student-authored Reasoning Boundary — COMPLETE

Keep platform facts separate from student-authored reasoning and preserve Reflection as a Soft Gate.

### Gate 5 — Acceptance + Reconciliation — COMPLETE

Verify AnalysisRun binding, historical `STALE` behavior, provenance, authorization, student-authored boundaries, and the absence of mechanics duplication.

First POC V1 is **CODE COMPLETE — MANUAL PRODUCT ACCEPTANCE PENDING**. Automated acceptance covers the explicit-Run Report/Reasoning flow, historical isolation, authorization, failure boundaries, purge, and full regression. It does not close the Post-PoC decisions above or authorize deferred features.
