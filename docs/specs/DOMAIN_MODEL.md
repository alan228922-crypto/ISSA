# DOMAIN_MODEL.md

## 0. 文件狀態

- 文件角色：核心 Entity、ownership、relationship、lifecycle、invariant 規格
- 階段：Truss-first P0 Domain Baseline
- 本文件描述 domain contract，不是 Django migration。
- Source of Truth：MASTER_SPEC.md v1.3；本 Domain Model 已完成 reconciliation。

### 狀態標記

- 【Confirmed】
- 【Recommended】
- 【Open Decision】
- 【Future】

---

## 1. Domain Map

```text
User
 ├── role
 └── EventMembership
        │
CompetitionEvent
        │
        └── Project
             ├── Material / Strip / Section references
             ├── Physical Model Draft
             │    ├── GeometryNode
             │    ├── PhysicalMember
             │    ├── Connection
             │    ├── Support
             │    └── NodeLoad
             │
             ├── Prediction
             ├── ModelRevision
             │     └── AnalysisRun
             │           ├── ValidationLog
             │           └── TeachingInsight
             │           └── Reflection (0..1)
             │
             └── ReportCompleteness
```

---

## 2. Identity and Ownership Rules

### 2.1 User

【Confirmed】

角色：

- `DEVELOPER`
- `MANAGER`
- `USER`

【Recommended】

核心欄位概念：

- id
- username
- password_hash（由 Django auth 管理）
- role
- must_change_password
- is_active
- created_at

Invariant：

1. 密碼不可 plaintext persistence。
2. Manager 不得建立 Developer / Manager。
3. User 帳號代表一支參賽隊伍，而不是隊伍內每位學生的個人登入帳號。
4. 權限判斷不可只依 role，還需要 Event relationship / Project ownership。

### 2.2 EventMembership

【Recommended】

用途：表示 User/Manager 與 Event 的關係。

概念欄位：

- user_id
- event_id
- membership_type / event_role
- active

需要支援：

- USER participation
- MANAGER assignment

Developer 為 global role，不強制每個 Event 都建立 membership。

Invariant：

- 同一 User + Event 不重複有效 membership。
- User project ownership 必須位於其 participation Event。

---

## 3. CompetitionEvent

【Confirmed】

至少管理：

- event name
- competition date
- event code
- start
- end
- purge date
- status

Lifecycle：

```text
DRAFT → ACTIVE → FINISHED_GRACE → PURGED
```

### Invariants

1. `purge_at = event end + 7 days` 為目前業務規則。
2. `PURGED` 後不應仍存在該 Event 可還原的 student Project Operational Data。
3. Event status transition 必須由 server-side service 控制。
4. Manager 只能管理被授權 Event。

【Recommended】

`event_code` 與 competition date 分開存在。username format 雖以日期組成，但不得把 username 當作 Event foreign key。

---

## 4. Project

【Confirmed】

Project 屬於：

- 一個 CompetitionEvent
- 一個 User/team owner

【Recommended】

核心欄位概念：

- id
- event_id
- owner_user_id
- name
- analysis_type
- status
- created_at
- updated_at

P0：

```text
analysis_type = TRUSS_2D
```

【Future】

```text
FRAME_2D
```

### Invariants

1. User 只能讀寫自己的 Project。
2. Manager 預設可讀 assigned Event 的 Projects，但不能修改學生 Project。
3. Developer 可全域管理。
4. Project 不直接表示 Analysis Model；它是 physical/design 工作空間。
5. Project 的 mutable draft 與 immutable ModelRevision 分離。

---

## 5. Material

【Confirmed】

至少：

- name
- E
- density
- tensile_strength
- compressive_strength
- source_type
- note

固定 units：

- E：MPa
- density：g/mm³
- strengths：MPa

### Invariants

【Recommended】

- E 必須為正。
- density 若用於 mass calculation，必須為非負且有明確值。
- strengths 可 persistence，但 P0 不因此自動升格為 professional code check。
- Material 修改不應改寫已存在 ModelRevision 內冻结之數值 snapshot。

### Ownership

【Recommended】

P0 最簡單方案：Material 由 Project 或 team scope 擁有，避免跨 Event 資料生命週期耦合。

