# Student Learning Workspace UX Contract — M5 Gate 0A

## Status and authority

- Status: **CONFIRMED — M5 Gate 0A UX contract freeze**
- Parent authority: `MASTER_SPEC.md`
- Scope: the student-facing browser workspace for the existing Physical Draft, Model Check, Prediction, Analysis, Compare, Explain, and Reflection capabilities.
- Language: all student-visible copy is Simplified Chinese (`zh-CN`).

This contract freezes interaction and presentation only. It neither changes the `TRUSS_2D` mechanics assumptions nor creates a mechanics rule in the browser. Existing specialist contracts remain authoritative for persistence, authorization, revision lineage, analysis, Prediction, Compare, Explain, and Reflection.

## 1. Product goal

A first-time student can use one Project Workspace in a browser to complete:

```text
建模 → 模型检查 → 预测（可跳过）→ 分析 → 理解结果 → Compare → Explain
→ 反思（可跳过）→ 返回模型继续修改
```

The student must not need raw JSON, solver arrays, FEM internal numbering, or an expert FEM parameter panel. Solver calculations remain backstage; the learning outcome is foregrounded.

## 2. Workspace layout

The M5 workspace is one server-rendered Project page enhanced with Vanilla JavaScript and SVG. It is not a multipage wizard, conventional engineering dashboard, or large SPA.

| Area | Frozen responsibility |
|---|---|
| Left | Modeling tools and the selected object's properties. |
| Center | Persistent SVG structural canvas for modeling, selection, and stage-specific overlays. |
| Right | Stage-based learning workflow: ① 建模, ② 预测, ③ 分析, ④ 理解, ⑤ 反思. |
| Bottom | CAD-style status bar: `X`, `Y`, `ΔL`, `Angle`, `ORTHO`, `SNAP`. |

The canvas remains visible whenever practical during Prediction, Result, Explain, and Reflection. Only the relevant overlay is shown: base model, Prediction, actual result, or Compare; overlays are never indiscriminately stacked.

## 3. CAD-like interaction grammar

M5 is a lightweight CAD-style structural model editor. Mouse input performs picking, selecting, and geometric pointing. Keyboard input supplies exact coordinates, distances, angles, confirmation, and cancellation. The property panel supports inspection and exact post-editing; it does not replace direct canvas input.

The P0 modeling tool set is: **选择、节点、构件、连接、支座、荷载**. Student copy says “构件”, never `AnalysisElement`.

For member drawing, the interaction is: choose the 构件 tool → select a start point → move pointer while a preview is shown → click or enter numeric input → confirm. The dynamic display always shows current `X`, `Y`, distance, and angle.

### Coordinate grammar

All values use mm and degrees. Whitespace surrounding tokens may be ignored; no other numeric grammar is accepted in P0.

| Input | Unique meaning |
|---|---|
| `1000,500` | Absolute coordinate: global `X = 1000 mm`, `Y = 500 mm`. |
| `@1000,0` | Relative coordinate from the active command origin: `ΔX = 1000 mm`, `ΔY = 0 mm`. |
| `1000<30` | Polar endpoint from the active command origin: length `1000 mm`, angle `30°`. |

Angle convention is fixed: `0°` is global `+X`; positive angles are counter-clockwise. Polar input is valid only when a command has an active origin. Input is parsed by the UI for geometry entry; the server remains the authority for persisted physical-draft validation.

### Keyboard behavior

- `Enter`: confirm a complete numeric entry or the current command result.
- `Esc`: cancel only the incomplete active command and return to stable selection state; it does not undo a previously confirmed persisted operation.
- `Tab`: while a drawing command has dynamic fields, move focus through those fields. For example, `Length = 1000` → `Tab` → `Angle = 30` → `Enter` creates the corresponding polar endpoint.

Keyboard focus, an incomplete field, or parse failure must have a visible explanation. A malformed value never silently becomes another coordinate form.

## 4. Snap, ORTHO, view, and intersection

### O-M5-CAD-03 — Drawing State Transition Contract

