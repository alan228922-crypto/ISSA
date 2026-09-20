# POC V1 Known Issues / Deferred Verification

## Closure status

- First POC V1: **CODE COMPLETE — MANUAL PRODUCT ACCEPTANCE PENDING**
- Automated Critical defects: **0**
- Automated Important defects: **0**
- Recommended next mode: **BUG / UX STABILIZATION**

## Known issues

No reproducible Critical or Important production defect remains in the automated POC V1 acceptance baseline.

## Deferred manual verification

- Product Owner previously observed Workspace displaying “只读查看” during a real-device session. Automated authorization and Workspace tests have not reproduced a production defect. Status: **DEFERRED RUNTIME VERIFICATION**. Do not change production permission code without a reproducible failing test.
- Full Product Owner manual browser journey remains pending. This is why the release identity is not “fully user accepted.”

## Out of scope for POC V1

- Euler / Buckling automatic reporting is unavailable. O-001 remains **POST-POC / OPEN**.
- PDF, DOCX, and Excel export were not implemented.
- Advanced CAD, arbitrary-angle Roller, Frame2D, 3D, nonlinear mechanics, and a new optimization engine were not implemented.
- AI-generated report reasoning, AI scoring, reviewer workflow, teacher approval workflow, and new lifecycle states were not implemented.

These are deliberate scope exclusions, not defects.

## Post-PoC open items

- O-001, O-003, O-004, O-005, O-006 — **POST-POC / OPEN**
- T-M6-001, T-M6-002, T-M6-003 — **POST-POC / OPEN**