若未來要做 global template library，另行設計；P0 不先做共享材料市集/中央庫。

---

## 6. Strip

【Confirmed】

資料關係保留：

```text
Material → Strip → Section
```

常見基礎 strip：1 × 6 mm bamboo，但必須可自定義。

【Recommended】

Strip 表示「可用來拼截面的物理條材定義」，不是 solver element。

概念欄位：

- id
- material_id
- name
- width_mm
- thickness_mm
- note

Invariant：

- width/thickness > 0
- Strip 不持有 global structure geometry position。

---

## 7. Section

【Confirmed】

Section Designer 必須保留。

需要支援概念：

- rectangular
- H / I type
- T type
- box type
- free composite strip section

至少計算：

- A
- centroid
- Ix
- Iy
- mass_per_length
- strong_axis
- weak_axis

### Domain Separation

【Recommended】

Section 由兩部分構成：

```text
SectionDefinition
        ↓
SectionPropertyEngine
        ↓
SectionProperties
```

- `SectionDefinition`：使用者建立的截面幾何/strip composition。
- `SectionProperties`：由 pure Python `mechanics.sections` 計算的 numeric properties。

### Invariants

1. A > 0。
2. Ix / Iy 不得為負。
3. computed property 必須可追溯到 section definition version/hash。
4. Truss P0 使用 A 於 EA / stress。
5. Euler 使用相應 I，但 `K` 規則尚未核定。
6. Future Frame 使用 I 於 EI，不需重做 Section domain。

【Open Decision】

Euler 對實際壓杆該取哪個 I、如何與有效長度/弱軸教學連動，需 Mechanics Review；架構只保留必要 property。

---

## 8. GeometryNode

【Confirmed】

GeometryNode 是 Physical Layer 幾何位置，不等於 solver node。

概念欄位：

- id
- project_id
- x_mm
- y_mm
- label/order（可選）

Invariant：

- 座標使用 mm。
- GeometryNode 位置可被多個 PhysicalMember 端點引用。
- 幾何重合不應自動等於 Connection，除非 authoring rule 明確建立 connection。

### Editable Draft deletion boundary (D-DRAFT-INDEPENDENCE-01)

【Confirmed】Project 對草稿物件的 ownership FK 仍使用 CASCADE；草稿物件彼此的可缺省引用使用 nullable `SET_NULL`。刪除 GeometryNode 只使相關 Member 端點和 Connection 位置成為未指定；刪除 Member 只留下 Connection 中的 nullable participation slot；刪除 Connection 只使 Support / NodeLoad 作用位置未指定。Material / Section 可刪除而 Member 留存；Strip 的 Material 可未指定。這些 incomplete 狀態可保存和重綁，但不是合法 canonical Analysis Snapshot。Model Check 與 Analyze 的嚴格邊界由 ADR-34 約束。

---

## 9. PhysicalMember

【Confirmed】

PhysicalMember 表示實體連續杆件概念，不等於 TrussElement。

概念欄位：

- id
- project_id
- start_geometry_node
- end_geometry_node
- material_id
- section_id
- label
- active

### Invariants

1. start/end 不可為同一位置形成零長度。
2. 必須有可解析 Material / Section 才能 Analyze。
3. 幾何交叉不自動建立 connection。
4. 中途 connection 可在 Idealization Layer 將一根 PhysicalMember 拆成多個 analysis elements。
5. Analysis result 回映 physical member 時需透過 mapping，不假設一對一。

---

## 10. Connection

【Confirmed】

Connection 是「這些 physical entities 在此處具有共同結構節點」的明確意圖。

### P0 Truss Meaning

- connection idealization = pinned
- 不帶 rotational DOF
- 不表示剛接

【Recommended】

Connection 可以引用：

- GeometryNode / connection location
- participating PhysicalMembers

P0 只需支援 Truss 所需的 joint semantics；不建立 generic connection plugin system。

【Future】

Frame 可能新增 rigid/pinned connection semantics，但應由 Frame idealization 擴充，不污染 P0 Truss solver。

---

## 11. Support

【Confirmed】

P0：

- Pinned
- Roller

