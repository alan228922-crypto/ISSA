# AUTHORIZATION_AND_EVENT_ARCHITECTURE.md

## 0. 文件狀態

- 文件角色：RBAC、Event scope、Project ownership、帳號 provisioning、密碼 lifecycle、Event lifecycle、Purge 與 audit 架構。
- 階段：Truss-first P0。
- 不包含 production code / migration。
- Source of Truth：MASTER_SPEC.md v1.2；本文件已完成 reconciliation。

---

## 1. Authorization Principle

【Confirmed】

> 所有權限必須 server-side 驗證；前端隱藏按鈕不是權限控制。

【Recommended】

P0 不導入第三方 object-permission framework。使用：

- custom Django User model
- global role
- EventMembership
- Project ownership
- 小型 policy/helper + filtered queryset/application service

即可滿足需求。

---

## 2. Global Roles

【Confirmed】

```text
DEVELOPER
MANAGER
USER
```

### Developer

- 建立所有角色帳號。
- 建立/管理所有 Event。
- 查看所有 Project。
- 執行系統維護。

### Manager

- 建立 User。
- 批量建立 User。
- 管理被授權 Event。
- 查看 assigned Event 的參賽隊伍 Project。
- 預設不得修改學生 Project。
- 不得建立 Developer / Manager。

### User

- 一個帳號 = 一支參賽隊伍。
- 只能查看/修改自己的 Project。
- 不得查看其他隊伍 Project。

---

## 3. Event-scoped Authorization

【Recommended】

Global `role=MANAGER` 不代表能管理所有 Event。

必須另有：

```text
EventMembership(user, event, membership_type=MANAGER)
```

User participation 亦由 EventMembership 明確表示。

Authorization 問題拆成：

```text
Who are you?         → User.role
Which event?         → EventMembership
Which project?       → Project.owner + Project.event
What action?         → policy rule
```

---

## 4. Access Matrix

| Action | Developer | Assigned Manager | Unassigned Manager | Project Owner User | Other User |
|---|---:|---:|---:|---:|---:|
| View Event | ✓ | ✓ | ✗ | own participating event only | ✗ |
| Edit Event | ✓ | ✓ | ✗ | ✗ | ✗ |
| Create User | ✓ | ✓ User-only | ✗ | ✗ | ✗ |
| Create Manager | ✓ | ✗ | ✗ | ✗ | ✗ |
| Bulk Create User | ✓ | ✓ assigned event | ✗ | ✗ | ✗ |
| View Project | ✓ | ✓ assigned event | ✗ | ✓ own | ✗ |
| Edit Student Project | ✓ system/admin scope | ✗ default | ✗ | ✓ own | ✗ |
| Analyze Project | ✓ | ✗ default | ✗ | ✓ own | ✗ |
| View Analysis Result | ✓ | ✓ read-only | ✗ | ✓ own | ✗ |
| Purge Event | ✓ / system task | policy-limited | ✗ | ✗ | ✗ |

【Recommended】

Manager 的 purge 按鈕是否存在不是核心需求；實際 purge 建議由 scheduled system command 執行。Developer 可以有手動 maintenance trigger。

---

## 5. Authorization Enforcement Points

【Recommended】至少三層防線：

### 5.1 Query scope

例如 User project list 只 query owner 自己的 Project。

### 5.2 Object policy

進入 `/projects/<id>/...` 時再次檢查 read/write action。

### 5.3 Application service

對 bulk import、analyze、purge 等高價值操作，service 不接受「caller 已驗證」作假設；需明確傳入 actor/context 做 policy check 或只由受控入口呼叫。

前端 JS 絕不決定 authority。

---

## 6. Custom User Model Decision

【Recommended / Must decide at project start】

從第一個 migration 起使用 custom User model。

最低語意：

```text
User
- username
- role
- must_change_password
- is_active
```

不建立三種獨立 User table/class。

理由：中途切換 Django User model migration 成本高，這是少數必須一開始做對的架構決策。

---

## 7. Username Rule

【Confirmed】

隊伍 username：

```text
YYYYMMDD + TT
```

其中：

- `YYYYMMDD` = competition date
- `TT` = 兩位 team number

例：`2026110701`。

### Invariants

- team number 必須可正規化為兩位。
- 同一 Event team number unique。
- username 系統層 unique。
- 若日期改動會造成既有 username 變更，應由 Event 管理流程阻止在 provisioning 後任意改 competition date，或要求明確 migration/action；不可靜默重命名帳號。

【Recommended】Event 一旦已有參賽帳號，competition date 視為受保護欄位，修改需 Developer-level explicit workflow。

---

## 8. Initial Password Lifecycle

【Confirmed】

初始密碼 = 隊長學號。

【Recommended】實作流程：

