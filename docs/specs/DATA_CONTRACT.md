# DATA_CONTRACT.md

## 0. 文件狀態

- 文件角色：Operational persistence、immutable revision snapshot、solver I/O、analysis result、research derived data 的資料契約。
- 階段：Truss-first P0 Data Baseline。
- 本文件不等同 Django migration；欄位名稱可在實作時微調，但語意、ownership、immutability、retention 與 versioning 不得被破壞。
- Source of Truth：MASTER_SPEC.md v1.3；本 Data Contract 已完成 reconciliation。

### 狀態標記

- 【Confirmed】：已核定需求或既定專案條款。
- 【Recommended】：目前實作基線。
- 【Open Decision】：尚不可寫死為產品行為。
- 【Future】：P0 不實作，但保留 extension seam。

---

## 1. Data Architecture Principle

【Recommended】

P0 將資料分成四類，不建立 generic repository/event-store：

```text
1. Mutable Operational Data
   Project / Material / Section / Physical Model Draft

2. Immutable Analysis Evidence
   ModelRevision / AnalysisRun / SolverVersion

3. Derived Teaching / Report Data
   TeachingInsight / Prediction / Reflection / ReportCompleteness

4. Research Retention Data
   anonymous derived metrics only after purge
```

核心原則：

> 可編輯資料與可重現分析證據分開；可重現分析證據與 purge 後研究保留資料再分開。

---

## 2. Persistence Strategy

【Recommended】

P0 使用 Django ORM + SQLite。

### 2.1 Relational persistence

適合關係、ownership、authorization 與 lifecycle 的資料採 ORM rows：

- User
- CompetitionEvent
- EventMembership
- Project
- Material
- Strip
- Section
- GeometryNode
- PhysicalMember
- Connection
- Support
- NodeLoad
- ModelRevision metadata
- AnalysisRun metadata
- SolverVersion
- ValidationLog
- Prediction
- Reflection
- DesignRationale
- ReportCompleteness
- PurgeAudit
- BulkImportBatch

### 2.2 JSON snapshot / result payload

【Recommended】

P0 對以下內容使用 versioned JSON payload，而不是過度正規化成大量 result tables：

- `ModelRevision.physical_snapshot_json`
- `AnalysisRun.solver_input_json`（若需完整 operational reproducibility）
- `AnalysisRun.result_json`
- `AnalysisRun.diagnostics_json`
- section composite definition payload（若自由拼接幾何用 JSON 表示最簡單）

理由：

1. PoC 模型規模小。
2. Snapshot 本質上需要 immutable aggregate。
3. Truss 與 Future Frame result schema 不同，JSON + schema version 可保持上層 AnalysisRun 穩定。
4. 避免為每個 numerical array 建 ORM table。

限制：

- JSON 不是任意 dumping；必須有明確 schema/version。
- 不可把 Python pickle 當持久化 contract。
- 不可把 Django model `repr` 當 hash/input contract。

---

## 3. Global Units Contract

【Confirmed】

所有 mechanics persistence/snapshot/solver payload 固定：

| Quantity | Unit |
|---|---|
| length | mm |
| force | N |
| stress | MPa = N/mm² |
| E | MPa |
| area | mm² |
| second moment | mm⁴ |
| mass | g |
| density | g/mm³ |

P0 不在 Solver 內做 unit conversion。

【Recommended】

欄位名在 JSON contract 中應帶 unit suffix，例如：

- `x_mm`
- `fx_N`
- `E_MPa`
- `A_mm2`
- `Ix_mm4`
- `mass_g`

避免裸欄位 `x`, `force`, `E`, `I` 造成 contract 歧義。

---

## 4. Core Persisted Schema — Operational Data

以下為語意 schema，不是 migration 語法。

### 4.1 User

【Confirmed / Recommended】

```text
User
- id
- username                         unique
- password_hash                    Django auth managed
- role                             DEVELOPER | MANAGER | USER
- must_change_password             bool
- is_active                        bool
- created_at
- updated_at
```

敏感資料規則：

- 初始密碼來源為隊長學號【Confirmed】。
- provisioning service 只在建立帳號當下 transiently 使用隊長學號呼叫 password hashing。
- **不得**另建 `captain_student_id_plaintext` 或 `initial_password` 欄位長期保存。
- Audit log 不記錄密碼或隊長學號 plaintext。

### 4.2 CompetitionEvent

