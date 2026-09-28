# Structural Sketch Visual Language V1 — Design

## Intent and authority

The student Canvas is a structural-mechanics sketch, not a database visualization. A new viewer should recognize nodes, members, explicit connections, pinned and global-axis roller supports, and concentrated loads without opening Properties. This design implements the Product Owner's Structural Sketch Visual Language V1 brief on `main` commit `d2e2308ad42322e985c0e5cef48b908a9b760444`.

Editable Draft geometry, connection topology, support restraint meaning, Fx/Fy load values, canonical units, snapshots, solver, and analysis remain authoritative and unchanged. Symbols are a read-only presentation of current workspace state. Unsupported fixed support, distributed load, and moment objects are not added.

## Renderer boundary

Keep `renderer.js` responsible for ordered layers, grid, CAD feedback, and `renderWorkspace`. Move textbook symbol construction into a focused `structural-symbols.js` module with `renderNode`, `renderMember`, `renderConnection`, `renderSupport`, and `renderLoad` helpers. Each helper receives resolved world positions, the existing screen-to-world unit, and presentation state; it does not resolve or mutate Draft references. Reusable hatch and arrow definitions live in one SVG `<defs>` subtree per Canvas render, not per support.

Geometry remains in world coordinates. Nodes, supports, connection rings, arrowheads, labels, hit regions, and strokes use the renderer's screen-to-world unit so their apparent size stays readable across near/mid/far zoom. A member's displayed width is not its Section width. Each selectable object keeps the existing `data-object-kind` and `data-client-key` interaction wrapper. Decorative children have `pointer-events="none"`; a single transparent, wider hit shape within the wrapper preserves selection. No additional geometry or snap authority is introduced.

## Symbol grammar

- Node: white hollow circle with dark outline, roughly 14 px diameter, centered exactly on its geometry point.
- Member: begin with a dark neutral roughly 3 px body from center to center, plus a wider transparent hit stroke. At visual acceptance compare this clean engineering line against a thin outlined structural bar and keep the one that reads more like a mechanics textbook. Display width is adjustable and is never physical Section width. Analysis-result stroke color/dash remains on the body. Hover and selection are separate outer strokes/rings and never recolor the engineering body.
- Explicit Connection: a dark, thin annular marker outside the node circle. A geometric crossing without an explicit Connection gets no ring. Incomplete Connection with a known node can still show its ring plus a small warning cue.
- Pinned: triangle under the anchor, horizontal ground line, and hatched ground. Roller Y: triangle, two wheels, horizontal ground. Roller X: rotate the roller assembly 90° against a vertical wall. Screen-sized groups are anchored at the actual Connection/Node coordinate. Wheels, ground/wall, hatch, and triangle are decorative only: no Node identity, hit testing, Snap, Connection, or topology participation; clicking a wheel must not create or select a Node.
- NodeLoad: one red arrow per nonzero Fx and Fy component, oriented by the sign, with an absolute-magnitude `N` label. Each arrowhead points at the true Node/Connection anchor for its component, including downward, upward, and horizontal loads. Two nonzero components remain two arrows; their stems/labels may be visually offset for legibility while preserving the common true anchor. A zero load remains selectable but does not falsely show a force direction. Pointer preview uses the same temporary visual grammar, never Draft data.
- Incomplete objects: render a locatable fragment and warning cue only when existing geometry permits a truthful anchor; otherwise keep the object in the existing Properties/incomplete inventory. Never invent a point or hide an object from that inventory.

## Layering and interaction

Stable order is grid; CAD guides/member previews; members; supports; loads; explicit connections; nodes; hover/selection overlays; snap/dynamic feedback. Node and support symbols must remain distinguishable when coincident. Load glyphs receive a component-specific offset to avoid covering supports. Hover is subtler than selected, and neither changes topology or result semantics. Remove the current drop-shadow-based hover and inline rule that recolors every child; use symbol-specific overlays. CAD pointer routing, selection priority, Delete, Undo/Redo, Snap, ORTHO, pan/zoom/fit, and grid logic remain unchanged.

## Student-facing controls and feedback

The Support tool exposes three illustrated choices: 铰支座, 滚动支座／限制竖向移动, 滚动支座／限制水平移动. Values continue to map to `PINNED`, `ROLLER_Y`, and `ROLLER_X`; the backend contract stays unchanged. The Load tool exposes only 集中力 and explains 水平力 Fx／竖向力 Fy alongside numeric inputs. Property edits update the Canvas immediately through the existing state/render path. Do not add disabled future-mechanics noise unless needed for comprehension.

## Verification

Start with failing browser-level visual-contract tests for all symbols, sign directions, explicit-versus-crossing topology, selection/hover, pointer-event isolation, zoom, and incomplete states. Add a real simple-truss demo for browser screenshots at 1024×768, 1280×800, and 1440×900, reviewing pinned, Roller Y, Roller X, both load axes, selections, connection/crossing, and near/mid/far zoom. Preserve full non-browser and browser regressions. Run Django and migration checks and `git diff --check`. Completion means ready for Product Owner visual review, not automatic merge or deployment.
