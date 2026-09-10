# API_AND_APPLICATION_FLOW.md

## 0. 文件狀態

- 文件角色：Django routes、普通 forms/pages、JSON endpoints、Application Services、save/check/analyze/revision/result flow。
- 階段：Truss-first P0。
- P0 採 server-rendered Django + 少量 JSON，不採 SPA/API-first。
- Source of Truth：`MASTER_SPEC.md v1.0`；本文件已完成 reconciliation。

---

## 1. Interaction Architecture

【Recommended】

```text
Django Templates
  ├── normal forms/pages
  └── SVG + Vanilla JS interactive canvas
          │
          └── small JSON endpoints
                    │
                    ▼
             Application Services
                    │
        ┌───────────┴────────────┐
        ▼                        ▼
     Django ORM              Pure Domain
                             Idealization
                             Mechanics
```

原則：

- 頁面 navigation、管理、簡單 CRUD 用 Django form/page。
- 只有需要不整頁 reload 的建模/分析互動使用 JSON。
- 不引入 DRF 作為 P0 必要依賴。

---

## 2. Application Service Set

【Recommended】P0 最少：

```text
AccountProvisioningService
EventService
ProjectService
ModelDraftService
SectionService
ModelCheckService
AnalysisService
TeachingInsightService
ComparisonService
ReportService
PurgeService
ResearchMetricService
```

這些是邏輯責任邊界，不要求每個都建立 interface/class hierarchy；簡單 service function/module 即可。

---

## 3. Ordinary Django Pages / Forms

### Authentication

```text
GET/POST /login/
GET/POST /password/change-required/
POST     /logout/
```

### Event / Accounts

```text
GET      /events/
GET      /events/<event_id>/
GET/POST /events/new/                    Developer
GET/POST /events/<event_id>/edit/
GET      /events/<event_id>/users/
GET/POST /events/<event_id>/users/new/
GET/POST /events/<event_id>/users/import/
POST     /events/<event_id>/users/import/confirm/
```

### Project

```text
GET      /projects/
GET      /projects/<project_id>/
GET/POST /projects/<project_id>/settings/
```

### Material / Section metadata

```text
GET      /projects/<project_id>/materials/
GET/POST /projects/<project_id>/materials/new/
GET/POST /projects/<project_id>/materials/<material_id>/edit/
GET      /projects/<project_id>/sections/
GET      /projects/<project_id>/sections/<section_id>/edit/
```

Section Designer 若需要即時計算 property，使用 JSON preview endpoint；最終保存仍 server-side。

### Learning / Report

```text
GET/POST /projects/<project_id>/prediction/
GET/POST /projects/<project_id>/reflection/
GET      /projects/<project_id>/compare/
GET      /projects/<project_id>/report/
```

---

## 4. JSON Endpoints — P0 Minimum

【Recommended】

### 4.1 Save model draft

```text
POST /projects/<project_id>/model/save/
Content-Type: application/json
```

Request：

```json
{
  "schema_version": "physical-draft-v1",
  "expected_draft_version": 12,
  "nodes": [],
  "physical_members": [],
  "connections": [],
  "supports": [],
  "node_loads": []
}
```

Response 200：

```json
{
  "ok": true,
  "draft_version": 13,
  "validation": {
    "errors": [],
    "warnings": []
  }
}
```

### 4.2 Model check

```text
POST /projects/<project_id>/model/check/
```

【Recommended】對 **server-saved draft** 做 check，不信任前端自稱的 Project identity。

Request：

```json
{
  "draft_version": 13
}
```

Response：

```json
{
  "ok": true,
  "draft_version": 13,
  "can_analyze": false,
  "issues": [
    {
      "code": "...",
      "severity": "ERROR|WARNING",
      "entity_refs": [],
      "message": "beginner-facing text"
    }
  ]
}
```

### 4.3 Analyze

```text
POST /projects/<project_id>/analyze/
```

Request：

```json
{
  "draft_version": 13,
  "prediction_id": "optional"
}
```

成功 response：

```json
{
  "ok": true,
  "model_revision_id": "...",
  "analysis_run_id": "...",
  "result_url": "/projects/.../analyses/.../"
}
```

失敗不回 stack trace；回 stable error code + beginner-facing message。

### 4.4 Result data

```text
GET /projects/<project_id>/analyses/<run_id>/data/
```

用途：SVG visualization / deeper numeric panels。

### 4.5 Section property preview

```text
POST /projects/<project_id>/sections/preview/
```

Request 為 versioned section definition。

Response：

- A
- centroid
- Ix
- Iy
- mass/length
- strong/weak axis
- validation issues

Preview result 不自動 persistence；save Section 仍需明確 action。

---