`transition(state, event)` is pure and returns only `{state, fieldIndex}`. `fieldIndex` is `null` outside `DYNAMIC_INPUT`, `0` for `DISTANCE`, and `1` for `ANGLE`; the initial value is `{state:"IDLE",fieldIndex:null}`. Legal states are `IDLE`, `SELECTING`, `DRAW_NODE`, `DRAW_MEMBER_WAIT_START`, `DRAW_MEMBER_WAIT_END`, and `DYNAMIC_INPUT`.

Events are `SELECT_TOOL {type:"SELECT_TOOL",tool:"SELECT"|"NODE"|"MEMBER"}`, `POINTER_POINT {type:"POINTER_POINT",point:{x:number,y:number}}` (finite world coordinates), `INPUT_CHANGE {type:"INPUT_CHANGE",mode:"COMMAND"|"DYNAMIC",value:string,field?:"DISTANCE"|"ANGLE"}`, `TAB {type:"TAB"}`, `ENTER {type:"ENTER",valid:boolean,point?:{x:number,y:number}}`, and `ESC {type:"ESC"}`. A valid Enter that needs geometry requires a finite point; invalid Enter is always unchanged.

| Current state | Event | Result |
|---|---|---|
| any | SELECT_TOOL SELECT/NODE/MEMBER | SELECTING/null, DRAW_NODE/null, DRAW_MEMBER_WAIT_START/null respectively; cancels unfinished work without mutation |
| IDLE, SELECTING | POINTER_POINT, COMMAND/DYNAMIC INPUT_CHANGE, TAB, valid ENTER | unchanged |
| DRAW_NODE | POINTER_POINT, COMMAND INPUT_CHANGE, valid ENTER | DRAW_NODE/null; accepts a node point when supplied and keeps Node active |
| DRAW_NODE | DYNAMIC INPUT_CHANGE, TAB | unchanged |
| DRAW_MEMBER_WAIT_START | POINTER_POINT or valid ENTER | DRAW_MEMBER_WAIT_END/null; accepts member start |
| DRAW_MEMBER_WAIT_START | COMMAND/DYNAMIC INPUT_CHANGE, TAB | unchanged |
| DRAW_MEMBER_WAIT_END | POINTER_POINT or valid ENTER | DRAW_MEMBER_WAIT_START/null; accepts member end and completes that member |
| DRAW_MEMBER_WAIT_END | COMMAND INPUT_CHANGE, TAB | unchanged |
| DRAW_MEMBER_WAIT_END | DYNAMIC INPUT_CHANGE DISTANCE/ANGLE | DYNAMIC_INPUT/0 or DYNAMIC_INPUT/1 respectively |
| DYNAMIC_INPUT | POINTER_POINT or COMMAND INPUT_CHANGE | unchanged |
| DYNAMIC_INPUT | DYNAMIC INPUT_CHANGE DISTANCE/ANGLE | DYNAMIC_INPUT/0 or DYNAMIC_INPUT/1 respectively |
| DYNAMIC_INPUT/0 | TAB | DYNAMIC_INPUT/1 |
| DYNAMIC_INPUT/1 | TAB | DYNAMIC_INPUT/0 |
| any | ENTER valid:false | unchanged |
| any | ESC | IDLE/null; cancels tool/unfinished command without mutation |

`DYNAMIC_INPUT` always has `fieldIndex` in `{0,1}`. CAD-specific Tab is expressed only in that state; later DOM wiring may prevent default only then, preserving normal Tab accessibility otherwise. Member completion never chains its endpoint into a following member start. Task 3 creates no effects, draft mutations, Snap/Grid/ORTHO work, or Connection; Task 4 resolves points and Task 5 performs structural mutations.

P0 provides Node/Endpoint Snap, Grid Snap, Geometric Intersection Snap, ORTHO, Pan, Zoom, and Fit View. The status bar shows the active ORTHO and SNAP modes as well as the current pointer/drawing values.

### O-M5-CAD-01 — SNAP resolution policy

### O-M5-CAD-04 — SNAP Candidate & Coordinate Transform Contract

