# CAD Core Drawing V1 — Written Design Specification

## Authority, intent, and boundary

This specification records the Product Owner's approved CAD Core Drawing V1 Design Review and final decisions D-CAD-CORE-01 and D-CAD-CORE-02. The baseline is clean `main@9c45ace` with `physical-draft-v2` as the default for new Projects. The student should be able to choose **构件**, click a start, click an end, and obtain a structural member without first learning a CAD command language or separately placing endpoint Nodes. This is a student-first structural sketch, not an AutoCAD clone.

The package covers Grid display, 1 mm Grid Snap, ORTHO and temporary Shift inversion, NODE/INTERSECTION Object Snap, progressive Dynamic Input and numeric entry, blank-space Member start, cursor-centered wheel zoom, transparent middle-button pan, and the minimal status needed to explain them. It does not change canonical mechanics units `mm / N / MPa / g`, Solver, analysis, Draft schema, save protocol, or historical revisions. It must preserve the Node-as-Joint rule: **“有节点才连接；没有节点，交叉也不连接。”** A joint is a stable Node identity plus explicit member endpoint references or intermediate `MemberJointIncidence` records. Geometric proximity alone is never topology authority.

The approved architecture is **Approach B: a lightweight Interaction Controller with pure geometry/snap helpers**. Continuing to add conditions to the present canvas/modeling handlers (A) would increase gesture and state coupling. A full CAD command subsystem (C) would broaden scope and impose unnecessary concepts on beginners. The controller is a bounded coordinator, not a second editor or Draft store.

## Existing seams and ownership

The current main already has one-millimeter `GRID_SPACING`, SVG pattern-based 1/10/100 mm visual grid, `resolvePointerPoint`, Node/Intersection candidate discovery, a v2 editor reducer, transient CAD presentation, X/Y Node input, length/angle precision controls, wheel zoom, and middle pan. These are starting seams, not independent authorities. The current Member flow requires an existing Node at the start and may rediscover an endpoint Node by coordinate; the approved design replaces both behaviors. Current wheel handling passes browser client coordinates into SVG-local view math; the new coordinate boundary removes that mix. Current Object Snap can return an off-axis candidate before ORTHO; the new resolver must enforce ORTHO before accepting a candidate.

Responsibilities are fixed as follows:

| Unit | Owns | Must not do |
| --- | --- | --- |
| Interaction Controller | Active tool, pointer gesture, pending start, snap resolution, dynamic-input draft, preview, and event priority | Persist Draft, infer structural connection, implement Solver rules |
| Coordinate/geometry helpers | Pure client↔SVG-local↔world transforms, constrained point calculation, screen-distance measurement, typed snap resolution | Mutate Draft or DOM |
| `grid.js` | The sole `GRID_SPACING = 1 mm`, rounding rule, visual LOD decisions | Derive topology or viewport Fit |
| `cad-input.js` | Pure parsing/validation of decimal, relative, length/angle numeric input | Commit a point or modify Draft |
| `joint-candidates.js` and candidate index | Discover nearby Node, member, and geometric intersection candidates; expose stable source identities | Author incidences, silently merge equal-coordinate Nodes |
| `editor-v2.js` | Validate and atomically author confirmed Nodes, PhysicalMember, and explicit incidences as one Draft transition | Read cursor pixels, use renderer state, silently resolve ambiguous identities |
| `renderer.js` | Read-only grid, structural objects, preview and pointer-inert snap feedback | Decide or modify topology |
| Existing state/history/save layer | Committed Draft, one history entry per editor action, existing versioned save | Persist pending clicks or preview |

The controller should be split into a small event/state coordinator and reusable pure helpers; it must not become a new monolithic `editor.js`. Legacy v1 Draft readers and existing out-of-scope selection/edit controls remain compatible, but do not create a second v2 connection model.

## State model and lifecycle

