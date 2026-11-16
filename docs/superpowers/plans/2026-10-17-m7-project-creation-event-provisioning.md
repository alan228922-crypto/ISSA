# M7 Project Creation & Event Provisioning — TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. Owner approval of this plan and the execution method is required before implementation; this document does not authorize dispatching agents.

**Goal:** 让 ACTIVE Event 的既有有效参赛 USER 自助建立／进入自己的唯一正常 Project，同时关闭 FINISHED_GRACE 写入口及 PURGED 残留行读取缺口。

**Architecture:** 保留 Django SSR、现有角色／Membership 与 Project ownership authority。新建应用服务负责授权、事务内重复判断和 SQLite 安全串行化；薄 HTTP adapter 负责单字段表单及 Workspace redirect。现有授权边界统一实施状态限制，不建立第二套 Draft、Provisioning 或 Solver 系统。

**Tech Stack:** Python、Django 5.2.17、SQLite、pytest / pytest-django、Playwright；不新增依赖。

**Spec:** [MASTER_SPEC](../../specs/MASTER_SPEC.md)、[Authorization architecture](../../specs/AUTHORIZATION_AND_EVENT_ARCHITECTURE.md)、[ADR register](../../specs/ARCHITECTURE_DECISION_REGISTER.md)，以及 Product Owner 本轮批准的 D-M7-001/002/003 和 8 项冻结条件。旧文档中的 O-003 OPEN 由本次明确批准取代；执行 Task 1 时同步书面记录，不能以旧 OPEN 文案否决已批准决策。

**Estimated Size:** L (Owner amendment: M → L).

**Execution:** APPROVED — native Task 1 → Task 8; internal architecture checkpoints after Tasks 4 and 6. Stop only on the Owner-specified scope/architecture conflicts.

**Planning baseline:** clean `main@8dc11a1c095b5a350299296f555952af3268c946`，`.worktrees/main-integration`。本轮仅新增本文档；未运行实施、迁移或验收环境操作。

## Global Constraints

- M7 状态：`READY FOR TDD IMPLEMENTATION`；Owner 已批准原生逐 Task 执行。
- `D-M7-001 = Option A`：authenticated + active `USER` + exact Event active `PARTICIPANT`；只允许本人 self-create。
- 不开放 ACTIVE 新 User／Membership；Manager／Developer 不得代建。`O-006 = OPEN / FAIL CLOSED`。
- `D-M7-002 = Option A`：正常建立最多一个 `(Event, owner User)` Project；legacy 多 Project 保留、不合并、不删除、不选 latest。
- 一个合法既有 Project：返回它，不覆盖名称、Draft、资源或历史。
- `D-M7-003 = Option A`：`FINISHED_GRACE = READ-ONLY HISTORY`。允许历史读取；禁止 create / Save / Check / Analyze / Prediction / Reflection / Reasoning authoring 及其他学生写入。
- `PURGED` operational GET 与写入 fail closed，包括 Developer；不依赖物理清除已经完成。
- 新建要求 `ACTIVE` 且 `now < purge_at`；`now == purge_at` 必须拒绝。此检查不自动改变 Event 状态或执行 purge。
- 新建固定 `TRUSS_2D`、`physical-draft-v2`、`draft_version = 0`；空 Draft，不预建 AnalysisRun / ModelRevision / Snapshot / Prediction。
- 表单仅项目名称；成功直接 Workspace。Material / Section 不 seed，使用 owner 既有资源或自行创建。
- 无 Team model、Project status、primary/archive、hard delete、generic provisioning engine；无 schema / migration。
- Solver / Mechanics / units `mm / N / MPa / g`、Node-as-Joint、Draft Independence、Delete Impact 图操作语义、历史快照均不变。
- 不触碰 root / grid worktree、既有 demo／真实 DB、运行平台；不 stash / reset / restore / cleanup 用户修改。
- 后续实施在独立 `feat/project-creation-m7` worktree；不自动 merge / push / tag / deploy，不做真实数据转换。

## Review Focus

