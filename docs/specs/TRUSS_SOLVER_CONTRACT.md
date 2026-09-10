# TRUSS_SOLVER_CONTRACT.md

## 0. 文件狀態

- 文件角色：P0 `TRUSS_2D` Mechanics Core 正式邊界規格
- 範圍：pure Python domain contract；不描述 ORM、HTTP、Template
- 目標：讓 solver 可獨立 benchmark、可重現、可被 Idealizer 呼叫
- 本文件不是 production code。
- Source of Truth：`MASTER_SPEC.md v1.0`；本 Solver Contract 已完成 reconciliation。

### 狀態標記

- 【Confirmed】
- 【Recommended】
- 【Open Decision】
- 【Future】

---

## 1. Mechanics Scope

【Confirmed】

P0 Solver：

> 2D Linear Elastic Truss / direct stiffness method

基本假設：

- 2D
- small displacement
- linear elastic
- ideal truss member
- axial force only
- ideal pinned joints
- node DOF：`ux`, `uy`
- member stiffness based on `EA/L`
- node loads only
- no bending moment
- no shear force
- no rotational DOF

固定 units：

| Quantity | Unit |
|---|---|
| length | mm |
| force | N |
| stress / E | MPa = N/mm² |
| area | mm² |
| second moment | mm⁴ |
| mass | g |
| density | g/mm³ |

Solver 不做 unit conversion。

---

## 2. Contract Boundary

```text
Physical Snapshot
     ↓
Truss2DIdealizer
     ↓
TrussModel
     ↓
validate_truss_model
     ↓
Truss2DSolver
     ↓
TrussSolveResult
     ↓
Pure postprocess
     ├── axial stress
     ├── member mass
     └── Euler screening
     ↓
TrussAnalysisResult
```

【Confirmed】

`TrussModel` 不接受 Django ORM object。

【Recommended】

輸入/輸出使用 immutable pure Python value objects（實作可用 dataclass / tuple-like object，但本規格不強制具體語法）。

---

## 3. Identifier Rule

【Recommended】

Solver entity ID 使用 opaque scalar identifier（建議 string）。

例如：

```text
"N1"
"M7"
```

Solver 不依賴：

- DB primary key type
- Django model class
- UI display order

ID 只用於 topology reference 與 result mapping。

---

## 4. TrussModel Input Contract

概念 schema：

```text
TrussModel
- schema_version
- nodes[]
- members[]
- supports[]
- nodal_loads[]
```

### 4.1 `schema_version`

【Recommended】

字串，例如：

```text
"truss2d-input-v1"
```

用途是 contract compatibility，不是 Django migration version。

---

## 5. Node Contract

```text
Node
- id
- x_mm
- y_mm
```

### Invariants

【Confirmed / Recommended】

- id 在 model 內 unique。
- x/y 必須 finite numeric。
- 座標 unit = mm。
- Solver 不自行 merge 重合 nodes。
- 是否兩個 Physical entities 應共用 Node，已由 Idealizer 決定。

---

## 6. Member Contract

```text
Member
- id
- node_i
- node_j
- E_MPa
- A_mm2
```

【Recommended】

若 stability/mass postprocess 需要，analysis orchestration 可另外帶 member property context：

```text
MemberPropertyContext
- member_id
- density_g_per_mm3
- I_for_buckling_mm4
- physical_member_id
- section_id
- material_id
```

但 Truss stiffness solver 本身只需要 `E`, `A`, geometry。

### Invariants

- member id unique。
- node_i/node_j 必須存在。
- node_i != node_j。
- geometric length > numerical tolerance。
- `E_MPa > 0`
- `A_mm2 > 0`
- 同一對 analysis nodes 的 duplicate member 是否允許，P0 預設視為需明確驗證/警告；不可靜默重複。

---

## 7. Support Contract

P0 conceptual contract：

```text
Support
- node_id
- restrain_ux
- restrain_uy
```

【Confirmed】

P0 UI domain 只有 Pinned / Roller。

【Recommended】

Solver 不需要知道字串 `"PINNED"` 或 `"ROLLER"`；Idealizer 把 physical support 轉成 translational DOF restraints。

優點：

- Solver 保持 mechanics minimal。
- Future Frame 可以有自己的 support contract，包含 `rz`。
- 不必在 Truss solver 寫 `if support.type == FIXED`。

### Invariants