## 5. Why Full Draft Save Instead of Per-node REST CRUD

【Recommended】

P0 互動模型規模小，採完整 draft save 比以下方式更適合：

- `/nodes/<id>` individual API
- `/members/<id>` individual API
- client-side transaction orchestration

優點：

1. 一次 server-side 驗證整個 topology。
2. save transaction 簡單。
3. 減少大量 endpoint 與 partial-state bug。
4. 更符合學生 PoC，而非大型 collaborative CAD。

【Future】若模型大、多人協作或 autosave 成本變高，再考慮 finer-grained mutation；目前不需要。

---

## 6. Draft Version / Stale Client Protection

【Recommended】

使用 project-level integer `draft_version` 作極輕量 optimistic concurrency control。

流程：

```text
client loads version 12
  ↓
client POST save expected=12
  ↓
server current=12 → save → version=13
```

若 server 已是 13 而舊 client 送 expected=12：

```text
409 STALE_DRAFT
```

P0 即使沒有多人協作，此機制仍可避免使用者多分頁覆蓋與 analyze stale model；成本很低。

---

## 7. Save Flow

```text
Browser draft JSON
  ↓
CSRF + authentication
  ↓
Project write authorization
  ↓
Draft schema validation
  ↓
Domain validation
  ↓
transaction
  ├── replace/update project draft entities
  └── draft_version + 1
  ↓
return normalized draft_version + issues
```

Server-owned fields（owner/event/project ID）不接受 client override。

---

## 8. Model Check Flow

```text
POST model/check
  ↓
read authorization
  ↓
verify requested draft_version == current
  ↓
load current draft
  ↓
authoring validation
  ↓
build Physical Snapshot candidate
  ↓
Truss2D Idealization validation
  ↓
pre-solve mechanics validation
  ↓
map machine codes → beginner messages
  ↓
ValidationLog
  ↓
response
```

Model Check 不需要建立成功 AnalysisRun。

【Recommended】若 check 建立 transient solver model，不 persistence 為 ModelRevision；只有 Analyze 才 freeze revision。

---

## 9. Analyze Flow

【Recommended】正式 sequence：

```text
POST analyze(project, draft_version)
  ↓
1. authenticate
  ↓
2. authorize WRITE/ANALYZE on project
  ↓
3. verify approved Event access policy: ACTIVE follows permissions; PURGED has no purged Project Operational Data access; FINISHED_GRACE remains gated by Master O-003
  ↓
4. verify draft_version current
  ↓
5. load draft
  ↓
6. run authoring/domain validation
  ↓
7. freeze immutable ModelRevision
  ↓
8. canonicalize + model_hash
  ↓
9. Truss2DIdealizer → TrussModel + mapping
  ↓
10. canonical input + input_hash
  ↓
11. create AnalysisRun metadata
  ↓
12. mechanics validation
  ↓
13. Truss2DSolver
  ↓
14. stress / mass / Euler postprocess
  ↓
15. persist raw result + diagnostics
  ↓
16. deterministic TeachingInsight
  ↓
17. return run/result URL
```

### Failure before revision freeze

純 authoring incomplete 可不建 revision。

### Failure after revision freeze

若 mechanics/solver 對已冻结輸入失敗：

- 保留 ModelRevision。
- AnalysisRun = `VALIDATION_FAILED` 或 `SOLVER_FAILED`。
- 保存 stable failure code。

這對 traceability/研究 error count 有價值。

---

## 10. ModelRevision Creation Rule

【Recommended】

Analyze 建立新 revision 的最小規則：

- 若 current draft content hash 與上一 revision 相同，可選擇 reuse existing revision，而建立新的 AnalysisRun。
- 若內容不同，建立下一 revision。

P0 最簡單也可每次 Analyze 都建立 revision；但若大量重按 Analyze 會產生重複 revision。

**推薦 baseline：以 model_hash 去重同一 draft，AnalysisRun 仍每次記錄。**

這不需要 generic dedup system，只需 current project last revision comparison。

---

## 11. Prediction Gate

【Confirmed】教學循環為 Predict → Analyze。

【Recommended】

Analyze service 可檢查是否已有針對 current draft/version 的 Prediction。

是否「沒有 Prediction 就禁止 Analyze」屬 Product/Teaching policy；架構支援但不在 service hard-code 未核定規則。

P0 可先把 Prediction 作 strongly encouraged step，而是否 blocking 在 UX spec 決定。

---

## 12. Result Page Flow

【Confirmed】第一層結果先回答：

- 力從哪裡進入？
- 支座如何提供反力？
- 哪些杆受拉？
- 哪些杆受壓？
- 哪裡位移最大？
- 哪些壓杆值得注意屈曲？

【Recommended】