1. 同一 owner 的同时双请求：不能双建或覆盖已有 Draft；Task 4 文件型 SQLite 并发测试。
2. 页面打开后撤销 Membership／停用 User／Event 到期：POST 必须重新授权，事务等待后也不能使用旧权限；Tasks 2/4/5。
3. legacy 多 Project、FRAME_2D、blocked v1：不能过滤掉以后偷偷新建，不能 latest 猜测；Task 3。
4. GRACE 历史首次 Results disclosure 与 Prediction 共用 guard：禁止 authoring 不能误伤历史读取；Task 2。
5. 通过另一个 ACTIVE Project 删除共享资源：不能间接改写 GRACE/PURGED Project；Task 6。

## File / responsibility map

| 文件 | 职责 |
| --- | --- |
| `competitions/authorization.py` | 既有角色／Membership authority；增加 Project operational 状态门禁 |
| `projects/services.py` | 复用中央权限，保留 blocked migration 门禁 |
| `projects/creation.py` (new) | create policy、create-or-open、锁／有限重试、结果与错误类型 |
| `projects/forms.py`, `projects/creation_views.py`, `projects/event_urls.py` (new) | 单字段 SSR form、HTTP adapter、Event-scoped route |
| `config/urls.py` | 注册 Event-scoped Project route，不改变 provisioning route |
| `accounts/views.py`, `templates/accounts/event_landing.html` | 可创建 Event 的入口，保留所有合法 legacy Project 卡片 |
| `templates/projects/project_create.html` (new) | 安全学生文案、CSRF、名称字段 |
| `projects/workspace.py`, `templates/projects/workspace.html` | GRACE readonly bootstrap／提示，历史入口仍可用 |
| `learning/services.py` | Prediction 写入 guard 与历史 disclosure guard 分离，补齐残留行读取检查 |
| `modeling/services.py`, `analysis/services.py` | 如现有入口只在事务前检查权限，锁定后补一次状态复核；不改数值／验证算法 |
| `materials/services.py`, `materials/views.py` | Project-context 写门禁及共享资源对只读 Project 的间接变更保护 |
| `docs/specs/{MASTER_SPEC,ARCHITECTURE_DECISION_REGISTER,AUTHORIZATION_AND_EVENT_ARCHITECTURE,API_AND_APPLICATION_FLOW}.md` | 批准决策、端点、边界同步；不清理无关旧文档 |
| `tests/permissions/test_m7_event_policy.py` (new) | 角色、Event 状态、GRACE/PURGED 权限矩阵 |
| `tests/application/test_project_creation.py` (new) | 创建、幂等、legacy、精确默认与零副作用 |
| `tests/application/test_project_creation_concurrency.py`, `tests/m7_concurrency_settings.py` (new) | 独立连接、真实文件型 SQLite 并发与重试测试 |
| `tests/endpoints/test_project_creation.py`, `tests/endpoints/test_m7_read_only.py` (new) | 表单／公开 HTTP、全部读写入口矩阵 |
| `tests/browser/test_m7_project_creation.py` (new) | 真实公开控件建立、资源准备、建模／保存／检查／分析、只读历史 |
| 既有权限、reasoning、materials、landing 测试 | 与已批准状态变化有关的精确断言更新，其他语义不放宽 |

## Contract decisions for implementation

### Create or open

- 唯一路由：`GET/POST /events/<int:event_id>/projects/create/`，URL name `event_projects:create`。
- GET 不建 Project、不写业务数据。POST 只接收 `name` 与 CSRF；拒绝额外 owner/event/schema/type/Draft 字段，不能把它们赋值给模型。
- `ProjectCreateForm.name`：strip whitespace、必填、1–200 字符；初始显示「我的结构方案」。无 Material/Section 输入。
- 授权先于 existing lookup/reuse；GRACE 即使已有 Project，create POST 也不得作为旁路成功。
- 全部 `(event_id, owner_user_id)` 行参与 cardinality，不先过滤 schema/type。
- 0 行：新建固定默认 Project。1 行：仅当 TRUSS_2D、schema 为 v1/v2 且没有 BLOCKED migration audit 时返回原 Project；合法 v1 不转换。
- 1 行但不可用：409 `PROJECT_EXISTING_UNAVAILABLE`；2+ 行：409 `PROJECT_MULTIPLE_EXISTING`，安全提示从赛事页选择现有项目。不得新增／自动选第一或 latest。
- 正常 HTTP success 使用 302 PRG 到既有 `projects:workspace`；首次和重复成功均同样 redirect。
- 安全错误：不存在 Event 404；身份／角色／Membership 403 `PROJECT_CREATE_DENIED`；非 ACTIVE 403 `EVENT_NOT_ACTIVE`；PURGED 403 `EVENT_PURGED`；到期 403 `EVENT_ACCESS_EXPIRED`；锁重试耗尽 503 `PROJECT_CREATE_BUSY`。学生 DOM 不显示这些 machine codes / raw exceptions。
- 无 name 更新操作；一个合法 existing Project 的重复 POST 仍须通过表单校验，invalid name 返回 200 带字段错误且不写入。