- support node 存在。
- 至少一個 restraint 為 true。
- duplicate support definition 必須在 Idealization/Validation 被規範化或拒絕。

---

## 8. NodalLoad Contract

```text
NodalLoad
- node_id
- fx_N
- fy_N
```

【Confirmed】

P0 只支援 node force。

### Invariants

- target node 存在。
- components finite numeric。
- 允許單一 component = 0。
- 多筆同 node load 是否先 aggregate 可由 Idealizer/Application 決定；solver contract 應對確定的總 nodal force 有一致結果。

【Confirmed Deferred】

Self Weight 不在核心 P0。

【Future P0.x/P1】

Self Weight 若啟用，先轉成 nodal load，再進此 contract；solver 不新增 distributed self-weight input。

---

## 9. DOF Convention

【Confirmed】

每 node：

```text
ux
uy
```

【Recommended】

全域 DOF ordering 必須 deterministic。

例如按 input node sequence：

```text
[node0.ux, node0.uy, node1.ux, node1.uy, ...]
```

實際內部 ordering 可變，但不得影響 public result mapping。

---

## 10. Sign Convention

【Recommended】

為避免 UI/benchmark 不一致，P0 鎖定：

- global +x：右
- global +y：上
- displacement 與 reaction 依 global axis
- member axial force `N > 0`：tension
- member axial force `N < 0`：compression
- axial stress採相同正負規則

若 MASTER_SPEC 有不同 convention，必須標記 SPEC CONFLICT 再改，不可靜默混用。

---

## 11. Solver Responsibilities

【Confirmed】

Truss solver kernel 負責：

1. model mechanics validation
2. member geometry evaluation
3. local/global stiffness contribution
4. global stiffness assembly
5. load vector assembly
6. restraint application
7. linear solve
8. node displacement
9. support reaction
10. member axial force
11. numerical diagnostics

【Recommended】

Axial stress `N/A` 可放 pure postprocess，而不必耦合 stiffness solve function。

Mass 與 Euler screening 明確位於 pure postprocess/stability module。

---

## 12. Solver Non-responsibilities

Solver 不負責：

- ORM save/load
- authorization
- Event status
- account rules
- physical line intersection logic
- creating structural Connection
- section drawing UI
- teaching message
- report text
- design recommendation
- AI reasoning
- unit conversion
- self-weight generation in P0
- Frame behavior

---

## 13. Validation Result Contract

【Recommended】

Validation 不只回傳 boolean。

```text
ValidationIssue
- code
- severity
- entity_type
- entity_ids[]
- field
- numeric_context
```

Severity 最少：

```text
ERROR
WARNING
```

- `ERROR`：阻止 solver。
- `WARNING`：可繼續，但應由 Application/Teaching 決定如何呈現。

### 13.1 Stable Error Codes

P0 建議至少保留：

```text
EMPTY_MODEL
UNKNOWN_NODE_REFERENCE
DUPLICATE_NODE_ID
DUPLICATE_MEMBER_ID
ZERO_LENGTH_MEMBER
INVALID_YOUNGS_MODULUS
INVALID_AREA
INVALID_NUMERIC_VALUE
NO_SUPPORT
INSUFFICIENT_RESTRAINT
SINGULAR_GLOBAL_STIFFNESS
DUPLICATE_ANALYSIS_MEMBER
```

【Recommended】

`SINGULAR_GLOBAL_STIFFNESS` 是 solver/numerical outcome；不等同「一定是某一種機構」。Teaching Layer 可說「可能存在剛體位移或機構」，不可由 solver 假裝已完成結構診斷。

---

## 14. SolverError Contract

【Recommended】

區分：

### Expected domain/mechanics failure

以 structured issue/result 表達：

- invalid model
- singular system
- unsupported input

### Unexpected internal failure

```text
SolverInternalError
- solver_version
- diagnostic_id
- safe_context
```

UI 不直接顯示 stack trace。

AnalysisRun 應記錄 `SOLVER_FAILED`，但避免把敏感 server diagnostics 暴露給學生。

---

## 15. TrussSolveResult Contract

```text
TrussSolveResult
- solver_version
- input_schema_version
- node_displacements[]
- support_reactions[]
- member_axial_forces[]
- diagnostics
```

### 15.1 Node Displacement

```text
NodeDisplacement
- node_id
- ux_mm
- uy_mm
```

