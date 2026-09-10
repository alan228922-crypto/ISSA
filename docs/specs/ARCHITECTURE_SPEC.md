# ARCHITECTURE_SPEC.md

## 0. 文件狀態

- 文件角色：平台總體軟體架構規格
- 階段：Architecture Baseline / Truss-first P0
- 狀態：可供後續規格細化與 Codex 實作規劃使用；**不是 production code**
- 優先原則：最新確認之 Truss-first 決策 > 舊 Frame-first 研究描述
- Source of Truth：`MASTER_SPEC.md v1.0`；本 Architecture Spec 已完成 reconciliation。

### 狀態標記

- 【Confirmed】：Product Owner 已確認或目前專案明確既定條款。
- 【Recommended】：System Architect 技術建議；不得改寫 MASTER_SPEC 的產品語意或 Open Decision。
- 【Open Decision】：尚未核定，不得在 production behavior 中偷偷寫死。
- 【Future】：明確不屬於 P0，但需留下清楚 extension seam。

---

## 1. Architecture Objective

【Confirmed】

平台為面向結構設計競賽初學者的 **Truss-first Progressive Structural Learning Platform**。P0 核心是：

- 2D Linear Elastic Truss
- Predict → Analyze → Explain → Compare → Reflect
- 支座反力、節點位移、桿件軸力、拉壓、應力、重量、Euler 屈曲篩查
- 教學解釋與計算書輔助
- 不把 AI 當作 solver authority
- 不擴張為通用 FEM、3D、最佳化或專業規範檢核軟體

【Recommended】

系統採用：

> **Django Modular Monolith + Application/Idealization Layer + Pure Python Mechanics Core**

理由：

1. 保持 PoC 部署與除錯簡單。
2. Mechanics 可脫離 Django 獨立測試。
3. Physical Model 與 Truss Analysis Model 不綁死。
4. 未來可新增 Frame kernel，而不重做 Event/User/Project/Material/Section/Revision/Research 架構。
5. 不需要 microservice、CQRS、event sourcing、message queue 等 P0 無收益複雜度。

---

## 2. Top-level Architecture

```text
Browser
  │
  ├── Django Templates / HTML / CSS
  ├── Vanilla JavaScript
  └── SVG Canvas
  │
  ▼
Django Presentation Layer
  │
  ├── Forms / Pages
  └── Small JSON Endpoints
  │
  ▼
Application Services
  │
  ├── Authorization
  ├── Event / Account Provisioning
  ├── Project / Model Editing
  ├── Revision / Analysis Orchestration
  ├── Teaching / Comparison
  └── Report / Research Extraction
  │
  ▼
Physical Snapshot
  │
  ▼
Idealization Layer
  │
  ├── Truss2D Idealizer                  [P0]
  └── Frame2D Idealizer                  [Future]
  │
  ▼
Pure Python Mechanics Core
  │
  ├── common
  ├── sections
  ├── truss2d                           [P0]
  ├── stability                         [P0]
  └── frame2d                           [Future]
  │
  ▼
Numerical Result
  │
  ├── Teaching Interpretation
  ├── Comparison
  ├── Report
  └── Research Derived Metrics
```

---

## 3. Dependency Direction

【Confirmed】

核心依賴方向必須為：

```text
Django / UI
   ↓
Application Services
   ↓
Idealization
   ↓
Mechanics Core
```

### 3.1 禁止反向依賴

以下情況禁止：

- `mechanics` import Django ORM model。
- `mechanics` import Django settings / request / session。
- Django View 直接組裝 stiffness matrix。
- JavaScript 實作 authoritative solver。
- Teaching rule 修改 mechanics 原始數值。
- ORM entity 本身同時充當 `TrussMember` solver object。

### 3.2 可接受的依賴