`resolvePointerPoint({worldPointer,screenPointer,candidates,viewTransform,origin,ortho,gridEnabled,explicitNumeric})` uses finite `{x,y}` worldPointer, screenPointer, and origin; `screenPointer` is CSS px. `viewTransform` is the only plain affine world-to-screen form `{a,b,c,d,e,f}`, all finite: `screenX=a*worldX+c*worldY+e`, `screenY=b*worldX+d*worldY+f`. Its output and screenPointer share CSS-pixel coordinates.

Each candidate is `{kind:"NODE"|"ENDPOINT"|"INTERSECTION",canonicalKey:string,worldPoint:{x:number,y:number}}`. Malformed candidates are ignored; malformed top-level inputs are caller-contract violations. NODE/ENDPOINT are class 1 and return `NODE`; INTERSECTION is class 2 and returns `INT`; Grid is class-3 fallback and returns `GRID`. Same-class eligibility is distance `<=12` CSS px, then nearest, then lexical canonicalKey; array/DOM/query order never decides. Canonical keys are `NODE:<node_client_key>`, `ENDPOINT:<physical_member_client_key>:START|END`, and `INTERSECTION:<lower_member_key>|<higher_member_key>` with lexical member ordering.

### O-M5-CAD-05A — Support Canonical Identity Capability

**RESOLVED.** A Support is a first-class canonical editable Physical Draft object with its own non-empty, project-scoped unique `client_key`, persisted with the same `CharField(128)` convention as other keyed physical collections. The canonical `physical-draft-v1` / `workspace-bootstrap-v1.draft.supports` object is `{client_key,target_connection_client_key,support_type,restrained_axis}`. `target_connection_client_key` remains only a relationship reference and is never Support identity. The identity round-trips through draft save and serialization; snapshot identity follows existing keyed-object precedent as `id`, while support idealization continues to consume only its target and restraint semantics.

When `explicitNumeric===true`, worldPointer is the exact parseCadInput point and immediately returns it with `snapType:null,candidateKey:null`: it bypasses Node/Endpoint/Intersection, ORTHO, and Grid. Otherwise resolve class 1, then class 2, then apply ORTHO from worldPointer-origin (horizontal if `|dx|>=|dy|`, vertical otherwise), then fixed global-origin 100 mm Grid; under ORTHO Grid changes only the free axis. `origin` is the drawing origin, never Grid origin. This decision adds no mutation, Connection, Snap type ENDPOINT, custom grid, UCS, or alternate transform shape.

The only P0 snap candidate classes are Node/Endpoint, Geometric Intersection, and Grid. A pointer-based drawing point is produced by one resolution pipeline: collect candidates → resolve Node/Endpoint → otherwise resolve Intersection → otherwise apply ORTHO when enabled → apply Grid assistance → final point. Separate UI modules must not snap that result again.

Priority is **Node/Endpoint > Geometric Intersection > Grid**. A valid higher-priority candidate prevents every lower-priority candidate from changing the final point. Candidate eligibility is measured from the pointer to the screen-projected candidate using a **12 CSS px** screen-space tolerance; it is never a fixed world-coordinate/mm tolerance and does not vary with zoom.

Within one priority class, choose the candidate nearest to the pointer in screen-space. If that distance is exactly tied, choose by a stable canonical candidate key. Implementations must reuse a stable domain client key where available and must not rely on DOM order, database query order, creation time, or incidental iteration order. Node and member Endpoint are one highest-priority class: neither receives a further product priority, and coincident representations must produce the same geometry.

Intersection is geometry only. Hovering, snapping, clicking, or drawing through an intersection must not create a Connection. Its marker/label must be visibly distinct from an explicit structural Connection; creating a Connection requires the explicit connection action and server validation.

Object Snap (Node/Endpoint or Intersection) outranks ORTHO. Without one of those object candidates, ORTHO first constrains the candidate to global horizontal or vertical: compare `|Δx|` and `|Δy|` from the active command origin; `|Δx| > |Δy|` selects horizontal, `|Δy| > |Δx|` selects vertical, and exact equality selects horizontal. ORTHO is a drawing aid only and never changes support, mechanics, or solver semantics.

### O-M5-CAD-02 — Grid policy