```text
CompetitionEvent
- id
- name
- competition_date
- event_code                       unique or scoped unique
- starts_at
- ends_at
- purge_at
- status                           DRAFT | ACTIVE | FINISHED_GRACE | PURGED
- created_at
- updated_at
```

Invariant：`purge_at = ends_at + 7 days`【Confirmed】。

### 4.3 EventMembership

```text
EventMembership
- id
- event_id
- user_id
- membership_type                 PARTICIPANT | MANAGER
- is_active
- created_at
```

Recommended unique invariant：`(event_id, user_id, membership_type)` 不重複有效資料。

### 4.4 Project

```text
Project
- id
- event_id
- owner_user_id
- name
- analysis_type                    TRUSS_2D [P0]
- status
- draft_version                    monotonically increasing integer
- created_at
- updated_at
```

`FRAME_2D`【Future】只作可擴展 enum/value，不在 P0 UI 提供。

### 4.5 Material

```text
Material
- id
- project_id or owner scope
- name
- E_MPa
- density_g_per_mm3
- tensile_strength_MPa             nullable if product allows incomplete draft
- compressive_strength_MPa         nullable if product allows incomplete draft
- source_type
- note
- created_at
- updated_at
```

Analyze 時所需值必須完整；draft 階段可允許未完成欄位，由 authoring validation 管理。

### 4.6 Strip

```text
Strip
- id
- project_id or owner scope
- material_id
- name
- width_mm
- thickness_mm
- note
```

### 4.7 Section

```text
Section
- id
- project_id or owner scope
- name
- section_type
- definition_schema_version
- definition_json
- properties_schema_version
- properties_json
- definition_hash
- created_at
- updated_at
```

`properties_json` 至少能表達：

```json
{
  "A_mm2": 0.0,
  "centroid_x_mm": 0.0,
  "centroid_y_mm": 0.0,
  "Ix_mm4": 0.0,
  "Iy_mm4": 0.0,
  "mass_per_length_g_per_mm": 0.0,
  "strong_axis": "X|Y|EQUAL",
  "weak_axis": "X|Y|EQUAL"
}
```

數字 `0.0` 只代表 shape example，不代表合法實際截面值。

### 4.8 GeometryNode

```text
GeometryNode
- id
- project_id
- client_key                       stable within project/UI
- x_mm
- y_mm
- label
```

【Recommended】

`client_key` 讓 SVG/JSON round-trip 不依賴資料庫 PK；可使用 UUID 或 project-local opaque string。

### 4.9 PhysicalMember

```text
PhysicalMember
- id
- project_id
- client_key
- start_geometry_node_id
- end_geometry_node_id
- material_id
- section_id
- label
- is_active
```

不可加入 `truss_element_id` 一對一欄位作永久耦合。

### 4.10 Connection

【Recommended】

P0 最小持久化語意：

```text
Connection
- id
- project_id
- client_key
- geometry_node_id                 connection location
- participating_member_refs        normalized relation or validated JSON refs
- created_at
```

實作可採 join table 或簡單關聯模型；不得以「線段相交」取代 Connection record。

### 4.11 Support

```text
Support
- id
- project_id
- target_connection
- support_type                     PINNED | ROLLER
- restrained_axis                  null for PINNED; X | Y for ROLLER
```

【Confirmed】不支持 angle 或 local support coordinate system。

### 4.12 NodeLoad

```text
NodeLoad
- id
- project_id
- target_geometry_node_id / connection_id
- fx_N
- fy_N
- label
```

【Confirmed】P0 不存 member UDL；Self Weight 延後。

---

## 5. Mutable Draft Contract

【Recommended】

Interactive canvas 可交換一個完整 draft payload：

```json
{
  "schema_version": "physical-draft-v1",
  "draft_version": 12,
  "nodes": [],
  "physical_members": [],
  "connections": [],
  "supports": [],
  "node_loads": []
}
```

注意：

- 此 payload 是 authoring contract，不是 solver contract。
- save 後 server validation 成功，`draft_version` +1。
- client 不得藉 payload 改 `project_id`, `owner_user_id`, `event_id` 等 server-owned 欄位。
- server 以 URL/object context 判斷 Project，而非信任 payload ownership。

---

## 6. ModelRevision Contract

【Confirmed】ModelRevision 必須支援分析可追溯。

【Recommended】

```text
ModelRevision
- id
- project_id
- revision_number
- analysis_type
- source_draft_version
- physical_snapshot_schema_version
- physical_snapshot_json
- model_hash
- created_by
- created_at
```