Committed Draft and view transform remain distinct. Interaction state has: `activeTool`; `gesture` (`NONE` or `MIDDLE_PAN`, with client/SVG-local last point); optional `pendingMemberStart`; latest typed `snapResolution`; uncommitted `dynamicInput`; `preview`; and `temporaryOrtho`. A pending start contains either `{kind: EXISTING_NODE, nodeClientKey, worldPoint}` or `{kind: PROVISIONAL_POINT, worldPoint}`, together with the Draft version/identity against which it was resolved. It is **not** a `GeometryNode`, is never added to the Draft, does not enter save/analysis/history, and is cleared on Esc, tool change, cancel, or a stale-Draft invalidation. A changed Draft requires re-resolving or explicitly cancelling a stale pending start before commit; never reinterpret its coordinates as a different Node.

The Member tool begins in `WAITING_FOR_START`. The first confirmed left click or numeric point stores a pending start, including an empty-space point. A live member preview then follows the resolved endpoint. The second confirmed point requests one atomic editor action. On success, the preview/input/start clear, the Member tool stays active, and state returns to `WAITING_FOR_START`. **There is no automatic chaining** from the prior endpoint. On failure, the Draft and history remain unchanged; the pending start and useful input remain available for correction unless the user cancels. A zero-length member or identical start/end Node identity is rejected before commit.

The Node tool remains necessary for independent Nodes, Nodes in a member interior, and explicit conversion of a geometric crossing to a structural Joint. Hover, preview, marker display, wheel, pan, and the first Member click cannot dispatch an editor topology action.

## Atomic Member creation and topology guard

The second point submits one v2 editor action containing typed start/end references or provisional world points, chosen material/section fields under the existing member-profile rules, and one requested PhysicalMember identity. The reducer validates the entire proposed result before returning a new Draft. For blank–blank it creates two endpoint Nodes and one PhysicalMember in **one action and one history entry**; for one or two NODE-snapped endpoints it uses their exact `nodeClientKey` and creates only missing endpoints. No commit path may use nearest-coordinate search to replace a selected Node identity. Exact coordinate equality is not identity; an ambiguous same-location legacy identity blocks the action with an explanation rather than choosing silently. Numeric input follows the same commit rule.

The editor must add every required explicit intermediate incidence when the new Member strictly passes through an existing normal v2 Node. Creating an endpoint Node on the interior of one existing member must author that existing member's incidence in the same atomic edit, with clear pre-commit feedback. The same editor action verifies all newly introduced Node/member pass-through relations, including provisional start/end Nodes; it cannot leave a visible normal v2 Node on a member without explicit participation. A new Member crossing another member **without a Node** does not create a Joint or incidence. The editor, not candidate discovery, determines all strict pass-throughs using the v2 geometry validation contract. On failed validation, no partial Node, Member, incidence, or history entry remains. Undo of a successful action removes exactly its newly created Nodes, Member, and incidences together; redo reapplies the same identities. Save/reload preserves those identities and relations.

There is an important guard at an unjoined crossing. If either provisional Member endpoint would lie at a point where **two or more pre-existing members pass but no Node exists**, the Member operation must not secretly join those pre-existing members. The controller rejects that point as a Member start or end and explains “此处是尚未连接的构件交点；请先用「节点」工具建立连接”; the v2 editor action independently rejects it if reached through another caller or a stale preview. The Draft remains unchanged. This guard applies whether that coordinate came from INT Snap, Grid Snap, or numeric input. A snapped existing NODE at the same location is different: its real identity is used, and normal v2 incidence rules apply. Placing a Node there with the Node tool is the explicit confirmation that authors incidences for **all** strictly passing members. This resolves the apparent tension between “Member endpoint at INT does not automatically connect the old crossing” and the v2 invariant that every visible normal Node on a passing member must participate. No hidden detached Node or new legacy exception is created.

