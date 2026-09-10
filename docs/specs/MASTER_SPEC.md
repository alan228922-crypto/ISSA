# MASTER_SPEC.md

## 0. 文件資訊

- 專案名稱：校內結構設計競賽互動式分析與學習平台
- 文件角色：專案最高層級總規格（Current Source of Truth）
- 版本：v1.0
- 狀態：**CURRENT / APPROVED BASELINE — 專案最高層級 Source of Truth**
- 核准日期：2026-09-10
- 目前產品路線：**Truss-first Progressive Structural Learning Platform**
- P0 核心分析類型：`TRUSS_2D`

> 本文件已由 Product Owner 指示執行升格，作為目前專案唯一最高層級 Source of Truth。
>
> 本文件管理產品方向、力學邊界、資料治理、角色權限、研究需求與架構原則；不取代各專項規格的細節。所有專項 CURRENT Specs、Implementation Plan 與後續程式碼不得與本文件衝突。
>
> `Open Decision` / `MECHANICS REVIEW REQUIRED` 仍保持未決狀態。正式 MASTER_SPEC 的存在不代表這些項目已被默認核准。

---

# 1. 規格治理與權威關係

## 1.1 狀態標記

本專案所有規格內容必須使用以下語意區分：

### 【Confirmed】

已由 Product Owner 明確確認，或已在目前最新專案方向中確立。

此類內容可作為後續設計、測試與實作基線。

### 【Recommended】

System Architect / Product / Mechanics / Research 等角色提出之建議。

在尚未獲 Product Owner 確認前，不得假裝成既定需求。

### 【Open Decision】

尚需 Product Owner、老師或指定 reviewer 決定。

不得由 Codex、開發者或 AI 擅自補上預設。

### 【Future】

已確認屬於未來擴充方向，但不屬於 P0。

必須保留清楚 extension seam，但不得為此提前擴充 P0 複雜度。

---

## 1.2 文件權威層級

【Confirmed】

正式 `MASTER_SPEC.md` 建立後，文件權威順序應為：

```text
MASTER_SPEC.md
    ↓
專項 CURRENT Specs
    ↓
Architecture Decision Register
    ↓
Implementation Plan
    ↓
Code / Tests / Migration
```

專項 CURRENT Specs 包括：

- `ARCHITECTURE_SPEC.md`
- `DOMAIN_MODEL.md`
- `DATA_CONTRACT.md`
- `TRUSS_SOLVER_CONTRACT.md`
- `AUTHORIZATION_AND_EVENT_ARCHITECTURE.md`
- `API_AND_APPLICATION_FLOW.md`
- `TEST_ARCHITECTURE.md`
- `FRAME_EXTENSION_STRATEGY.md`

若專項文件與 `MASTER_SPEC.md` 衝突：

> 不得自行融合，必須標記 `SPEC CONFLICT`。

---

## 1.3 舊規格處理原則

【Confirmed】

過去 Frame-first 研究計畫與目前 Truss-first 路線衝突之處，不再作為 P0 實作依據。

舊資料仍可作為：

- 歷史背景
- Stage 2 Frame 研究參考
- 教學研究方法參考

但不得重新把 P0 改回 Frame-first。

---

# 2. 產品定位

## 2.1 核心定位

【Confirmed】

本平台是：

> **面向結構設計競賽初學者的互動式結構力學學習平台。**

平台不是以「提供最多分析功能」為目標，而是透過可靠的結構分析後台，引導學生建立結構力學理解。

---

## 2.2 平台不是什麼

【Confirmed】

本平台不是：

- 縮小版 MIDAS
- 縮小版 SAP2000
- 通用 FEM 軟體
- topology optimization 工具
- automatic structural optimization 工具
- AI 自動設計工具
- 專業結構設計規範檢核工具

---

## 2.3 核心價值

【Confirmed】

平台應協助學生：

- 建得對
- 看得懂
- 比得出
- 寫得出

並把重點從「操作專業軟體」轉回：

- 結構體系
- 荷載傳遞
- 拉壓
- 位移
- 截面
- 穩定
- 設計推理

---

# 3. 教學循環

## 3.1 固定教學流程

【Confirmed】

核心學習循環為：

```text
Predict
→ Analyze
→ Explain
→ Compare
→ Reflect
```

---

## 3.2 教學原則

【Confirmed】

平台不替學生決定「最佳設計」。

平台的分析結果應作為：

- 理解工具
- 比較工具
- 設計推理依據
- 計算書資料來源

而不是：

- 自動設計
- 自動最優化
- 自動替學生完成設計論證

---

# 4. 發展路線

## 4.1 Stage 1 — Truss Learning Platform

