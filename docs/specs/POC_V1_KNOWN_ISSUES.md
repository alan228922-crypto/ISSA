# POC V1 Known Issues / Deferred Verification

## Closure status

- First POC V1: **PRODUCT-ALIGNED — MANUAL OWNER ACCEPTANCE READY**
- Automated Critical defects: **0**
- Automated Important defects: **0**
- Recommended next mode: **MANUAL OWNER ACCEPTANCE**

## Known issues

No reproducible Critical or Important production defect remains in the automated POC V1 acceptance baseline.

## Deferred manual verification

- The earlier owner “只读查看” observation is closed as non-reproducible after owner and Manager/Developer browser evidence: owners receive editable controls, while authorized non-owners receive an explained read-only state. A future recurrence still requires a reproducible failing test before authorization changes.
- Product Owner sign-off on a real device remains pending. Automated public-control browser acceptance is complete, so the release is ready for that manual pass but is not described as owner-accepted.

## Out of scope for POC V1

- Euler / Buckling automatic reporting is unavailable. O-001 remains **POST-POC / OPEN**.
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