- Django Application Service 將 ORM state 轉成 immutable physical snapshot。
- Idealizer 將 physical snapshot 轉成 `TrussModel`。
- Mechanics Core 接收 pure Python input，回傳 pure Python result。
- Application Service 將 result persistence 化，再交給 Teaching Layer 解讀。

---

## 4. Django App Boundaries

【Recommended】

P0 採下列粗粒度 Django apps；不採「一個 entity 一個 app」。

### `accounts`

責任：

- custom User
- global role：Developer / Manager / User
- password lifecycle
- `must_change_password`
- authentication integration
- 帳號稽核相關最小欄位

不得負責：

- Event-specific authorization rule
- Project ownership rule
- Mechanics

### `competitions`

責任：

- CompetitionEvent
- EventMembership / Manager assignment
- Event lifecycle
- bulk User provisioning
- purge orchestration / audit

### `projects`

責任：

- Project
- Project ownership
- Project status
- analysis type selection（P0 唯一可選 `TRUSS_2D`）

### `materials`

責任：

- Material
- Strip
- Section
- Section definition
- Section calculated properties persistence / cache policy

### `modeling`

責任：

- GeometryNode
- PhysicalMember
- Connection
- Support
- NodeLoad
- mutable Project Draft

### `analysis`

責任：

- ModelRevision
- AnalysisRun
- SolverVersion
- ValidationLog
- input hash / model hash
- analysis orchestration
- numerical result persistence

### `learning`

責任：

- Prediction
- Reflection
- DesignRationale
- TeachingInsight
- deterministic result interpretation
- comparison metadata

### `reports`

責任：

- calculation report data package
- ReportCompleteness
- report preparation status

### `research`

【Recommended, conditional P0】

只在研究資料留存真的啟用時建立。只保存匿名化 derived metrics，不保存可重建完整學生模型之 raw snapshot。

不得成為 Operational Data 的永久備份。

---

## 5. Pure Python Modules

【Recommended】

```text
mechanics/
├── common/
│   ├── geometry
│   ├── numeric
│   └── conventions
├── sections/
│   ├── model
│   ├── properties
│   └── validation
├── truss2d/
│   ├── model
│   ├── validation
│   ├── assembly
│   ├── solver
│   ├── postprocess
│   └── errors
└── stability/
    ├── euler
    └── errors
```

【Future】

```text
mechanics/frame2d/
├── model
├── validation
├── assembly
├── solver
├── postprocess
└── errors
```

### 5.1 不建立 Generic FEM Framework

【Confirmed / YAGNI】

P0 不建立：

- `GenericElement`
- universal DOF registry
- generic element plugin
- multi-dimensional mesh framework
- solver service API
- dependency injection container

Truss2D 與 Future Frame2D 可共享少量 geometry/numeric utilities，但 mechanics kernel contract 與 benchmark 必須獨立。

---

## 6. Physical → Idealization → Analysis Separation

### 6.1 Physical Layer

【Confirmed】

Physical Layer 表示學生認為自己「做了一根什麼、在哪裡、在哪裡連接」。

核心概念：

- GeometryNode：幾何定位點
- PhysicalMember：實體連續構件
- Connection：明確的結構連接意圖
- Section / Material assignment
- Support
- NodeLoad

### 6.2 Intersection ≠ Connection

【Confirmed】

兩根線段幾何交叉不自動產生 joint。

```text
PhysicalMember A ───────
                    ╳
PhysicalMember B     │

幾何相交 ≠ 結構連接
```

只有顯式 Connection 才可在 Idealization 中產生共用 analysis node。

### 6.3 PhysicalMember ≠ AnalysisElement

【Confirmed】

一根 PhysicalMember 可能因中途 Connection 被理想化拆分成多個 analysis elements。

P0 Idealizer 可以只實作目前 Truss 所需的最小拆分規則，但 persistence model 不得永久將 PhysicalMember 與 TrussElement 一對一寫死。

### 6.4 Idealization Layer

【Recommended】

Idealizer 負責：