【Confirmed】

第一階段核心：

> **2D Truss Learning Platform**

教學重點：

- 結構體系
- 靜力平衡
- 支座反力
- 荷載傳遞
- 拉杆 / 壓杆
- 節點位移
- 軸向應力
- Euler 屈曲篩查
- 模型重量
- Predict → Analyze → Explain → Compare → Reflect

---

## 4.2 Stage 2 — Frame Extension

【Future】

未來逐步增加：

- rotational DOF `rz`
- Fixed support
- rigid connection
- EA + EI
- shear force V
- bending moment M
- member transverse load
- bending deformation
- stiffness distribution
- compatibility
- statical indeterminacy
- Truss vs Frame idealization comparison

---

## 4.3 Truss-first 原則

【Confirmed】

> Truss-first ≠ 永遠只做 Truss。

目前架構必須做到：

- P0 足夠簡單
- 不提前實作 Frame mechanics
- 未來加入 Frame 時，不需要重做：
  - User
  - Event
  - Project
  - Material
  - Strip
  - Section
  - Physical Geometry
  - Revision
  - AnalysisRun
  - Learning
  - Research
  - Report

---

# 5. P0 Mechanics Scope

## 5.1 分析模型

【Confirmed】

P0：

> **2D Linear Elastic Truss**

---

## 5.2 基本假設

【Confirmed】

- 2D
- small displacement
- linear elastic
- ideal truss member
- member carries axial force only
- ideal pinned joint
- node DOF = `ux`, `uy`
- member stiffness based on `EA/L`
- loads applied at nodes
- no member bending moment
- no member shear force
- no rotational DOF

---

## 5.3 Solver 基本方程

【Confirmed】

使用二維桁架直接剛度法：

```text
K u = P
```

核心輸出：

- node displacement
- support reaction
- member axial force

---

# 6. 單位系統

【Confirmed】

P0 固定使用：

| Quantity | Unit |
|---|---|
| length | mm |
| force | N |
| stress | MPa = N/mm² |
| E | MPa |
| area | mm² |
| second moment of area | mm⁴ |
| mass | g |
| density | g/mm³ |

P0 不提供多套 unit system 切換。

Mechanics Core 不負責自動 unit conversion。

---

# 7. Support

## 7.1 P0 Support

【Confirmed】

P0 只支援：

- Pinned
- Roller

---

## 7.2 Fixed

【Future】

Fixed support 主要留給 Stage 2 Frame。

P0 不實作 rotational restraint。

---

## 7.3 Roller Orientation

【Open Decision】

尚需確認：

- P0 Roller 是否只允許水平 / 垂直方向
- 或允許任意方向 restraint

在正式確認前：

> 不得由開發端自行泛化為任意角度 roller。

---

# 8. Load

## 8.1 P0 Node Load

【Confirmed】

核心 P0 只支援：

- Node Force `Fx`
- Node Force `Fy`

---

## 8.2 Self Weight

【Confirmed】

Self Weight 不屬於核心 P0。

【Future — P0.x / P1】

若啟用：

- 由 member self weight 換算為 equivalent nodal load
- 分配至 member 兩端 analysis nodes
- 必須明確標示為 idealization
- 不把 distributed self-weight 直接加入 Truss solver contract

---

## 8.3 Frame Loads

【Future】

以下不屬於 P0：

- Member UDL
- member transverse point load
- bending load
- node rotational load/restraint

---

# 9. Material

## 9.1 Material 自定義

【Confirmed】

Material 由使用者自行設定。

至少包含：

- name
- E
- density
- tensile strength
- compressive strength
- source_type
- note

---

## 9.2 Material 使用原則

【Confirmed】

材料參數不由平台假裝提供絕對真實值。

常見竹材可作為使用情境參考，但使用者仍需負責輸入適合其模型/試驗的參數。

---

# 10. Strip 與 Section

## 10.1 基礎 Strip

【Confirmed】

常見基礎材料幾何：

> `1 × 6 mm bamboo strip`

但系統必須允許使用者自定義。

---

## 10.2 資料關係

【Confirmed】

保留：

```text
Material
→ Strip
→ Section
→ Physical Member
```

---

## 10.3 Section Designer

【Confirmed】

Section Designer 是核心功能，不因第一階段是 Truss 而刪除。

至少需支援概念：

- rectangular section
- H / I type
- T type
- box type
- free composite strip section

---

## 10.4 Composite Section Properties

【Confirmed】

至少計算：

- A
- centroid
- Ix
- Iy
- mass / length
- strong axis
- weak axis

---

## 10.5 Section 在 Truss 與 Frame 的使用

【Confirmed】

P0 Truss：

