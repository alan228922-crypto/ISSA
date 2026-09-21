# POC V1 Product Reconciliation Design

## Status

- Design state: **FROZEN / PRODUCT OWNER APPROVED**
- Approved approach: **学生旅程纵向修复**
- Starting commit: `65926249c95627696e39a26e3eda5d50bdd0bdea`
- Working branch: `stabilize/poc-v1-product-reconciliation`
- Product authority: `docs/specs/MASTER_SPEC.md` v1.12 and its frozen specialist specs

## Goal

Reconcile the shipped POC V1 with the frozen product intent so a first-time structural-design student can complete the real browser journey from an empty Project through modeling, analysis, learning, calculation-report assistance, student reasoning, reflection, and historical reload without private-module calls or fixture-only shortcuts.

The repair remains a Django modular monolith with server-rendered templates, Vanilla JavaScript, SVG, existing application services, and the existing pure-Python mechanics kernel. No mechanics contract changes are authorized.

## Product boundaries

- Keep `TRUSS_2D`, 2D linear elastic, small displacement, ideal pin joints, axial-only members, nodal `Fx/Fy`, `ux/uy`, and mm/N/MPa/g unchanged.
- Do not infer Euler `K`, a controlling buckling axis, or buckling risk bands.
- Do not decide O-003, O-004, O-005, O-006, or T-M6-001/002/003.
- The minimum Section path uses the already validated rectangular definition and its authoritative computed `A`, `Ix`, `Iy`, and mass/length. It does not add overlap-capable composite editing.
- Do not add Frame, 3D, nonlinear mechanics, optimization, AI reasoning/scoring, export formats, reviewer workflow, a SPA framework, or a second CAD/mechanics authority.
- Historical learning and report state always binds an explicit `AnalysisRun`; there is no latest-run fallback.

## Starting evidence

- Runtime: Python 3.13.14, Django 5.2.17, SQLite, Playwright Chromium.
- Baseline non-browser suite: `465 passed, 32 deselected`.
- Baseline browser suite: `32 passed` when allowed to bind the pytest-django live server.
- Real browser smoke at 1024×900: owner session produced `read_only=false`; Model Check and Analyze succeeded; Compare and Explain controls were absent; the Report run selector did not learn about the just-created run until reload; the calculation-report table overflowed its panel.
- The existing browser “full journey” directly imports modules and calls reducers/services for key steps. It proves component behavior, not real product reachability.

## Product Gap Matrix

### P0 — Flow blockers

| ID | Area | Planned behavior | Current behavior / root cause | Chosen repair | Acceptance evidence |
|---|---|---|---|---|---|
| P0-01 | Blank Project / Materials / Sections | A student can create/select owned P0 material and section data, then create the first PhysicalMember from an empty Project. | Member creation clones `material_id` and `section_id` from the first existing member. No Material/Section UI or bootstrap choices exist. | Add owner-scoped Material and safe rectangular Section forms, expose available choices and an explicit current member profile in Workspace, and require that profile for first-member creation. | Real Playwright journey creates Material, Section, nodes, and first Member in an empty Project; save/reload preserves IDs and geometry. |
| P0-02 | CAD interaction | Frozen numeric grammar, Node/Endpoint/Intersection/Grid SNAP, ORTHO, and Fit are usable controls. | Parser/resolver/reducer functions exist but actual modeling events use raw pointer coordinates; dynamic input is permanently hidden; SNAP/ORTHO/Fit have no controls. | Wire the existing `cad-input.js`, `cad-state.js`, `geometry.js`, and `reduceView` authority into the visible toolbar/status/input flow. Do not duplicate geometry rules. | Playwright types absolute/relative/polar input, toggles SNAP/ORTHO, activates Fit, and verifies persisted coordinates. |
| P0-03 | Learning loop | Analyze → Results → Compare → Explain → Report → Reasoning → Reflection is reachable through UI. | Compare/Explain endpoints and helper functions exist, but no buttons invoke or render them. The old journey test calls functions directly. | Add explicit result-stage controls and renderers driven by the selected explicit run; connect report/reasoning/reflection to the same run context. | Real Playwright clicks every stage and verifies visible backend-derived output without `page.evaluate` state injection. |

### P1 — Product contract gaps