1. 讀取 immutable physical snapshot。
2. 驗證 Physical → Analysis 映射前提。
3. 根據明確 Connection 將 physical geometry 轉為 analysis topology。
4. resolve Material / Section 到數值 properties。
5. 將 Support / NodeLoad 映射到 analysis node。
6. 產生 `TrussModel`。
7. 保留 physical entity → analysis entity mapping，供結果回映 UI。

Idealizer **不解方程**。

---

## 7. Analysis Orchestration

【Recommended】

一次 Analyze 流程：

```text
User clicks Analyze
  ↓
Server-side authorization
  ↓
Validate mutable draft completeness
  ↓
Freeze immutable ModelRevision
  ↓
Build canonical physical snapshot
  ↓
Compute input/model hash
  ↓
Truss2D Idealizer
  ↓
Mechanics validation
  ↓
Truss2DSolver
  ↓
Postprocess: stress / mass / stability
  ↓
Persist AnalysisRun + numerical result
  ↓
Teaching deterministic interpretation
  ↓
Return result view model
```

### 7.1 Revision Rule

【Recommended】

- Project Draft：可變。
- ModelRevision：不可變。
- 不在每個滑鼠拖曳時建立 revision。
- 至少在 Analyze 時建立/鎖定 revision。
- 額外 checkpoint 是否提供 UI，可延後。

### 7.2 Analysis Traceability

【Confirmed】

每個成功或失敗的 AnalysisRun 至少可追溯：

- Project
- ModelRevision
- analysis_type
- schema_version
- solver_version
- input_hash
- timestamps
- validation outcome
- numerical result / failure code

---

## 8. Solver Versioning

【Recommended】

`SolverVersion` 不代表每次網站部署版本，而是 mechanics behavior 可識別版本。

至少紀錄：

- solver name：`TRUSS_2D`
- solver semantic/version string
- input schema version
- optional git commit/build reference（若部署流程可提供）

只要會改變數值結果、sign convention、validation semantics 或 solver contract，就應更新可追溯版本。

---

## 9. Teaching Layer Separation

【Confirmed】

Mechanics Core 負責：

- mechanics validation
- stiffness
- solve
- reaction
- axial force
- stress calculation
- Euler screening calculation
- numerical diagnostics

Teaching Layer 負責：

- beginner-facing explanation
- tension/compression explanation
- max displacement explanation
- prediction comparison
- model-check educational text
- report completeness
- reflection prompt
- design comparison explanation

### 9.1 不可修改原始結果

TeachingInsight 必須保留 source metric reference，例如：

```text
insight:
  type = "MAX_DISPLACEMENT"
  source_analysis_run = ...
  source_metric = "node_displacement_magnitude"
  source_entity = "analysis_node:N7"
```

Teaching Layer 不得把 numerical result 改成「較合理」的值。

### 9.2 P0 AI Policy

【Confirmed】

P0 優先 deterministic rules + explicit source metrics。

LLM 不參與 mechanics correctness 判斷，不成為 solver fallback。

---

## 10. Authorization Architecture

【Confirmed】

所有存取控制 server-side 驗證。

```text
Developer
  └── global management

Manager
  └── assigned Event(s)
      ├── manage authorized Event
      ├── create/bulk create User
      └── read projects in Event
          └── no student project write by default

User
  └── own team account
      └── own Project only
```

【Recommended】

Event-level permission 不只依 `User.role`，必須有 Event assignment / membership relation。

View、JSON endpoint、service 都不得直接用前端傳來的 project ID 當 authorization proof。

---

## 11. Competition Event Lifecycle

【Confirmed】

```text
DRAFT
  ↓
ACTIVE
  ↓
FINISHED_GRACE
  ↓
PURGED
```

比賽結束後 7 天清除該 Event 的參賽 Project Operational Data。

### 11.1 Purge Implementation

【Recommended】

PoC 不使用 Celery。

使用：