### State policy

| 操作 | DRAFT（既有行为） | ACTIVE | FINISHED_GRACE | PURGED |
| --- | --- | --- | --- | --- |
| 新建 Project | 拒绝 | 满足完整 create 条件时允许 | 拒绝 | 拒绝 |
| 已有 Project/历史读取 | 保留既有角色权限 | 保留 | 保留既有角色权限 | 拒绝残留行 |
| Save / Check / Analyze / authoring | 不扩大既有授权 | 保留既有授权 | 拒绝 | 拒绝 |

- 本次不把所有 DRAFT Project 变成只读，不扩大 Manager／Developer 作者权限。
- `purge_at` cutoff 本轮明确用于 create；不假装 scheduler 已实现，也不自动 purge/推进 Event。
- GRACE 合法历史 GET 允许既有最小 `StudentResultReveal` disclosure receipt（系统访问记录，不是学生 authoring）；禁止创建 Prediction/Reflection/Reasoning、Run、Revision、变更 Draft。
- 共享 owner library 不改变归属。通过 GRACE Project 的资源写入拒绝；从 ACTIVE 上下文修改／删除被 GRACE/PURGED 当前 Project 引用的资源也拒绝，不能隐式改写只读 Draft。未被这些 Project 引用的 owner 资源仍可在合法可写上下文管理。不自动复制资源，不改变删除依赖图语义。

## Task 1 — Freeze the written contract and isolated execution baseline

**Files:** 上述四份 `docs/specs/` 文件；本计划。无 production/test 修改。

**Interfaces:** Produces 已批准 D-M7-001/002/003 的书面状态、create/public-access contract；后续 Tasks 2–8 消费本计划签名与矩阵。

- [x] 复查 main HEAD/clean、root 原有 dirty 文件清单，不输出可能含凭证的 README diff；如基线漂移先报告，不覆盖。
- [x] 依据 using-git-worktrees 技能，从批准基线建立独立 `feat/project-creation-m7`。所有测试使用隔离测试 DB；不启动／接管旧 server。
- [x] 在任何 production/test 修改前运行 fresh baseline：`pytest -q -m 'not browser'`；`pytest tests/permissions tests/endpoints/test_event_landing.py tests/endpoints/test_reasoning_json.py -q`；`pytest tests/mechanics -q`；`python3 manage.py check`；`python3 manage.py makemigrations --check --dry-run`；`git diff --check`；选择现有 Event landing / Workspace lifecycle browser subset。失败先诊断，不算 M7 RED。
- [x] 更新四份 spec：关闭 O-003 为 GRACE readonly；记录 D-M7-001/002/003、新建 v2 默认与 legacy 保留；O-006/O-004 保持 OPEN。不要顺便改 Grid 文档。
- [x] 验证 `git diff --check`，逐项核对本文 Global Constraints；仅 docs 发生变化。此任务是合同同步，无伪造 RED。
- [x] 后续执行时提交：`docs: freeze M7 project creation and event access decisions`。

## Task 2 — RED → state authorization, residual reads and history-safe learning