| ID | Area | Planned behavior | Current behavior / root cause | Chosen repair | Acceptance evidence |
|---|---|---|---|---|---|
| P1-01 | Identity / read-only | Project, Event, current identity, owner context, and read-only reason are understandable. | Owner is editable in runtime, but non-owner UI only says “只读查看”; a stale/wrong session is indistinguishable from an authorization bug. | Include safe identity and permission presentation in bootstrap/header, explain read-only without exposing role internals, and provide Events/logout navigation. | Owner and assigned reviewer browser scenarios assert toolbar state, identity, reason, and navigation. |
| P1-02 | Properties | Selected Node, Member, Connection, Support, and Load are understandable and frozen editable fields are exposed. | Panel shows identity only for Node/Member/Connection; only Support type and Load force edit. | Add Node coordinate/label, Member material/section/label/active, Connection relationship summary, Support, and Load controls. Relationship retargeting remains forbidden. | Real UI edits each supported kind, saves, reloads, and verifies persistence. |
| P1-03 | Delete | All five object kinds have safe deletion with no silent cascade. | Reducer supports dependency-aware delete, but no UI exposes it. | Add selected-object Delete with clear dependency-conflict messages; deletion marks dirty and persists only after Save. | Browser deletes unreferenced objects, observes dependency refusal, then saves/reloads. |
| P1-04 | Workflow guidance | The five stages communicate current progress and next action. | Workflow is a static ordered list; report sits outside the learning context. | Add visible stage state and explicit actions without introducing hard gates. Keep Prediction and Reflection optional. | Browser assertions verify active/completed/optional states through the journey. |
| P1-05 | Beginner results | Level 1 explains force transfer, maximum deformation, tension/compression, and places to reconsider without internal IDs. | Results lead with `connection:c2`, numerical precision noise, and a list of member states; support/load context and Why layer are absent. | Resolve stable keys to student labels, format values, present load/support/force-state summaries, and place raw tables under Engineering Details. | Browser sees student labels and learning summaries; internal keys remain only in DOM/state or technical disclosure. |
| P1-06 | Error presentation | Errors use zh-CN what/why/next-action; machine codes are secondary technical data. | Generic presenter appends machine code directly to the main message and gives weak action guidance. | Centralize code-specific safe copy and put the code in a collapsed technical disclosure. Preserve backend codes. | Browser triggers invalid/unstable/dependency/stale cases and sees actionable copy without raw exception data. |
| P1-07 | Report continuity | The explicit run returned by Analyze immediately enters Report workflow. | Run options load once at page start, so a successful run is absent until reload. | Refresh run discovery after success and select only the just-returned explicit run ID; never ask the server for “latest”. | Browser analyzes, opens that run’s report without reload, and verifies the selected ID. |
| P1-08 | Historical restore | Explicit historical run selection restores its Results, Report, Reasoning, and Reflection without cross-run leakage. | Report has a run selector; Results and Reflection are tied only to the in-memory just-analyzed run. | Promote explicit run selection to a shared history control; loading a run fetches its data and run-scoped learning/report records. Missing Reflection is a normal empty state. | Two-run browser test switches Run #1/#2 and verifies isolated values/text after reload. |
| P1-09 | Desktop usability | Workspace and Report are readable and operable at 1024px+. | Three narrow panels crowd controls; report tables/long assumptions overflow; important actions have weak hierarchy. | Rebalance columns, group controls, wrap/scroll technical tables locally, improve spacing and visible state, and keep the canvas practical at 1024px. | 1024×900 screenshots and DOM overflow assertions show no page-level horizontal overflow or obscured controls. |

### P2 — High-value UX quality gaps

| ID | Area | Gap | Repair decision |
|---|---|---|---|
| P2-01 | Entry pages | Login, forced-password, and Events pages are bare forms with no shared navigation/context. | Add a small shared product shell and clear help copy; preserve normal Django forms and password security. |
| P2-02 | Visual hierarchy | Native-button density and ungrouped learning controls make first use difficult. | Add purposeful groups, labels, status badges, and consistent control hierarchy without redesigning the visual identity. |
| P2-03 | Expected empty states | Missing Reflection returns an expected 404 that appears as a browser console resource error. | Treat “no Reflection yet” as an explicit normal read response at the Workspace boundary or otherwise avoid noisy failed-resource UX while preserving endpoint semantics where required. |

