# POC V1 Known Issues / Deferred Verification

## Closure status

- First POC V1: **POC V1 FRONTEND CONTRACT COMPLETE — MANUAL PRODUCT ACCEPTANCE PENDING**
- Automated Critical defects: **0**
- Automated Important defects: **0**
- Frontend reconciliation gaps: **P1 0 / P2 0**
- Recommended next mode: **MANUAL PRODUCT ACCEPTANCE**
- UX V2 follow-on: **UX V2 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING**；以学生为中心的六阶段界面尚待 Product Owner 实机确认。

## Known issues

No reproducible Critical or Important production defect remains in the automated POC V1 acceptance baseline.

## Deferred manual verification

- The earlier owner “只读查看” observation is closed as non-reproducible after owner and Manager/Developer browser evidence: owners receive editable controls, while authorized non-owners receive an explained read-only state. A future recurrence still requires a reproducible failing test before authorization changes.
- Product Owner sign-off on a real device remains pending. Automated public-control browser acceptance is complete, so the release is ready for that manual pass but is not described as owner-accepted.
- UX V2 的 3 秒产品用途识别、5 秒阶段/下一步识别、无需文档开始建模等体验标准，仍须由 Product Owner 在真实设备上主观核验；自动化仅证明入口、流程与控件可用，不替代该验收。

## Out of scope for POC V1

- Euler / Buckling automatic reporting is unavailable. Its automatic-product success criterion is `SPEC_CONFLICT`, blocked by O-001, which remains **POST-POC / OPEN**; this closure does not infer K, choose a controlling axis, or add risk bands.
- PDF, DOCX, and Excel export were not implemented.
- Advanced CAD, arbitrary-angle Roller, Frame2D, 3D, nonlinear mechanics, and a new optimization engine were not implemented.
- AI-generated report reasoning, AI scoring, reviewer workflow, teacher approval workflow, and new lifecycle states were not implemented.

These are deliberate scope exclusions, not defects.

## Post-PoC open items

- O-001, O-003, O-004, O-005, O-006 — **POST-POC / OPEN**
- T-M6-001, T-M6-002, T-M6-003 — **POST-POC / OPEN**

## Verified reconciliation evidence

- Empty-project Material / Rectangle Section / first-member creation and persistence;
- visible SNAP / ORTHO / Fit / numeric coordinate workflow;
- frozen property editing and dependency-safe deletion;
- explicit AnalysisRun selection across Result / Compare / Explain / Report / Reasoning / Reflection;
- two-Run historical isolation and stale labeling;
- beginner result/error presentation and 1024×900 desktop containment;
- Login-to-history Playwright journey using public controls only.
- frontend contract closure checks for transient CAD preview/SNAP feedback, stable student labels, MIXED evidence, persisted-state workflow projection, keyboard pan/zoom/Fit, and 1024/1280/1440 viewport containment.

No mechanics formula, solver, idealization, postprocess, or result-schema behavior changed in the frontend contract closure.