Existing incomplete Draft semantics remain: unrelated nullable fields may remain incomplete and Analyze continues to block them; this package does not make geometry-only topology or server-side repair acceptable. Structural contradictions and ambiguous overlap are rejected, not saved as an incomplete member.

## Coordinate and view authority

The single coordinate pipeline is browser `client` point → SVG-local point via the SVG screen CTM inverse → world mm via the current view-transform inverse. World mm → SVG-local → browser client uses the corresponding forward transforms. The same adapter supplies pointer readout, Grid/OSNAP resolution, preview, dynamic input, wheel anchor, pan delta, and hit-radius conversion. `clientX/Y` must never be passed directly into world or `viewBox` math. A missing/non-invertible CTM or non-finite coordinate cancels that gesture with visible feedback; it must not commit a guessed point.

`reduceView` accepts SVG-local anchors and deltas only. Wheel zoom converts the current client pointer to SVG-local first. Pan converts two client points to SVG-local and subtracts them; it does not add raw CSS-pixel deltas to a user-space transform. Toolbar plus/minus uses the center of the **visible canvas** converted to SVG-local, not fixed `(500,300)`. Fit uses model bounds and visible viewport, never Grid spacing. Pointer-facing sizes and tolerances are measured in CSS pixels after the full SVG-to-client transform (including responsive `viewBox` scaling), rather than assuming one transform unit equals one pixel.

## Grid, constraints, and Object Snap

`GRID_SPACING = 1 mm` remains the only logical Grid and Grid Snap authority. Existing SVG patterns supply minor 1 mm, medium 10 mm, and major 100 mm visuals with zoom-aware LOD and pointer-events disabled; no per-millimeter SVG lines are created. Hiding minor lines does not alter snapping. Grid display and Grid Snap toggles are independent. Grid Snap ON rounds the movable coordinate according to the existing resolver's tie-breaking; OFF retains decimal mm. Explicit numeric values retain decimal precision and are not silently rounded by Grid or ORTHO.

For a Member endpoint under ORTHO, the pending start's exact world coordinate is the constraint origin. The dominant horizontal/vertical direction is chosen from pointer movement, then the locked axis stays **exactly** at that origin; Grid Snap may round only the moving axis. Thus `(12.4,7.6)` plus horizontal ORTHO and Grid Snap may resolve to `(13,7.6)`, never `(13,8)`. With Grid Snap OFF, the moving axis may remain decimal. Shift temporarily inverts the effective ORTHO state while drawing; the visible toggle remains the persistent state. Shift is ignored for this purpose while a dynamic/numeric input is focused, and temporary inversion clears on key release, blur, cancellation, or tool change.

Object Snap discovery uses a starting hit radius of approximately **10 CSS px**; reasonable adjustment within 8–12 px requires browser evidence. Among eligible candidates the priority is **NODE > INTERSECTION > GRID**. A NODE result contains its stable `nodeClientKey` and exact stored world point. An INTERSECTION result contains the source member identities and a geometric point; it is **not** a Joint. Candidate ties within a category are resolved deterministically and feedback identifies the selected candidate. If ORTHO is active, an off-axis NODE/INT candidate is ineligible, even when its screen distance is closer; show the actual constrained/Grid point instead. Direct clicks on a rendered Node follow the same constraint and identity resolution contract; they cannot bypass ORTHO through a separate DOM-target path. Neither a marker nor a tooltip may claim an object snap that the resolver did not choose. A snapped intersection or its hover never changes Draft topology. The Node tool's explicit confirmation is the sole operation that turns an unjoined crossing into a Node plus all passing incidences.

Markers are pointer-inert, visually distinct (`NODE` versus `INT`), and approximately constant CSS-pixel size across zoom; labels identify the real selected candidate. The intersection message is “几何交点，尚未连接；使用节点工具才会连接。” A GRID marker may be quieter but must still reflect the actual resolved point. Decorative support/load/axis/grid children remain outside candidate, selection, and topology authority.

