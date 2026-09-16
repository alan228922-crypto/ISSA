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

P0 provides Node/Endpoint Snap, Grid Snap, Geometric Intersection Snap, ORTHO, Pan, Zoom, and Fit View. The status bar shows the active ORTHO and SNAP modes as well as the current pointer/drawing values.

### O-M5-CAD-01 — SNAP resolution policy

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