**Files:** `competitions/authorization.py`, `projects/services.py`, `projects/workspace.py`, `learning/services.py`；必要的 `modeling/services.py`, `analysis/services.py`；`tests/permissions/test_m7_event_policy.py`, `tests/endpoints/test_m7_read_only.py`, `tests/endpoints/test_reasoning_json.py`。

**Interfaces:** 保留 `can_view_event(actor, event) -> bool`、`can_view_project(actor, *, event_id, owner_user_id) -> bool`、`can_modify_project(actor, *, event_id, owner_user_id) -> bool` 和 `projects.services` 的 `(actor, project) -> bool` wrappers。新增 `learning.services._authorize_prediction_author(project, actor) -> None`，沿用 `PredictionError`；`_authorize_student_owner(project, actor) -> None` 保留 owner/participant 读取／disclosure 身份检查，不作为新的 authoring gate。

- [x] 写 RED `test_grace_denies_operational_writes_but_preserves_history`，参数化 Save、Check、Analyze、Prediction create/complete、Reflection create/update/complete、Reasoning POST、section preview：合法 owner 返回拒绝；Draft/version、Run、Revision、Prediction、Reflection、Reasoning 数量与内容不变。把既有 reasoning GRACE=200 断言改成 403，DRAFT/ACTIVE 断言保留。
- [x] 写 RED `test_purged_residual_rows_are_not_operationally_readable`：保留 Project、Run、Revision、learning rows 后将 Event 标 PURGED；对 owner/Manager/Developer，Workspace、legacy export、analyses list/data/report/comparison/explanation、Prediction GET、Reflection GET、Reasoning GET 均非 2xx 且无数据泄露，赛事页不列出残留 Project；直接调用相关 read services 同样拒绝。
- [x] 写 RED `test_first_historical_disclosure_in_grace_is_readable`：ACTIVE 时通过真实分析服务产生成功 Run，转 GRACE 后首次 GET data/report/comparison/explanation 可读；至多产生既有 disclosure receipt，不能新建 authoring 记录或分析。补 `test_grace_workspace_is_read_only_with_results_navigation`，bootstrap readonly=true、Save/Check/Analyze 不可用、历史四入口保留。
- [x] 运行 `pytest tests/permissions/test_m7_event_policy.py tests/endpoints/test_m7_read_only.py tests/endpoints/test_reasoning_json.py -q`；预期 RED 是现有 GRACE 写入成功、PURGED 残留读取成功或错误 readonly bootstrap，不能把 fixture/setup 错误算 RED。
- [x] 实现最小中央状态门禁，拒绝 inactive/anonymous actor；GRACE/PURGED 写入 fail closed，PURGED operational reads fail closed。Prediction 两个 writer 使用新 author guard；disclosure 保留读取 guard。补 reflection owner early-return 前 read guard。事务内重新取 Project/Event 后复核权限，避免用事务前缓存状态写入；不改 validation 或 mechanics。
- [x] 重新运行上述命令及 `pytest tests/permissions tests/endpoints/test_prediction_json.py tests/endpoints/test_reflection_json.py tests/endpoints/test_compare_explanation_json.py tests/endpoints/test_report_json.py -q`；要求 GREEN、既有合法历史角色访问不回退。
- [x] 提交：`fix: enforce M7 read-only and purged operational boundaries`。

## Task 3 — RED → strict create-or-open service and default object graph

**Files:** new `projects/creation.py`, `tests/application/test_project_creation.py`。

**Interfaces:**
- `ProjectCreationError(code: str, status_code: int)` exposes `.code`, `.status_code`。
- immutable `ProjectCreationResult(project: Project, created: bool)`。
- `project_creation_error(*, actor: User, event: CompetitionEvent, now: datetime) -> str | None`：仅资格检查，不查／写 Project；用于入口展示和事务内复核。
- `create_or_open_project(*, actor: User, event_id: int, name: str) -> ProjectCreationResult`：读取当前时间；服务也验证名称，不能只依赖 form；实际锁逻辑由 Task 4 完成。