- A → EA
- A → axial stress
- I → Euler buckling screening

【Future】

Frame：

- I → EI
- bending mechanics

因此 Section domain 必須跨 Truss / Frame 共用。

---

## 10.6 Composite Strip Overlap

【Open Decision】

若 free composite section 允許條材幾何重疊，需另外確認：

- 重疊面積是否允許
- 面積 / 慣性矩如何處理
- 是否視為建模錯誤

在正式決策前，不得默認實作 overlap union/subtraction mechanics。

---

# 11. Physical Model 與 Analysis Model

## 11.1 核心分層

【Confirmed】

必須保留：

```text
Physical Layer
↓
Idealization Layer
↓
Analysis Layer
```

---

## 11.2 Intersection ≠ Connection

【Confirmed】

兩根杆件在 2D 畫面上交叉：

> 不自動代表結構上相連。

只有使用者明確建立 Connection / Joint，才可產生分析上的共同節點。

---

## 11.3 Physical Member ≠ Analysis Element

【Confirmed】

PhysicalMember 不得永久與 TrussElement 綁成同一個 domain object。

未來若一根實體連續杆件中途有 Connection：

- UI 仍可視為一根 Physical Member
- Idealization Layer 可拆成多個 Analysis Elements

---

## 11.4 Geometry Node

【Confirmed】

GeometryNode 表示 Physical Layer 的幾何位置。

它不必然直接等於 Analysis Node。

---

# 12. Idealization Layer

## 12.1 職責

【Confirmed】

Idealization Layer 負責：

- 讀取 Physical Model snapshot
- 將 Connection 映射為 analysis topology
- 將 PhysicalMember 依需求拆分
- resolve Material / Section numerical properties
- 將 Support / Load 映射到 analysis model
- 產生 TrussModel
- 保留 physical ↔ analysis mapping

---

## 12.2 非職責

【Confirmed】

Idealization Layer 不負責：

- stiffness solve
- 教學說明
- 權限判斷
- UI drawing
- report writing

---

# 13. Mechanics Core

## 13.1 技術邊界

【Confirmed】

Mechanics Core 為：

> **Pure Python domain**

不得依賴：

- Django ORM
- request/session
- template
- browser
- JavaScript

---

## 13.2 P0 Mechanics Modules

【Recommended】

最低模組：

```text
mechanics/
├── common/
├── sections/
├── truss2d/
└── stability/
```

---

## 13.3 Future Frame

【Future】

新增：

```text
mechanics/frame2d/
```

必須有獨立：

- contract
- validation
- solver
- benchmark

---

## 13.4 Generic FEM 禁止

【Confirmed】

不得為了 Future Frame 建立過度泛化：

- universal FEM element base
- generic DOF registry
- plugin FEM framework
- solver microservice

除非未來明確有必要再重新評估。

---

# 14. P0 Analysis Pipeline Output

【Confirmed】

P0 **分析流程**至少輸出：

- node displacement
- support reaction
- member axial force N
- tension / compression state
- axial stress
- member / total mass
- Euler buckling screening

其中 authoritative `Truss2DSolver` kernel 的核心數值輸出為：

- node displacement
- support reaction
- member axial force N

其餘 stress / tension-compression classification / mass / Euler screening 由 pure-Python postprocess / stability modules 基於 solver result 計算，不由 Teaching Layer 產生。

---

## 14.1 Sign Convention

【Recommended】

目前建議：

- global +x = right
- global +y = up
- `N > 0` = tension
- `N < 0` = compression
- axial stress 採同一正負號

正式升格 `MASTER_SPEC.md` 前應與 Mechanics Spec 最終同步。

---

# 15. Euler Buckling Screening

## 15.1 定位

【Confirmed】

Euler 屈曲功能是：

> **buckling risk screening**

不是：

- nonlinear buckling analysis
- eigenvalue buckling analysis
- 真實竹材破壞荷載預測
- 專業設計規範驗證

---

## 15.2 基本公式

【Confirmed】

```text
Pcr = π² E I / (K L)²
```

---

## 15.3 Effective Length Factor K

【Open Decision — MECHANICS REVIEW REQUIRED】

目前尚未確認：

- K 的 default
- controlling I / weak-axis selection policy
- K 的自動判定
- 支承/節點理想化與 K 的關係
- risk band threshold
- beginner-facing risk wording

因此：

- Euler formula 可以接受 explicit K 作為 mechanics unit test
- 自動 Euler product behavior 在老師確認前不得視為完成

---

# 16. Mechanics Validation

## 16.1 基礎檢查

【Confirmed】

至少需要檢查：