Grid is a drawing aid, not a mechanics constraint, structural topology, or physical property. Its snap spacing is fixed at **100 mm** in world space on both X and Y, anchored at global origin `(0, 0)`. Grid coordinates are integer multiples of 100 mm, including negative values. Pan and Zoom change only display transformation; they never move the grid origin or alter snap spacing. P0 excludes custom/per-project/adaptive/zoom-dependent spacing, major/minor snap levels, grid rotation, and local or polar grids.

Grid Snap has an independent `ON`/`OFF` state. When off, it suppresses only Grid assistance; Node/Endpoint Snap, Intersection Snap, and ORTHO remain available. Grid visibility is a separate visual concern and may be on while Grid Snap is off, or off while Grid Snap is on. Visual density may omit minor lines at a given zoom, but it never changes the 100 mm snap targets.

With no higher-priority object candidate and Grid Snap on, ORTHO off independently snaps X and Y to their nearest 100 mm multiple. At an exact midpoint between multiples, each axis resolves toward positive coordinates: `50 → 100`, `-50 → 0`, `150 → 200`, and `-150 → -100`. Implementations must not depend on language-default banker rounding. With ORTHO on, Grid may adjust only its free axis and preserves the locked axis; for example, horizontal from `(100,75)` near X `493` resolves `(500,75)`, and vertical from `(125,100)` near Y `487` resolves `(125,500)`.

Grid never creates or merges nodes, creates a Connection, connects crossing members, or modifies a Support or Load. Node/Endpoint Snap still wins within the 12 CSS px object tolerance even if the candidate is off-grid. Valid complete numeric input remains authoritative and bypasses Grid Snap at Enter confirmation.

Valid complete numeric input (`x,y`, `@dx,dy`, or `length<angle`) is the authoritative geometry intent at Enter confirmation and is never changed by pointer SNAP. Before pointer confirmation, the canvas presents a short, distinguishable visible marker/label for the resolved class: `NODE`, `INT`, or `GRID`.

ORTHO is a drawing aid only. When on, it preferentially locks a drawing preview to global horizontal or vertical direction. It is not a mechanics constraint and does not change supports, degrees of freedom, or analysis assumptions.

Intersection Snap may detect, highlight, and use the geometric crossing as a pointing location. It must never create a structural Connection automatically. At a geometric crossing without an explicit Connection, the UI explicitly says: **“这里有构件交叉，但尚未建立连接。”** A Connection is created only by the explicit 连接 tool and subsequent server validation. This preserves `Intersection ≠ Connection` and `PhysicalMember ≠ AnalysisElement`.

### O-M5-CAD-05 — Structural Editor Action Contract

`applyEditorAction(draft, action) -> newDraft` is a deterministic, immutable, local-only transformation of `workspace-bootstrap-v1.draft` (`physical-draft-v1`). It neither mutates `draft`, calls network/Django/save/solver/idealization, creates analysis objects, nor changes root `version` (or any server-owned metadata). `client_key` is non-empty and unique only within its project-scoped canonical collection; keys may coincide across kinds, so all targets use `{kind,clientKey}` and never a database id, array index, coordinate, target reference, or DOM id. Legal target kinds are `GEOMETRY_NODE`, `PHYSICAL_MEMBER`, `CONNECTION`, `SUPPORT`, and `NODE_LOAD`.

Canonical object shapes are exactly: `GeometryNode {client_key,x_mm,y_mm,label}`; `PhysicalMember {client_key,start_node_client_key,end_node_client_key,material_id,section_id,label,is_active}`; `Connection {client_key,geometry_node_client_key,participating_member_client_keys}`; `Support {client_key,target_connection_client_key,support_type,restrained_axis}`; and `NodeLoad {client_key,target_connection_client_key,fx_N,fy_N,label}`. No alternative frontend naming is permitted.