【Recommended】

Teaching/Application 可另計：

```text
magnitude_mm = sqrt(ux² + uy²)
```

不應用四捨五入後值做後續 mechanics calculation。

### 15.2 Support Reaction

```text
SupportReaction
- node_id
- rx_N
- ry_N
```

只輸出被 restraint 產生的 reaction；若 API 最終希望固定欄位，也可對自由方向回 0，但 contract 必須全局一致。

### 15.3 Member Axial Force

```text
MemberAxialForce
- member_id
- axial_force_N
```

Sign：

- positive = tension
- negative = compression

---

## 16. Diagnostics

【Recommended】

最低可包含：

- total_dof
- free_dof
- restrained_dof
- equilibrium residual metrics
- optional condition indicator（若可靠且有 benchmark）

P0 不必暴露完整 global K matrix 給一般 UI。

### Equilibrium Diagnostics

至少允許 benchmark 檢查：

- ΣFx residual
- ΣFy residual

【Future Frame】

ΣM global equilibrium 在 Frame benchmark 中更重要；Truss P0 若可穩定計算也可測，但不為了 research 舊規格擴張 solver UI。

---

## 17. Postprocess: Stress

【Confirmed】

```text
stress_MPa = axial_force_N / A_mm2
```

Sign convention 與 N 一致。

結果：

```text
MemberStress
- member_id
- axial_stress_MPa
- state: TENSION | COMPRESSION | ZERO
```

【Recommended】

ZERO 使用 numeric tolerance 決定，不用 `value == 0`。

Tension/compression label 是 deterministic numerical interpretation，不需要 LLM。

---

## 18. Postprocess: Mass

【Confirmed】

member mass：

```text
mass = density × A × L
```

在固定 units 下：

```text
(g/mm³) × (mm²) × (mm) = g
```

結果：

```text
MemberMass
- member_id / physical_member_mapping
- length_mm
- mass_g
```

Total mass 為 sum。

### Mapping Note

若一根 PhysicalMember 被 idealize 成多個 Truss Members，報告 physical mass 時不可重複計算；mass owner 應以 physical geometry/section 為基準，或透過明確 mapping aggregation。

---

## 19. Euler Buckling Screening

【Confirmed】

Euler 屈曲是 **screening**，不是 nonlinear stability analysis，也不是真實破壞荷載保證。

基本形式：

```text
Pcr = π² E I / (K L)²
```

### Required Inputs

```text
BucklingInput
- member_id
- E_MPa
- I_mm4
- L_mm
- K
- compression_force_magnitude_N
```

### Output

```text
BucklingScreen
- member_id
- Pcr_N
- compression_force_N
- utilization_or_ratio
- numeric_context
```

【Open Decision / MECHANICS REVIEW REQUIRED】

以下暫不鎖死：

- `K` 的 default
- `K` 的自動推斷
- 哪個 I 為正式控制軸的 UI policy
- risk band thresholds
- beginner-facing risk wording細節

因此：

> Euler numerical module 可被開發與 unit tested with explicit `K` input，但產品自動 screening behavior 在 K policy 核定前不得視為完成。

---

## 20. TrussAnalysisResult Aggregate

【Recommended】

Application 可將純計算輸出組合成：

```text
TrussAnalysisResult
- solve_result
- member_stresses
- member_states
- member_masses
- total_mass_g
- buckling_screens[]
- validation_issues[]
```

其中：

- `solve_result` 為 authoritative numerical solver result。
- buckling screening 只對 compression member 有意義。
- TeachingInsight 不屬於此 mechanics aggregate。

---

## 21. Physical-to-Analysis Mapping Contract

【Recommended】

Idealizer 應回傳：

```text
IdealizationResult
- truss_model
- mapping
- idealization_warnings
```

mapping 最少支持：

```text
analysis_node_id → physical connection/geometry entity
analysis_member_id → physical_member_id
physical_member_id → analysis_member_ids[]
```

目的：

- 結果回映 SVG。
- 一根 PhysicalMember 被拆分後仍能顯示 physical identity。
- Future Frame 可使用自己的 mapping contract，不需要改 persistence identity。

---

## 22. Canonical Input Hash

【Confirmed】

每次 AnalysisRun 必須有 ModelHash / InputHash。

【Recommended】

hash 對 canonicalized solver-relevant input 生成，至少包含：