Fixed 為 Future Frame。

【Recommended】

Physical Support 應綁定可 idealize 為 analysis node 的 connection/geometry location。

P0 解析結果：

- Pinned → restrain ux + uy
- Roller → restrained_axis=X 限制 ux；restrained_axis=Y 限制 uy

【Confirmed】P0 不支持任意角度 restraint。

---

## 12. Load

### 12.1 NodeLoad

【Confirmed】

P0 只要求：

- Node Force Fx
- Node Force Fy

固定 unit：N。

概念欄位：

- id
- project_id
- target physical node/connection
- fx_N
- fy_N
- note/label（可選）

Invariant：

- target 必須能 idealize 成 analysis node。
- Solver 只接收 nodal loads。

### 12.2 Self Weight

【Confirmed Deferred】

核心 P0 不實作。

【Future P0.x/P1】

若啟用：

- 以 equivalent nodal load 方式在 Solver 前轉換。
- 必須在 Teaching/UI 標示 idealization。
- 不新增 Truss member distributed load 到 solver contract。

### 12.3 Frame Loads

【Future】

- member UDL
- transverse point load
- bending/member load concepts

不進 P0。

---

## 13. Mutable Draft

【Recommended】

Project 現行建模內容為 mutable draft。

Draft 包含目前：

- nodes
- physical members
- connections
- supports
- node loads
- assignments

Draft 本身不是可重現分析證據。

---

## 14. ModelRevision

【Confirmed】

研究與可追溯性要求保留 ModelRevision。

【Recommended】

ModelRevision 為 immutable analysis checkpoint。

核心概念欄位：

- id
- project_id
- revision_number
- analysis_type
- source_draft_version
- physical_snapshot
- schema_version
- model_hash/input_hash
- created_by
- created_at

### Invariants

1. 建立後不可原地修改。
2. AnalysisRun 必須指向一個 ModelRevision。
3. 修改 Project Draft 不影響既有 ModelRevision。
4. Material / Section numeric properties 在 revision snapshot 中 freeze。
5. Purge 後 raw revision snapshot 必須依 Event policy 刪除。
6. Reuse identity 是 `(Project, source_draft_version, model_hash)`；僅相同 Project、相同 authoring draft、相同 content hash 才可 reuse。
7. 不同 `source_draft_version` 即使 snapshot、`model_hash` 與後續 `input_hash` 相同，也必須建立新的 immutable ModelRevision；`revision_number` 在 Project 內連續遞增。

---

## 15. Prediction

【Confirmed】

Prediction 位於 Analyze 之前的 Soft Gate 教學循環，綁定 `Project + source_draft_version`，而非 Analyze 後才存在的 ModelRevision。`DRAFT → COMPLETED|INVALIDATED`；COMPLETED immutable，舊 completed draft 為 derived stale historical evidence，不是 stored status。Prediction 不被 Solver 讀取。O-M5-P01 冻结每个 `(Project, source_draft_version)` 的 P0 cardinality 为 `0..1`；实现以应用层并发保护与兼容时的持久层唯一性保证创建。历史重复行不得删除、合并、改写或被任意选择；current discovery 必须 fail closed 为 `PREDICTION_AMBIGUOUS`。

P0 使用一個 versioned JSON aggregate，不建立 member/displacement/path 子表：所有 PhysicalMember 的 `TENSION|COMPRESSION|ZERO_FORCE|UNSURE`、一個 restricted PhysicalPointRef、和一條代表性 Connection/PhysicalMember alternating load-path hypothesis。`ZERO_FORCE` 是學生選項，不是 analysis classification。

`AnalysisRun.prediction` nullable FK 表示一個 Run 至多使用一個 completed Prediction；同一 Prediction 可連到同 draft 的多個 Run。完整 contract 見 `PREDICTION_AND_REVEAL_ARCHITECTURE.md`。

## 15.1 StudentResultReveal

【Confirmed】

`StudentResultReveal(Project, source_draft_version)` 以唯一約束記錄 student owner 首次獲得 SUCCESS numerical/classified result 的時間、Run 與 actor。它不保存結果資料。它阻止同 draft 的晚完成 Prediction；Manager/Developer read 不觸發。Prediction completion 和 reveal 共享 Project-row transaction lock。