- isolated node / disconnected structure
- zero-length member
- duplicate member
- support insufficiency / possible mechanism
- invalid node reference
- missing or invalid parameters
- invalid E / A
- invalid load target
- singular stiffness matrix
- non-finite numeric input

---

## 16.2 Machine-readable Error

【Recommended】

Mechanics Core 應輸出穩定 error code，例如：

- `ZERO_LENGTH_MEMBER`
- `INVALID_YOUNGS_MODULUS`
- `INVALID_AREA`
- `INSUFFICIENT_RESTRAINT`
- `SINGULAR_GLOBAL_STIFFNESS`

---

## 16.3 Beginner-facing Error

【Confirmed】

學生看到的錯誤訊息由 Teaching / Application Layer 轉譯。

例如：

```text
SINGULAR_GLOBAL_STIFFNESS
```

可呈現為：

> 模型目前無法得到唯一位移解，可能存在剛體移動或機構。請檢查支座與杆件連接。

Mechanics Core 不直接承擔 UX 文案。

---

# 17. Teaching Layer

## 17.1 與 Mechanics 分離

【Confirmed】

Teaching Layer 不得修改 Solver 原始結果。

---

## 17.2 P0 Teaching Insight

【Confirmed】

優先採：

> deterministic rules + explicit source metrics

不用 LLM 判斷 mechanics correctness。

---

## 17.3 第一層結果頁

【Confirmed】

結果頁第一層優先回答：

- 力從哪裡進入？
- 支座如何提供反力？
- 哪些杆件主要受拉？
- 哪些杆件主要受壓？
- 哪裡位移最大？
- 哪些壓杆需要注意屈曲？

詳細數值表放在更深層。

---

# 18. AI Boundary

【Confirmed】

AI 不得作為：

- Solver authority
- mechanics fallback
- 自動結構設計者
- 自動最佳化器
- 專業規範判定者

AI 若未來用於教學表達，只能建立於已驗證 numerical result 之上。

---

# 19. User / Role

## 19.1 Role Pyramid

【Confirmed】

三級角色：

```text
Developer
老師 + Product Owner
        ↓
Manager
建協會長 + 部分授權幹部
        ↓
User
每一參賽隊伍
```

---

## 19.2 Developer

【Confirmed】

可以：

- 建立所有角色帳號
- 建立 / 管理 Competition Event
- 查看所有 Project
- 系統維護

---

## 19.3 Manager

【Confirmed】

可以：

- 建立 User
- 批量建立 User
- 建立 / 管理被授權 Event
- 查看該 Event 所有隊伍 Project

預設：

- 不能修改學生 Project
- 不能建立 Developer
- 不能建立 Manager

---

## 19.4 User

【Confirmed】

一個帳號對應一支參賽隊伍。

User：

- 只能查看自己的 Project
- 只能修改自己的 Project
- 不能查看其他隊伍 Project

---

## 19.5 Authorization

【Confirmed】

所有權限必須 server-side 驗證。

不能只依賴：

- 隱藏按鈕
- 前端 route guard
- JavaScript

---

# 20. Account Rules

## 20.1 Username

【Confirmed】

格式：

```text
YYYYMMDD + two-digit team number
```

例如：

```text
2026-11-07
Team 01
→ 2026110701
```

---

## 20.2 Initial Password

【Confirmed】

初始密碼：

> 隊長學號

---

## 20.3 Password Security

【Confirmed】

- 只保存 password hash
- 不保存 plaintext
- 管理員不能查看現有密碼
- 首次登入後必須強制修改密碼

---

# 21. Bulk User Account Creation

【Confirmed】

至少支援：

- CSV import
- preview
- validation
- duplicate handling
- transaction / all-or-nothing
- audit log

---

## 21.1 Security Rule

【Confirmed】

Audit log 不得保存 plaintext initial password。

---

# 22. Competition Event

## 22.1 Event Definition

【Confirmed】

一個 Event 代表一次具體結構設計競賽。

至少管理：

- event name
- competition date
- event code
- participating users
- projects
- start
- end
- purge date
- status

---

## 22.2 Event Lifecycle

【Confirmed】

```text
DRAFT
→ ACTIVE
→ FINISHED_GRACE
→ PURGED
```

---

## 22.3 Grace Period

【Confirmed】

比賽結束後 7 天清除該 Event 的參賽 Project Operational Data。

---

## 22.4 FINISHED_GRACE Access

【Open Decision】

目前尚未正式確認 User 在 `FINISHED_GRACE` 是否：

- read-only
- 可繼續修改
- 完全禁止進入

【Recommended】

建議 read-only，供學生查看 / 匯出結果，但不再改模型。

---

# 23. Purge

## 23.1 Purge Core Rule

【Confirmed】