- Django management command
- OS cron / deployment scheduler
- `PurgeService`

PurgeService 必須：

- idempotent
- transactional at appropriate boundary
- auditable
- authorization-independent（系統任務）
- 對已 PURGED Event 重跑安全

### 11.2 Operational / Research Separation

【Confirmed】

Product Owner 已選擇：

> Purge 後只保留匿名化 **derived mechanics / research metrics**；不保留 raw student model snapshot。

因此 research storage 不得包含足以完整重建被 purge Project 的原始 geometry/member/load snapshot。

---

## 12. Account Provisioning

【Confirmed】

隊伍 username：

```text
YYYYMMDD + two-digit team number
```

初始密碼：隊長學號。

首次登入後強制修改密碼。

只保存 password hash；不保存 plaintext；管理員不能查看現有密碼。

### 12.1 Bulk Provisioning

【Confirmed / Recommended】

CSV workflow：

```text
Upload
  ↓
Parse
  ↓
Preview
  ↓
Validation
  ↓
Duplicate detection
  ↓
Explicit confirm
  ↓
Single transactional create
  ↓
Audit record
```

若 confirm 階段任何 row 不符合 blocking rule：

> all-or-nothing，不部分建立。

Preview 階段可顯示帳號與來源欄位，但完成建立後不得提供「查看目前密碼」。

---

## 13. Front-end / Endpoint Strategy

【Recommended】

P0 不採 SPA，不導入 DRF 作為必要前提。

### 普通 Django Form / Page

適合：

- Login / force password change
- Event CRUD
- User management
- Bulk CSV upload/preview/confirm
- Material metadata
- Project metadata
- Prediction
- Reflection
- Report view

### Small JSON Endpoints

只用於明顯互動狀態：

- model draft save
- model check
- analyze
- result visualization payload
- section property preview（若 Section Designer 需要即時回饋）

【Future】

若後續真的需要獨立客戶端，再評估 API strategy；P0 不做複雜 versioned REST API。

---

## 14. Validation Architecture

【Recommended】

分三層：

### Layer A — Authoring / Persistence Validation

例：

- required field missing
- malformed coordinate
- unknown section reference
- duplicate team number in import

### Layer B — Mechanics Validation

穩定 machine-readable code，例如：

- `ZERO_LENGTH_MEMBER`
- `DUPLICATE_ANALYSIS_MEMBER`
- `INVALID_YOUNGS_MODULUS`
- `INVALID_AREA`
- `UNSUPPORTED_SUPPORT_FOR_TRUSS`
- `INSUFFICIENT_RESTRAINT`
- `SINGULAR_GLOBAL_STIFFNESS`

Mechanics error 不包含 UI 教學策略。

### Layer C — Teaching Interpretation

把 code + context 轉成 beginner-facing message，例如：

> 「模型可能存在剛體移動或機構，請檢查支座是否提供足夠約束，以及杆件是否真的在節點連接。」

必須保留原 error code 供測試、稽核與 research metrics。

---

## 15. Data Retention Boundary

【Confirmed】

Purge 前：

- Project Draft
- Physical model
- ModelRevision raw snapshot
- AnalysisRun raw input/result
- Validation logs
- learning records
- report operational data

可存在 Operational DB。

Purge 後：

- 原始 Project/Revision/Analysis raw reconstruction data：刪除。
- Research：只允許匿名 derived metrics（已核定 B）。
- 研究保留期限與最終刪除政策：應在研究倫理/研究計畫正式啟用前再定。

---

## 16. Frame Extension Seam

【Future】

共用：

- User
- Role
- Event
- Project
- Material
- Strip
- Section
- GeometryNode
- PhysicalMember
- Connection
- general load ownership concept
- ModelRevision
- AnalysisRun
- Prediction
- Reflection
- Report

新增而非污染 Truss kernel：

