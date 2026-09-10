# FRAME_EXTENSION_STRATEGY.md

## 0. 文件狀態

- 文件角色：Stage 2 `FRAME_2D` 的 architecture seam 與 migration risk 控制。
- 狀態：Future strategy，**不是 Frame implementation spec**。
- 目的：避免 P0 為 Future Frame 過度抽象，同時避免把 Truss 寫成無法擴展的死路。
- P0 不得因本文件而實作 Frame mechanics。

---

## 1. Core Strategy

【Confirmed】

Truss-first ≠ 永遠只做 Truss。

【Recommended】

Frame extension 採：

```text
Shared Product / Physical Domains
              │
      ┌───────┴────────┐
      ▼                ▼
Truss2D Idealizer   Frame2D Idealizer
      │                │
      ▼                ▼
TrussModel          FrameModel
      │                │
      ▼                ▼
Truss2DSolver       Frame2DSolver
```

不是：

```text
GenericFEMSolver
  if type == TRUSS ...
  elif type == FRAME ...
  elif type == ...
```

---

## 2. Domains Reused Without Conceptual Rewrite

【Confirmed / Recommended】以下上層概念應共用：

- User
- Role
- CompetitionEvent
- EventMembership
- Project
- Material
- Strip
- Section
- GeometryNode
- PhysicalMember
- Connection（概念共用，Frame semantics 可擴充）
- ModelRevision
- AnalysisRun
- SolverVersion
- Prediction
- Reflection
- DesignRationale
- Report
- Research derived metrics framework

這些 domain 不應命名成 `TrussProject`, `TrussMaterial` 等。

---

## 3. Mechanics That Must Stay Separate

【Confirmed】

```text
TrussModel → Truss2DSolver
FrameModel → Frame2DSolver
```

不可為了 code reuse 強行共用：

- DOF model
- element stiffness formulation
- equivalent nodal load logic
- internal force recovery
- support DOF semantics
- result schema
- benchmark suite

---

## 4. Shared Mechanics Utilities — Allowed

【Recommended】只有真正數學相同者共用：

- coordinate/geometry helpers
- finite-number validation helpers
- numeric tolerance helpers
- selected matrix utilities
- SectionPropertyEngine
- hashing/canonical serialization（更適合 application/common，不屬 element mechanics）

共用的判斷標準：

> 如果改動它會同時改變 Truss 與 Frame mechanics 行為，就必須同時跑兩套 regression。

---

## 5. Analysis Type Seam

【Recommended】

Project / ModelRevision / AnalysisRun 有：

```text
analysis_type = TRUSS_2D | FRAME_2D
```

P0：

- persistence 可允許 enum extension。
- UI 只建立 `TRUSS_2D`。
- service 對任何未啟用 analysis type 明確拒絕。

Stage 2 才開啟 `FRAME_2D`。

不需要建立 generic plugin registry。

---

## 6. Physical Model Seam

### 6.1 GeometryNode

共用 2D coordinates，不加 rz。

`rz` 是 Analysis DOF，不是 GeometryNode coordinate。

### 6.2 PhysicalMember

共用：

- endpoints
- material
- section
- physical identity

不在 P0 PhysicalMember 加：

- end moments
- shear forces
- rotational DOF state
- Frame stiffness matrix

### 6.3 Connection

【Future】Frame 加入時可能需要表達：

- rigid connection
- pinned/released connection

P0 只需要「明確連接」且 Truss idealization 為 pinned。

【Recommended migration seam】未來可新增 connection behavior/analysis idealization 欄位或 Frame-specific connection assignment，而不修改 Connection identity/geometry relationship。

不要現在建立複雜 release matrix、semi-rigid spring model。

---

## 7. Support Seam

P0 UI：

- Pinned
- Roller

Future Frame：

- Fixed
- translational/rotational restraint combinations as required

### Why Truss Solver Uses DOF Flags

Truss contract：

```text
restrain_ux
restrain_uy
```

Frame contract Future：

```text
restrain_ux
restrain_uy
restrain_rz
```

兩個 solver model 分開，因此 P0 不必現在加假的 `rz=False` 到每個 Truss node。

Persistence Support domain 未來擴充 Fixed choice 即可。