Event 結束 7 天後：

> 清除該 Event 的學生 Project Operational Data。

---

## 23.2 Purge Service

【Recommended】

Purge 必須：

- server-side
- idempotent
- auditable
- transaction-safe
- 可重跑

PoC 不需要 Celery。

可採：

- Django management command
- OS cron / deployment scheduler

---

## 23.3 Account Lifecycle After Purge

【Open Decision】

尚未確認：

- team account 保留
- disable
- delete

因此 Project data purge 不得順便擅自刪除 User。

---

# 24. Operational Data 與 Research Data

## 24.1 必須分離

【Confirmed】

```text
Operational Data
≠
Research Data
```

---

## 24.2 Purge 後研究資料

【Confirmed】

Product Owner 已選擇：

> **B：只保留匿名化 derived mechanics / research metrics**

不保留 raw student model snapshot。

---

## 24.3 不得保留的內容

【Confirmed】

Purge 後 Research Data 不得保留足以完整重建學生 Project 的：

- full node coordinates
- full member connectivity
- complete load/support snapshot
- complete raw model revision
- captain student ID
- original login identity

---

## 24.4 可保留的 Derived Metrics

【Recommended】

若研究正式啟用且符合研究倫理，可保留：

- anonymous research key
- Analysis count
- First-pass success
- error count / category
- task duration
- max displacement summary
- tension / compression count
- buckling screening summary
- Design Reasoning Score
- Report Completeness
- concept test result
- SUS result

實際收集仍遵守 minimum necessary data principle。

---

# 25. ModelRevision

## 25.1 Revision 原則

【Confirmed】

每個分析必須可追溯到 ModelRevision。

---

## 25.2 Mutable Draft vs Immutable Revision

【Recommended】

使用：

```text
Mutable Project Draft
        ↓ Analyze / checkpoint
Immutable ModelRevision
```

不要每次 mouse drag 就建立 revision。

---

## 25.3 Revision Snapshot

【Confirmed】

ModelRevision 必須凍結當時計算所需的數值資訊。

例如：

- coordinates
- topology
- support
- nodal load
- E
- A
- relevant section properties

不能只保存 foreign key 而讓後續 Material/Section 修改改變舊分析語意。

---

# 26. AnalysisRun

## 26.1 核心追溯

【Confirmed】

每次 AnalysisRun 至少追溯：

```text
Project
→ ModelRevision
→ AnalysisRun
→ SolverVersion
→ InputHash
```

---

## 26.2 一個 Revision 可多次 Run

【Recommended】

同一 ModelRevision 可因：

- solver version
- retry
- validation
- testing

產生多個 AnalysisRun。

不得修改原 Revision。

---

# 27. SolverVersion / InputHash

【Confirmed】

分析必須記錄：

- solver version
- model/input hash
- model revision
- analysis type

目的：

- reproducibility
- regression
- research traceability
- benchmark diagnosis

---

# 28. Prediction

【Confirmed】

Prediction 應在 Analyze 前發生。

可包含：

- 預期主要受拉位置
- 預期主要受壓位置
- 預期最大位移位置
- 簡短理由

Prediction 不作為 Solver input。是否「沒有 Prediction 就禁止 Analyze」仍為 Open Decision；不得自行建立 blocking requirement。

---

# 29. Compare / DesignRationale / Reflection

## 29.1 Compare

【Confirmed】

學生應能比較不同方案。

比較重點可包含：

- weight
- displacement
- force
- stress
- stability screening

---

## 29.2 DesignRationale

【Confirmed】

平台應記錄重大修改理由，以支援：

- 學習反思
- 設計推理
- 研究分析

---

## 29.3 Reflection

【Confirmed】

Reflect 是核心教學循環的一部分。

平台可以引導學生說明：

- 為什麼修改
- 哪個分析結果影響決策
- 修改後有何 trade-off

但不能替學生生成最終設計論證。

---

# 30. Calculation Report

## 30.1 定位

【Confirmed】

平台提供：

> 計算書輔助 / 基礎資料包

不是自動替學生完成整份設計論證。

---

## 30.2 至少可整理

【Confirmed】

- model basic information
- analysis assumptions
- material / section
- load / support
- member axial force
- tension / compression
- node displacement
- stress
- stability screening
- mass
- result figure / diagram
- report completeness

---

## 30.3 學生仍需自行完成

【Confirmed】

- 結構選型理由
- 設計思路
- 方案比較
- 修改理由
- 最終結論

---

# 31. Web 技術方向

## 31.1 Backend

【Confirmed】

- Python 3.12+
- Django 5.x
- NumPy
- SQLite for PoC

【Future】

必要時可升級 PostgreSQL。