```text
CSV/form receives captain student ID
  ↓
validate only for provisioning input
  ↓
Django set_password(captain_student_id)
  ↓
store password hash only
  ↓
must_change_password = True
  ↓
discard plaintext provisioning value
```

禁止：

- 儲存 `initial_password` plaintext。
- Audit log 存 plaintext。
- 管理員查看目前密碼。
- 在匯入完成頁永久回顯隊長學號作密碼。

---

## 9. Forced Password Change

【Confirmed】首次登入必須強制改密碼。

【Recommended】

登入成功但 `must_change_password=True` 時：

- 允許：logout、password-change page、必要 static assets。
- 阻止：Event、Project、Analyze、管理頁等其他功能。

成功改密碼後：

```text
must_change_password = False
```

P0 不需要 password history、MFA、enterprise identity provider。

---

## 10. Bulk User Account Creation

【Confirmed】至少支援 CSV import、preview、validation、duplicate handling、transaction/all-or-nothing、audit log。

### 10.1 Minimal CSV logical columns

【Recommended】

```text
team_number
captain_student_id
optional_team_name
```

Event 由頁面 context 選定，不由每列 CSV 自由指定，降低誤匯到錯 Event 的風險。

### 10.2 Workflow

```text
Upload CSV
  ↓
Parse in memory / temporary request context
  ↓
Normalize
  ↓
Validate rows
  ↓
Preview usernames + errors
  ↓
Explicit Confirm
  ↓
Revalidate server-side
  ↓
transaction.atomic
  ↓
create all Users + EventMemberships
  ↓
Audit summary
```

### 10.3 Blocking validation

至少：

- malformed team number
- missing captain student ID
- duplicate team number within CSV
- generated username collision
- existing participation conflict
- caller not authorized for Event
- Event status不允許 provisioning

### 10.4 Duplicate policy

【Recommended】

P0 採「blocking duplicate」，不自動 overwrite、merge 或 skip。

原因：all-or-nothing + preview 比自動猜測安全且易理解。

---

## 11. Bulk Import Audit

【Recommended】

Audit 只保存：

- actor
- event
- timestamp
- source filename（sanitized）
- row count
- success/failure
- created account count
- validation error summary codes

不得保存 CSV 原文或初始 password plaintext，除非另有明確 operational requirement；P0 不需要。

---

## 12. Project Ownership

【Confirmed】

```text
Project.event_id
Project.owner_user_id
```

是 authorization truth。

### Rules

- User：`project.owner_user_id == request.user.id` 且 participation 有效。
- Manager read：`project.event_id ∈ assigned_manager_events`。
- Manager write student project：false by default。
- Developer：global maintenance access。

【Recommended】

不要根據 username prefix 猜 Project ownership；username 格式不是 foreign key。

---

## 13. Event Lifecycle

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

### Recommended transition semantics

#### DRAFT

- Event 可設定。
- Developer/assigned Manager 可 provisioning。
- User 是否可登入但不可建模，由產品流程決定；P0 可簡化為不能使用 Project。

#### ACTIVE

- User 可使用 own Project。
- Analyze enabled if Project valid。
- Team provisioning 由 Master O-006 决定；当前服务端 fail-closed 并返回 PROVISIONING_STATUS_POLICY_GAP，不是永久禁止规则。

#### FINISHED_GRACE

- 比賽已結束，purge 尚未發生。
- 【Recommended】read-only 僅為建議。User view/edit/analyze 行為由 Master O-003 決定；read-only、editable、denied 仍為未決選項。
- Manager/Developer 可查看/匯出必要資料。

#### PURGED

- student raw Project 不存在。
- User 無 Project operational access。
- Research 只剩核定 derived metrics。

【Open Decision — Master O-003】FINISHED_GRACE User access 尚未確認；核定前不得建立永久 allow/deny edit/analyze assertions。不影響 Project Operational Data purge。

#### M4C Reflection narrow authoring rule

M4C `reflection-v1` is a narrow learning-evidence rule, not a resolution of Master O-003. During ACTIVE, only the Project student owner may create, edit a DRAFT, or complete an eligible Reflection. FINISHED_GRACE Reflection authoring is temporarily fail-closed; PURGED rejects authoring. DRAFT is visible only to its student owner. A COMPLETED Reflection is readable, but never writable, by its student owner and by assigned Manager/Developer through existing Project-read authorization. This does not set the broader FINISHED_GRACE Project view/edit/analyze policy.

---

## 14. Purge Scheduling

【Confirmed】`purge_at = ends_at + 7 days`。

【Recommended】

P0：

- Django management command：例如 `purge_due_events`
- OS cron / platform scheduler 每日執行
- 不導入 Celery/Redis

每日一次足以符合 7 日政策；若老師要求精確到分鐘，再改 schedule，不需改 PurgeService。

---

## 15. PurgeService Contract

【Recommended】

輸入：