---

## 8. Load Seam

【Confirmed】P0：Node Force Fx/Fy。

【Future】Frame：

- nodal force
- possible nodal moment
- member UDL
- member transverse point load

【Recommended】不要建立 generic polymorphic `Load` table hierarchy just for future。

P0 保持 `NodeLoad`。

Frame 到來時新增清楚的 Frame-specific member load persistence/domain，Application Service 再依 analysis type idealize。

Self Weight 若 P0.x/P1 啟用仍先轉 nodal load；不要用它提前迫使 Frame member load abstraction出現。

---

## 9. Section Seam

這是最重要的共享 mechanics asset。

【Confirmed】Section 現在就保留：

- A
- centroid
- Ix
- Iy
- mass/length
- strong/weak axis

Truss P0：

- A → EA / stress
- I → Euler screening

Frame Future：

- A → axial stiffness
- I → EI / bending

因此 SectionPropertyEngine 應保持 analysis-type agnostic。

### Not now

P0 不必因 Frame 加：

- shear area
- torsional J
- warping constant
- plastic section modulus
- code-specific section classification

---

## 10. Idealization Seam

### P0

```text
PhysicalSnapshot
  ↓
Truss2DIdealizer
  ↓
TrussModel
```

### Future

```text
PhysicalSnapshot
  ↓
Frame2DIdealizer
  ↓
FrameModel
```

各 Idealizer 負責自己的：

- topology mapping
- connection semantics
- support mapping
- load mapping
- property extraction

Physical layer 不需要知道 element stiffness equations。

---

## 11. Solver Contract Separation

### Truss

```text
Node DOF = ux, uy
Member properties = E, A
Result = u, reaction, N
```

### Frame Future

```text
Node DOF = ux, uy, rz
Member properties = E, A, I
Result = u, rotation, reaction, N, V, M
```

【Recommended】Frame contract 建新文件，例如未來 `FRAME_SOLVER_CONTRACT.md`，而不是改寫 `TRUSS_SOLVER_CONTRACT.md` 變成大量 optional fields。

---

## 12. Analysis Result Persistence Seam

【Recommended】

AnalysisRun 上層 metadata 共用：

- revision
- analysis_type
- solver_version
- input_hash
- status

Result payload 依 schema version 分開：

```text
truss2d-result-v1
frame2d-result-v1
```

因此 relational schema 不需為 Future `M`, `V`, `rz` 預先加大量 nullable columns。

---

## 13. Teaching Layer Extension

P0 TeachingInsight：

- force path
- reaction
- tension/compression
- displacement
- buckling screening

Frame Future 新增：

- bending/moment
- shear
- deformation shape with rotation
- stiffness distribution
- compatibility
- statical indeterminacy
- Truss vs Frame idealization comparison

Mechanics raw result仍是 source of truth；Teaching Layer 按 `analysis_type` 使用對應 rule set。

不要把 Frame 教學文案提前塞進 P0 result page。

---

## 14. Report Extension

P0 calculation package：

- assumptions
- materials/sections
- node loads/supports
- reactions
- displacement
- axial force/stress
- buckling screening
- mass

Frame Future新增：

- Fixed/rigid assumptions
- rotations
- V/M
- bending deformation
- member transverse loads

Report domain共用，但 section blocks依 analysis type選擇。

---

## 15. Research Extension

【Confirmed Resolution】

Stage 1 research 只測 Truss-compatible concepts/benchmarks。

Stage 2 可新增：

- bending
- Fixed support
- Ix/EI interpretation
- N/V/M
- Frame benchmark suite
- Truss vs Frame idealization learning outcomes

Research schema只新增 derived metric names；不需要重建 Operational architecture。

---

## 16. Migration Path from P0 to Frame Stage

【Recommended】

### Step 1 — Freeze Truss baseline

- all Truss benchmarks green
- solver version pinned
- P0 contracts stable

### Step 2 — Add Frame pure domain

建立：

```text
mechanics/frame2d/
FrameModel
Frame2DSolver
FRAME_SOLVER_CONTRACT.md
```

不修改 Truss kernel。

### Step 3 — Extend persistence only where product concept truly changes