---

## 31.2 Frontend

【Confirmed】

- Django Templates
- HTML
- CSS
- Vanilla JavaScript
- SVG

---

## 31.3 網路環境

【Confirmed】

考慮中國大陸網路環境：

- 不依賴 Google Fonts
- 不依賴不可控國外 CDN
- static assets 儘量本地化

---

# 32. 系統架構

## 32.1 P0 Architecture

【Confirmed】

採：

> **Django Modular Monolith + Application / Idealization Layer + Pure Python Mechanics Core**

---

## 32.2 依賴方向

【Confirmed】

```text
Browser / Django UI
        ↓
Application Services
        ↓
Physical Snapshot
        ↓
Idealization
        ↓
Mechanics Core
```

---

## 32.3 禁止反向依賴

【Confirmed】

Mechanics Core 不得 import：

- Django ORM
- views
- request
- session
- template

Django View / JavaScript 不得實作 authoritative stiffness / solver mechanics。

---

# 33. Django Apps

【Recommended】

P0 建議 apps：

- `accounts`
- `competitions`
- `projects`
- `materials`
- `modeling`
- `analysis`
- `learning`
- `reports`

`research` 僅在實際啟用研究 retention 時建立。

不採「一個 Entity 一個 App」。

---

# 34. API / Page 原則

## 34.1 Server-rendered Page

【Recommended】

普通 Django page/form 適合：

- login
- password change
- Event management
- account management
- CSV import
- Material
- Prediction
- Reflection
- Report

---

## 34.2 JSON Endpoint

【Recommended】

只用於互動式操作：

- model draft save
- model check
- analyze
- result visualization data
- section preview

---

## 34.3 P0 不做 API-first

【Confirmed】

P0 不需要：

- SPA
- complex REST versioning
- DRF-first architecture
- WebSocket

---

# 35. Testing / Benchmark Gate

## 35.1 原則

【Confirmed】

> Mechanics correctness 優先於 UI 美觀。

AI / Vibe Coding 不可作為計算正確性的證據。

---

## 35.2 P0 Benchmark

【Confirmed】

至少：

### B/T01 單杆拉壓

- δ = PL/EA
- axial force
- reaction
- sign convention

### B/T02 簡單三角桁架

- reaction
- member force
- displacement

### B/T03 對稱平面桁架

- symmetry
- reaction
- force symmetry

### B/T04 簡單超靜定桁架

- global stiffness assembly
- restraint handling
- trusted reference comparison

### B/S01 Composite Section

- A
- centroid
- Ix
- Iy

### B/E01 Euler

- explicit K
- Pcr formula

---

## 35.3 Stage 2 Benchmark

【Future】

舊 Frame-first 研究計畫中的：

- cantilever beam
- simply supported beam
- UDL
- portal frame
- Fixed
- N/V/M

全部移至 Frame Stage 2 benchmark。

---

# 36. Research Direction

## 36.1 Research Positioning

【Confirmed】

研究定位應為：

- PoC / Pilot
- Exploratory Engineering Education Study
- 真實競賽場域
- 小樣本
- mixed methods

---

## 36.2 P0 Research Concepts

【Confirmed】

Truss-first P0 應優先研究：

- equilibrium
- support reaction
- force path
- tension / compression
- displacement
- axial stress
- weight
- buckling

---

## 36.3 Frame Learning Metrics

【Future】

以下改到 Stage 2：

- Fixed support
- bending
- moment
- EI
- Frame compatibility
- N/V/M interpretation

---

# 37. Non-goals

【Confirmed】

P0 不設計或實作：

- 3D
- 3D Frame
- topology optimization
- automatic optimization
- contact FE
- glue nonlinear mechanics
- torsion
- dynamics
- modal analysis
- plasticity
- P-Delta
- large deformation
- eigenvalue buckling
- plate / shell / solid
- real-time collaborative editing
- WebSocket
- microservices
- complex message queue
- Redis
- Celery
- AI automatic design
- professional design code checking

---

# 38. YAGNI / Complexity Control

【Confirmed】

每個 architecture component 都必須回答：

> 如果第一階段不做，會阻礙 Truss PoC 嗎？

若答案是否：

> 優先延期。

特別避免：

- Repository Pattern everywhere
- generic plugin framework
- excessive interfaces
- CQRS
- event sourcing
- microservices
- generic FEM abstraction
- Frame-specific nullable fields everywhere

---

# 39. Future Frame Extension Boundary

## 39.1 共用 Domain

【Confirmed】

Future Frame 共用：

- Project
- Event
- User
- Material
- Strip
- Section
- Geometry Node
- Physical Member
- Connection
- high-level Load ownership concept
- ModelRevision
- AnalysisRun
- Prediction
- Reflection
- Report