The only actions are `{type:"CREATE_NODE",node}`, `{type:"CREATE_MEMBER",member}`, `{type:"CREATE_CONNECTION",connection}`, `{type:"CREATE_SUPPORT",support}`, `{type:"CREATE_NODE_LOAD",nodeLoad}`, `{type:"UPDATE_OBJECT",target:{kind,clientKey},changes}`, and `{type:"DELETE_OBJECT",target:{kind,clientKey}}`. Every created object supplies its own canonical `client_key`, which must be unused in that collection. A member's two node keys must exist. A connection's node key must exist; its member-key array is non-empty, has no duplicates, is lexical ascending by member key, and every member key must exist. A support and node load each reference an existing connection. Create actions add only their named physical object: they never create missing references, split members, infer topology, or create a Connection from SNAP, a crossing, or a node location. Thus `CREATE_CONNECTION` is the sole action that creates a Connection.

`UPDATE_OBJECT` fail-closes for every field outside this whitelist: GeometryNode `x_mm`, `y_mm`, `label`; PhysicalMember `material_id`, `section_id`, `label`, `is_active`; Support `support_type`, `restrained_axis`; NodeLoad `fx_N`, `fy_N`, `label`. Connection updates are forbidden. `client_key`, member endpoints, connection membership, relationship retargeting, root `version`, and any project/database/revision/result/hash/timestamp/mechanics field are never editable; topology changes use explicit delete/create actions.

`DELETE_OBJECT` never cascades. A GeometryNode cannot be deleted while any PhysicalMember references it through `start_node_client_key` or `end_node_client_key`, or any Connection references it through `geometry_node_client_key`. A PhysicalMember cannot be deleted while any Connection lists its key in `participating_member_client_keys`. A Connection cannot be deleted while a Support or NodeLoad references it through `target_connection_client_key`. An unreferenced Connection, Support, or NodeLoad deletes only itself. Geometric proximity, crossing, renderer hierarchy, and DOM order are not dependencies.

Malformed or unknown actions throw `EditorActionError` with `name:"EditorActionError"` and deterministic `code`: `EDITOR_INVALID_ACTION` (malformed/unknown action), `EDITOR_TARGET_NOT_FOUND` (update/delete target absent), `EDITOR_DUPLICATE_CLIENT_KEY` (create key already present in its collection), `EDITOR_REFERENCE_NOT_FOUND` (a required create reference absent), `EDITOR_UPDATE_FIELD_NOT_ALLOWED` (a disallowed change or Connection update), or `EDITOR_DEPENDENCY_CONFLICT` (a delete target is still canonically referenced). On every failure, the input remains unchanged and no partial result is produced. Task 7, not this contract, supplies student-facing error copy.

### O-M5-CAD-06 — Canvas Navigation & Picking Contract

**RESOLVED.** `pickAt(screenPoint, renderedObjects)` returns `{kind,clientKey}` or `null`, using CSS-pixel hit geometry `{kind,clientKey,hit:{type:"POINT",point:{x,y}}|{type:"SEGMENT",start:{x,y},end:{x,y}}}`. GeometryNode, Connection, Support, and NodeLoad use POINT; PhysicalMember uses SEGMENT. POINT tolerance is 10 CSS px and SEGMENT tolerance is 8 CSS px. Multiple hits resolve by priority Support, NodeLoad, Connection, GeometryNode, PhysicalMember; within a class choose shorter screen distance then lexical `${kind}:${clientKey}`. Input/DOM/query/creation order and database identity never decide. Keyboard focus/Enter does not call `pickAt`: it reads the existing SVG `data-object-kind` and `data-client-key` directly into the same `{kind,clientKey}` selection shape.

The canonical view is the O-M5-CAD-04 affine world-to-CSS transform `{a,b,c,d,e,f}` without rotation, skew, or UCS. `reduceView(view,event)` is immutable: `PAN {deltaScreen:{x,y}}` changes only `e+=x,f+=y`; `ZOOM {factor>0,anchorScreen:{x,y}}` scales about that fixed screen anchor and clamps scale to 0.05–20 CSS px/mm; `FIT_VIEW {worldBounds:{minX,minY,maxX,maxY}|null,viewport:{width,height}}` is unchanged for null bounds, otherwise expands either world extent below 100 mm about its center, uses 40 CSS-px padding, centers the resulting bounds, preserves axis orientation, and applies the same clamp. The renderer applies exactly one authoritative world-to-screen transform to physical geometry and world-generated Grid. PAN/ZOOM/FIT never mutate draft world coordinates, Grid origin `(0,0)`, or Grid spacing `100 mm`; SNAP continues to use the same affine formula, while screen overlays may remain untransformed.