## Dynamic input, keyboard, and status

The primary interaction is a cursor-adjacent, small numeric form. Before a Node placement or Member start it shows **X / Y**. After a Member start it shows **Length / Angle** first; Tab cycles the editable fields or a clearly labeled relative **ΔX / ΔY** mode. It does not display all six fields at once. The existing `@dx,dy` and similar syntax may remain in the collapsed advanced precision area for compatibility but is not required to learn the primary workflow. Input accepts finite signed decimal values; the UI displays `mm` and `°`, but typing unit characters is optional rather than required. Display values may be sensibly abbreviated, while the stored world coordinate must retain its actual decimal value.

Enter confirms the focused numeric field/current drawing step after validation. A length/angle or relative-coordinate entry resolves a provisional world point and then follows the same Node-identity, unjoined-crossing guard, and atomicity rules as pointer confirmation. Explicit numeric values use the existing precise-input semantics: they bypass pointer ORTHO/Grid/OSNAP adjustment and are not covertly snapped or rounded. Esc clears uncommitted input, pending point, and preview; it does **not** delete or undo a committed object. Enter-to-repeat-command and a full command-line workflow are not part of this package. Numeric fields own their typing, Shift, and function keys while focused; canvas shortcuts cannot steal them.

The existing bottom region should expose clickable **网格**, **网格吸附 · 1 mm**, **正交 · 仅水平/竖直**, **物件捕捉 · 节点/交点**, the active snap label, and **X / Y** in mm. Coordinates must not always be rounded to integers: when Grid Snap is OFF, the display shows enough decimal digits to distinguish the actual point from its nearest integer. Existing other status controls remain functional but are not redesigned here. Optional F7/F8/F9/F3 shortcuts map to Grid/ORTHO/Grid Snap/Object Snap respectively when the canvas owns focus; failure of an OS/browser to deliver an F-key cannot remove access because the buttons are primary.

## Pointer routing, zoom, and transparent pan

Event priority is: **(1)** middle-button pan and wheel zoom; **(2)** focused dynamic/numeric input; **(3)** active Node/Member drawing; **(4)** existing selection interactions. A view event cannot call the editor reducer. Left click on a resolved drawing point advances the current tool once; pointermove only resolves candidates and updates feedback. Existing selection/grip features are compatibility-tested, not redesigned.

Wheel uses an approximately 1.1 step and the current reasonable minimum/maximum scale. For any pointer over the canvas, the same world point should remain under that client position before and after zoom with at most **1 CSS px** screen drift, including an offset/responsive canvas and clamped zoom limits. Wheel outside the canvas or while editing an input must not unexpectedly alter Draft. Zoom changes presentation only.

Middle-button drag pans at any drawing step, including after a provisional Member start. It cannot cancel, commit, create a Node, alter the start, or modify Draft/history. Middle mouseup cannot become a left click. After each pan update and on release, feedback and Member preview are re-resolved against the **new** transform immediately, not one frame later. Existing double-middle Fit behavior, if retained, likewise changes only the view.

## Performance and accessibility

Grid DOM count must remain bounded as visible world size grows. Candidate discovery is cached/indexed by Draft identity or version and queried by a pointer-centered screen-radius world envelope; no pointermove may perform all-Nodes × all-Members work or globally sort all candidates. Nearby segment intersections may be computed on demand or cached per Draft; either way the index is only a discovery accelerator, never a connection authority. Pointermove updates the transient preview/marker rather than rebuilding the entire Canvas DOM. Pan/zoom should update the world transform and necessary Grid LOD without repeated Node×Member topology presentation scans each frame. These are performance requirements for the implementation design, not permission to change structural validation.

Every primary control is operable by click and exposes its current state and short Chinese explanation; shortcuts are optional. Focused numeric inputs remain editable with standard keyboard behavior. Snap markers, Grid, origin, axes, and decorative structural symbols use `pointer-events: none`. Canvas feedback must be readable without relying on color alone, and an input overlay must move/flip as needed so it does not cover its target Node, Support, or member endpoint.