---

## 39.2 Mechanics 分離

【Confirmed】

```text
TrussModel
→ Truss2DSolver
```

【Future】

```text
FrameModel
→ Frame2DSolver
```

---

## 39.3 禁止大量 if / else 泛化

【Confirmed】

不得為了 code reuse 把 Truss / Frame solver 塞進單一巨大 kernel。

允許共用：

- numeric helpers
- geometry utilities
- section properties

但：

- DOF
- element stiffness
- load vector
- force recovery
- support semantics
- benchmark

應保持 mechanics kernel 獨立。

---

# 40. Architecture Decisions 已確認

以下目前可視為專案級 Confirmed：

| ID | Decision |
|---|---|
| D-001 | P0 採 `TRUSS_2D` |
| D-002 | Future 保留 `FRAME_2D` |
| D-003 | Django Modular Monolith |
| D-004 | Mechanics Core 為 pure Python |
| D-005 | Physical Model / Idealization / Analysis 三層隔離 |
| D-006 | Intersection ≠ Connection |
| D-007 | PhysicalMember ≠ AnalysisElement |
| D-008 | ModelRevision immutable |
| D-009 | AnalysisRun 必須追溯 SolverVersion + InputHash |
| D-010 | Teaching Layer 不修改 solver results |
| D-011 | Server-side authorization |
| D-012 | P0 manual Node Force only |
| D-013 | Self Weight 延至 P0.x/P1 |
| D-014 | Purge 後只留 anonymous derived metrics |
| D-015 | 初始密碼仍使用隊長學號 |
| D-016 | 首次登入強制改密碼 |
| D-017 | Frame benchmark / learning metric 移至 Stage 2 |
| D-018 | 不建立 generic FEM framework |
| D-019 | 不使用 AI 作 mechanics authority |

---

# 41. Open Decisions

以下尚未升格為 Confirmed：

## O-001 — Euler Effective Length / Buckling-axis Policy

**Owner：老師 / Mechanics Reviewer**

範圍包含 effective length factor K、automatic/default K、controlling I / weak-axis selection policy、final risk bands 及相關教學文案。僅可用明確提供的 E、I、L、K 驗證 Euler 公式；不得自動選擇控制軸或推斷 K。

Status：

> `MECHANICS REVIEW REQUIRED`

---

## O-002 — Roller Orientation

**Owner：Product Owner + Mechanics Reviewer**

需決定 P0 restraint capability。

---

## O-003 — FINISHED_GRACE User Access

**Owner：Product Owner**

【Recommended】

read-only。

---

## O-004 — User Account after Purge

**Owner：Product Owner**

選項：

- retain
- disable
- delete

目前不得自動決定。

---

## O-005 — Composite Strip Overlap

**Owner：Product Owner + Mechanics Reviewer**

只有在 free-composite 允許重疊時需要決定。

---

# 42. Mechanics Review Required

目前至少：

### MRR-001 — Euler K / controlling I / weak-axis policy

在此項核定前：

- 可測 explicit K formula
- 不可正式完成 automatic buckling risk classification

若後續發現新的力學風險：

> 必須新增 `MECHANICS REVIEW REQUIRED`，不得自行修正後悄悄寫進 spec。

---

# 43. Implementation Gate

## 43.1 MASTER_SPEC 狀態

【Confirmed】

本文件已升格為：

> `MASTER_SPEC.md v1.0`

並作為目前唯一最高層級 Source of Truth。

---

## 43.2 Architecture Reconciliation

【Confirmed】

已完成與目前 Architecture Specification Set 的一致性審查。

結果：

- 未發現需要推翻目前 Truss-first architecture 的 blocking conflict。
- 舊 Frame-first research / benchmark 內容已維持 Stage 2。
- Operational / Research purge 邊界一致。
- Physical / Idealization / Analysis 分層一致。
- Truss kernel / postprocess / Teaching Layer authority 已釐清。
- 尚未確認的產品/力學項目仍保留為 Open Decision，不視為 conflict。

---

## 43.3 Architecture Freeze

【Confirmed】

Architecture 狀態：

> `FINAL_FROZEN`

此狀態表示架構與 P0 scope 可進入實作，不表示所有 Open Decision 均已關閉。

---

## 43.4 Scoped Implementation Gates

以下項目只阻擋其直接相關功能，不阻擋其他 P0 模組：

- Euler automatic risk behavior → 等待 `O-001 / MRR-001`
- Roller UI / Support JSON final shape → 等待 `O-002`
- FINISHED_GRACE final UX permission → 等待 `O-003`
- post-purge User lifecycle → 等待 `O-004`
- overlap-capable free composite geometry → 等待 `O-005`