- [x] 写 RED `test_active_participant_creates_empty_v2_project`，核心断言：
  ```python
  result = create_or_open_project(actor=owner, event_id=event.pk, name=" 我的结构方案 ")
  assert result.created is True
  assert (result.project.owner_user_id, result.project.event_id) == (owner.pk, event.pk)
  assert (result.project.analysis_type, result.project.draft_schema_version,
          result.project.draft_version) == ("TRUSS_2D", "physical-draft-v2", 0)
  assert result.project.name == "我的结构方案"
  ```
  分别断言 Node/Member/Connection/Incidence/Support/Load/Run/Revision/Prediction=0，Material/Section/User/Membership 计数不变。
- [x] 写 `test_create_policy_matrix`：anonymous、inactive USER、Manager、Developer（即使有 PARTICIPANT）、missing/inactive/wrong-Event/wrong-type Membership 全拒绝；仅精确 active PARTICIPANT USER 允许。DRAFT/GRACE/PURGED 拒绝；stale ACTIVE 在 purge_at 前允许、等于／之后拒绝；用可控时间而非 sleep。
- [x] 写 `test_duplicate_returns_same_project_without_mutation`：重复名称不同仍同 pk，created=false，原名称/Draft/version/updated_at/历史不变。参数化合法 v1/v2；验证无自动 conversion。
- [x] 写 `test_legacy_cardinality_and_unavailable_project_fail_closed`：2+ legacy 保持全部数据；一个 FRAME/未知 schema/BLOCKED v1 也不新建。补服务直接调用 invalid blank/201 字符名称拒绝、exception rollback 无半成品。
- [x] 运行 `pytest tests/application/test_project_creation.py -q`；先记录缺失服务／行为的真实 RED，再实现以上签名及分支；不使用 demo seed helper 或 raw exception 学生文案。
- [x] 同命令 GREEN；确保普通测试不是对单独 helper 做断言而绕过 public service。
- [x] 提交：`feat: add authorized create-or-open project service`。

## Task 4 — RED → real SQLite concurrency and stale-authorization revalidation

**Files:** `projects/creation.py`；new `tests/application/test_project_creation_concurrency.py`, `tests/m7_concurrency_settings.py`。

**Interfaces:** 保留 Task 3 public signatures；新增内部 `_create_or_open_once(*, actor_id: int, event_id: int, name: str) -> ProjectCreationResult`，单次完整 transaction；public service 仅对 SQLite busy/locked 做最多 5 次完整事务尝试，退避 `0.05 * (attempt + 1)` 秒，其他异常不重试。耗尽映射 `PROJECT_CREATE_BUSY` / 503，不伪报成功。

- [x] 新测试 settings 从 `config.settings` 导入、复制 DATABASES；只将 `default.TEST.NAME` 指向必填环境变量 `M7_TEST_DB_PATH` 的临时文件，缺失则拒绝运行此专用配置。不更改生产 SQLite timeout/transaction_mode；测试结束不接触 root DB。
- [x] 写 RED `test_concurrent_creates_share_one_project`：`django_db(transaction=True)`、两个独立连接／worker 同步进入 service，文件型 SQLite；两个返回同 pk，created 标志恰好一个 true，Project count=1，名称为获胜者输入且不会被另一请求覆盖。不要使用内存 SQLite证明并发。
- [x] 写 RED `test_membership_revocation_while_waiting_denies_create`、`test_event_closes_while_waiting_denies_create`、`test_user_disabled_before_retry_denies_create`：用 Event/barrier 控制竞争与提交顺序，重新授权拒绝，count=0；不靠随机延迟。补 `test_locked_retry_restarts_whole_transaction` 和 `test_lock_exhaustion_returns_busy_without_partial_write`，mock 只用于注入明确 lock 异常，不替代真实竞争测试。
- [x] 运行（先用 `mktemp -d` 分配目录，将下面占位换成实际绝对路径）：`PYTHONPATH=tests M7_TEST_DB_PATH=/private/tmp/<allocated-dir>/m7.sqlite3 pytest --ds=m7_concurrency_settings tests/application/test_project_creation_concurrency.py -q`。要求先看到 Task 3 仅检查后创建时的竞争 RED；若自然竞争未稳定暴露，用受控同步使两个请求完成旧 cardinality read 再推进，不改 production 流程来迎合测试。
- [x] 实现：先做只读资格 preflight；transaction 内首先对 Event 执行值不变的 `UPDATE status = F('status')`，获得 SQLite write serialization（不能只用被 SQLite 忽略的 `select_for_update`）；随后重新读取 Event、User、Membership、当前时间与所有 owner Projects，再判断／创建。Event 不更新时间戳，不改变 status。锁序 Event → User/Membership 读取 → Project；每次重试均重新读取。检查 User/Membership 时使用适用数据库的行锁，SQLite 的写锁已排除并行更新；不新增 schema。
- [x] 重跑上述文件型命令至少 3 次独立 process，均 GREEN；然后重跑 Task 3 文件。明确保证仅覆盖正常应用 create path，不声称 raw ORM 被 DB unique constraint 禁止。
- [x] 内部 architecture checkpoint：SQLite serialization、无 schema、legacy 保留符合冻结设计即可继续，无须等待 Owner。
- [x] 提交：`fix: serialize project creation and revalidate eligibility`。