HTML first render 可帶 summary，SVG/詳細數值再讀 result-data endpoint。

```text
GET result page
  ↓
Authorization READ
  ↓
AnalysisRun SUCCESS?
  ↓
Teaching summary + mapping
  ↓
render System View
  ↓
optional fetch deeper result JSON
```

N/V/M 不出現在 P0 contract。

---

## 13. Compare Flow

【Recommended】

P0 不做 automatic optimization。

比較應以兩個或多個已成功 AnalysisRun / ModelRevision 為輸入：

- total mass
- max displacement
- key axial force/stress
- tension/compression pattern summary
- buckling screening summary

系統描述差異，不替學生決定「最佳設計」。

若比較後有修改，DesignRationale 可關聯 before/after revision。

---

## 14. Error Response Contract

【Recommended】JSON error shape：

```json
{
  "ok": false,
  "error": {
    "code": "STALE_DRAFT",
    "message": "目前頁面的模型版本較舊，請重新載入最新模型。",
    "entity_refs": [],
    "details": {}
  }
}
```

### Suggested HTTP status

| Condition | Status |
|---|---:|
| unauthenticated | 302 login / 401 for JSON policy |
| forbidden object | 403 or 404 policy-consistent |
| not found | 404 |
| stale draft | 409 |
| malformed request | 400 |
| domain validation blocks analyze | 422 recommended |
| unexpected server error | 500 |

P0 不必為了純粹 REST purity 增加複雜度；最重要是全平台一致。

---

## 15. Beginner-facing Error Mapping

【Confirmed】Mechanics code 與 Teaching message 分離。

```text
Mechanics issue
  code=SINGULAR_GLOBAL_STIFFNESS
  context=...
        ↓
Teaching/Error Presenter
        ↓
student message
```

Presenter 可依：

- code
- entity refs
- page context

產生提示，但不可更改 mechanics outcome。

---

## 16. Section Designer Flow

```text
User composes strips/shape
  ↓
POST section preview JSON
  ↓
server authorization
  ↓
pure SectionPropertyEngine
  ↓
A / centroid / Ix / Iy / mass-length
  ↓
visual comparison
  ↓
explicit Save Section form/action
```

【Recommended】即時 preview 也由 server-side pure Python engine 計算 authoritative property；JS 可做畫圖，但不應有另一套獨立截面力學公式成為權威。

---

## 17. Bulk Import Flow

普通 form/page，不需要 general JSON API：

```text
GET/POST import page
  ↓
preview table
  ↓
POST confirm with signed/session batch reference
  ↓
revalidate
  ↓
transactional provisioning
  ↓
result page
```

不要把 plaintext password 放進 hidden HTML field 往返多次。

【Recommended】preview/confirm 間可以保留短期 server-side parsed batch 或重新 parse temporary upload；實作選較簡單且不落長期 plaintext 的方式。

---

## 18. Purge Application Flow

非一般 User endpoint。

```text
scheduler
  ↓
management command
  ↓
find due events
  ↓
PurgeService(event)
  ↓
PurgeAudit
```

Developer manual maintenance action若需要，應為明確確認頁 + POST，不提供 GET destructive action。

---

## 19. CSRF / Authorization Rules for JSON

【Recommended】

- 使用 Django session auth + CSRF token。
- 不因 endpoint 是 JSON 就跳過 CSRF。
- 每個 project endpoint重新確認 object permission。
- client-supplied `user_id`, `event_id`, `owner_id` 全部忽略/拒絕。

P0 不需要 JWT。

---

## 20. Endpoint Inventory — P0 Minimum

### Required pages

- auth login/change/logout
- Event list/detail/edit
- Event user list/import
- Project list/workspace
- Material/Section management
- Prediction
- Result
- Compare
- Reflection
- Report

### Required JSON

1. `model/save`
2. `model/check`
3. `analyze`
4. `analysis/data`
5. `sections/preview`

這五類已足以支撐 P0 互動分析主線。

---

## 21. Safe Deferrals

P0 可安全延期：

- public REST API
- DRF
- API version namespace `/api/v1`
- WebSocket
- autosave every keystroke
- per-node mutation API
- background Analyze jobs
- progress streaming
- realtime collaboration
- external OAuth
- GraphQL

---

## 22. Open Decisions

### OD-API-01 — Prediction 是否為 Analyze blocking gate

【Open Decision】Teaching/UX 決定；架構已留檢查點。

### OD-API-02 — FINISHED_GRACE User access（Master O-003）

【Open Decision】read-only 僅為建議；view/edit/analyze 不得在 Master O-003 確認前定案。

### OD-API-03 — Roller orientation UI

【Open Decision】會影響 Support JSON shape，應在實作 support editor 前確認。