### 6.1 Snapshot properties

Snapshot 必須 freeze solver-relevant 與 report-relevant 數值：

ModelRevision 的 reuse identity 為 `(project_id, source_draft_version, model_hash)`。`source_draft_version` 是 authoring lineage，不納入 hash 語意：不同 draft 版本即使內容 hash 相同，仍建立新的 revision；同一 draft 的相同 `model_hash` 可 reuse。

- geometry coordinates
- explicit connection topology
- physical member assignments
- resolved material numeric values
- resolved section numeric values / definition hash
- supports
- nodal loads
- units contract/version

因此後續修改 Material/Section 不改變既有 revision。

### 6.2 Immutability

ModelRevision 建立後：

- 不提供 edit form。
- 不被 draft save 更新。
- 若資料錯誤，建立新 revision，不 patch 舊 revision。

---

## 7. Canonical Physical Snapshot Schema

【Recommended】

概念形狀：

```json
{
  "schema_version": "physical-snapshot-v1",
  "analysis_type": "TRUSS_2D",
  "units": {
    "length": "mm",
    "force": "N",
    "stress": "MPa",
    "mass": "g"
  },
  "nodes": [
    {"id": "GN1", "x_mm": 0.0, "y_mm": 0.0}
  ],
  "physical_members": [
    {
      "id": "PM1",
      "start_node_id": "GN1",
      "end_node_id": "GN2",
      "material": {
        "source_id": "MAT1",
        "E_MPa": 0.0,
        "density_g_per_mm3": 0.0
      },
      "section": {
        "source_id": "SEC1",
        "definition_hash": "...",
        "A_mm2": 0.0,
        "Ix_mm4": 0.0,
        "Iy_mm4": 0.0
      }
    }
  ],
  "connections": [],
  "supports": [],
  "node_loads": []
}
```

數值零值仍僅為 schema example。

---

## 8. Truss Solver Input Data Contract

【Confirmed】詳細 contract 以 `TRUSS_SOLVER_CONTRACT.md` 為 authoritative mechanics spec。

Analysis service 傳入：

```text
TrussModel
- schema_version
- nodes[id, x_mm, y_mm]
- members[id, node_i, node_j, E_MPa, A_mm2]
- supports[node_id, restrain_ux, restrain_uy]
- nodal_loads[node_id, fx_N, fy_N]
```

並另帶 postprocess context：

- density
- I for buckling
- physical ↔ analysis mapping

---

## 9. AnalysisRun Contract

```text
AnalysisRun
- id
- project_id                        denormalized convenience allowed
- model_revision_id
- analysis_type
- solver_version_id/value
- input_schema_version
- input_hash
- status
- started_at
- finished_at
- solver_input_json                 operational retention only
- result_schema_version
- result_json
- diagnostics_json
- failure_code
- prediction_id                     nullable; completed same-project/same-draft evidence only
```

Recommended status：

- `PENDING`
- `SUCCESS`
- `VALIDATION_FAILED`
- `SOLVER_FAILED`

P0 synchronous execution 可讓 `PENDING` 很短，但保留狀態語意不代表引入 background queue。

---

## 10. Analysis Result Schema

【Recommended】

P0 result payload：

```json
{
  "schema_version": "truss2d-result-v1",
  "node_displacements": [
    {"node_id": "N1", "ux_mm": 0.0, "uy_mm": 0.0}
  ],
  "support_reactions": [
    {"node_id": "N1", "rx_N": 0.0, "ry_N": 0.0}
  ],
  "member_results": [
    {
      "member_id": "M1",
      "physical_member_id": "PM1",
      "axial_force_N": 0.0,
      "axial_stress_MPa": 0.0,
      "state": "TENSION|COMPRESSION|ZERO",
      "mass_g": 0.0,
      "buckling": null
    }
  ],
  "total_mass_g": 0.0,
  "diagnostics": {}
}
```

### 10.1 Precision rule

- persistence 保存未經 UI rounding 的 float。
- display rounding 只在 presentation layer。
- hash 不使用 display-formatted number。

---

## 11. ValidationLog Contract

```text
ValidationLog
- id
- project_id
- model_revision_id                nullable before revision creation
- analysis_run_id                  nullable
- stage                            AUTHORING | IDEALIZATION | MECHANICS
- code
- severity                         ERROR | WARNING
- category
- entity_type
- entity_refs_json
- numeric_context_json
- created_at
```