## Task 5 — RED → one-field SSR form, public endpoint and Event entry

**Files:** new `projects/forms.py`, `projects/creation_views.py`, `projects/event_urls.py`, `templates/projects/project_create.html`, `tests/endpoints/test_project_creation.py`；modify `config/urls.py`, `accounts/views.py`, `templates/accounts/event_landing.html`, `tests/endpoints/test_event_landing.py`。

**Interfaces:** `ProjectCreateForm(forms.Form)` only field `name`；`project_create(request: HttpRequest, event_id: int) -> HttpResponse` consumes Task 3 service。`event_projects:create` route 如上；Event entries 新增 presentation state `project_entry_state: str` = `CREATE` / `CONTINUE` / `MULTIPLE` / `UNAVAILABLE`；资格和所有 owned Project cardinality 共同决定，不能仅依据资格。0 项且合资格显示「创建项目」；1 项显示「继续建模」，无 Create CTA；2+ 项保留全部合法卡片、安全说明且无 Create CTA、不选 latest；不新增 domain/schema。模板不嵌入 owner/schema/type 等内部字段。

- [x] 写 RED `test_get_create_form_has_only_name_and_no_side_effects`：GET 200；业务字段集合恰为 name，含 CSRF，无数据库对象新增。`test_create_post_redirects_directly_to_workspace`：302+正确 Location，follow 后空 v2 Workspace 可打开、version0；重复 POST redirect 同 pk。
- [x] 写 `test_post_revalidates_after_form_open`：GET 后撤 Membership、换 Event status、停用 actor／跨 Event forged POST，均不新建。CSRF-enforcing Client 无 token POST=403，GET 不能创建，非法 HTTP method=405；forced password middleware 仍按既有改密流程阻挡。
- [x] 写 `test_name_validation_and_tampered_fields_are_safe`：空白/201 字符返回安全字段错误无写入；HTML名称被 escape；额外 owner/event/schema/type/raw Draft 参数 400 安全文案且无写入；未知 exception=500 通用中文，无 traceback/code/payload。已知 403/409/503 只显示 allowlisted「发生什么／下一步」文案。
- [x] 写 `test_event_landing_create_entry_and_legacy_cards`：符合资格的 ACTIVE USER 有「建立项目」入口；DRAFT/GRACE/PURGED、Manager/Developer 无此入口；有一个 Project 可进入原 Project；legacy 多卡片完整保留、无 latest 或覆盖行为。入口不承担授权，直接 forged POST 仍拒绝。
- [x] 运行 `pytest tests/endpoints/test_project_creation.py tests/endpoints/test_event_landing.py -q`，确认 route/form 缺失的 RED。
- [x] 按接口注册 SSR endpoint；public service 负责授权／事务，view 不复制 create 逻辑；GET 独立检查资格。已有资源为空不阻挡创建；沿用 Workspace 明确材料／截面准备引导，不偷偷 seed。最小 structured logging 仅 actor/event/project/action/outcome，不记 raw name、密码、CSV、Draft。
- [x] 同命令 GREEN，加 `pytest tests/permissions/test_password_change_gate.py tests/application/test_team_provisioning.py -q`。补 ACTIVE provisioning preview/confirm 仍 `PROVISIONING_STATUS_POLICY_GAP` 的回归（包括 Developer）；不开放新 Membership。
- [x] 提交：`feat: expose student project creation through event page`。