- analysis type
- schema version
- node coordinates
- topology
- E/A
- restraints
- nodal loads
- relevant postprocess properties if AnalysisRun 要宣稱完整可重現

Canonicalization 必須 deterministic。

不得直接 hash ORM object repr。

---

## 23. Numerical Precision Policy

【Recommended】

- 內部使用 NumPy float64。
- persistence/result display rounding 與 internal calculation 分離。
- Benchmark tolerance 由 TEST_ARCHITECTURE 定義，不用 UI 小數位數作正確性標準。
- 所有輸入需 finite；NaN/Inf 為 validation error。

P0 不引入 arbitrary precision。

---

## 24. Benchmark Gate

【Confirmed】

Mechanics completion 必須有 benchmark。

P0 建議 benchmark baseline：

### B/T01 — 單杆軸向拉壓

驗證：

- `δ = PL/EA`
- reaction
- axial force
- stress sign

### B/T02 — 簡單三角桁架

驗證：

- hand/textbook result
- reaction
- selected member forces
- node displacement

### B/T03 — 對稱平面桁架

驗證：

- symmetry
- reaction balance
- member force symmetry

### B/T04 — 簡單超靜定桁架

驗證：

- assembly
- restraint handling
- displacement/force against trusted reference

### B/S01 — Composite Section

驗證：

- A
- centroid
- Ix
- Iy

### B/E01 — Euler with explicit K

驗證：

- `Pcr` formula for known E/I/L/K

【Confirmed Resolution】

舊研究計畫中的：

- cantilever beam
- simply supported beam
- UDL beam
- portal frame
- N/V/M Frame benchmark

移至 Stage 2，不是 P0 gate。

---

## 25. Test Layers Expected by This Contract

### Unit

- element geometry/stiffness
- transformation
- assembly
- support reduction/application
- axial force recovery
- stress
- mass
- Euler formula explicit K
- section properties

### Benchmark

解析/手算/可信 reference。

### Property / invariant style checks

- equilibrium
- symmetry
- scaling behavior
- deterministic output for same input

### Failure tests

- zero length
- missing support
- singular mechanism
- invalid E/A
- bad references
- NaN/Inf

---

## 26. Teaching Error Mapping

【Confirmed】

Mechanics issue：

```text
code = SINGULAR_GLOBAL_STIFFNESS
```

Teaching example：

> 模型目前無法得到唯一位移解；可能存在剛體移動或機構。請檢查支座約束與構件是否真的在節點連接。

Solver 不直接回傳這段學生文案。

---

## 27. Frame Extension Boundary

【Future】

Frame 不透過在 Truss solver 中加入大量 if/else 實現。

```text
TrussModel → Truss2DSolver
FrameModel → Frame2DSolver
```

可共享：

- numeric tolerance helpers
- geometry vector helpers
- selected matrix utilities
- SectionProperties

不可強制共用：

- DOF definition
- element stiffness
- load vector logic
- end-force recovery
- support semantics
- benchmark suite

---

## 28. Explicitly Unsupported by This Contract

【Confirmed】

- rz
- Fixed support mechanics
- bending stiffness EI
- V / M
- member UDL
- member transverse point load
- 3D
- nonlinear
- P-Delta
- dynamics
- eigenvalue buckling
- code checking
- optimization

收到這些輸入時，不得「猜著算」；應由上層阻止或回 unsupported validation。

---

## 29. Completion Gate

`TRUSS_2D` 不應被標記為 mechanics-complete，除非：

1. Input contract 有 validation。
2. 所有核心 benchmark 通過預設 tolerance。
3. sign convention tests 通過。
4. reactions / displacement / N 可追溯。
5. singular model 有 structured failure。
6. Django-independent tests 可直接執行。
7. SolverVersion 可記錄。
8. input hash deterministic。
9. Teaching code 沒有進入 solver。
10. Euler product behavior 對 K 的未決事項被明確 gate，而不是暗藏預設。

---

## Approved reconciliation — Master O-001

**MECHANICS REVIEW REQUIRED**: Master O-001 includes effective length factor K, default/automatic K inference, controlling I / weak-axis selection policy, final risk bands and related beginner-facing wording. None is implicitly approved. M1 may verify `Pcr = π² E I / (K L)²` using explicit E, I, L and K; numerical section properties do not authorize automatic buckling-axis selection. Automatic product behavior remains blocked.