【Recommended】

學生可見文字不必永久複製到 log；保存穩定 `code` + context，比保存易改版文案更有研究與測試價值。

---

## 12. Prediction / Reflection / DesignRationale

### Prediction

```text
Prediction
- id
- project_id
- created_by
- source_draft_version
- created_at
- status                            DRAFT | COMPLETED | INVALIDATED
- completed_at / invalidated_at
- invalidation_code                 nullable stable code
- prediction_schema_version         prediction-v1
- payload_json                      immutable after completion

StudentResultReveal
- id
- project_id
- source_draft_version
- first_analysis_run_id
- revealed_to_user_id
- first_revealed_at
- unique(project_id, source_draft_version)

`prediction-v1` contains exact member judgments, one restricted PhysicalPointRef, and an alternating representative load-path hypothesis. It contains no coordinates, model snapshot, material/section data, or solver result. `ZERO_FORCE` is a Prediction choice only; analysis-side policy remains O-007 Open.
```

### DesignRationale

```text
DesignRationale
- id
- project_id
- from_revision_id                 nullable
- to_revision_id                   nullable until next analysis
- referenced_analysis_run_id       nullable
- rationale_category
- text
- created_at
```

### Reflection

```text
Reflection
- id
- project_id
- analysis_run_id / comparison context
- created_by
- reflection_json / text
- created_at
```

【Recommended】

P0 不需要 rich-text editor 或 event sourcing；短結構欄位 + 短句已足以支援研究與教學循環。

---

## 13. ReportCompleteness Contract

```text
ReportCompleteness
- id
- project_id
- based_on_analysis_run_id
- schema_version
- items_json
- updated_at
```

例：

```json
{
  "model_assumptions": true,
  "material_section": true,
  "load_support": true,
  "force_displacement": true,
  "stability": false,
  "comparison": false,
  "design_rationale": false
}
```

學生端呈現「缺漏/準備度」，不自動宣稱設計品質分數。

---

## 14. SolverVersion Contract

```text
SolverVersion
- id
- analysis_type
- solver_version
- input_schema_version
- result_schema_version
- build_reference                  optional
- activated_at
```

【Recommended】

以下變更至少應造成 solver/version contract 可識別變更：

- numerical algorithm behavior
- sign convention
- stiffness/force recovery formula
- mechanics validation semantics
- input/result schema breaking change

UI 文案修改本身不需要 bump solver version。

---

## 15. Hash Contract

【Confirmed】需有 ModelHash / InputHash。

【Recommended】使用 canonical JSON serialization 後的 SHA-256。

Canonicalization：

1. UTF-8。
2. object keys deterministic sorting。
3. list ordering由 contract 明確定義；若輸入 entity order 無 mechanics 意義，idealizer 應先 deterministic sort。
4. 使用完整 numerical value representation，不使用 UI formatting。
5. hash payload 包含 schema version 與 analysis type。

### `model_hash`

對 immutable physical snapshot 生成。

### `input_hash`

對 solver + postprocess 可重現所需的 canonical analysis input 生成。

兩者可以相同也可以不同，但語意不可混用。

`model_hash` 仍是內容 identity，`input_hash` 仍是 canonical numerical input identity；兩者均不取代 `source_draft_version` 的 authoring lineage identity。

---

## 16. Research Data Contract

【Confirmed】Purge 後保留方案 B：**匿名化 derived metrics**。

### 16.1 Allowed retained data

【Recommended】

```text
ResearchDerivedMetric
- research_team_key
- event_research_key
- metric_name
- metric_value / metric_json
- metric_schema_version
- captured_period / relative_time
```

可保留：

- analysis count
- validation/error count by category
- first-pass success
- task duration
- max displacement summary value
- member tension/compression counts
- buckling screening summary count
- model complexity summary（node/member count）
- design reasoning score
- report completeness metrics
- concept/SUS scores（若正式研究流程允許）

### 16.2 Prohibited retained raw reconstruction data

Purge 後不得保留：

- full node coordinates
- full member connectivity
- exact support/load topology
- full ModelRevision snapshot
- full AnalysisRun input
- original username
- captain student ID
- plaintext credentials
- 可直接還原學生完整 Project 的 composite payload

### 16.3 Research key

【Recommended】

- 產生 random opaque `research_team_key`。
- Operational 階段可以有暫時 mapping 供研究 extraction。
- purge 完成後刪除 username/team identity → research key 對照，使 retained dataset 不再可由平台直接回推出隊伍帳號。