```text
physical snapshot
   ├── Truss2DIdealizer → TrussModel → Truss2DSolver
   └── Frame2DIdealizer → FrameModel → Frame2DSolver
```

Frame 新增：

- `rz`
- Fixed
- rigid connection semantics
- EI
- V / M
- transverse member loads
- bending deformation

P0 不提前實作。

---

## 17. P0 Explicit Non-goals

【Confirmed】

不設計或實作：

- 3D / 3D Frame
- topology optimization
- automatic optimization
- contact FE
- glue nonlinear mechanics
- torsion
- dynamics / modal
- plasticity
- P-Delta
- large deformation
- eigenvalue buckling
- plate/shell/solid
- WebSocket / realtime collaboration
- microservices
- message queue / Redis / Celery
- AI automatic design
- professional design code checking

---

## 18. Deferred Items

【Confirmed】

Self Weight 不屬於核心 P0。

【Future / P0.x or P1】

若啟用 Self Weight：

- 由 member mass 等效分配到端節點。
- 必須標示為 idealization。
- 不改變 Truss solver contract 的「只接收 nodal load」原則；self-weight conversion 發生在 solver 之前。

【Open Decision / MECHANICS REVIEW REQUIRED】

Euler effective length factor `K` 的正式規則尚未核定。

在核定前：

- 可以在 stability contract 中保留 `K` 參數位置。
- 不得把 UI 預設、自動推斷與風險分級寫死。
- Euler production-ready gate 必須等待老師/Mechanics Reviewer 確認。

---

## 19. Architecture Guardrails for Codex

後續 Codex 實作必須遵守：

1. 不把 ORM model 傳進 mechanics solver。
2. 不在 View/JS 寫 stiffness/solve。
3. 不把 PhysicalMember 當 TrussElement persistence。
4. 不因 Future Frame 建 generic FEM framework。
5. 不新增 P0 scope 未核定之 Fixed、M、V、UDL、rz。
6. AnalysisRun 必須連到 immutable ModelRevision。
7. numerical result 與 TeachingInsight 分開存取。
8. authorization 必須 server-side testable。
9. purge 必須 idempotent。
10. mechanics 行為沒有 benchmark 不得視為完成。

---

## 20. SPEC CONFLICT Register

### SC-01 — Frame-first Research Plan vs Truss-first P0

【Confirmed Resolution】

舊研究文件中的 2D Frame、N/V/M、Fixed、梁與剛架 benchmark 移至 Stage 2。

P0 Research 只使用 Truss-compatible 技術與概念指標。

### SC-02 — Research raw snapshot vs Event purge

【Confirmed Resolution】

Purge 後只保留匿名化 derived metrics，不保留 raw model snapshot。

### SC-03 — MASTER_SPEC establishment

【Resolved】

`MASTER_SPEC.md v1.0` 已建立並完成 reconciliation。本文件若日後與 MASTER_SPEC 衝突，仍不得自行融合；必須新增 conflict record。

---

## 21. Acceptance Criteria for This Architecture

符合本架構的 P0 應滿足：

- Truss mechanics 可在無 Django 環境測試。
- Django 不包含 solver mathematics。
- Physical model 可不改 schema 核心概念地支援 Future Frame idealizer。
- 每個分析結果可追到 revision / input hash / solver version。
- student project access 與 purge 不依賴前端自覺。
- Teaching Layer 不修改 numerical result。
- Truss benchmarks 是 mechanics completion gate。
- P0 不被未來 Frame 拖入過度抽象。

---

## Approved reconciliation — Master O-001

**MECHANICS REVIEW REQUIRED**: Master O-001 includes effective length factor K, default/automatic K inference, controlling I / weak-axis selection policy, final risk bands and related beginner-facing wording. None is implicitly approved. M1 may verify `Pcr = π² E I / (K L)²` using explicit E, I, L and K; numerical section properties do not authorize automatic buckling-axis selection. Automatic product behavior remains blocked.