## Task 6 — RED → close project-context and indirect resource write bypasses

**Files:** `materials/views.py`, `materials/services.py`, `tests/endpoints/test_m7_read_only.py`, `tests/endpoints/test_material_pages.py`, `tests/application/test_materials.py`。

**Interfaces:** `materials.views._owned_project(request, project_id, *, write=False) -> Project`，先 owner + central read guard，write 时检查 `projects.services.can_modify_project`。新增 `materials.services.assert_resource_mutable(*, actor: User, resource: Material | Section | Strip) -> None`，不可修改抛既有 `SectionServiceError("PROJECT_WRITE_DENIED")`；在资源更新／删除／Strip rebind transaction 内检查，使用局部 import 避免 projects/services ↔ materials/services 循环。

- [x] 写 RED 参数化 `test_grace_blocks_every_project_resource_post`：material create/edit/delete、rectangle/composite section create/edit/delete、strip rebind 全拒绝，无资源/引用/Draft version/audit 变化。PURGED 对应资源 GET 也拒绝；GRACE index 只读可读，编辑／新建／删除 form 不提供可提交作者入口。
- [x] 写 RED `test_active_context_cannot_delete_or_edit_resource_used_by_read_only_project`：同 owner ACTIVE+GRACE/PURGED 引用同资源，从 ACTIVE 上下文更新／删除也拒绝；资源、成员引用、两个 Project versions、ResourceDeletionAudit 不变。Material、Section、关联 Strip 各覆盖；Section definition 的 strip_id 关系通过实际存储格式检查，不假设不存在的 FK。
- [x] 搜索全部实际 Material/Section/Strip mutation callers；`assert_resource_mutable()` 是 service-level mutation authority，不仅 endpoint guard。至少 direct service mutation regression；不存在的其他入口记录 NOT APPLICABLE，不新建入口。
- [x] 写 `test_active_unshared_resource_management_stays_unchanged`：未被只读 Project 引用的合法 create/edit/delete、Strip recovery 保持成功，现有独立删除+引用失效语义保留，历史 revision 不变。
- [x] 运行 `pytest tests/endpoints/test_m7_read_only.py tests/endpoints/test_material_pages.py tests/application/test_materials.py -q`；预期当前只查 owner 或跨 Project deletion 能成功的真实 RED。
- [x] 最小实现上述 context guard；transaction 内在现有稳定 Project 锁序检查受影响只读 Projects，拒绝后不继续写。所有 material form.save() 分支也必须经过保护，不能只包 section service。安全提示为何只读、可返回何处；不向学生输出 code/DB id。
- [x] 同命令及 `pytest tests/application/test_draft_independence.py tests/application/test_revisions.py -q` GREEN；如必须改变 Delete Impact 图操作或引入资源复制才可继续，STOP 请求范围确认，不自行扩展。
- [x] 内部 architecture checkpoint：service-level authority、GRACE/PURGED 间接写入保护不依赖资源复制／Draft semantics 变化即可继续。
- [x] 提交：`fix: protect read-only projects from resource write bypasses`。

## Task 7 — RED → real-browser product journey and historical regression

**Files:** new `tests/browser/test_m7_project_creation.py`；如需修复，仅上述所属 task 的最小文件，不引入新 UX 功能。

**Interfaces:** 消费 live_server、既有真实登录／Workspace browser seam；可新增此测试文件内的 `open_event_page(page, live_server, *, user) -> None`，通过 Django 测试 session cookie 登录后 browser.goto `/events/`，不能用自动预建 Project 的 fixture 代替创建流程。生产不增加测试专用 endpoint。