若研究倫理要求改採 pseudonymization、保留 re-identification key，這是新的 Data Governance 決策，不可自行改寫方案 B。

---

## 17. Purge Data Contract

【Confirmed】Event 結束 7 天後清除 student Project Operational Data。

【Recommended】purge transaction/service 順序：

```text
eligible Event
  ↓
compute/finalize approved derived research metrics
  ↓
write PurgeAudit pre-state counts
  ↓
delete operational Project children
  ↓
delete ModelRevision raw snapshots
  ↓
delete AnalysisRun raw input/result
  ↓
remove identity ↔ research key mapping
  ↓
mark Event PURGED
  ↓
write final counts/status
```

### PurgeAudit 可保留

- event_id / event_code
- started_at / completed_at
- status
- deleted row counts by category
- retained research metric counts
- error code if failed

不得保留被刪除 raw payload。

---

## 18. Retention Table

| Data | Before purge | After purge | Notes |
|---|---|---|---|
| Project | Yes | No raw project | Confirmed |
| Physical model | Yes | No | Confirmed |
| Material/Section tied to project | Yes | No if project-scoped | Recommended |
| ModelRevision snapshot | Yes | No | Confirmed by option B |
| AnalysisRun raw input/result | Yes | No | Confirmed by option B |
| ValidationLog raw context | Yes | No | Derived counts may remain |
| Prediction/Reflection raw text | Yes | No by default | Derived score/count only unless separately approved |
| Report operational data | Yes | No | Derived completeness metrics may remain |
| Research derived metrics | Yes/optional | Yes | Anonymous only |
| Password hash/account | Separate policy | Separate policy | Account lifecycle still open |
| PurgeAudit metadata | Yes | Yes | No raw student data |

---

## 19. Data Validation Boundaries

【Recommended】

### Form/serializer validation

- required input
- type/range
- duplicate import username
- malformed coordinates

### Domain validation

- ownership relations
- Project/Event consistency
- Material/Section assignment consistency
- Connection target consistency

### Mechanics validation

- zero length
- invalid E/A
- unsupported support
- singular system

資料庫 constraint 不取代 mechanics validation；mechanics validation 也不取代 authorization。

---

## 20. Schema Versioning

【Recommended】

不同 contract 分開 version：

- `physical-draft-v1`
- `physical-snapshot-v1`
- `section-definition-v1`
- `section-properties-v1`
- `truss2d-input-v1`
- `truss2d-result-v1`
- `prediction-v1`
- `research-metric-v1`

不建立複雜 API version namespace。

Breaking schema change 才 bump contract version；新增 optional non-breaking display metadata 可不必建立全新 API 世代。

---

## 21. SQLite → PostgreSQL Portability

【Recommended】

P0 可用 SQLite，但避免：

- SQLite-only raw SQL business logic
- DB-specific JSON query 成為核心 domain requirement
- 依靠沒有 application validation 的寬鬆 typing

Future migration 至 PostgreSQL 時，核心 mechanics 與 domain contract 不應改變。

---

## 22. Open Decisions

### Resolved — Roller orientation representation（Master O-002）

PINNED 的 restrained_axis 必须为 null；ROLLER 必须为 X 或 Y。

### OD-DATA-02 — Event purge 後 User account lifecycle

【Open Decision】raw Project purge 已確定，但 team account 是停用、刪除或保留尚未核定。

### OD-DATA-03 — Euler `K`

【MECHANICS REVIEW REQUIRED】Data contract 只允許 explicit K，不設 product default。

---

## 23. YAGNI Guardrails

P0 不建立：

- generic event store
- data lake
- warehouse ETL
- polymorphic universal FEM entity table
- generic JSON schema registry service
- distributed cache
- object storage requirement
- multi-tenant SaaS abstraction

只保留真正會阻礙 Truss P0 correctness、traceability、purge 或 Future Frame seam 的資料結構。

---

## Approved reconciliation — Master O-001

**MECHANICS REVIEW REQUIRED**: Master O-001 includes effective length factor K, default/automatic K inference, controlling I / weak-axis selection policy, final risk bands and related beginner-facing wording. None is implicitly approved. M1 may verify `Pcr = π² E I / (K L)²` using explicit E, I, L and K; numerical section properties do not authorize automatic buckling-axis selection. Automatic product behavior remains blocked.