```text
PurgeEventCommand
- event_id
- actor/system_identity
- now
```

Preconditions：

- Event 存在。
- `now >= purge_at`，除非 Developer 執行明確 force maintenance flow。
- Event 尚未成功 purge。

主要步驟：

1. lock/serialize Event purge operation。
2. 計算並保存核定 research derived metrics。
3. 記錄 pre-delete counts。
4. 刪除 Project child operational data。
5. 刪除 raw revisions/results/log payloads。
6. 刪除 identity→research key mapping。
7. Event → PURGED。
8. 保存 PurgeAudit summary。

### Idempotency

對 `PURGED` Event 再執行：

- 不重新建立資料。
- 不報破壞性錯誤。
- 回傳 already-purged/no-op result。

---

## 16. Purge Transaction Boundary

【Recommended】

P0 優先以單一 database transaction 處理「研究 metric finalize + operational delete + status update」。

若未來資料量超過 SQLite/單 transaction 可接受範圍，再重新設計 batch purge；P0 不提前引入 distributed job state。

---

## 17. Purge Audit

```text
PurgeAudit
- id
- event_id/event_code
- started_at
- completed_at
- status
- deleted_counts_json
- retained_counts_json
- trigger_type                      SCHEDULED | MANUAL
- actor_id                          nullable for system
- error_code                       nullable
```

禁止保留被刪 raw model payload。

---

## 18. Research Separation During Purge

【Confirmed】只保留匿名 derived metrics。

PurgeService 不允許：

- copy ModelRevision JSON 到 research table
- copy AnalysisRun raw input/result 到 archive table
- 保留 username → research key mapping

若未來論文要求 raw anonymous model，必須重新開 Data Governance 決策，不得由 Developer自行繞過 purge。

---

## 19. Event Status Authorization Effects

【Recommended】

| Status | User Edit | User Analyze | User View | Manager View | Provisioning |
|---|---:|---:|---:|---:|---:|
| DRAFT | ✗ | ✗ | limited | ✓ | ✓ |
| ACTIVE | ✓ own | ✓ own | ✓ own | ✓ | ✓ / policy |
| FINISHED_GRACE | Master O-003 Open | Master O-003 Open | Master O-003 Open; read-only recommended only | ✓ | ✗ |
| PURGED | ✗ | ✗ | no raw project | metadata only | ✗ |

---

## 20. HTTP Security Baseline

【Recommended】

P0 至少：

- Django authentication/session
- CSRF protection on state-changing requests
- secure password hashing using Django defaults
- server-side permission checks
- no password in logs
- no stack trace shown to normal users
- POST for destructive/state-changing operations
- production deployment 開啟 HTTPS（部署環境責任）

不需要自建 crypto、JWT、OAuth server。

---

## 21. Authorization Test Requirements

必須有 integration/permission tests：

1. User A cannot view User B project by guessed ID。
2. User A cannot POST save/analyze to User B project。
3. Manager assigned Event A cannot read Event B project。
4. Manager cannot modify student project。
5. Manager cannot create Manager/Developer。
6. Developer can perform allowed global actions。
7. `must_change_password=True` cannot bypass password-change flow by direct URL。
8. PURGED 不可操作已 purge 的 Project Operational Data；FINISHED_GRACE 依 Master O-003 保持未決，不建立永久 allow/deny edit/analyze assertions。
9. CSV import re-checks authorization at confirm，不只 preview。
10. purge management command cannot be triggered by ordinary User HTTP action。

---

## 22. Open Decisions

### OD-AUTH-01 — Purge 後 team account lifecycle（authoritative gate: Master O-004）

【Open Decision】

選項：

- disable account
- delete account
- retain login identity but block all project access

Master O-004 確認前，不由 PurgeService 自動刪除或停用 team User。Project Operational Data purge 已 Confirmed，不因帳號 lifecycle 未決而停止。之後可獨立加 account cleanup policy。

### OD-AUTH-02 — FINISHED_GRACE User access（authoritative gate: Master O-003）

【Open Decision】建議 read-only，但需 Product Owner 確認。

### OD-AUTH-03 — ACTIVE Event Team Provisioning（authoritative gate: Master O-006）

【Open Decision】DRAFT 已确认允许 provisioning，PURGED 已确认拒绝。ACTIVE 期间当前安全 fallback 为 fail-closed + PROVISIONING_STATUS_POLICY_GAP；这不是最终业务政策，也不与 FINISHED_GRACE 的 O-003 混用。

---

## 23. YAGNI Guardrails

P0 不加入：

- Keycloak/Auth0 dependency
- OAuth/OIDC server
- per-field ACL
- generic policy DSL
- third-party object permission engine
- MFA mandatory flow
- password vault
- distributed purge workers
- background queue

只做目前三級角色 + Event scope + Project ownership 真正需要的 server-side controls。