---

## 16. AnalysisRun

【Confirmed】

AnalysisRun 是一次實際 mechanics execution 記錄。

核心關聯：

```text
ModelRevision 1 ── * AnalysisRun
SolverVersion 1 ── * AnalysisRun
Prediction 1 ── * AnalysisRun (nullable on Run)
```

概念欄位：

- id
- model_revision_id
- solver_version_id/value
- analysis_type
- started_at
- finished_at
- status
- input_hash
- result payload / normalized result
- diagnostics
- failure code

### Status

【Recommended】

```text
PENDING / SUCCESS / VALIDATION_FAILED / SOLVER_FAILED
```

不需要複雜 job queue state machine。

### Invariants

1. Run 不修改 revision。
2. Run 結果不可被 TeachingInsight 覆寫。
3. 相同 input_hash + solver_version 應具有可重現預期。
4. Purge 前可保留 raw result；Purge 後依 Operational policy 刪除。

---

## 17. SolverVersion

【Confirmed】

分析必須可追溯 SolverVersion。

【Recommended】

可以是 persistence entity 或 immutable version record，至少包含：

- analysis_type
- solver_version
- input_schema_version
- build/git reference（若可得）
- activated_at

不需要建立 plugin registry。

---

## 18. ValidationLog

【Confirmed】

用於：

- mechanics / model-check error code
- error category
- entity/context
- timestamp
- whether analyze blocked

【Recommended】

關聯：

- Project
- optionally ModelRevision
- optionally AnalysisRun

Purge 前可保存 operational detail。

Purge 後 research 只保留匿名 aggregated/derived error metrics，例如：

- error type count
- first-pass success
- correction count

不得保留可重建完整 raw model 的 payload。

---

## 19. TeachingInsight

【Recommended】

TeachingInsight 是 deterministic interpretation output。

關聯：

- AnalysisRun
- source metric/entity
- insight type
- severity/priority（教學排序，不等於 failure probability）
- message key / rendered text

Invariant：

- source numerical result immutable。
- insight 可重算，不應成為 mechanics authority。
- 「風險」不得表述為確定破壞。

---

## 20. Reflection integrates P0 Design Rationale

The older separate `DesignRationale` record is **SUPERSEDED for M4C P0**. The authoritative aggregate is one `Reflection` per AnalysisRun (`AnalysisRun 1 → 0..1 Reflection`), with `next_iteration_intent` serving as P0 Design Rationale. Reflection is traceable to source draft through its Run and ModelRevision, but is not identified by draft version.

There is no independent DesignRationale model, second lifecycle, comparison-set binding, or DesignIteration domain. A future independent rationale design needs a new architecture decision. The full `reflection-v1` lifecycle, eligibility, visibility, and purge contract lives in `REFLECTION_AND_RATIONALE_ARCHITECTURE.md`.

---

## 21. ReportCompleteness

【Confirmed】

平台只輔助計算書，不替學生完成設計論證。

【Recommended】

ReportCompleteness 記錄各必要部分是否已準備，例如：

- model assumptions
- material/section
- load/support
- force/displacement result
- stability
- comparison
- rationale

學生端以「缺漏/準備度」呈現，不用自動給假的完整品質分數。

---

## 22. ResearchDerivedMetric

【Confirmed】

Product Owner 已確認 purge 後保留方案 B：匿名化 derived metrics。

【Recommended】

允許例：

- anonymized event/team research key
- analysis count
- first-pass success
- error counts by category
- max displacement summary
- tension/compression member counts
- buckling screening summary count
- task duration
- design reasoning score
- report completeness score
- SUS / concept score（若研究正式收集且符合倫理要求）

不允許：

- full node coordinates
- full member connectivity
- complete load/support snapshot
- raw section layout sufficient to reconstruct project
- original student identifier
- captain student ID

---

## 23. Account Provisioning Domain

【Confirmed】

username：

```text
competition_date(YYYYMMDD) + team_no(2 digits)
```

初始密碼：隊長學號。

首次登入強制修改。

### BulkImportBatch

【Recommended】

