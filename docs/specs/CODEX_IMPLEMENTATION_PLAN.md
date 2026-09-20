# Truss-first P0 Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use a task-by-task execution workflow with fresh review gates. Implement using TDD, keep commits small, and verify each task independently before continuing.

**Goal:** Build the first usable Truss-first PoC while preserving strict separation between Django persistence/application code, Physical→Idealization mapping, and independently benchmarked pure-Python Truss mechanics.

**Architecture:** Django 5.x modular monolith for accounts/events/projects/persistence and server-rendered UX; pure Python `mechanics` package for section properties, truss analysis and Euler formula; a narrow Idealization layer converts immutable physical model snapshots into solver contracts. P0 exposes only `TRUSS_2D`, Pinned/Roller and manual nodal Fx/Fy.

**Tech Stack:** Python 3.12+, Django 5.x, NumPy, SQLite, pytest, pytest-django, Django Templates, HTML/CSS, Vanilla JavaScript, SVG.

**Specs:** `MASTER_SPEC.md v1.12` is the highest-level Source of Truth. Read it plus the relevant specialist spec before each task. `ARCHITECTURE_FREEZE.md` defines scoped open gates.

## Current implementation status

**First POC V1: CODE COMPLETE — MANUAL PRODUCT ACCEPTANCE PENDING.**

M5 — Student Learning Workspace — **COMPLETE**. M6 — Calculation Report Assistance — **COMPLETE (Gates 0–5)**. Gate 5 automated acceptance and merged-main regression passed on 2026-09-20. The Product Owner manual browser pass remains pending; deferred verification and exclusions are recorded in `POC_V1_KNOWN_ISSUES.md`.

The Lifecycle / Research / PoC grouping below is retained as historical implementation-plan content for Tasks 24–26. Those tasks are not M6 and remain a future, unfrozen candidate area after M6.

## Global Constraints

- P0 analysis type: `TRUSS_2D` only.
- Units: mm / N / MPa / g.
- Truss node DOF: `ux`, `uy`.
- Truss members carry axial force only.
- Truss joints are ideal pinned joints.
- Core P0 loads: manual nodal Fx/Fy only.
- Self Weight: deferred to P0.x/P1.
- Mechanics Core must not import Django.
- PhysicalMember must not be the solver TrussMember object.
- Geometry intersection must not automatically create structural connection.
- Teaching code must not modify solver numerical results.
- Authorization must be enforced server-side.
- Every analysis must be traceable to immutable ModelRevision + SolverVersion + InputHash.
- Event project operational data is purged after the 7-day grace policy; only approved anonymous derived research metrics may survive.
- Euler automatic K behavior is blocked pending mechanics review.
- P0 ROLLER restrains global X or Y only; arbitrary-angle support is out of scope.
- No Frame/3D/nonlinear/optimization/microservice/CQRS/event-sourcing scope in P0.

---

# A. Repository/File Map

The implementation should converge toward this structure. Existing repository conventions take precedence if a real repository already exists; do not restructure unrelated code merely to match this map.

```text
manage.py
config/
├── settings.py
├── urls.py
└── wsgi.py

accounts/
├── models.py
├── forms.py
├── services.py
├── views.py
├── urls.py
└── admin.py

competitions/
├── models.py
├── authorization.py
├── provisioning.py
├── purge.py
├── views.py
├── urls.py
└── management/commands/purge_due_events.py

projects/
├── models.py
├── services.py
├── views.py
└── urls.py

materials/
├── models.py
├── services.py
├── views.py
└── urls.py

modeling/
├── models.py
├── snapshot.py
├── services.py
├── views.py
└── urls.py

analysis/
├── models.py
├── services.py
├── serialization.py
├── hashing.py
├── views.py
└── urls.py

learning/
├── models.py
├── insights.py
├── services.py
├── views.py
└── urls.py

reports/
├── models.py
├── services.py
├── views.py
└── urls.py

research/
├── models.py
└── services.py

idealization/
├── __init__.py
├── physical.py
└── truss2d.py

mechanics/
├── __init__.py
├── common/
│   ├── geometry.py
│   ├── numeric.py
│   └── conventions.py
├── sections/
│   ├── model.py
│   ├── validation.py
│   └── properties.py
├── truss2d/
│   ├── model.py
│   ├── errors.py
│   ├── validation.py
│   ├── assembly.py
│   ├── solver.py
│   └── postprocess.py
└── stability/
    └── euler.py

templates/
static/
├── css/
└── js/
    └── model_editor.js

tests/
├── mechanics/
│   ├── unit/
│   ├── benchmarks/
│   │   ├── truss2d/
│   │   ├── sections/
│   │   └── stability/
│   └── fixtures/
├── idealization/
├── application/
├── permissions/
├── purge/
├── contracts/
└── integration/
```

