# ISSA Results / AV-01 UI Integration Plan

> **For agentic workers:** Use superpowers:executing-plans inline; one independent final code review. Owner authorized direct implementation of approved v1.1. Do not request visual replanning approval.

**Goal:** Integrate R01/R02 and Results toolbar/layers/legend/responsive presentation using genuine Saved Run data.
**Architecture:** Keep readonly renderer, projection validation, run epoch/token and all data/permission contracts. Reorganize existing generated DOM and styles; use shared tokens/controls/icons. SVG geometry derives exclusively from existing view DTO, with screen-space glyphs and separate existing hit targets.
**Tech Stack:** Django, vanilla JS/CSS/SVG, pytest/Playwright; no dependency/CDN.
**Spec:** User Phase2B-2 scope; MASTER_SPEC v1.12 readonly; Design7933932 inventory/system/redesign/graphics/icons/handoff. Product base5dd2f7d.

## Global Constraints
- No Solver/Mechanics/Schema/Permissions/AnalysisRun/Revision/spec changes. Saved Run only; no Draft fallback or synthetic production fixtures.
- Preserve force signs, per-load rows, original/deformed positions, AUTO/maximum, exact tiny nonzero/zero, MIXED segments, warning/partial/unavailable and epoch cleanup.
- Preserve CAD focus isolation and Phase2B1 ?/XY key. Keep50442/50584/50586 untouched.
- New private50588/DB/cookies; no merge/push/deploy. Simplified Chinese UI.

## Review Focus
- 1024x768: viewport canvas and scrollable Inspector must not cover symbols or primary controls; short/narrow screen falls back to vertical document flow.
- Dense force annotations: existing overflow warning and exact numeric fallback remain reachable; symbol changes must not shrink hit domains.
- Run switch clears all old selections/hover/evidence; reorder must not detach focused controls or introduce reparent loops.
- Partial facts and missing teaching view: disable only unavailable layers, retain saved geometry/forces and notices.
- Tiny nonzero versus true zero: rounded conclusion must never display a nonzero displacement as exact zero.

### Task 1 — R01 shell and engineering drawing
- [x] Baseline targeted tests and real Saved Run Before3sizes on private runtime.
- [x] New UI/layout assertions RED; integrate shared controls/icon sprites and Results layout with main canvas +268/300/324px rail.
- [x] Refine node/support/force/ghost/dimension/axis drawing only from saved view; retain hit, direction, normalization and warnings.
- [x] Related targeted verification; independent local commit.

### Task 2 — R02 evidence hierarchy
- [x] New evidence hierarchy/precision tests RED.
- [x] Conclusion then object evidence then full values; layers/list/legend locally scroll, exact tables remain accessible. Keep original hooks and focus behavior.
- [x] Relevant targeted tests pass; local commit.

### Task 3 — final bounded QA and handoff
- [x] One related Browser Regression: AV01 reaction/deformation/layers/evidence/run integration plus Build/shared SSR smoke.
- [x] Final real Saved Run screenshots3sizes; retain failures and related bounded reruns only.
- [x] Fresh independent code review; fix important findings, preserve original5 dirty hashes and other worktree heads/status.
- [x] R01/R02 coverage, QA limits, screenshot comparison, private runtime, Phase2C handoff; final local commit and STOP.


## Execution record

- Task1/2 share generated DOM/mount layout; delivered as one reversible product commit3a91105 instead of splitting mutually dependent shell/evidence code. No data authority/state machine changes.
- Initial167 targeted baseline; UI RED; 179 targeted pass; initial203 related Browser185pass/18fail. No Full Browser/Mechanics run.
- Fixed locator ambiguity with explicitCanvas hook, retained original neutral force-off and Tab contract, file-backed QA DB isolated concurrency. Bounded45pass. Product settings unchanged.
- Independent reviewer found only narrow/short panel480px cap; real4cases RED→GREEN; fixcommitd7f3773.
- Added empty Results state RED→GREEN to keep Draft canvas out of unselected saved-result stage. No API or Run behavior changed.
- Final179 application/endpoint pass;14UI pass;54 real screenshot files; original5 dirty hashes and readonly source worktrees unchanged.
- Owner already directed keep worktree, no merge/push/deploy and STOP. Final evidence/runtime commit supplies Phase2C base.