- [x] 写 `test_student_creates_project_from_event_and_completes_v2_journey`：仅预置 ACTIVE Event、USER、有效 Membership；browser 点建立、输入名称、submit，直接空 Workspace；无材料时看到真实准备引导。通过公开资源 UI 创建材料／截面，再通过 Canvas 建立稳定三角桁架、支座与荷载，Save → Check PASS → 正常 Prediction/Analyze → Results/Report；不得直接 seed Run/Snapshot。
- [x] 写 `test_duplicate_create_preserves_saved_model`：从赛事页再次 create 请求不复制 Project、不改名称和 Draft，reload 数据不丢失。`test_grace_history_remains_readable_without_authoring`：将该测试专用 Event 转 GRACE（测试安排状态），再通过 browser 读历史，结论／预测对比／为什么／技术数据四入口往返；Save/Check/Analyze/作者入口不可用，直接 HTTP POST 也拒绝。
- [x] 写 `test_legacy_multiple_projects_have_no_automatic_selection`、`test_create_error_has_safe_student_copy`：保留多卡片，显示可操作安全说明，不出现内部 machine code、raw identity/schema/payload。
- [x] 先在所属功能实现前建立对应 browser RED（可以在 Tasks 2/5 开始时落测试），记录真实失败；运行 `pytest tests/browser/test_m7_project_creation.py -q`。不能等所有功能完成后编造一个已 RED 的记录。
- [x] 在同一命令 GREEN 后，真实浏览器检查 empty/no-resource、create error、GRACE historical Workspace，保存无隐私 screenshots 与实际请求证据；等待 PO 操作不等于自动宣告人工验收 PASS。
- [x] 提交：`test: cover M7 public project creation and read-only history`。

## Task 8 — Fresh regression, review and owner handoff

**Files:** 仅计划执行记录／证据；修复只回到对应 RED task，不无关清理。

**Interfaces:** 消费 Tasks 1–7 的 public contracts；输出 feature HEAD、fresh commands/results、文件范围及未变更证据。没有 merge API 或 deploy 操作。

- [x] 再跑全部 targeted policy/create/endpoint/material tests 和 Task 4 文件型 SQLite suite，所有 PASS 且并发 tests 未 skip。
- [x] 独立依次执行并记录实际计数／退出码：
  ```bash
  pytest -q -m 'not browser'
  pytest tests/browser -q
  pytest tests/mechanics -q
  python3 manage.py check
  python3 manage.py makemigrations --check --dry-run
  git diff --check
  ```
  使用项目已验证 Python environment；禁止为了跑 check 对真实 DB migrate。任何失败先诊断，不能减少断言、加无依据等待或更改 mechanics 绕过。
- [x] Review diff：无 model/migration、mechanics/solver、真实 DB、seed 资源或假 AnalysisRun；正常 create count1、legacy count不变、historical snapshot内容不变；O-006 仍 fail closed。使用 requesting-code-review 技能执行批准的 review 方式，处理有效发现后重跑受影响回归。
- [x] 确认 root 原有四文件变更未被触碰、grid 未变、旧平台未重启；如出现未授权 out-of-band 变动先报告，不清理。
- [x] 回报 `M7 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING`，附 branch/HEAD、测试和真实 browser evidence。未获新授权前不建立/切换 Owner 当前验收环境，不宣告人工 PASS，不 merge/push/tag/deploy；STOP。

## Plan self-review / execution gates

- Owner decisions → Tasks：D-M7-001 与资格/期限 3–5；D-M7-002 3–4；D-M7-003、PURGED read gap 2/6/7；默认/表单/资源 3/5/6；不扩 schema/Team/provisioning 1/5/8。
- Review Focus 五项分别有命名测试；服务签名、route name、返回属性在 producer/consumer 中一致。
- 唯一被允许的 GRACE 技术写入是现有历史读取 disclosure receipt，不包含学生 authoring；若现有 contract review 不接受该区分，先提交决定请求，不能靠放开 Prediction 写入解决。
- 无数据库唯一约束承诺；正常创建一致性由应用事务 boundary 保证，legacy/ORM 仍按既有事实处理。
- RED、targeted GREEN、browser GREEN、full regression、review 为后续执行门禁；本文不声称已执行这些步骤。
- 最终完成条件：Task 1–8 GREEN，停在 `M7 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING`；不 merge/push/tag/deploy。