## Browser acceptance and regression gate

Future implementation must use real pointer/browser tests, not pure helper tests alone:

1. Grid Snap ON: pointer `(12.6,8.4)` previews `(13,8)`; Snap OFF preserves decimal values through save/reload.
2. From `(12.4,7.6)`, horizontal ORTHO + Grid Snap resolves `(13,7.6)`, not `(13,8)`; vertical and Snap-OFF decimal cases also pass.
3. NODE marker names N3 and Member/Node confirmation uses N3's exact identity; an off-axis NODE near an ORTHO-constrained point cannot break the axis.
4. INT hover shows a distinct marker and leaves Draft/topology/history unchanged. The Node tool at a two- or three-member crossing creates one Node and all strict passing incidences atomically.
5. Blank Member start + blank end makes two Nodes and one Member as one history entry; Undo/Redo and save/reload preserve the atomic relation. Blank start + Esc creates nothing.
6. Existing NODE-snapped start/end reuse their exact keys; a Member through an existing Node authors its explicit intermediate incidence. A geometrical Member crossing without Node remains disconnected.
7. A provisional Member endpoint at an unjoined multi-member crossing is blocked, including pointer INT, Grid, and numeric routes; no hidden Joint or partial object appears. Explicit Node-tool confirmation permits subsequent Member use of that Node.
8. Wheel zoom preserves the target world point within 1 CSS px at an offset/responsive canvas and at scale limits; toolbar zoom uses the visible canvas center.
9. Middle pan during Member preview changes only view; start and preview survive, align immediately after pan, and middle mouseup does not commit.
10. Decimal length/angle, X/Y and relative input produce the expected world geometry; focused fields do not trigger ORTHO Shift or F-key toggles. Esc cancels only transient state.
11. After Member commit the tool remains active but waits for a fresh start; it does not auto-chain. Visual Grid LOD changes never change the same pointer's logical 1 mm Grid Snap result.
12. Large 500×500, 1000×1000, and 2000×1000 mm views keep Grid DOM bounded and pointer/pan/zoom responsive; no per-pointermove full-canvas reconstruction.

Protect existing Node, Member, Support, Load, selection, Save/reload, Model Check, Analyze, incomplete-Draft blocking, historical v1 revisions, and Node-as-Joint behavior. No Solver or mechanics numerical contract changes are permitted.

## Product Owner visual acceptance

Review the real browser at near/mid/far zoom: the Grid is subordinate to the structure while 1 mm precision remains usable; NODE and INT markers cannot be confused; an INT marker does not look like a completed Joint; the mini input and labels do not obscure Node/Support; blank-start Member drawing feels like “click start, click end” rather than a command language; wheel and middle pan feel stable; the four primary status controls are understandable without AutoCAD knowledge. Visual approval complements, rather than replaces, the identity/topology browser checks.

## Explicit exclusions and risks

No window/crossing selection, Shift multi-select, grip redesign, complex Node drag, overlap chooser, delete redesign, full Undo/Redo redesign, automatic Member chaining, repeat command, command line, Layers, UCS, Trim, Extend, Fillet, Offset, Array, Blocks, Layouts, or 3D. No real Project conversion, migration, merge, push, or deployment belongs to this design phase.

Primary implementation risks are: client/SVG/world coordinate drift; an off-axis OSNAP defeating ORTHO; replacing a chosen Node identity with coordinate lookup; a provisional endpoint silently joining an old crossing; partial writes/history entries from a multi-object Member action; and candidate/render work scaling with total geometry on pointermove. The specified typed resolution, editor atomicity, crossing guard, coordinate adapter, and real browser acceptance are blocking controls for those risks. The Product Owner's architectural and interaction choices above are final for this spec; no further product decision is required before reviewing the written document.
