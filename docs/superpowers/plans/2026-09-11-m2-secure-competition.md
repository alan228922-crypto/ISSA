# M2 Secure Competition Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 建立 Django 账户、赛事授权、团队 CSV 开户和材料条材持久化的安全最小骨架。

**Architecture:** Django modular monolith 使用 custom User、EventMembership 和小型 server-side policy。Project 仅以 `event_id` 与 `owner_user_id` 参数作为授权上下文，不建立 Project ORM。

**Tech Stack:** Python 3.13、Django 5.2、pytest、pytest-django、SQLite。

**Spec:** `docs/specs/MASTER_SPEC.md` v1.1 与 M2 Product Owner authorization。

## Global Constraints

- 用户可见文字、中文注释和 docstring 使用简体中文（zh-CN）。
- Identifier 与 mechanics machine-readable codes 使用英文。
- 不实现 Project Draft、Physical Model、ModelRevision、AnalysisRun、Idealization 或 M3 endpoint。
- 不改变 `mechanics/`。
- O-001 至 O-005 保持开放；尤其不定义 FINISHED_GRACE 的学生权限。
- DRAFT 可 provisioning，PURGED 拒绝；ACTIVE provisioning 为 POLICY GAP，不作为允许规则实现。

---

### Task 2: Django bootstrap、Custom User 与首次改密保护

**Files:** `manage.py`、`config/{settings,urls,wsgi,asgi}.py`、`accounts/{models,forms,views,middleware,urls,apps}.py`、`templates/accounts/*.html`、`tests/permissions/test_password_change_gate.py`。

- [ ] 写 role、`must_change_password`、密码 hash、直达 URL 拦截和改密后解锁的失败测试。
- [ ] 运行 `python3 -m pytest tests/permissions/test_password_change_gate.py -v`，确认缺少 Django/accounts 而失败。
- [ ] 建立 custom User，配置 `AUTH_USER_MODEL`，实现只放行登录、退出和改密的 middleware；改密表单成功时清除标记。
- [ ] 运行目标测试、`manage.py check`、全套 pytest；生成并提交初始 accounts migration。

### Task 3: CompetitionEvent、membership 与 policy

**Files:** `competitions/{models,authorization,apps}.py`、`tests/permissions/test_event_project_access.py`。

- [ ] 写 Developer、assigned/unassigned Manager、participant 和最小 project context 的失败权限矩阵测试。
- [ ] 运行目标测试，确认 policy/model 尚不存在。
- [ ] 建立 Event、membership 与 `can_view_event`、`can_manage_event`、`can_create_role`、`can_view_project`、`can_modify_project`、`can_analyze_project`；只接收 event/owner IDs。
- [ ] 验证 `purge_at=ends_at+7 days`、唯一 membership 与权限套件；生成 migration 并提交。

### Task 4: Transactional team provisioning

**Files:** `competitions/{provisioning,forms,views,urls}.py`、`templates/competitions/provision_*.html`、`tests/application/test_team_provisioning.py`。

- [ ] 写 username、解析/预览、非法 row、权限、collision、confirm revalidation、rollback、hash、membership 和 sanitized audit 的失败测试。
- [ ] 运行目标测试，确认 provisioning API 不存在。
- [ ] 在内存中解析 CSV；confirm token 仅保存短生命周期、签名且不进入数据库/audit 的行数据；confirm 重新验证并用 `transaction.atomic` 创建 User、membership、audit summary。
- [ ] DRAFT 允许、PURGED 拒绝；ACTIVE 返回明确 `PROVISIONING_STATUS_POLICY_GAP`。
- [ ] 运行 application/permission suites、生成 migration 并提交。

### Task 5: Material 与 Strip 持久化

**Files:** `materials/{models,services,apps}.py`、`tests/application/test_materials.py`。

- [ ] 写有效值、非正 E/尺寸、负 density、NaN/Inf、跨 owner 材料引用与 ownership policy 的失败测试。
- [ ] 运行目标测试，确认 models/services 不存在。
- [ ] 建立 owner-scoped Material/Strip、validators、constraints 和 server-side ownership helpers；不复制 mechanics 公式。
- [ ] 运行 application suite、mechanics regression、Django check、migration check、全套 pytest；生成 migration 并提交。

### Final verification

- [ ] 运行 `python3 manage.py check`、`python3 manage.py makemigrations --check --dry-run`、permission/application/mechanics/full pytest、`git diff --check` 和 `git status`。
- [ ] 确认数据库模型与 audit 没有 plaintext credential 字段，未改 `mechanics/`，并在 M2 报告中记录 ACTIVE provisioning policy gap。