---

# B. Delivery Strategy

Implement in vertical increments. Each task ends in a testable state and should be reviewed before the next task.

Do **not** begin Task 1 until the actual project repository is identified.

The Source-of-Truth gate is now **OPEN**: `MASTER_SPEC.md v1.12` is established and architecture is `FINAL_FROZEN`.

The tasks below are the intended order. Stop only when a task reaches one of the scoped open gates in `ARCHITECTURE_FREEZE.md`.

---

### Task 1: Project bootstrap and architectural import guard

**Files:**
- Create/confirm: `config/settings.py`
- Create: `tests/contracts/test_architecture_boundaries.py`
- Create packages: `mechanics/`, `idealization/`

**Interfaces:**
- Produces: importable `mechanics` and `idealization` packages.
- Constraint: `mechanics` must remain importable without Django setup.

- [ ] **Step 1: Write a failing architecture-boundary test**

```python
def test_mechanics_imports_without_django_setup():
    import mechanics
    assert mechanics is not None
```

Also add a static/source scan test that fails if files under `mechanics/` import `django`.

- [ ] **Step 2: Run the contract test**

```bash
pytest tests/contracts/test_architecture_boundaries.py -v
```

Expected before package setup: FAIL.

- [ ] **Step 3: Add only the minimum package scaffolding**

No solver behavior yet. Do not add generic FEM base classes.

- [ ] **Step 4: Re-run**

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mechanics idealization tests/contracts config
git commit -m "chore: establish truss platform architecture boundaries"
```

**Acceptance gate:** mechanics package imports with no Django environment and no reverse dependency.

---

### Task 2: Custom User model and forced password-change state

**Files:**
- Create/modify: `accounts/models.py`
- Create: `accounts/forms.py`
- Create: `accounts/views.py`
- Create: `tests/permissions/test_password_change_gate.py`

**Interfaces:**
- Produces: User role enum `DEVELOPER`, `MANAGER`, `USER`.
- Produces: `must_change_password: bool`.

- [ ] **Step 1: Write tests for role storage and password-change gate**

```python
def test_new_team_user_can_be_marked_must_change_password(db, user_factory):
    user = user_factory(role="USER", must_change_password=True)
    assert user.must_change_password is True
```

Add a request test proving a user with `must_change_password=True` cannot directly enter project pages.

- [ ] **Step 2: Run targeted tests and verify failure**

```bash
pytest tests/permissions/test_password_change_gate.py -v
```

- [ ] **Step 3: Implement the minimum custom user state and redirect/middleware/view guard**

Use Django password hashing only. Do not persist captain student ID as a plaintext password record.

- [ ] **Step 4: Run tests**

- [ ] **Step 5: Commit**

```bash
git commit -am "feat: add role-aware user and forced password change"
```

**Acceptance gate:** direct-URL bypass of forced password change is prevented server-side.

---

### Task 3: Competition Event, membership and server-side authorization policy

**Files:**
- Create/modify: `competitions/models.py`
- Create: `competitions/authorization.py`
- Create: `tests/permissions/test_event_project_access.py`

**Interfaces:**
- Produces:
  - `CompetitionEvent`
  - `EventMembership`
  - authorization functions/policies consumed by views/services.

- [ ] **Step 1: Write permission matrix tests**

Cases:

```text
Developer → global allowed actions
Manager assigned Event A → may read Event A projects
Manager assigned Event A → cannot read Event B project
Manager → cannot modify student project
Manager → cannot create Manager/Developer
User → may read/write own project only
User → cannot read other team's project
```

- [ ] **Step 2: Run and see failure**

- [ ] **Step 3: Implement minimum event/membership models and authorization helpers**

Do not add generic ACL framework.

- [ ] **Step 4: Run permission tests**

- [ ] **Step 5: Commit**

**Acceptance gate:** object ownership is verified on the server; URL guessing does not bypass access.

---

### Task 4: Bulk team-account provisioning

**状态：已在 M2 完成。** Event status policy 遵循 Master O-006：DRAFT 允许 provisioning，PURGED 拒绝，ACTIVE 在 Product Owner 确认最终政策前暂时 fail-closed 并返回 PROVISIONING_STATUS_POLICY_GAP。

**Files:**
- Create: `competitions/provisioning.py`
- Create/modify: account import form/view/template
- Create: `tests/application/test_bulk_provisioning.py`

**Interfaces:**
- Consumes: CompetitionEvent, User roles.
- Produces: parsed preview + transactional confirm.

- [ ] **Step 1: Write tests for username generation**

```python
def test_username_is_date_plus_two_digit_team_number():
    assert make_team_username(date(2026, 11, 7), 1) == "2026110701"