Codex 不得自行關閉上述 gates。

---

# 44. Codex Guardrails

正式交付 Codex 後：

1. Codex 必須先讀 `MASTER_SPEC.md` 與對應專項 spec。
2. 不可擅自修改 mechanics assumptions。
3. 不可擴 P0 scope。
4. 不可把 Recommended 當 Confirmed。
5. 遇到 Spec Conflict 必須停止該部分並回報。
6. Mechanics 修改必須先有 failing test / benchmark。
7. 不得為讓測試通過而任意放寬 benchmark tolerance。
8. 不得把 Teaching behavior 寫入 Solver。
9. 不得把 Django ORM 寫進 Mechanics Core。
10. 不得提前實作 Frame mechanics。

---

# 45. P0 Success Criteria

【Confirmed】

P0 至少應做到：

1. 學生能完成基本 2D Truss 建模。
2. Model Check 能發現主要建模問題。
3. Solver 能可靠輸出 displacement / reaction / axial force。
4. 學生能辨識 tension / compression。
5. 平台能顯示最大位移。
6. 平台能計算 axial stress。
7. 平台能計算 theoretical mass。
8. 平台能進行 Euler buckling screening（待 K policy 完整化）。
9. 學生能比較至少兩個設計 revision。
10. 平台能支援 Predict → Analyze → Explain → Compare → Reflect。
11. 平台能輸出 calculation report 基礎資料。
12. 所有核心 mechanics 有 benchmark gate。
13. 所有分析可追溯到 ModelRevision + SolverVersion + InputHash。
14. 權限不可由前端繞過。
15. Event purge 能被驗證且不依賴人工記得。
16. Purge 後 Research Data 不可還原原始學生 Project。
17. P0 不被 Future Frame 拖入過度設計。

---

# 46. 正式文件關係

本文件升格後，應成為：

```text
MASTER_SPEC.md
│
├── ARCHITECTURE_SPEC.md
├── DOMAIN_MODEL.md
├── DATA_CONTRACT.md
├── TRUSS_SOLVER_CONTRACT.md
├── AUTHORIZATION_AND_EVENT_ARCHITECTURE.md
├── API_AND_APPLICATION_FLOW.md
├── TEST_ARCHITECTURE.md
└── FRAME_EXTENSION_STRATEGY.md
```

另外：

```text
ARCHITECTURE_DECISION_REGISTER.md
```

負責記錄重要決策歷史與變更理由。

```text
CODEX_IMPLEMENTATION_PLAN.md
```

只描述實作順序，不得取代規格。

---

# 47. v1.0 Product Owner Review Record

本輪已完成下列一致性檢查：

- [x] P0 明確維持 Truss-first
- [x] P0 Mechanics assumptions 與現行 Truss 規劃一致
- [x] Frame 保留為 Stage 2，而非刪除
- [x] Material / Strip / Section 路線保留
- [x] Physical / Analysis 分離原則一致
- [x] User / Event / Project ownership 一致
- [x] Purge 後只留匿名 derived metrics
- [x] Teaching / AI authority boundary 一致
- [x] Non-goals / YAGNI 邊界一致
- [x] 舊 Frame-first P0 內容已排除
- [x] Solver kernel 與 pure postprocess 的責任已釐清
- [x] Open Decisions 保持 open，未被偷偷決定

仍需後續確認，但不阻擋 MASTER_SPEC v1.0 成立：

- [ ] Euler effective length factor `K`
- [ ] Roller orientation
- [ ] FINISHED_GRACE user access
- [ ] account lifecycle after purge
- [ ] composite strip overlap policy（若 feature 需要）

---

# 48. v1.0 結論

目前專案最高層級方向可總結為：

> **以 Truss-first 的教學路線建立一個面向結構設計競賽初學者的互動式結構力學平台。P0 使用可靠且可獨立 Benchmark 的 2D Linear Elastic Truss Mechanics Core，透過 Physical Model → Idealization → Analysis 分層，配合 Section Designer、模型檢查、Predict/Analyze/Explain/Compare/Reflect、計算書輔助與可追溯研究資料，在不擴張成通用 FEM 軟體的前提下，建立可於 Stage 2 延伸至 Frame 的穩定基礎。**

本文件目前為：

> **`MASTER_SPEC.md v1.0` — CURRENT / APPROVED BASELINE**

後續 Architecture Specs、Implementation Plan、Codex implementation 與測試均必須以本文件為最高層級依據。若需求或 mechanics assumptions 需要改變，應先更新 MASTER_SPEC / Decision Register，再修改 implementation。