## 5. Modeling, draft, and revision UX

The workspace shows the server-authoritative current draft version, for example **“当前草稿 v4”**. Local edits remain clearly marked as unsaved; Save sends the complete physical draft with its expected draft version. A successful save replaces the displayed version with the server response. Model Check uses that current saved version and does not create an AnalysisRun.

On stale-draft rejection, the UI explains: what happened, why the page is older, and how to recover (reload the newest model before retrying). It must not merge concurrent drafts in the browser or fabricate a new version.

Every AnalysisRun is labelled with its immutable source draft version. When the current draft differs, result-related panels state: **“这个分析结果属于上一版结构，不能代表当前草稿。”** The old result remains historical evidence and may be viewed under read authorization; it cannot be presented as the current draft's result. M5 creates no DesignIteration domain.

## 6. Learning workflow

The right panel communicates progress as guidance, not a hard gate:

1. **建模** — edit, save, and Model Check the physical draft.
2. **预测** — “先猜一猜”; explicitly offers **“跳过预测，直接分析”**.
3. **分析** — submit the existing Analyze request for the current saved draft and, if applicable, its completed Prediction.
4. **理解** — present results, Compare, and Explain with progressive disclosure.
5. **反思** — “建议记录这次分析后的想法”; explicitly offers **“稍后再说”**.

Skipped Prediction and skipped/absent Reflection never block save, Model Check, Analyze, result access, or further editing.

## 7. Prediction UX

Prediction is student-owner authoring only and is a hypothesis, never Solver input or an examination. The canvas is used to choose the maximum-displacement `PhysicalPointRef` and to identify the representative ordered path. The path prompt is: **“请选择你认为比较关键的一条传力路径。”** It must not say “正确传力路径”.

For every current PhysicalMember, the student chooses exactly one visible option: **受拉、受压、近似零力、不确定**. These map only to the existing prediction contract choices `TENSION`, `COMPRESSION`, `ZERO_FORCE`, and `UNSURE`. “近似零力” is student-facing wording; it does not expose or alter the numerical residual-cleanup rule.

After a completed Prediction is linked to an AnalysisRun, it is immutable. Workspace reload resumes the sole current-draft DRAFT or COMPLETED Prediction under O-M5-P01; it never creates a second Prediction. A current DRAFT is not auto-bound: the student may complete it or select “跳过预测，直接分析”, which sends `prediction_id = null`. A current COMPLETED Prediction may be explicitly bound. If legacy data is ambiguous, the Workspace presents `PREDICTION_AMBIGUOUS` with **“当前预测记录存在数据歧义，暂时无法继续使用预测。请联系管理员处理。”** and does not select a Prediction. A Prediction from an old draft is visibly historical/stale rather than reused for the new draft. No score, grade, correctness percentage, ranking, selector, or forced completion is introduced.

## 8. Analyze and result disclosure

Analyze first performs the existing server-side model/authorization path. A failed check or analysis is displayed through the beginner-facing error format in §13; the frontend never diagnoses stiffness, support conditions, or forces itself.

For a successful run, the workspace presents results in this fixed progressive-disclosure order:

1. **发生了什么？** Maximum displacement, tension members, compression members, and approximate-zero members, plus an optional Prediction comparison entry point.
2. **为什么？** Deterministic Explain blocks and their linked member evidence.
3. **工程数据** Raw authoritative engineering values and segment evidence for inspection, not as the first screen.

Result state is conveyed by text, symbol/line treatment, and focusable labels as well as color. Color alone is never the sole carrier of force state or selection.

## 9. Compare and Explain UX

Compare is a disclosure of deterministic backend facts. Student-facing labels are:

| Backend state | Student wording |
|---|---|
| `MATCH` | 和预测一致 |
| `MISMATCH` | 和预测不同 |
| `UNSURE` | 之前选择“不确定” |
| `NOT_COMPARABLE` | 暂不比较 |
| `NO_PREDICTION` | 未进行预测，仍可查看分析说明。 |