```

- [ ] **Step 2: Add validation tests**

Must cover:

- duplicate team number in same batch
- duplicate existing username
- malformed team number
- missing captain student ID
- unauthorized Manager
- Manager attempting privileged role creation

- [ ] **Step 3: Add transaction test**

One invalid confirmed row must create **zero** users.

- [ ] **Step 4: Implement parse → preview → confirm service**

At confirm:

- re-check authorization
- recompute validation
- set password through Django hashing
- set `must_change_password=True`
- never write plaintext credential to audit log

- [ ] **Step 5: Run tests and commit**

**Acceptance gate:** all-or-nothing behavior is proven by test.

---

### Task 5: Material / Strip persistence and basic validation

**Files:**
- Create/modify: `materials/models.py`
- Create: `tests/application/test_materials.py`

**Interfaces:**
- Produces project/team-scoped Material and Strip records.
- Units are fixed by contract, not user-selectable.

- [ ] **Step 1: Write Material invariant tests**

Check:

- E > 0
- density >= 0 when present/required
- strip width > 0
- strip thickness > 0

- [ ] **Step 2: Implement minimal models/forms**

Do not introduce global template marketplace.

- [ ] **Step 3: Run tests and commit**

**Acceptance gate:** invalid mechanics parameters cannot silently reach analysis.

---

### Task 6: Pure Section Engine — rectangles first

**Files:**
- Create: `mechanics/sections/model.py`
- Create: `mechanics/sections/validation.py`
- Create: `mechanics/sections/properties.py`
- Create: `tests/mechanics/benchmarks/sections/test_rectangle.py`

**Interfaces:**
- Produces `SectionProperties(A_mm2, centroid_x_mm, centroid_y_mm, Ix_mm4, Iy_mm4, mass_per_length_g_per_mm, ...)`.

- [ ] **Step 1: Write exact rectangle benchmark**

Use closed-form:

```text
A = b h
Ix = b h^3 / 12
Iy = h b^3 / 12
```

- [ ] **Step 2: Run test → FAIL**

- [ ] **Step 3: Implement the minimum rectangle section function**

No Django imports.

- [ ] **Step 4: Run benchmark → PASS**

- [ ] **Step 5: Commit**

**Acceptance gate:** benchmark output matches analytical formula within specified tolerance.

---

### Task 7: Composite Section Engine

**Files:**
- Modify: `mechanics/sections/model.py`
- Modify: `mechanics/sections/properties.py`
- Create: `tests/mechanics/benchmarks/sections/test_composite.py`

**Interfaces:**
- Consumes explicit strip rectangles with local position/orientation.
- Produces composite A, centroid, Ix, Iy, mass/length.

- [ ] **Step 1: Add symmetric composite benchmark**
- [ ] **Step 2: Add asymmetric composite benchmark**
- [ ] **Step 3: Verify failures**
- [ ] **Step 4: Implement area-weighted centroid and parallel-axis theorem**
- [ ] **Step 5: Verify benchmarks**

Do not implement overlap subtraction/union unless `O-SECTION-01` has been decided.

- [ ] **Step 6: Commit**

**Acceptance gate:** B/S01 benchmark set passes.

---

### Task 8: Physical model persistence and whole-draft save

**Files:**
- Create/modify: `modeling/models.py`
- Create: `modeling/services.py`
- Create: `modeling/views.py`
- Create: `tests/application/test_model_draft_save.py`

**Interfaces:**
- Produces mutable Project Draft entities:
  - GeometryNode
  - PhysicalMember
  - Connection
  - Support
  - NodeLoad
- JSON save uses `expected_draft_version`.

- [ ] **Step 1: Write version-conflict test**

A save with stale `expected_draft_version` must not overwrite newer server state.

- [ ] **Step 2: Write topology persistence tests**

Prove that line intersection alone creates no Connection.

- [ ] **Step 3: Implement full-draft transactional save**

Do not create per-node REST CRUD.

- [ ] **Step 4: Run tests and commit**

**Acceptance gate:** draft save is atomic and concurrency conflicts are explicit.

---

### Task 9: Implement resolved Roller contract

**Precondition met:** Master O-002 confirms restrained global X/Y only.

**Files:**
- Update relevant spec/ADR first.
- Then modify Support persistence and JSON validation tests.

**Required outcome:** one unambiguous P0 representation of Roller restraint.

If decision is still absent, **stop this task**. Do not invent arbitrary-angle support behavior.

---

### Task 10: Immutable Physical Snapshot and ModelRevision

**Files:**
- Create: `modeling/snapshot.py`
- Create/modify: `analysis/models.py`
- Create: `analysis/hashing.py`
- Create: `tests/contracts/test_model_revision.py`

**Interfaces:**
- Produces `physical-snapshot-v1` canonical immutable snapshot.
- Produces deterministic input/model hash.
- Produces immutable ModelRevision.

- [ ] **Step 1: Write immutability test**

Changing live Material/Section/Project draft after revision creation must not alter revision snapshot.

- [ ] **Step 2: Write deterministic hash test**

Same canonical content in different dictionary key order must yield same hash.

- [ ] **Step 3: Implement canonical serialization + hash**

Do not hash ORM repr.

- [ ] **Step 4: Run tests and commit**

**Acceptance gate:** historical analysis inputs remain reproducible until purge.

---

### Task 11: Pure Truss domain objects and input validation

**Files:**
- Create: `mechanics/truss2d/model.py`
- Create: `mechanics/truss2d/errors.py`
- Create: `mechanics/truss2d/validation.py`
- Create: `tests/mechanics/unit/test_truss_validation.py`

**Interfaces:**
- Produces:
  - TrussModel
  - Node
  - Member
  - Support
  - NodalLoad
  - ValidationIssue

- [ ] **Step 1: Write failure tests**

Cover:

- empty model
- unknown node reference
- duplicate IDs
- zero-length member
- invalid/nonfinite E
- invalid/nonfinite A
- no support
- obvious insufficient restraint case
- duplicate analysis member policy

- [ ] **Step 2: Run → FAIL**
- [ ] **Step 3: Implement validation only**
- [ ] **Step 4: Run → PASS**
- [ ] **Step 5: Commit**

**Acceptance gate:** invalid contract inputs fail with stable machine-readable codes.

---

### Task 12: Truss element stiffness and global assembly

**Files:**
- Create: `mechanics/truss2d/assembly.py`
- Create: `tests/mechanics/unit/test_truss_stiffness.py`
- Create: `tests/mechanics/unit/test_truss_assembly.py`

**Interfaces:**
- Consumes validated TrussModel.
- Produces global K, load vector and deterministic DOF map.

- [ ] **Step 1: Write known element stiffness benchmark**
- [ ] **Step 2: Test symmetry and E/A/L scaling**
- [ ] **Step 3: Run → FAIL**
- [ ] **Step 4: Implement minimum element/global assembly**
- [ ] **Step 5: Run → PASS**
- [ ] **Step 6: Commit**

**Acceptance gate:** assembly tests pass without any Django setup.

---

### Task 13: Linear solve, reaction recovery and axial force recovery

**Files:**
- Create: `mechanics/truss2d/solver.py`
- Modify: `mechanics/truss2d/postprocess.py`
- Create: `tests/mechanics/benchmarks/truss2d/test_single_bar.py`

**Interfaces:**
- Produces:
  - NodeDisplacement
  - SupportReaction
  - MemberAxialForce
  - diagnostics
- Sign convention:
  - `N > 0` tension
  - `N < 0` compression

- [ ] **Step 1: Write B/T01 analytical benchmark**
- [ ] **Step 2: Verify fail**
- [ ] **Step 3: Implement restrained DOF solve**
- [ ] **Step 4: Implement reaction recovery**
- [ ] **Step 5: Implement axial force recovery**
- [ ] **Step 6: Run benchmark**
- [ ] **Step 7: Commit**

**Acceptance gate:** `δ = PL/EA`, reaction, force and sign convention pass.

---

### Task 14: Truss benchmark gate B/T02–B/T04

**Files:**
- Create benchmark fixtures and tests under `tests/mechanics/benchmarks/truss2d/`.

**Interfaces:**
- No new public production interface unless a failing benchmark exposes a defect.

- [ ] **Step 1: Add simple triangular truss expected results**
- [ ] **Step 2: Add symmetric truss invariants**
- [ ] **Step 3: Add simple indeterminate truss trusted reference**
- [ ] **Step 4: Run full mechanics suite**
- [ ] **Step 5: Fix solver only if benchmark demonstrates a real defect**
- [ ] **Step 6: Commit benchmark fixtures and any verified fix**

**Acceptance gate:** B/T01–B/T04 pass at documented tolerances.

---

### Task 15: Pure post-processing — stress, mass and explicit-K Euler formula

**Files:**
- Modify/create: `mechanics/truss2d/postprocess.py`
- Create: `mechanics/stability/euler.py`
- Create:
  - `tests/mechanics/unit/test_stress_mass.py`
  - `tests/mechanics/benchmarks/stability/test_euler_explicit_k.py`

**Interfaces:**
- `stress = N/A`
- `mass = density A L`
- `Pcr = π² E I / (K L)²`

- [ ] **Step 1: Write stress sign tests**
- [ ] **Step 2: Write mass unit-consistency test**
- [ ] **Step 3: Write Euler explicit-K benchmark**
- [ ] **Step 4: Implement minimum pure functions**
- [ ] **Step 5: Run tests**

Do **not** implement automatic K/default risk bands.

- [ ] **Step 6: Commit**

**Acceptance gate:** formula-level Euler works only with explicit K; product policy remains gated.

---

### Task 16: Truss Idealizer and physical-analysis mapping

**Files:**
- Create: `idealization/physical.py`
- Create: `idealization/truss2d.py`
- Create: `tests/idealization/test_truss_idealizer.py`

**Interfaces:**
- Consumes immutable Physical Snapshot.
- Produces:
  - TrussModel
  - analysis→physical mapping
  - physical→analysis mapping
  - idealization warnings

- [ ] **Step 1: Test no implicit joint at crossing**
- [ ] **Step 2: Test explicit Connection creates shared analysis node**
- [ ] **Step 3: Test one PhysicalMember split by intermediate Connection maps to multiple Truss members**
- [ ] **Step 4: Implement minimal mapping**
- [ ] **Step 5: Run tests and commit**

**Acceptance gate:** the three core physical/analysis invariants are executable tests, not documentation only.

---

### Task 17: AnalysisRun orchestration and SolverVersion traceability

**Files:**
- Modify: `analysis/models.py`
- Create/modify: `analysis/services.py`
- Create: `analysis/serialization.py`
- Create: `tests/application/test_analysis_service.py`

**Interfaces:**
- `AnalysisService.analyze(project_id, draft_version, actor, prediction_id=None)`
- Produces immutable ModelRevision if needed + AnalysisRun.

- [ ] **Step 1: Test authorization before analysis**
- [ ] **Step 2: Test stale draft version rejection**
- [ ] **Step 3: Test validation failure persists structured run/log state**
- [ ] **Step 4: Test success links revision + solver version + input hash**
- [ ] **Step 5: Implement orchestration in service layer**
- [ ] **Step 6: Run tests and commit**

Do not solve mechanics in Django view.

**Acceptance gate:** same revision may have multiple runs without mutating revision.

---

### Task 18: Model Check and beginner-facing error mapping

**Files:**
- Create/modify: `learning/insights.py`
- Create: `analysis/views.py`
- Create: `tests/application/test_model_check_messages.py`

**Interfaces:**
- Consumes stable ValidationIssue codes.
- Produces student-facing messages and entity refs.

- [ ] **Step 1: Test `SINGULAR_GLOBAL_STIFFNESS` mapping**
- [ ] **Step 2: Test raw error code remains available**
- [ ] **Step 3: Implement deterministic message catalog**
- [ ] **Step 4: Verify no solver result mutation**
- [ ] **Step 5: Commit**

**Acceptance gate:** student message can evolve without changing solver code.

---

### Task 19: Minimum JSON endpoints

**Files:**
- Modify: `modeling/urls.py`, `modeling/views.py`
- Modify: `analysis/urls.py`, `analysis/views.py`
- Modify: `materials/urls.py`, section preview view
- Create: `tests/integration/test_json_endpoints.py`

**Endpoints:**
- `POST /projects/<id>/model/save/`
- `POST /projects/<id>/model/check/`
- `POST /projects/<id>/analyze/`
- `GET /projects/<id>/analyses/<run_id>/data/`
- `POST /projects/<id>/sections/preview/`

- [ ] **Step 1: Test server-side ownership for every endpoint**
- [ ] **Step 2: Test content/schema errors**
- [ ] **Step 3: Implement thin views calling services**
- [ ] **Step 4: Run integration + permission tests**
- [ ] **Step 5: Commit**

**Acceptance gate:** endpoints contain no mechanics mathematics.

---

### Task 20: Basic server-rendered project workflow

**Files:**
- Templates/views/urls for:
  - login
  - password change
  - events
  - projects
  - materials
  - sections
  - prediction
  - model editor shell
  - results
  - reflection
  - report

**Interfaces:**
- Consumes application services and JSON endpoints.

- [ ] **Step 1: Add Django client smoke tests for required pages**
- [ ] **Step 2: Implement minimum navigation/workflow**
- [ ] **Step 3: Ensure model editor JS has no authoritative mechanics**
- [ ] **Step 4: Run tests and commit**

**Acceptance gate:** a team can move through the P0 workflow without requiring SPA infrastructure.

---

### Task 21: Result visualization data and deterministic TeachingInsight

**Files:**
- Create/modify: `learning/services.py`
- Create result serializers
- Modify result template/JS
- Create: `tests/application/test_teaching_insights.py`

**Required first-layer answers:**

- where force enters
- how supports react
- primary tension members
- primary compression members
- maximum displacement
- compression members needing stability attention, once approved data exists

- [ ] **Step 1: Write source-metric traceability tests**
- [ ] **Step 2: Implement deterministic insight extraction**
- [ ] **Step 3: Keep professional numeric tables in deeper result layer**
- [ ] **Step 4: Run tests and commit**

Euler risk wording remains constrained by `O-MECH-01`.

---

### Task 22: Prediction, comparison, rationale and reflection

**Files:**
- Modify: `learning/models.py`, `learning/services.py`, views/templates
- Create: `tests/application/test_learning_cycle.py`

**Interfaces:**
- Prediction is stored before analysis.
- DesignRationale may link `from_revision → to_revision`.
- Reflection may reference comparison/analysis context.

- [ ] **Step 1: Test Prediction persistence before Analyze**
- [ ] **Step 2: Test two revisions can be compared**
- [ ] **Step 3: Test rationale does not alter analysis result**
- [ ] **Step 4: Implement minimum workflow**
- [ ] **Step 5: Commit**

If Product/Teaching later decides Prediction is a blocking gate, update the application test first.

---

### Task 23: Calculation-report data package

**Files:**
- Create/modify: `reports/services.py`, views/templates
- Create: `tests/application/test_report_package.py`

**Interfaces:**
- Produces structured report data, not an auto-written design argument.

- [ ] **Step 1: Test inclusion of model assumptions, materials/sections, loads/supports, member force/stress, displacement, mass and stability data where available**
- [ ] **Step 2: Test missing student rationale is reported as incomplete rather than fabricated**
- [ ] **Step 3: Implement report package**
- [ ] **Step 4: Commit**

**Acceptance gate:** platform assists “寫得出” without authoring the student's design reasoning.

---

### Task 24: Event lifecycle and purge service

**Files:**
- Modify: `competitions/models.py`
- Create: `competitions/purge.py`
- Create: `competitions/management/commands/purge_due_events.py`
- Create: `tests/purge/test_purge_service.py`

**Interfaces:**
- Lifecycle: `DRAFT → ACTIVE → FINISHED_GRACE → PURGED`.
- Purge removes operational project data.
- Purge is idempotent.

- [ ] **Step 1: Write lifecycle transition tests**
- [ ] **Step 2: Write purge due-date test**
- [ ] **Step 3: Write idempotency test**
- [ ] **Step 4: Write raw-data deletion test**
- [ ] **Step 5: Implement PurgeService**
- [ ] **Step 6: Run twice and verify second run is safe**
- [ ] **Step 7: Commit**

Do not auto-delete or disable User account until Master O-004 is confirmed. Project Operational Data purge is confirmed and is not blocked by the account lifecycle decision.

---

### Task 25: Anonymous research-derived metric extraction

**Files:**
- Create/modify: `research/models.py`
- Create: `research/services.py`
- Create: `tests/purge/test_research_retention.py`

**Interfaces:**
- Consumes approved operational metrics before purge.
- Produces non-reconstructive anonymous derived records.

- [ ] **Step 1: Write allowed-field test**
- [ ] **Step 2: Write forbidden raw-data test**

Explicitly reject retention of:

```text
full node coordinates
full connectivity
full loads/support snapshot
captain student ID
original team login identity
complete raw model snapshot
```

- [ ] **Step 3: Implement extraction**
- [ ] **Step 4: Run purge + retention test**
- [ ] **Step 5: Commit**

**Acceptance gate:** research storage cannot reconstruct the purged student project.

---

### Task 26: Full P0 integration gate

**Files:**
- Add/modify integration fixtures only as necessary.
- No new product features in this task.

- [ ] **Step 1: Run pure mechanics suite**

```bash
pytest tests/mechanics -v
```

- [ ] **Step 2: Run contract/idealization suite**

```bash
pytest tests/contracts tests/idealization -v
```

- [ ] **Step 3: Run permission/purge suite**

```bash
pytest tests/permissions tests/purge -v
```

- [ ] **Step 4: Run application/integration suite**

```bash
pytest tests/application tests/integration -v
```

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

- [ ] **Step 6: Perform manual acceptance path**

```text
Login
→ forced password change
→ Event
→ Project
→ Material / Strip / Section
→ Truss model
→ Support
→ Node load
→ Model Check
→ Predict
→ Analyze
→ System View
→ Modify
→ Compare
→ Reflect
→ Report
```

- [ ] **Step 7: Verify no P0 leakage**

Search repository for premature:

```text
FRAME_2D
Fixed support behavior
rz
member UDL solver logic
V/M recovery
3D
generic FEM element framework
```

Allowed references are documentation/enums/future seam only, not implemented mechanics.

- [ ] **Step 8: Commit release-candidate baseline**

**Acceptance gate:** all P0 benchmark, permission, purge and workflow tests pass.

---

# C. Blocking Decision Map

The following tasks may proceed independently of Euler K:

- mechanics truss solver
- section properties
- physical model
- revisions
- authorization
- event lifecycle
- reporting without automatic K-derived risk policy

The following cannot be fully closed until decisions arrive:

| Decision | Blocks |
|---|---|
| MASTER_SPEC reconciliation | **Resolved — no longer blocking** |
| Euler K policy | automatic buckling screening UX/risk classification |
| Master O-003: FINISHED_GRACE User access (Open; read-only recommended only) | final event UX permission matrix; no permanent allow/deny edit/analyze assertions before confirmation |
| Account lifecycle after purge | account cleanup behavior |
| Composite overlap | overlap-capable free composite section implementation |

---

# D. Recommended Implementation Milestones

## Milestone M0 — Source-of-Truth Gate — COMPLETE

Delivered:

- `MASTER_SPEC.md v1.0` established
- architecture specs reconciled
- architecture state = `FINAL_FROZEN`

Implementation may proceed subject to scoped open gates.

## Milestone M1 — Trustworthy Mechanics Kernel

Tasks:

- 1, 6, 7, 11, 12, 13, 14, 15

Exit:

- Truss and Section benchmark gates pass
- explicit-K Euler formula benchmark passes
- no Django dependency in mechanics

## Milestone M2 — Secure Competition Skeleton

Tasks:

- 2, 3, 4, 5

Exit:

- roles/events/accounts work
- bulk account transaction tests pass
- forced password change cannot be bypassed

## Milestone M3 — Physical Model + Reproducible Analysis

Tasks:

- 8, 9, 10, 16, 17, 18, 19

Exit:

- intersection/connection invariant proven
- immutable revision + run traceability
- model check/analyze API works

## Milestone M4 — Teaching Workflow

Tasks:

- 20, 21, 22, 23

Exit:

- Predict → Analyze → Explain → Compare → Reflect → Report works
- no AI mechanics authority
- no fabricated design rationale

## Milestone M6 — Calculation Report Assistance — COMPLETE

Goal:

- organize authoritative engineering facts from one explicit `AnalysisRun` into an online calculation-report data package;
- preserve provenance through `ModelRevision`, Physical Snapshot, `SolverVersion`, and `InputHash`;
- keep historical reports viewable but mark them `STALE` after later draft edits;
- preserve student authorship for design reasoning and conclusions;
- avoid mechanics recomputation, AI-generated rationale, Euler automatic reporting, and export-format commitment.

Gates:

- Gate 0 — Report Contract Freeze — COMPLETE
- Gate 1 — Authoritative Report Package — COMPLETE
- Gate 2 — Completeness + Limitation — COMPLETE
- Gate 3 — Report Workspace — COMPLETE
- Gate 4 — Student-authored Reasoning Boundary — COMPLETE
- Gate 5 — Acceptance + Reconciliation — COMPLETE

Detailed scope, data blocks, authority, completeness states, non-goals, open-decision impact, and acceptance boundaries are defined in `CALCULATION_REPORT_ASSISTANCE_SPEC.md`.

## Future milestone candidate — Lifecycle / Research / PoC Gate (UNFROZEN)

Tasks:

- 24, 25, 26

Exit:

- purge idempotency
- approved anonymous retention only
- full test suite passes
- manual P0 workflow passes

This historical grouping must not be read as M5 or M6. Its Tasks 24–26 remain future/unfrozen work pending explicit sequencing and the relevant open decisions.

---

# E. Codex Guardrails

When this plan is executed by Codex:

1. Read the relevant spec before each task.
2. Do not reinterpret a `Recommended` item as an approved product expansion.
3. Stop at any `Open Decision` that changes public behavior.
4. If a spec conflict appears, create a conflict note instead of silently choosing.
5. Use tests as gates before editing mechanics behavior.
6. Do not weaken benchmark tolerance merely to make a failing test green.
7. Do not add dependencies unless the task cannot be completed with the baseline stack.
8. Do not refactor unrelated modules while implementing a task.
9. Keep commits small and reversible.
10. Never claim a mechanics feature is correct without benchmark evidence.

---

# F. Definition of P0 Architecture-Conformant Completion

The implementation is P0-complete only when:

- `TRUSS_2D` is the only implemented analysis kernel.
- core benchmark suite passes.
- Section Engine is independently tested.
- Physical and Analysis models remain separate.
- every AnalysisRun traces to immutable ModelRevision + SolverVersion + InputHash.
- server-side permission tests pass.
- Event purge tests pass and research retention is non-reconstructive.
- beginner-facing validation is layered above stable mechanics codes.
- TeachingInsight is derived from explicit metrics.
- the student workflow reaches calculation-report assistance.
- no hidden Frame-first, 3D, optimization or generic FEM scope entered P0.

---

## Approved reconciliation — Master O-001

**MECHANICS REVIEW REQUIRED**: Master O-001 includes effective length factor K, default/automatic K inference, controlling I / weak-axis selection policy, final risk bands and related beginner-facing wording. None is implicitly approved. M1 may verify `Pcr = π² E I / (K L)²` using explicit E, I, L and K; numerical section properties do not authorize automatic buckling-axis selection. Automatic product behavior remains blocked.