### P3 — Polish backlog

| ID | Area | Deferred item |
|---|---|---|
| P3-01 | Visual polish | Further iconography, animation, dense-table aesthetics, and mobile optimization remain backlog. |

## Architecture and data flow

### Entry and authorization presentation

Server-side authorization remains in `competitions.authorization` and application services. Workspace derives a presentation-only access context from the already authorized Project: current username, Event label, owner label, editable boolean, and a safe read-only explanation. UI visibility never grants authority; every mutation continues through existing server checks.

### Material and Section capability

Normal Django forms own create/edit operations. Material persists the existing owner-scoped fields with `E_MPa` and `density_g_per_mm3` required for this flow. Section creation calls the existing `create_section` service with a rectangular `section-definition-v1` definition; width, height, and density generate authoritative `A`, `Ix`, `Iy`, and mass/length. The UI may show these computed values but never accept `A` as an unverified solver override.

Workspace bootstrap includes only Materials and Sections belonging to the Project owner and a default profile when both exist. The student explicitly chooses the profile before drawing a member. A missing profile blocks only Member completion and links to the setup forms; Node creation remains available.

### CAD controller

One interaction controller owns tool state, active origin, pointer resolution, numeric fields, ORTHO, Grid Snap, Grid visibility, and Fit. It delegates parsing and state transitions to existing frozen modules. Valid numeric input bypasses SNAP. Pointer input collects stable candidates, passes through the existing resolver exactly once, and never creates a Connection from an intersection.

The property panel dispatches only existing editor actions. Delete invokes the current dependency matrix. All local edits remain dirty until whole-draft Save succeeds.

### Learning and historical run context

The Workspace has one explicit selected-run context. Analyze sets it from the response’s `analysis_run_id`; historical selection sets it from the run-discovery list. Loading a selected run fetches that run’s Results, Compare, Explain, Report, owner-only Reasoning, and eligible Reflection independently. No component queries or substitutes a latest run.

Compare and Explain are rendered only from their existing backend contracts. `NO_PREDICTION`, `UNSURE`, and `NOT_COMPARABLE` are normal learning states. Historical stale status remains informational, not an error.

### Error and result presentation

The server remains the source of codes and safe messages. A presentation map supplies outcome, cautious explanation, and next action. Unknown codes receive a safe generic message. Codes and safe details live in a collapsed technical disclosure.

Student labels prefer the object’s non-empty label, otherwise a consistent localized type plus normalized client key. Stable client keys and Analysis IDs remain unchanged for persistence and tracing.

## Testing design

- Each gap begins with a test that fails because the production path is absent or wrong.
- Endpoint/application tests cover owner scoping, foreign IDs, validation, authorization, and explicit run isolation.
- Component browser tests continue to protect pure CAD/reducer contracts.
- Product acceptance uses real Playwright controls: click, fill, select, Save, reload, and historical switching. It must not call reducers, private JS functions, or inject final draft/learning state.
- Mechanics benchmarks remain unchanged and run in regression.
- A 1024×900 browser scenario asserts usable controls and no page-level horizontal overflow.

## Logical repair batches

1. **Entry and blank-project foundation** — identity/read-only clarity, Material/Section setup, member profile, first-member flow.
2. **CAD completion** — numeric input, SNAP/ORTHO/Fit, properties, safe delete.
3. **Learning continuity** — Results, Compare, Explain, Report, Reasoning, Reflection, explicit historical restore.
4. **Beginner UX and acceptance** — result/error language, identifier cleanup, 1024px layout, genuine full-journey browser test, docs.

Each batch receives targeted RED→GREEN evidence and one logical commit. Documentation is updated only after verified behavior exists.

## Exit criteria

- P0 remaining: 0.
- P1 remaining: 0, except explicit policy/teacher-open items.
- Empty Project from zero: PASS.
- Real browser full journey using public controls: PASS.
- Read-only root cause and UX: resolved.
- Compare/Explain reachability: PASS.
- Historical run isolation and reload: PASS.
- 1024px desktop usability: PASS.
- Mechanics unchanged and benchmarks: PASS.
- Critical/Important review findings: 0.
- Required targeted, non-browser, browser, Django, migration, and diff checks: GREEN.
