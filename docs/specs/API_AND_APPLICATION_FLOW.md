# API_AND_APPLICATION_FLOW.md

## 0. 文件狀態

- 文件角色：Django routes、普通 forms/pages、JSON endpoints、Application Services、save/check/analyze/revision/result flow。
- 階段：Truss-first P0。
- P0 採 server-rendered Django + 少量 JSON，不採 SPA/API-first。
- Source of Truth：MASTER_SPEC.md v1.3；本文件已完成 reconciliation。

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
- 用户可见 copy 默认使用简体中文（zh-CN）；validation 与 model-check 的 machine-readable code 保持英文，由 Application / Teaching Layer 提供简体中文解释。

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
POST/GET /projects/<project_id>/predictions/... (M4A JSON; exact variants in §4.4.1)
GET/POST /projects/<project_id>/analyses/<run_id>/reflection/ (M4C singleton; exact contract in §4.4.3)
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
  "expected_draft_version": 13,
  "prediction_id": 42
}
```

`prediction_id` may be omitted or `null`; this remains analyzable. When supplied, it must identify completed same-Project, same-source-draft evidence or Analyze fails closed.

成功 response：

```json
{
  "ok": true,
  "model_revision_id": 17,
  "analysis_run_id": 42,
  "status": "SUCCESS",
  "result_schema_version": "truss2d-result-v1"
}
```

Analyze metadata must not contain numerical/classified answers. Failures do not return a stack trace and use a stable English code plus zh-CN message.

### 4.4 Result data

```text
GET /projects/<project_id>/analyses/<run_id>/data/
```

用途：SVG visualization / deeper numeric panels。

For M4A, an owner read of a SUCCESS numerical result must record the server-side `(Project, source_draft_version)` StudentResultReveal before returning the payload. Manager/Developer reads do not record student reveal.

### 4.4.1 M4B Compare and Explain derived data

```text
GET /projects/<project_id>/analyses/<run_id>/comparison/
GET /projects/<project_id>/analyses/<run_id>/explanation/
```

Both endpoints are GET-only deterministic derived views, not CRUD resources: they create no Comparison/Explanation aggregate, list endpoint, POST action, or client-side “mark revealed” action. They follow the existing M3 JSON success envelope while returning exactly one M4B domain contract and no incidental analysis/model payload:

```json
{"ok": true, "comparison": {"schema_version": "comparison-v1"}}
```

```json
{"ok": true, "explanation": {"schema_version": "explanation-v1"}}
```

The nested value is the complete contract defined respectively in `COMPARISON_CONTRACT.md` or `EXPLANATION_CONTRACT.md`. The response must not add full `result_json`, solver input, physical snapshot, Prediction ORM row, Material/Section data, credentials, or internal ORM metadata.

The View remains thin: authenticate; scoped Project/Run lookup; apply existing `can_view_project`; call one minimal application disclosure service; map its stable result/error to `JsonResponse`. The application service alone validates `SUCCESS`, invokes deterministic Compare/Explain Core, then calls the existing `record_student_result_reveal(project, run, actor)` before returning authoritative numerical/classified content. Views do not recompute teaching states, ZERO_FORCE, displacement, templates, mechanics, or reveal policy.

The scoped Run lookup is `run.pk + project_id` as in Result Data. A Run from another Project is indistinguishable from an absent scoped Run (`PROJECT_NOT_FOUND`, 404); an actor without Project read permission receives the existing `PROJECT_READ_DENIED`, 403. Manager and Developer follow existing read authorization but the existing reveal service records no StudentResultReveal for them. Student-owner reveal recording is idempotent by `(Project, source_draft_version)` and must commit before the response; a reveal persistence failure returns `RESULT_REVEAL_FAILED`, 500, with no derived content. A Compare/Explain reveal therefore also blocks later same-draft Prediction completion via the existing `PREDICTION_AFTER_RESULT_REVEAL` invariant.

Only `AnalysisRun.status = SUCCESS` may return a normal M4B output. `VALIDATION_FAILED` and `SOLVER_FAILED` return `ANALYSIS_NOT_SUCCESS`, 422, with the zh-CN message “分析尚未成功完成，暂无可用的比较或解释结果。”, create no reveal, and do not become a diagnostic-teaching feature. Integrity failures such as an incompatible Prediction/source draft fail closed with `COMPARE_SOURCE_MISMATCH`, 409; other immutable result/provenance conflicts use the endpoint-specific English integrity code with 409. Unexpected errors use the standard safe `INTERNAL_ERROR`, 500, without traceback.

Prediction remains a Soft Gate:

- Compare with `AnalysisRun.prediction = null` returns HTTP 200 and the nested `comparison-v1` unavailable form (`comparison_available: false`, `reason: "NO_PREDICTION"`), never 404/409.
- Explain with no Prediction returns HTTP 200 and complete `explanation-v1` member-force / maximum-displacement blocks, `comparison_available: false`, `comparison_reason: "NO_PREDICTION"`, and no prediction-comparison or representative-load-path blocks.

Dependency direction is `Analysis facts → Compare → Explain`; when no Prediction, it is `Analysis facts → Explain`. Neither Core mutates the other, and HTTP never calls mechanics directly.

### 4.4.2 Prediction JSON minimum

```text
POST /projects/<project_id>/predictions/                         create DRAFT
GET  /projects/<project_id>/predictions/current/                 discover current-draft Prediction
POST /projects/<project_id>/predictions/<prediction_id>/complete/ complete prediction-v1
GET  /projects/<project_id>/predictions/<prediction_id>/          read own/historical Prediction
```

All POST endpoints retain CSRF and use thin views. There is no generic CRUD API and no client “mark revealed” endpoint.

The current-discovery route uses the Project's server-authoritative `draft_version` as `source_draft_version` and returns exactly `NONE`, one `DRAFT`, one `COMPLETED`, or fails closed with `PREDICTION_AMBIGUOUS` when legacy rows violate P0 cardinality. It must not choose a row by timestamp or status, return a list selector, or mutate evidence. A `DRAFT` is resumable but never auto-bound to Analyze; a `COMPLETED` record is the only one the Workspace may explicitly offer for Analyze binding. `NONE` and a skipped `DRAFT` use `prediction_id: null`. The authoritative cardinality, concurrency, remediation, and evidence-preservation rules are in `PREDICTION_AND_REVEAL_ARCHITECTURE.md` under O-M5-P01.

Prediction GET follows existing Project read authorization; authoring remains student-owner-only. JSON errors use 400 for malformed/unknown request shape, 403/404 for authorization and scoped lookup, 409 for lifecycle conflict or `PREDICTION_AMBIGUOUS`, 422 for payload/topology validation, and a safe 500 for unexpected failure. Machine codes are English and human messages are zh-CN; no traceback is returned.

### 4.4.3 Reflection JSON minimum

Reflection is an AnalysisRun-scoped singleton; its primary route identity is `run_id`, never `reflection_id`:

```text
GET  /projects/<project_id>/analyses/<run_id>/reflection/           read
POST /projects/<project_id>/analyses/<run_id>/reflection/           create or update DRAFT
POST /projects/<project_id>/analyses/<run_id>/reflection/complete/  complete DRAFT
```

Every route scopes `AnalysisRun(pk=run_id, project_id=project_id)`. A Run outside the URL Project is indistinguishable from an absent scoped Run (`PROJECT_NOT_FOUND`, 404); no route accepts a Reflection id. `GET` of an absent singleton returns `REFLECTION_NOT_FOUND`, 404. Absence is valid product state and never means Analyze, Prediction, Result, Compare, or Explain is blocked.

All POST endpoints retain Django CSRF and use the existing authenticated JSON convention. The authoring request is an object whose only allowed keys are `original_reasoning`, `unexpected_results`, and `next_iteration_intent`. It is a DRAFT upsert: if no Reflection exists, the View calls `create_reflection(run, actor)` and then applies the supplied fields; if a DRAFT exists, it calls `update_reflection(reflection, actor, fields)`; if it is COMPLETED, it returns the immutable lifecycle conflict. Missing fields retain their existing DRAFT values, while an explicitly supplied empty string clears that field. Client input cannot set identity, author, status, timestamps, or schema version.

The complete action accepts an empty JSON object only and calls `complete_reflection(reflection, actor)`. Completion policy—including DRAFT state, three trimmed non-empty fields, the server timestamp, ACTIVE-event authoring, SUCCESS/same-source Reveal eligibility, and immutability—remains solely in the Reflection application service. The HTTP boundary does not reproduce lifecycle or authorization policy and never creates a `StudentResultReveal`.

Reflection GET returns only `reflection-v1` metadata and student text: `analysis_run_id`, `project_id`, `source_draft_version`, `status`, `original_reasoning`, `unexpected_results`, `next_iteration_intent`, `reflection_schema_version`, `created_at`, `updated_at`, and `completed_at`. It never returns result, solver input, physical snapshot, Compare/Explain data, or a full User object. DRAFT is owner-private. COMPLETED is readable by its owner and by existing authorized Manager/Developer Project readers, who remain read-only; other users have no access.

Errors use English machine codes and zh-CN messages without traceback. `MALFORMED_JSON` and `INVALID_REQUEST` are 400; scoped absence/inaccessible data follows existing 403/404 policy; `REFLECTION_ALREADY_EXISTS`, `REFLECTION_ALREADY_COMPLETED`, and `REFLECTION_NOT_DRAFT` are 409; `REFLECTION_NOT_ELIGIBLE`, `REFLECTION_RUN_NOT_SUCCESS`, `REFLECTION_INCOMPLETE`, and `REFLECTION_INVALID_FIELDS` are 422; unexpected failures are `INTERNAL_ERROR`, 500. No DELETE, archive, restore, reopen, list, generic CRUD, or DRF endpoint exists.

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

【Confirmed】

Analyze 建立新 revision 的最小規則：

- 僅當 current Project、`source_draft_version` 與 `model_hash` 都與既有 revision 相同時，才可 reuse existing revision，而建立新的 AnalysisRun。
- 新的 `source_draft_version` 必須建立下一 revision，即使 content hash 相同。
- 內容不同時同樣建立下一 revision。

P0 最簡單也可每次 Analyze 都建立 revision；但若大量重按 Analyze 會產生重複 revision。

**Baseline：以 `(Project, source_draft_version, model_hash)` 去重同一 draft，AnalysisRun 仍每次記錄。**

這不需要 generic dedup system，只需 current project last revision comparison。

---

## 11. Prediction Gate

【Confirmed】教學循環為 Predict → Analyze。

【Recommended】

Analyze service 可檢查是否已有針對 current draft/version 的 Prediction。

Prediction is confirmed Soft Gate: absence never blocks Analyze. If supplied, the service verifies completed status, same Project, owner, and exact current source draft version before creating the Run link.

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

Any future student-owner response that exposes numerical/classified answers must pass through the same server reveal boundary before content is returned; SUCCESS metadata alone is not reveal.

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

M4C P0 若要记录下一版的修改或重新观察意图，使用绑定 AnalysisRun 的 `Reflection.next_iteration_intent`；不建立关联 before/after revision 的独立 DesignRationale aggregate。M4C endpoint 仍待后续 Gate 冻结。

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

Confirm 必须在服务端重新验证 Event status：DRAFT 允许，PURGED 拒绝；ACTIVE 在 Master O-006 未关闭前 fail-closed 并返回 PROVISIONING_STATUS_POLICY_GAP。前端不得决定该政策。

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

### Resolved — Prediction is an Analyze Soft Gate

Prediction absence never blocks Analyze. A supplied Prediction must be completed, same-Project, owner-bound, and exactly current-draft evidence before its nullable AnalysisRun link is created.

### OD-API-02 — FINISHED_GRACE User access（Master O-003）

【Open Decision】read-only 僅為建議；view/edit/analyze 不得在 Master O-003 確認前定案。

### Resolved — Roller orientation UI（Master O-002）

Support JSON 使用 restrained_axis；ROLLER 只允许 X/Y，PINNED 为 null。