可能 migrations：

- enable `FRAME_2D` analysis_type
- add Fixed support option
- add connection behavior semantics
- add Frame member load entities

### Step 4 — Add Frame2DIdealizer

Physical → Frame mapping。

### Step 5 — Add Frame result schema + Teaching rules

`frame2d-result-v1`。

### Step 6 — Add independent Frame benchmark gate

只有 benchmark stable 後才開 UI Stage 2。

---

## 17. Expected Migrations That Are Acceptable

未來加入 Frame **有 migration 不等於架構失敗**。

可接受：

- enum/value extension
- new Frame load table
- new connection behavior field/table
- new result schema version
- new analysis type

真正需要避免的是：

- 把 `TrussElement` table改造成整個 PhysicalMember system
- 重做 Event/User/Project ownership
- 重做 Material/Section identity
- 丟棄所有 ModelRevision/AnalysisRun traceability

---

## 18. Anti-patterns to Avoid Now

### 18.1 Universal Element class

不要：

```text
Element(type, dof_count, E, A, I, J, ... 40 nullable fields)
```

### 18.2 Universal Solver with branches

不要：

```text
if truss: ...
elif frame: ...
```

散落在 assembly/recovery/validation。

### 18.3 Pre-adding rz everywhere

Truss P0 不需要 rotational DOF。

### 18.4 Pre-adding Fixed/member loads UI

會擴 scope 並讓學生誤以為 P0 支援 Frame mechanics。

### 18.5 Generic FEM plugin framework

目前沒有第三種 solver 的實際需求；interface/plugin system收益不足。

---

## 19. Architecture Seams That Must Be Preserved in P0 Code Review

後續 Code Review 應特別抓：

1. `mechanics.truss2d` 是否 import Django。
2. `PhysicalMember` 是否被一對一綁死成 TrussElement。
3. UI 是否以 line intersection 自動建立 joint。
4. Truss data class 是否被加進大量 Frame-only optional fields。
5. Analysis service 是否以 `analysis_type` dispatch 到明確 idealizer/solver boundary，而非到處 branching。
6. Section engine 是否保持共用、無 Truss-only assumptions。
7. AnalysisRun/result schema 是否能並列 Future Frame result version。
8. Truss tests是否保持獨立可跑。

---

## 20. What Must NOT Be Implemented Now

【Confirmed】

- Frame stiffness matrix
- `rz`
- Fixed support mechanics
- rigid joint force transfer
- V/M recovery
- member UDL
- bending deformation
- statical indeterminacy teaching engine
- Frame UI
- Frame report blocks
- Frame research tests

此文件存在的目的正是**阻止**提前做這些。

---

## 21. Frame Readiness Criteria for P0 Architecture

P0 可宣稱「Frame-ready architecture」只需要滿足：

1. upper domains不叫 Truss-specific names。
2. PhysicalMember 與 AnalysisElement分離。
3. explicit Idealization layer存在。
4. Section properties含 A/Ix/Iy。
5. AnalysisRun有 analysis_type + versioned result contract。
6. Truss solver是獨立 kernel。
7. support/load persistence沒有阻止 future extension。
8. tests可在 Future Frame加入後保留 Truss regression。

不需要任何 Frame mechanics production code。

---

## 22. Main Future Risks

| Risk | Mitigation |
|---|---|
| Connection semantics不足 | Stage 2 migration擴充 behavior，不改 identity |
| Support enum太封閉 | 可擴 enum；Truss kernel仍只收 ux/uy flags |
| Load ORM過早泛化 | P0 NodeLoad，Stage 2新增明確 Frame member loads |
| Result tables綁死 N only | versioned JSON result schema |
| Section只有 A | P0 已保留 Ix/Iy |
| Truss code被抽成 Generic FEM | code review guardrail + independent benchmarks |

---

## 23. Final Strategy Statement

【Recommended】

> P0 要做的是「清楚的 Truss」，不是「半完成的 Generic FEM」。

只要 Physical / Idealization / Mechanics 分界、共享 Section、versioned AnalysisRun 與 independent benchmark seam 被守住，Stage 2 Frame 可以作為新增 kernel 與 idealizer，而不需要推翻整個平台。