`NO_PREDICTION`, `UNSURE`, `NOT_COMPARABLE`, and skipped prediction are normal learning states, not errors. The UI never says “正确/错误”, assigns a score, or claims one unique solver-truth load path.

When a PhysicalMember projects to `MIXED`, the UI says that one physical member can correspond to multiple analysis segments and those positions have different force states. It exposes the supplied segment evidence and does not force a single state or verdict.

Explain is rendered from deterministic `explanation-v1` output. It does not call an LLM, recompute mechanics, change results, recommend an optimization, or independently classify stress/force state.

## 10. Canvas and teaching-panel linkage

The workspace provides conceptual two-way linkage:

- Selecting a member/result item in the right panel highlights its PhysicalMember/available segment evidence on the canvas.
- Selecting a canvas member focuses the corresponding right-panel information.

The selected item has a text name and non-color focus indication. If the selected PhysicalMember is `MIXED`, the panel identifies it as such rather than highlighting one segment as its whole truth.

## 11. Reflection UX

Reflection is AnalysisRun-scoped, optional, and follows its existing `DRAFT → COMPLETED` lifecycle. The workspace provides the three fixed prompts:

1. “我原本是怎么判断这个结构的？”
2. “哪些分析结果和我的预想不同？”
3. “下一版我想修改什么，或重新观察什么？”

The student may save a partial DRAFT explicitly, edit it, or clear a field. Complete is an explicit action. A completed Reflection is read-only and must clearly say it cannot be modified. Reflection remains a Soft Gate; it never blocks a later model edit or Analyze. M5 adds no standalone DesignRationale or DesignIteration aggregate.

## 12. Read-only Manager and Developer UX

The workspace honours existing server-side Project-read authorization. Assigned Managers and Developers may inspect read-authorized project/results; student learning evidence follows its specialist visibility contracts (notably, only completed Reflection is visible to those roles). They receive a clear **“只读查看”** state and no student-authoring controls for Prediction or Reflection.

Manager write access to a student project remains false by default. Developer maintenance authority is not reinterpreted as a normal student-learning authoring flow. The FINISHED_GRACE page behavior is not frozen here: Master O-003 remains open, so the workspace must defer final view/edit/analyze presentation to the existing server decision.

## 13. Error UX and accessibility

Every student-facing error follows this order:

1. **发生了什么** — concise outcome.
2. **为什么** — a safe, understandable cause supplied or mapped by the backend.
3. **可以怎么处理** — the next safe action, such as correcting a support, saving, or reloading a stale draft.

Machine codes are optional expandable **技术信息**, not primary student copy. Normal learning states listed in §9 are not errors.

The keyboard can reach tools, dynamic fields, property fields, workflow actions, result rows, and status indicators. Focus is visible; controls have programmatic names; status/error changes are announced accessibly; and contrast/text labels prevent reliance on color. Pan/zoom/fit controls have keyboard alternatives. Canvas pointer affordances are supplemented by the exact keyboard grammar and property panel.

## 14. Frontend/backend authority boundary

Frontend responsibilities are interaction state, SVG visualization, drawing previews, coordinate parsing, UI state, and authenticated API calls. Backend responsibilities remain authorization, draft validation and persistence, model check, immutable revisions, analysis, result disclosure, Prediction/Reflection lifecycle, Compare derivation, Explain derivation, and all mechanics truth.

The browser must not become an authority for solver calculations, stress, force-state truth, comparison truth, explanation truth, access control, revision lineage, or automatic Connection creation.

## 15. Backend capability gaps recorded for later M5 gates

No endpoint changes are made in Gate 0A. The current implementation has the analysis/learning JSON disclosures, but the following boundaries are absent and must be explicitly addressed before the Gate that implements the affected behavior:

| ID | Required capability | Current missing boundary | Blocks |
|---|---|---|---|
| BCG-M5-01 | Open/reload a Workspace with the authoritative mutable physical draft and current draft version. | No project Workspace page or read-draft delivery boundary is present. | M5 Gates 1–5. |
| BCG-M5-02 | Restore the Prediction state relevant to the current draft after a page reload. | O-M5-P01 freezes a minimal current-discovery contract (`NONE`, one `DRAFT`, one `COMPLETED`, or fail-closed `PREDICTION_AMBIGUOUS`); Gate 0B must plan it and later gates implement it. | M5 Gates 2–5. |
| BCG-M5-03 | Deliver the M5 Workspace shell and local static assets. | No Project Workspace template, project page route, or project static JS/CSS structure is present. | M5 Gate 1 and all UI gates. |

These are **BACKEND_CAPABILITY_GAP** records, not permission to implement endpoints in Gate 0A. They do not change existing mechanics or learning contracts.

## 16. Explicit non-goals

M5 does not add 3D, frame bending, nonlinear analysis, arbitrary-angle Roller, a generic FEM editor, distributed-load expansion, full CAD clone, Trim/Extend/Offset/Fillet/Array/Block/Layer system/CAD command language, Euler/buckling UI, a Section Designer, DesignIteration, AI mechanics authority, grading/scoring, automatic optimization/reinforcement, or a failure guarantee.

## 17. Acceptance scenarios

### Scenario A — Full Learning Loop

Student opens the Workspace, builds a simple truss, saves/checks it, completes Prediction, analyzes, sees maximum displacement and force-state understanding, opens Compare and Explain, expands engineering details, writes or completes Reflection, then modifies the model again. The modified draft receives a new current version; the earlier result is labelled as an earlier structure version.

### Scenario B — Soft Gate

Student models/checks, selects “跳过预测，直接分析”, analyzes, reaches Result, sees Compare as no-prediction/unavailable rather than an error, uses Explain, selects “稍后再说”, and continues editing. Neither skipped step blocks the flow.

### Scenario C — CAD Precision

Student starts member drawing, chooses a start point, enters `1000,500`, `@1000,0`, or `1000<30` in its valid context; uses Tab to move dynamic fields; presses Enter; and obtains the corresponding geometry. Esc cancels an unfinished command without changing a confirmed object.

### Scenario D — Intersection

Two members cross geometrically. The intersection can be detected and snapped, but no Connection is created. The UI identifies the crossing as not yet structurally connected until the student explicitly uses the connection workflow.

### Scenario E — Read-only review

An assigned Manager or Developer opens a read-authorized student Workspace. The page is visibly read-only; it exposes no Prediction or Reflection authoring. A DRAFT Reflection is not shown to that reviewer, while a completed one may be read under the existing authorization contract.

## 18. Definition of Done for M5 UX implementation

M5 UX implementation is complete only when a server-rendered single Workspace with the frozen three-panel layout and status bar satisfies all acceptance scenarios; uses SVG and Vanilla JavaScript; preserves the listed authority boundaries; reports the recorded capability gaps as resolved by separately specified work; has accessible text/non-color state; and does not add any non-goal or alter the current mechanics assumptions. Automated tests for each implemented browser/API integration boundary and the existing backend suite must pass in their respective later gates.

## 19. POC V1 reconciliation status（2026-09-21）

BCG-M5-01、BCG-M5-02、BCG-M5-03 已由 Workspace read/bootstrap、current Prediction discovery 与 server-rendered Workspace/static assets 分别解决。它们保留在 §15 作为 Gate 0A 的历史记录，不再是当前 capability gap。

真实 Playwright 旅程 `tests/browser/test_poc_v1_student_journey.py` 只使用公开页面与控件，覆盖 Scenario A、显式 Run 历史恢复和空白项目第一根构件。补充浏览器回归覆盖 Soft Gate、CAD 解析/捕捉、Intersection ≠ Connection、只读角色、依赖删除保护、1024px 桌面布局与技术错误折叠。

Level 1 现在以“荷载 → 支座 → 传力路径”的谨慎观察顺序呈现后端事实，使用对象标签与舍入显示值；源数值仍保持不变。机器码仅位于折叠的“技术信息”中。任何不稳定提示都要求检查支座、连接、孤立节点与整体稳定性，不宣称唯一失稳机制。