不必先做複雜 import framework，可有最小 batch 概念：

- uploaded_by
- event
- parsed row count
- validation summary
- confirmed_at
- result summary

建立必須 transaction all-or-nothing。

Audit log 不保存 plaintext password。

---

## 24. Purge Domain Rules

【Confirmed】

Event 結束 7 天後清除參賽 Project data。

【Recommended】

Purge domain operation處理順序概念：

1. verify event eligible
2. extract approved anonymous derived research metrics（若 research enabled）
3. delete operational child data
4. delete/disable team-specific project relation as policy requires
5. set event `PURGED`
6. persist purge audit summary

### Invariants

- 重複 purge 安全。
- 單一 Project 以 `purge_project_operational_data(project_id, actor_id=None)` 為邊界；有受保護歷史關聯時直接 `Project.delete()` 不受支援。保留 `PROTECT`，依序刪除 Reflection、Reveal、ValidationLog、AnalysisRun、Prediction/ModelRevision、物理草稿子資料，最後 Project；User、Material、Section、SolverVersion 保留。
- 同一交易保存 `ProjectOperationalPurgeAudit`：unique primitive project ID、primitive event ID、時間、刪除類型/數量 JSON、optional primitive actor ID；不引用被刪 Project、不保存 raw payload。重跑回傳首次 audit；失敗全部回滾。
- Purge audit 可保留「何時、哪個 Event、刪除類型/數量」等 metadata，但不保留被刪 raw payload。
- User account 是否一併刪除/停用可在 Authorization/Event Spec 再細化；Project raw data purge 不能受此未決項阻擋。

---

## 25. Frame Extension Domain Seam

【Future】

不需重做：

- Event/User/Project
- Material/Strip/Section
- GeometryNode/PhysicalMember/Connection
- Revision/Run
- learning/report/research high-level entities

Frame 專屬概念應新增在 idealization/mechanics contract：

- rotational DOF `rz`
- Fixed support
- rigid connection
- EI
- V/M
- member transverse loads

避免把現在的 Truss domain entity 加上一堆 null frame-only 欄位。

---

## 26. Domain Invariant Summary

Codex 後續實作至少要有 tests 保證：

1. User 不可跨 Project ownership 存取。
2. Manager 不可修改 student Project（除非未來明確授權）。
3. Intersection 不自動 Connection。
4. PhysicalMember 不等於 AnalysisElement。
5. ModelRevision immutable。
6. AnalysisRun 永遠指向 Revision + SolverVersion。
7. Material/Section 修改不 retroactively 改舊 Revision。
8. Purge 可重跑且不保留 raw student model。
9. TeachingInsight 不修改 numerical result。
10. P0 Load 僅 Node Force。
11. P0 Analysis Type 僅 TRUSS_2D。
12. Euler K 未核定前不得暗藏 production default。

---

## 27. Open Domain Decisions

### OD-01 — Euler effective length factor `K`

【Open Decision / MECHANICS REVIEW REQUIRED】

老師/Mechanics Reviewer 決定後才能鎖定。

### Resolved — Roller orientation capability（Master O-002）

P0 Support contract 已冻结为 ROLLER + restrained_axis X/Y。

### OD-03 — Event purge 後 team account lifecycle

【Open Decision, non-blocking for mechanics】

Project raw data purge 已確定；帳號是否停用、刪除或留作 event archive identity，可在 Authorization/Event Spec 決定。

---

## 28. Safe Deferrals

可以安全延期而不阻礙 Truss P0：

- Self Weight
- Frame2D
- Fixed support
- member loads
- global material library
- team collaboration
- realtime editing
- advanced revision diff UI
- API-first architecture
- PostgreSQL-specific optimization
- async queue
- automatic design

---

## Approved reconciliation — Master O-001

**MECHANICS REVIEW REQUIRED**: Master O-001 includes effective length factor K, default/automatic K inference, controlling I / weak-axis selection policy, final risk bands and related beginner-facing wording. None is implicitly approved. M1 may verify `Pcr = π² E I / (K L)²` using explicit E, I, L and K; numerical section properties do not authorize automatic buckling-axis selection. Automatic product behavior remains blocked.
