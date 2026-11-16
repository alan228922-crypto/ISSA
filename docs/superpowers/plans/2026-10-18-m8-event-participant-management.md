# M8 — Event Operations & Active Participant Provisioning — TDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This document is a plan, not permission to start Task 1 or dispatch agents. Owner must approve the plan and select the execution method first.

**Goal:** 为 active Developer / exact assigned active Manager 提供可审计、可重试的单笔参赛资格管理，统一修正 DRAFT CSV 的 credential preview 安全，并保持 M7 学生 self-create 与历史权限契约。

**Architecture:** Django SSR + centralized application authorization + Event-serialized transactions. Existing database-backed Django Session rows hold bounded opaque preview state; BulkImportBatch gains only a controlled operation_details_json field. No Team, new workflow aggregate, scheduler, Project provisioning or mechanics authority.

**Tech Stack:** Existing Python 3.12+, Django 5.2.17, SQLite, pytest / pytest-django and Playwright. No new product dependency.

**Spec:** MASTER_SPEC.md §§19–23 / O-004 / O-006; AUTHORIZATION_AND_EVENT_ARCHITECTURE.md; ARCHITECTURE_DECISION_REGISTER.md; API_AND_APPLICATION_FLOW.md; Owner's `M8 PRODUCT DECISIONS — APPROVED` dated 2026-10-18 in this conversation. M7 contracts are recorded in `2026-10-17-m7-project-creation-event-provisioning.md` and `docs/development/M7_IMPLEMENTATION_EVIDENCE.md`. Task 1 records the approved M8 decisions in the repository before product edits.

**Baseline:** main@fa9c000ddbff89adc41a34711bf44a0b509d19fe. Estimated size: L. Owner APPROVED native sequential Tasks 1–9 on 2026-10-18, with Tasks 4/6 checkpoints and Task 9 independent review. Execution started with isolated worktree setup; production/tests remain untouched before fresh baseline.

## Approved bounded amendments (2026-10-18)

1. Current mixed identity uses ACTIVE Memberships only. Active PARTICIPANT + active MANAGER fails closed; inactive historical rows grant no authority and do not block otherwise legitimate authority. Preserve historical rows. No promotion or legacy repair. Explicit contradictory binding spec -> STOP — PRODUCT POLICY CONFLICT.
2. BulkImportBatch is an authorized business receipt, never an unauthorized-attempt log. Persist only SUCCESS/NOOP for CREATE_USER/JOIN_EXISTING/REACTIVATE/DEACTIVATE. DRAFT_CSV_CREATE remains an internal channel/action for lifecycle control and records CREATE_USER with multiple targets. Denials, malformed requests, invalid/expired references and conflicts produce no business receipt. Any existing security logging must exclude passwords, hashes, preview refs, CSV, request bodies, Session data and tracebacks. Explicit contradictory mandatory formal audit spec -> STOP — SPEC CONFLICT.
3. TTL 600 seconds is SERVICE ACCESS CUTOFF, not automatic physical deletion. An encountered expired owned preview must be deleted or rewritten hash-free immediately; abandoned expired preview rows must be physically removed by Django clearsessions, verified by RED/GREEN retention tests. No new preview model, scheduler, worker or aggregate; unsafe Session backend -> STOP — ARCHITECTURE DECISION REQUIRED.

These amendments override older wording below and are binding on all tasks. O-006 remains OPEN / FAIL CLOSED until complete implementation and acceptance; this execution cannot declare Owner acceptance.

## Global Constraints

- D-M8-001: authenticated active DEVELOPER, or active MANAGER + exact Event active MANAGER Membership; Membership alone never grants Manager authority. Mixed identity fails closed.
- D-M8-002: DRAFT retains CSV; DRAFT/ACTIVE share single-entry CREATE_USER / JOIN_EXISTING / REACTIVATE / DEACTIVATE. ACTIVE CSV remains fail closed. GRACE forbids all qualification mutations; PURGED refuses participant operational access.
- D-M8-003: existing target must be active USER, explicitly verified as the same team, without management/mixed-role conflict. Preserve password, must_change_password, role, User.is_active, other Memberships, Project ownership, Draft and history. Reactivation updates original row; deactivation never deletes.
- D-M8-004: only BulkImportBatch.operation_details_json + its necessary migration. Fixed allowlisted schema, no fabricated legacy details. Mutation + successful/no-op audit + preview consumption share one transaction.
- Initial password remains captain student ID, Django hash only, forced first password change. Plaintext never enters HTML/token/response/log/audit; password hash is server-preview-only and User-password-only, never audit/client output.
- Preview is opaque, actor/Event/operation/target/expiry bound, one-time/replay-safe. Never accept the old signed raw-row token as a compatibility fallback.
- projects/creation.py and M7 create contract stay byte-for-byte unchanged. No automatic Project/Material/Section/Draft/Revision/Run/Snapshot/Prediction.
- O-004 remains OPEN. No global User recovery/deletion, reset-password flow, Manager assignment/revoke/promotion, impersonation or unrestricted identity reuse.
- No Event transition UI/service expansion, scheduler, ACTIVE CSV, public signup/join code, Team/workflow model, solver/mechanics/units changes, GitHub/showcase work or M7 Minor polish.
- No root/grid/user dirty-work changes, real DB migration, old-server takeover, merge/push/tag/deploy. Use isolated feature worktree and test DBs at execution time.

## Review Focus

1. Preview granted but Manager revoked / actor disabled / Event closed while waiting: confirm reloads and refuses (Tasks 2/4/6).
2. Credential visible through encoded tokens, exceptional logging or opaque-preview serialization: response allowlists and secret canaries, not substring-only template checks (Tasks 4/7/8).
3. Same reference concurrent retry versus two independent references: one committed effect/receipt, no reactivation after a stale deactivate preview or re-execution of a consumed reference (Tasks 5/6).
4. `1`, `01`, empty/header-only CSV, malformed columns and global username races: normalize first, explicit validation, atomic batch rollback (Tasks 4/6).
5. Existing User / dual Membership / other Event resources: no identity inference from email or username prefix, no account overwrite and no Project/history/resource side effects (Tasks 5/8).

## A. Frozen contracts

Authority is the approved M8 decision, not the earlier audit recommendation. O-006 is not declared resolved by this planning document; implementation evidence must prove its scoped replacement before resolution is recorded. O-003 stays resolved; O-004 stays open.

| Operation | DRAFT | ACTIVE, now < purge_at | FINISHED_GRACE | PURGED |
| --- | --- | --- | --- | --- |
| DRAFT_CSV_CREATE | allowed for qualified administrator | fail closed | deny | deny |
| CREATE_USER / JOIN_EXISTING / REACTIVATE / DEACTIVATE | allowed for qualified administrator | allowed for qualified administrator | deny | deny |
| Manager assignment/revoke/promotion / admin reset / signup | not introduced | not introduced | not introduced | deny |
| Student Project create | M7 deny | unchanged M7 authority | M7 deny | M7 deny |

ACTIVE cutoff is `now < purge_at`, including exact-equality denial; no inferred automatic transition at ends_at. DRAFT CSV does not silently acquire an unrelated new calendar policy.

## B. Architecture and interfaces

Responsibilities:

- `competitions/authorization.py`: central role/scope/lifecycle decision; no duplicated template/view authority.
- `competitions/participant_services.py`: public previews, confirm, transactional dispatch, state revalidation and replay-safe results.
- `competitions/participant_previews.py`: private bounded DB Session state storage, encoding/decoding/redaction/consumption; not an independently authorized mutation API.
- `competitions/participant_inputs.py`: private shared input allowlists, CSV normalization and credential hashing; no authority, persistence or public mutation interface.
- `competitions/participant_audit.py`: fixed-schema validation and private transaction-only audit writer.
- `competitions/provisioning.py`: DRAFT CSV compatibility adapter, preserving public wrapper names but replacing token contract; delegates to participant_services, which uses participant_inputs. No reverse import from participant_services to provisioning.
- `competitions/forms.py`, `views.py`, `urls.py`, templates: SSR input/presentation only.

Exact producer/consumer contracts (keyword-only for new APIs):

```python
# competitions/authorization.py
can_manage_event(actor, event) -> bool
participant_management_error(*, actor, event, operation: str, now) -> str | None

# competitions/participant_services.py
class ParticipantManagementError(ValueError):  # .code, .status_code; no raw payload
    ...
preview_participant_change(*, actor, event_id: int, operation: str, fields: dict) -> dict
preview_csv_participants(*, actor, event_id: int, source_filename: str, csv_text: str) -> dict
confirm_participant_change(*, actor, event_id: int, operation: str, preview_ref: str) -> dict

# Existing adapter names in competitions/provisioning.py
preview_team_import(actor, event, source_filename, csv_text, requested_role=User.Role.USER) -> dict
confirm_team_import(actor, event, preview_ref: str) -> dict
```

Preview response keys: `rows` (safe username/action/impact only), `errors` (allowlisted codes internal to presentation), `preview_ref` (opaque string or null for invalid input), `audit` (safe filename/count/error summary only for CSV compatibility). Never `token`, raw parsed rows, captain input or hashes. Confirm returns safe internal result dictionary with `outcome` (SUCCESS/NOOP), `created_count`, and `changed_membership_count`; private receipt references must not appear in displayed text.

Compatibility exception: ProvisioningError retains its import name and becomes a thin ParticipantManagementError subtype/adapter with `.code` and `.status_code`; existing wrappers translate only allowlisted codes, not raw exception text. Views consume typed errors through presentation, not `str(exc)`. ParticipantManagementError lives in participant_services (which never imports provisioning), keeping the dependency acyclic.

Operations are exactly `DRAFT_CSV_CREATE`, `CREATE_USER`, `JOIN_EXISTING`, `REACTIVATE`, `DEACTIVATE`. Public adapters reject unknown operations, forged role/Event/owner/password-hash fields; DRAFT CSV accepts only requested_role USER even for Developer. This does not redefine general Developer maintenance capabilities.

## C. Schema / migration

Add only `BulkImportBatch.operation_details_json = models.JSONField(default=dict, blank=True)` in `competitions/migrations/0003_bulkimportbatch_operation_details.py`, depending on 0002. `{}` means legacy summary only; do not backfill targets/actions. New application writers must supply a validated versioned object.

Ordering: fresh old-HEAD baseline -> Task 2 authority -> Task 3 migration RED/forward/backward tests -> migrate only isolated test DBs -> Tasks 4/5 consumers. Never run migrate on main/root/old demo DB. This document does not execute or generate migration code.

No User/EventMembership/Project schema change, new unique constraint, workflow table, invitation or domain aggregate. If durable replay or safe preview cannot use existing Session + this audit extension, STOP rather than adding another model.

## D. Credential preview design

- Require database-backed Django Session storage on the default transactional DB. Create a separate bounded Session row per preview, not a map in the administrator's auth session: avoids concurrent tabs overwriting each other's pending previews. The row must not contain auth-login/session impersonation keys.
- TTL: 600 seconds, preserving current preview window; exact expiry (`now >= expires_at`) refuses. A server-generated random 32-character lowercase ASCII alphanumeric Session key is the opaque reference; browser receives no encoded payload. Accept only `[a-z0-9]{32}`, never decode the old signing format.
- Server state namespace/schema `participant-preview-v1`: actor ref, Event ref, operation, fixed target refs or absent-target username, relevant expected state, issued/expires timestamps, stage PENDING/CONSUMED, server-only password hashes for new-account targets, sanitized source metadata. Use JSON-compatible primitives (UTC epoch timestamps, ISO competition_date); never serialize whole ORM objects, request objects or arbitrary fields. Never plaintext/raw CSV. This is bounded storage data, not a new ORM workflow model.
- Parse into local memory, validate shape/size, hash captain input with Django make_password, then discard raw input. No raw CSV/file is stored in Session. Use `SessionStore.encode/decode` and explicit existing Session model persistence; never put data in signed-cookie sessions. A non-DB/default-DB-incompatible configuration is an execution STOP.
- Single-entry input CREATE_USER: team_number + captain_student_id. JOIN_EXISTING: exact username + explicit `same_team_verified=True`; no email/fuzzy directory lookup. REACTIVATE/DEACTIVATE: existing participant target from Event-scoped lookup + explicit confirmation; join/reactivation require identity verification, not knowledge of current password.
- New usernames use competition_date + normalized 01..99. Existing username is immutable; joining a verified team does not infer Membership from its prefix or rename it to match this Event. No unrestricted account discovery, cross-Event transfer or merging.
- Public preview authenticates/authorizes current actor and Event, validates target, persists safe state, then returns allowlisted presentation. Validation-error preview creates no User/Membership/success audit and offers no confirm reference. Expired/pending references fail safely.
- At successful confirm, strip all credential hashes and replace server state with a CONSUMED tombstone containing only bindings + audit receipt reference until the original expiry. It is saved atomically with mutation/audit, not through response-time auth-session middleware. No hash ever enters audit.
- Expired owned preview handling discards its credential-bearing state and refuses; never revives or extends TTL on retry. Use existing Django DB-session expiration/clearsessions maintenance for abandoned rows, not an Event scheduler or a new workflow model. Document that Session physical housekeeping is separate from the mandatory 600-second service-access cutoff; no claim that an expired row has already been physically deleted without checking it.
- Same-reference retry within TTL reauthorizes current actor/Event and checks the receipt/target bindings, then returns the committed historical receipt without another mutation/audit. Do not compare a completed CREATE to its old absent-target precondition or execute it again. A closed Event, revoked actor or expired reference still denies; replay is not a lifecycle bypass. If target identity/role has become invalid, refuse safely; later legitimate qualification changes are never undone, and result copy says the request was already processed and the roster should be refreshed. Other-actor/Event/operation/ref tampering denies without consuming a legitimate owner's reference.
- Old signed hidden tokens are invalid after transition; ask administrators to preview again. Do not retain two credential models.
- Reject body/file oversize before reading into application memory; plan limits: UTF-8/UTF-8-BOM CSV <=1 MiB, 1..99 rows, only team_number/captain_student_id/optional_team_name headers, captain input <=128 characters; team_number ASCII decimal normalized to integer1..99. Optional team name is not stored as a new profile. This limit is an input-security bound, not a new identity field.

## E. Authorization contract

- can_manage_event checks authenticated + current active actor; Developer global authority or global MANAGER + exact active MANAGER Membership. Ordinary USER with MANAGER Membership is denied.
- For participant operations, reject actor with active PARTICIPANT and active MANAGER rows in this Event; inactive historical rows do not participate. Developer needs no Membership but is not exempt from an actual active mixed identity in this Event. Target must be active global USER and have no active MANAGER Membership conflict; do not repair legacy role data automatically.
- Every public preview/confirm reloads actor by id and Event by id, checks central authority and action lifecycle; cached actor/Event flags are never authoritative. Confirm repeats all checks after serialization, with current time.
- read management/list requires central manager authority and non-PURGED Event; GRACE pages read-only, no mutation controls. Raw participant records never become ordinary User directory access.
- Existing Project read/write helpers and projects/creation.py remain unchanged. If dual-role remediation requires broadening Project policy, STOP; fail-closed participant management is not license to rewrite M7.

## F. Participant transitions

| Operation | Required preview/current facts | Committed effect |
| --- | --- | --- |
| CREATE_USER | canonical username absent | active USER + hash + must_change_password=True + active PARTICIPANT |
| JOIN_EXISTING | verified same team, active USER, no manager conflict, Membership absent | one PARTICIPANT; no User edits |
| JOIN_EXISTING / REACTIVATE, already active at preview | same safe identity, original active Membership | NOOP receipt; no second Membership |
| REACTIVATE | original inactive PARTICIPANT row, active safe USER | same row.is_active=True |
| DEACTIVATE | original active PARTICIPANT row, active safe USER | same row.is_active=False |
| DEACTIVATE, already inactive at preview | same safe identity, original inactive row | NOOP receipt |

Inactive global User: deny, never recover. CREATE_USER encountering an existing username asks to use explicit existing-account flow, never silently joins/overwrites. Relevant target facts (User existence/identity/role/active state, Membership identity/type/active state and Event competition_date) changed since preview -> PREVIEW_STATE_CHANGED, no mutation; a fresh preview can legitimately report NOOP. Concurrent creation of an absent target never converts CREATE into JOIN. User password changes are never overwritten: confirm reads the current User and never assigns credential fields for an existing User.

Deactivate affects the next server authorization, not already delivered responses. Preserve all Project/Draft/revision/run/learning/resource rows and other Event Memberships. Reactivation restores only permissions allowed by current Event state; GRACE/PURGED operation itself still denies.

## G. Transaction / concurrency / idempotency

Confirm sequence on SQLite:

1. Non-authoritative cheap validation/preflight outside transaction; no User/Membership mutation.
2. Begin atomic; first DB operation is no-op Event UPDATE `status=F('status')` to obtain write serialization, without changing status/timestamps.
3. Reload Event, actor, actor Memberships, target Users/Memberships and preview Session in stable key order; reauthorize using fresh now. Missing Event/preview is safe refusal, never a new preview fallback.
4. Validate actor/Event/operation/target/expiry bindings. If CONSUMED, verify its audit receipt belongs to those bindings and return it without repeating the operation.
5. For PENDING, validate relevant expected state, then apply the explicit transition (entire CSV all-or-nothing).
6. Write controlled audit in the same transaction. Internal request_key is SHA-256 of the opaque reference (not a password/hash/token); do not save the bearer reference itself in audit.
7. Save credential-free CONSUMED tombstone referencing the audit, keeping original expiry. Commit; only then return success/PRG.

Session consumption, successful/no-op audit and User/Membership writes must roll back together. Domain validation errors leave no partial mutation or business receipt. DENIED attempts never persist BulkImportBatch. Expired owned preview credential cleanup must survive refusal, not be undone by an exception rollback. Invalid actor/ref attempts must not acquire another actor's receipt or overwrite that actor's valid preview.

Retry only SQLite busy/locked, at most 5 whole-transaction attempts, backoff `0.05*(attempt+1)` seconds; do not catch all errors and retry or add browser sleeps. Exhausted -> 503 PARTICIPANT_MANAGEMENT_BUSY, no partial effect. Username IntegrityError -> full rollback, safe conflict requiring fresh preview, not silent reuse. Existing User/Membership constraints remain backstops, not the serialization design. Same Event operations share M7's Event lock seam without editing M7 code.

Guarantee scope: approved application paths on SQLite; no raw-ORM or cross-database concurrency guarantee. Explicitly test competing Developer/Manager, same-reference retry, distinct-reference stale state, normalize1/01, reactivate/reactivate, deactivate/reactivate, revoked actor and Event closing. Opposing stale previews must not silently undo a just-committed change.

## H. Audit contract

`participant-operation-audit-v1` top-level allowlist: schema_version, request_key, operation, outcome, reason_code, targets. Each target allows only target_user_ref, target_membership_ref, before_active, after_active, outcome, reason_code. References are internal positive ids or null for absent targets; active values boolean/null, never loosely coerced strings. Fixed enums; no arbitrary keys/free text. CSV uses a controlled target list; single-entry has exactly one target.

Outcome enums: SUCCESS / NOOP only. Operations: CREATE_USER / JOIN_EXISTING / REACTIVATE / DEACTIVATE only. Fixed reason codes: CREATED / JOINED / REACTIVATED / DEACTIVATED / ALREADY_ACTIVE / ALREADY_INACTIVE. DRAFT CSV records CREATE_USER with a controlled multi-target list. No DENIED receipts, failure reason strings or fabricated references. A literal bool cannot pass validation as a positive integer ref.

Success/NOOP create exactly one receipt per preview; replay returns it. NOOP before=after, mutation counters=0. Existing actor/Event/created_at fields answer who/where/when; row_count and created_account_count remain truthful. Single-form source_filename uses fixed `single-entry`, CSV uses sanitized basename with no path/control characters. No raw username/password/request/CSV/token/Session cookie/password hash is placed in details; the non-credential request_key digest is explicitly allowed. Audit identity is retained operational metadata, not a research identity mapping or a new O-004 retention policy.

Helper interfaces in participant_audit.py: `validate_operation_details(details: dict) -> dict` (reject unknown shape) and private `_record_operation(*, actor, event, details, row_count: int, created_count: int, source_filename: str) -> BulkImportBatch`, requiring an active transaction. View cannot call this to bypass participant authority.

## I. Management UX and routes

New routes under existing competitions URL include, names prefixed `participant_` (no namespace change to old reverse names):

- GET `/competitions/<event_id>/manage/` -> event_management.
- GET `/competitions/<event_id>/participants/` -> participant_list.
- GET/POST `/competitions/<event_id>/participants/new/` -> participant_new (POST previews CREATE_USER).
- GET/POST `/competitions/<event_id>/participants/join/` -> participant_join (POST previews JOIN_EXISTING).
- POST `/competitions/<event_id>/participants/<membership_id>/reactivate/preview/` -> participant_reactivate_preview.
- POST `/competitions/<event_id>/participants/<membership_id>/deactivate/preview/` -> participant_deactivate_preview.
- POST `/competitions/<event_id>/participants/confirm/` -> participant_confirm; only operation, opaque preview_ref and CSRF; Event from URL, target only from trusted preview state.

Retain DRAFT CSV POST URLs `/accounts/preview/` and `/accounts/confirm/`; add GET `/competitions/<event_id>/accounts/import/` for actual upload form. Old confirm field `token` is rejected; new field `preview_ref` only. All writes POST+CSRF, GET never mutates User/Membership. Success uses PRG to participant list with a safe result banner; no receipt token or target DB id in displayed text. Refresh is a GET, not a repeated mutation.

Event landing shows management link only to centrally authorized administrators; ordinary student landing/M7 CTA unchanged. New/update/list pages use existing product header and local CSS, no new frontend framework or full dashboard redesign. Show username and qualification state, not password/hash/DB id/machine code. Confirm shows exact requested action and non-destructive data-retention impact. GRACE read-only, PURGED no roster/operational detail.

Error mapping is an explicit allowlist in `competitions/presentation.py`: PERMISSION_DENIED, EVENT_NOT_ACTIVE/STATUS_NOT_ALLOWED, EVENT_PURGED, EVENT_ACCESS_EXPIRED, PROVISIONING_STATUS_POLICY_GAP, USER_ROLE_CONFLICT, ACCOUNT_INACTIVE, MEMBERSHIP_NOT_FOUND, DUPLICATE_INPUT, INVALID_PROVISIONING_ROW, INVALID/EXPIRED_PREVIEW, PREVIEW_STATE_CHANGED, PARTICIPANT_MANAGEMENT_BUSY. Already active/inactive is a safe NOOP message, not raw exception. Unknown errors generic zh-CN; no `str(exc)` response. Initial-password instructions explain forced change without displaying any password. Sensitive POST/file fields are redacted from error reporting; do not log bodies, parsed rows or preview objects.

Use exact error identifiers EVENT_NOT_ACTIVE, EVENT_STATUS_NOT_ALLOWED, INVALID_PREVIEW, EXPIRED_PREVIEW (the slash notation above groups messages, not literal combined codes); include ACCOUNT_ALREADY_EXISTS for explicit CREATE collision. Redact sensitive POST values and service variables (raw CSV, captain inputs, rows, server preview state and encoded passwords) with Django sensitive-data decorators and safe application logging. Unknown exceptions return generic responses without a debug traceback/body or logging request/preview reprs.

## J. Task 1 → 9

### Task 1 — Freeze approved contract and fresh isolated baseline

**Goal / files:** docs only. Create `feat/event-participant-management-m8` at `.worktrees/event-participant-management-m8` from exact main fa9c000 using using-git-worktrees at execution time. Modify four spec/ADR files; create `docs/superpowers/specs/2026-10-18-m8-event-participant-management-decisions.md`; carry this approved plan into feature.

- [x] Inventory main/root/grid HEAD/status and root diff/DB fingerprints. At present this plan is the only intentional new untracked main planning artifact; if any other main dirt or baseline drift exists, STOP. Do not stash/reset/restore.
- [x] Create isolated feature from exact baseline before production/tests. Safely relocate only this newly authored plan: verify source and copied feature SHA-256, no destination overwrite, preserve content; then remove only the verified identical planning working copy from main. If divergent, retain both and STOP. This is not permission to remove any user file.
- [x] Run fresh baseline before any production/test edit: non-browser; permissions + landing + reasoning + provisioning; mechanics; Django/migration dry-run/diff; existing entry/Workspace lifecycle + M7 browser subset. Actual baseline failures -> diagnose, never count as M8 RED.
- [x] Record D-M8-001..004, scoped O-006 resolution criterion, credential conflict, role conflict, migration boundary and unchanged M7. Correct only directly conflicting old O-003 wording in touched sections; do not rewrite unrelated historical records/accepted Minors. O-006 remains safely closed in implementation until covered replacement is GREEN.
- [x] Doc self-review and diff check, capture fingerprints. No fake RED for docs. **GREEN:** exact baseline and documented counts/exit codes; contract consistent with approval.
- [x] **Commit:** `docs: freeze M8 participant management contracts`.

**STOP:** baseline mismatch, unrelated dirty state, unapproved policy/schema need. No Task 2 until baseline issues are understood.

### Task 2 — Central manager authority hardening

**Files:** competitions/authorization.py, provisioning.py (reuse central guard only); tests/permissions/test_participant_management.py; existing permission/provisioning tests.

- [x] **RED:** `test_manager_authority_requires_active_global_role_and_exact_membership`; Developer active/inactive, Manager assigned/unassigned/inactive, USER+MANAGER, mixed actor, forged other Event; directly call service/helpers, not only HTTP.
- [x] **RED:** `test_cached_actor_and_event_are_not_authority`; DB actor disabled/role changed or Manager revoked before preview; old Event DRAFT object while persisted ACTIVE must not allow CSV. Existing legal DRAFT + ACTIVE CSV denial assertions retained.
- [x] Run `pytest tests/permissions/test_participant_management.py tests/permissions/test_event_project_access.py tests/application/test_team_provisioning.py -q`; record actual behavioral failures.
- [x] **Minimal:** implement central authority/error signature; public provisioning wrappers fetch current objects and reuse it. No ACTIVE single-entry endpoint yet, no broad Project-policy changes.
- [x] **GREEN:** same command + M7 permissions/create application tests, all pass; no new privilege through role/membership combinations.
- [x] **Commit:** `fix: enforce active role-scoped participant authority`.

**STOP:** needs Project-role remediation, Manager provisioning policy beyond approved scope, or a new identity model.

### Task 3 — Controlled audit schema and minimal migration

**Files:** competitions/models.py; new migrations/0003_bulkimportbatch_operation_details.py; participant_audit.py; tests/application/test_participant_audit.py; tests/migrations/test_m8_participant_audit.py.

- [x] **RED:** `test_operation_details_accepts_only_versioned_allowlisted_shape`; required/unknown keys, enum/type validation, password/hash/token/CSV/free-text keys forbidden. `test_success_audit_requires_transaction`; failed writer rolls back, legacy rows remain legacy.
- [x] **RED:** MigrationExecutor test starts at competitions0002 on a disposable test DB, uses its historical app registry to create a real legacy batch, migrates forward, asserts details={}, actor/counts unchanged, no invented targets. Verify reverse on disposable DB and restore the latest schema in finally so subsequent tests are not polluted; never reverse a real DB.
- [x] Run `pytest tests/application/test_participant_audit.py tests/migrations/test_m8_participant_audit.py -q`; missing field/validator are true RED, migration setup errors are not.
- [x] **Minimal:** single AddField(default=dict, blank=True), no RunPython backfill; fixed-schema private audit writer. No audit-only API or new aggregate.
- [x] **GREEN:** same tests, Django check + migration dry-run + diff check. Review generated migration contains only the approved field.
- [x] **Commit:** `feat: add bounded participant operation audit details`.

**STOP:** additional field/model/index/constraint is required, or audit cannot remain transaction-bound without storing prohibited material.

### Task 4 — Opaque preview security and DRAFT CSV compatibility

**Files:** new participant_previews.py, participant_inputs.py, participant_services.py (CSV/shared confirm foundation), presentation.py (CSV-safe error foundation); modify provisioning.py, views.py and existing preview template to consume preview_ref atomically; tests/application/test_participant_previews.py, existing test_team_provisioning.py; new tests/endpoints/test_participant_management.py (existing CSV routes).

- [x] **RED:** `test_preview_response_contains_only_opaque_reference`; synthetic credential canary absent from all nested response values/HTML/logs/audit, and base64/signing decoding cannot recover it. Inspect server Session state: password hash present only there, plaintext absent; no auth session keys.
- [x] **RED:** actor/Event/operation/target binding, expiry equality, invalid/tampered ref, old signed-token rejection, two concurrent preview tabs, consumed reference retry; consumed tombstone has no password hash.
- [x] **RED:** encountered expired owned preview refuses and immediately removes its credential hash; abandoned expired Session is physically removed by Django clearsessions. Verify retention in actual DB, not only response. Document access cutoff versus housekeeping; no scheduler claim.
- [x] **RED:** DRAFT valid CSV User+Membership+hash+forced-change works; 1/01 duplicate, empty/header-only, missing/extra headers, invalid encoding/size/row limits fail safely; a failure in row2 leaves zero new Users/Memberships/success audit. ACTIVE CSV preview AND confirm remain denied even with an earlier DRAFT ref.
- [x] Run `pytest tests/application/test_participant_previews.py tests/application/test_team_provisioning.py tests/endpoints/test_participant_management.py -q`; log security failures before replacement.
- [x] **Minimal:** one DB Session preview contract, hash/discard credentials, central authority, atomic CSV mutation/audit/tombstone. Preserve wrapper names and legitimate DRAFT behavior; update explicit callers/tests from token to preview_ref. Delete signed raw-row serialization, not retain a hidden fallback. Error presentation allowlist replaces raw codes in touched CSV path.
- [x] **GREEN:** same command + password-change gates + audit tests; no stdout/body canaries. Check role-revocation/GRACE/PURGED after preview and stale object tests.
- [x] **Checkpoint:** credential confidentiality, same-transaction Session consumption/audit, no new workflow model. All pass -> continue; no claim of Owner manual PASS.
- [x] **Commit:** `fix: replace credential-bearing provisioning tokens with opaque previews`.

**STOP:** storage needs plaintext/client hash/signed-cookie state, lacks atomic default DB access, or requires accepting old secret-bearing tokens.

### Task 5 — Single participant lifecycle service

**Files:** participant_services.py; tests/application/test_participant_management.py; extend audit/preview tests and permissions tests. No new public SSR route until service is GREEN.

- [x] **RED:** named tests `test_active_manager_creates_user_and_membership_without_project`, `test_developer_participant_management`, `test_join_preserves_existing_user_and_other_events`, `test_reactivate_reuses_original_membership`, `test_existing_active_membership_is_noop`.
- [x] **RED:** `test_deactivate_preserves_project_draft_history_and_resources`; create real saved v2 + genuine successful Run through services, deactivate, compare before/after rows/versions/ownership; next owner Workspace/read/write/create checks deny. Reactivate original row and verify original Project access returns only under allowed lifecycle.
- [x] **RED:** target MANAGER/mixed/inactive User; missing/wrong-Event Membership; false same-team verification; unexpected fields; changed target/User role/active/username/date/membership since preview. New-user collision must not auto-join. Existing password and must_change_password remain byte-for-byte unchanged.
- [x] **RED:** force audit or tombstone save failure after candidate mutation: all User/Membership/audit/preview changes roll back together. Retry same ref can subsequently succeed exactly once. Fresh no-op receipt is truthful and cannot write Project history.
- [x] Stage the single-entry concurrency assertions from Task6 before minimal lifecycle implementation and record their actual RED; Task6 then validates the finalized real file-DB behavior. Missing service/schema setup failures are identified separately from reproduced race failures; never label an already-GREEN characterization as RED.
- [x] Run `pytest tests/application/test_participant_management.py tests/application/test_participant_audit.py tests/application/test_participant_previews.py tests/permissions/test_participant_management.py -q`.
- [x] **Minimal:** explicit state table, shared Event transaction boundary, audit and replay contract from Tasks3/4. No mutation of global accounts/other Memberships; no Project imports used for provisioning except tests/readonly checks.
- [x] **GREEN:** same command + M7 create/policy/readonly/resource tests; source diff for projects/creation.py empty.
- [x] **Commit:** `feat: add audited single participant lifecycle operations`.

**STOP:** any approved transition needs User recovery, Project rewriting or additional schema; or genuine historical fixture cannot be produced through normal analysis.

### Task 6 — Dedicated file-SQLite concurrency / stale state gate

**Files:** participant_services.py / participant_previews.py only if RED requires bounded changes; new tests/application/test_participant_management_concurrency.py and tests/m8_concurrency_settings.py. Settings copy production DATABASES but require M8_TEST_DB_PATH for default.TEST.NAME, never change production timeout/mode.

- [x] **RED:** controlled independent connections for same-ref two confirms -> one effect/audit, both same outcome; two CREATE refs for same normalized username -> one User/Membership, loser safe stale/conflict, never overwrite winning password.
- [x] **RED:** concurrent Developer/Manager JOIN or REACTIVATE, DEACTIVATE versus REACTIVATE/noop, and M7 create versus deactivate. Stable serialized outcome; stale opposite preview cannot undo the first committed change; no duplicate successful receipt. Use Barrier/Event, not timing luck or browser sleep.
- [x] **RED:** actor disable/Manager revoke/Event GRACE or expiry/target role change while waiting; fresh transaction check denies. Whole-transaction busy retry and exhaustion; no half-consumed preview/success audit. Simulated response loss after commit -> same ref returns same receipt.
- [x] Run on a freshly allocated absolute temp file DB: `PYTHONPATH=tests M8_TEST_DB_PATH=<fresh>/m8.sqlite3 pytest --ds=m8_concurrency_settings tests/application/test_participant_management_concurrency.py -q`. Record first genuine behavioral RED; if already protected by Tasks4/5, characterize and report GREEN, do not invent RED. Inject broken serialization/retry behavior only in test-owned controlled harness where needed, never alter policy to force failure.
- [x] **Minimal:** fill any missing same-Event serialization/reload/consumed-state protection, at most specified busy retry; no additional schema or distributed framework.
- [x] **GREEN:** three independent dedicated processes, each all collected tests actually run with zero skips, plus Task5 tests. Run existing seven M7 concurrency cases separately with a fresh M7_TEST_DB_PATH, still7 PASS/0skip. Record collected/executed counts, not a guessed final M8 count.
- [x] **Checkpoint:** review lock ordering, Session/audit atomicity, stale-target behavior and M7 interoperability before UI work.
- [x] **Commit:** `test: verify participant management concurrency and replay safety` (include bounded fix if required by RED).

**STOP:** SQLite serialization cannot satisfy invariants, concurrency skipped/in-memory, need new durable workflow/unique schema, or M7 must change.

### Task 7 — SSR management entry, participant list and safe failures

**Files:** competitions/forms.py, presentation.py, views.py, urls.py; accounts/views.py; templates/accounts/event_landing.html; templates/competitions/{event_management,participant_list,participant_form,participant_confirm,participant_result,provision_upload,provision_preview,provision_result}.html; tests/endpoints/test_participant_management.py; tests/endpoints/test_event_landing.py.

- [x] **RED:** authorized landing management link, scoped list/new/join/restore/deactivate preview/confirm routes; only prescribed fields and CSRF. Direct forged URL/role/target/ref requests denied despite hidden controls. GET mutation, unsupported method and extra payload fields safely reject.
- [x] **RED:** stage-by-stage input->preview->confirm->PRG. Preview changes no Users/Memberships. Confirm has only opaque reference/operation, no captain/hash/raw token. Refresh performs no duplicate mutation. GRACE read-only list, no mutation CTA; PURGED hides/denies roster. Ordinary User gets no management directory.
- [x] **RED:** each known error and unknown exception has safe zh-CN what/why/next-action; no raw codes, traceback, ids or credential canaries in displayed DOM, flash messages or captured logs; sensitive errors do not serialize preview state.
- [x] Run `pytest tests/endpoints/test_participant_management.py tests/endpoints/test_event_landing.py tests/permissions/test_participant_management.py -q`.
- [x] **Minimal:** thin SSR adapters consuming Task5 signatures and centralized permissions; existing header/local CSS; allowlisted forms and presentation only. No Event editing/transition/roles UI.
- [x] **GREEN:** same command + password-change/provisioning/M7 endpoint tests. New/admin links cannot alter ordinary student Create/Continue/MULTIPLE states.
- [x] **Commit:** `feat: expose scoped participant management through event pages`.

**STOP:** requires new dashboard framework, privileged account management or lifecycle transition workflow; unknown errors expose sensitive data.

### Task 8 — Real browser management journey and unchanged M7 handoff

**Files:** new tests/browser/test_participant_management.py; only bounded fixes returned to owning RED task. No fake DOM, internal renderer injection or fake Run fixtures.

- [x] Establish real browser RED for new SSR entry before Task7 completes (may stage this test when Task7 starts); missing route/control is real RED, unavailable Chromium/setup is not. Then run `pytest tests/browser/test_participant_management.py -q` after implementations.
- [x] Browser Manager: ACTIVE roster -> new team -> preview -> confirm -> one User/Membership, no Project; page refresh / same-ref replay safe. No raw password/token/hash in preview DOM. Synthetic secrets only.
- [x] Student: login with known synthetic initial credential -> forced change -> events -> public M7 create -> empty v2 version0 -> normal resource UI/model Save/Check/Analyze/Results as existing public journey. Never seed a fake AnalysisRun.
- [x] Manager: existing-account join, active no-op, inactive-row restore; deactivate student's Event qualification -> student next public request denied while underlying Project/Draft/history unchanged -> reactivate -> same Project returns. Separate GRACE/PURGED controlled fixtures prove no forbidden writes/reads; Developer journey and cross-Event Manager denial exercised.
- [x] Browser DRAFT CSV upload -> opaque preview -> confirm; ACTIVE CSV forged request still denied. Record safe management list/confirmation/result and student handoff screenshots without password input, cookies, hidden state or raw payload.
- [x] **GREEN:** M8 browser file plus existing test_m7_project_creation.py, test_student_entry_flow.py, and the three exact Workspace nodes listed in section L. Manual visual inspection checks labels/action consequences/read-only cues and credential redaction.
- [x] **Commit:** `test: cover participant management and M7 student handoff`.

**STOP:** real route differs from tested contract, credentials appear, identity changes cross Event, or stable reproduction of the historical Reflection transient. Keep screenshots/diagnostics; no sleep-based fixes or acceptance claim.

### Task 9 — Fresh regression, independent review and Owner handoff

**Files:** approved plan execution record and new docs/development/M8_IMPLEMENTATION_EVIDENCE.md; fixes only through corresponding RED task. No automatic acceptance environment or integration.

- [x] Run fresh targeted Tasks2–7 suites and dedicated fresh file-SQLite M8/M7 concurrency; zero skips in dedicated runs.
- [x] Independent full runs: non-browser, full browser, mechanics; Django check, migration dry-run, diff check. Record exact counts/skips/deselections/exit codes; do not promise M7 counts after adding M8 tests.
- [x] Read requesting-code-review skill and obtain actual independent whole-branch review of baseline..feature HEAD, focusing credentials/state storage, scope/roles, migration, rollback/replay/races, no Project effects, audit schema and SSR safety. Review is not performed by the implementing context describing its own work. Use the Owner-approved execution/review method; no agent dispatch before that approval.
- [x] Critical/Important findings -> named RED -> bounded fix -> targeted + affected browser -> fresh final full gates after last change. Unapproved policy/schema change -> STOP Owner. Do not defer the mandatory credential/authority conflicts as Minor.
- [x] Record O-006 implementation coverage only for proved DRAFT CSV + approved single-entry scope; list all still-denied operations. O-006 remains OPEN / FAIL CLOSED pending complete implementation and Owner acceptance. O-004 remains OPEN; no claim that all Event administration is implemented. Protect root/grid/main data fingerprints and projects/creation.py source identity.
- [x] Preserve safe screenshots and evidence. Report `M8 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING`, branch/HEAD, tests, one-field audit migration, unchanged boundaries and known debt. Do not start Owner environment unless separately requested, no fake Owner PASS, no merge/push/tag/deploy; STOP.
- [x] **Commit:** `docs: record M8 verification and manual acceptance handoff` (execution only).

**STOP:** any failing final gate, no genuine independent review, unresolved Important/Critical issue, extra model/schema, production DB requirement, or uncertain credential handling.

## K. Browser / manual acceptance journeys

Owner later receives a separately authorized isolated demo DB/server with synthetic Developer, Manager-A, Manager-B and participant accounts; ACTIVE/DRAFT/GRACE/PURGED Events, joined/inactive/existing-no-membership targets, and a real historical Project. No real account/password reset or old DB modification.

Owner verifies: management entry discoverable; correct target and action clear before confirm; no password echoed; existing account unchanged; next student request denied after deactivation; same saved Project returns after recovery; other Event unaffected; GRACE/PURGED refusal understandable; DRAFT CSV still works; ACTIVE CSV remains closed; student self-create remains natural. Report environment READY, not Owner PASS. No server startup in this planning turn.

## L. Full regression gates

Fresh execution baseline (Task1, before product/test edits):

```bash
pytest -q -m 'not browser'
pytest tests/permissions tests/endpoints/test_event_landing.py tests/endpoints/test_reasoning_json.py tests/application/test_team_provisioning.py -q
pytest tests/mechanics -q
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
git diff --check
pytest tests/browser/test_student_entry_flow.py tests/browser/test_m7_project_creation.py -q
pytest tests/browser/test_workspace.py::test_workspace_modeling_tools_mutate_draft_and_save tests/browser/test_workspace.py::test_workspace_modeling_tools_are_unavailable_for_read_only_viewer tests/browser/test_workspace.py::test_historical_explicit_run_selection_restores_all_student_artifacts -q
```

The three Workspace node ids above were read from the baseline repository; no separate test_workspace_lifecycle.py file exists. Before each dedicated concurrency command use a new mktemp directory and the exact test setting; do not reuse real DBs. Task9 commands:

```bash
pytest -q -m 'not browser'
pytest tests/browser -q
pytest tests/mechanics -q
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
git diff --check
```

Additionally fresh dedicated M8 and M7 file-SQLite commands; record0skip. Guard `git diff fa9c000..HEAD -- projects/creation.py mechanics/` empty and migration diff exactly the approved AddField. Browser localhost permission failures are environment failures, not product RED. Historical Reflection remains ROOT CAUSE NOT PROVEN / NOT CLAIMED FIXED; if it fails, preserve evidence and diagnose rather than altering waits/assertions or silently rerunning into a PASS claim.

## M. Independent review gate

Task4 internal checkpoint: one opaque credential model, safe Session storage, same-DB atomic consumption. Task6 internal checkpoint: real SQLite concurrency and bounded replay semantics. Task9 independent reviewer: entire branch against approved Owner decisions and this plan. Require actual findings/disposition/evidence, not a second manual acceptance or unperformed regression claim. Review method selected by Owner before implementation; recommended native sequential implementation + one fresh independent whole-branch reviewer, with internal checkpoints retained.

## N. Owner manual acceptance handoff

Implementation completion is not acceptance. Provide evidence and migration scope, wait for separate Owner environment request/authorization, then stop at MANUAL PRODUCT ACCEPTANCE PENDING. No automatic merge or demo data conversion. Existing M7 debts and Reflection history stay disclosed, not opportunistically fixed.

## O. Exact file scope

MODIFY: competitions/{authorization,provisioning,models,views,urls}.py; accounts/views.py; templates/accounts/event_landing.html; templates/competitions/{provision_preview,provision_result}.html; tests/application/test_team_provisioning.py; tests/permissions/test_event_project_access.py; tests/endpoints/test_event_landing.py; docs/specs/{MASTER_SPEC,AUTHORIZATION_AND_EVENT_ARCHITECTURE,ARCHITECTURE_DECISION_REGISTER,API_AND_APPLICATION_FLOW}.md; this plan at execution time.

NEW: competitions/{forms,participant_services,participant_previews,participant_inputs,participant_audit,presentation}.py; competitions/migrations/0003_bulkimportbatch_operation_details.py; templates/competitions/{event_management,participant_list,participant_form,participant_confirm,participant_result,provision_upload}.html; tests/permissions/test_participant_management.py; tests/application/test_{participant_audit,participant_previews,participant_management,participant_management_concurrency}.py; tests/endpoints/test_participant_management.py; tests/migrations/test_m8_participant_audit.py; tests/browser/test_participant_management.py; tests/m8_concurrency_settings.py; docs/superpowers/specs/2026-10-18-m8-event-participant-management-decisions.md; docs/development/M8_IMPLEMENTATION_EVIDENCE.md.

UNCHANGED: projects/creation.py and all M7 Project contracts; accounts/models.py; User/EventMembership/Project schema; modeling/analysis/learning numerical or Draft semantics; materials mutation contracts; mechanics/idealization; existing screenshots/archives/root/grid. Existing tests are updated only for intentionally replaced preview interface or new authority assertions, never weakened to mask failures.

## P. Risks / stop conditions

Mandatory STOP if new Team/participant/workflow/account-identity schema is needed; default transactional DB Session unavailable; opaque preview cannot be safe/atomic; SQLite gate fails; role mixtures require unapproved repair; legacy actor/target ambiguity needs a new product rule; preview storage would contain plaintext; race solution changes M7; source/data baseline drifts; sensitive output or real Project modification required. No additional schema is inferred from the approved audit migration.

## Q. Estimated size

L. Nine reviewable sequential tasks reflect the actual audit-before-mutation dependency, not extra scope. Shared security foundation and explicit interfaces are implemented once, not duplicated between CSV and single-entry.

## R. Readiness / plan self-review

- Owner RED1–4/11 -> Tasks2/5/7; RED5/13–17 -> Tasks4/6/7; RED6–10/18–19 -> Tasks5/8; RED12 -> Task6; RED20 -> Tasks3–6; RED21 -> Tasks8/9.
- Five Review Focus classes each have named test ownership. No production/test edits, migration generation or execution, commit, new worktree or Task1 was performed to prepare this plan.
- Every transition goes through the same authority and opaque preview; receipt/credential tombstone saved with the mutation, avoiding a response-time Session race. Schema stays exactly one audit field.
- Planning artifact only: this file is intentionally untracked in main integration, to be safely carried into the approved isolated feature at Task1; do not accidentally include other main/root changes.
- Current status: `M8 IMPLEMENTED — MANUAL PRODUCT ACCEPTANCE PENDING`.

Owner authorized Task1–9 with the three amendments above. Stop only at approved security/architecture/product gates or final manual-acceptance handoff.

## Execution closeout — 2026-10-20

Tasks1–9 executed sequentially on `feat/event-participant-management-m8`. Commits: f5d7bcd /632a471 /db60956 /0bfd7f3 /a39a628 /b346516 /a9172bd /e1441dc; Task9 bounded review fix8797dc2. Both internal architecture checkpoints passed. Genuine independent review found ABA freshness and CSV safe-boundary issues; named RED→GREEN and one bounded fix pass completed without additional schema or M7 changes.

Fresh final gates: targeted148 PASS; non-browser781 PASS22 file-concurrency skips313 browser deselections; full browser313 PASS; mechanics131 PASS; M8 dedicated file-SQLite15/15 in three independent processes0skip; M7 dedicated7/7 0skip; Django/migration dry-run/diff exit0. Full counts, times, review disposition, every ruling, preserved screenshots and disclosed framework/M7 debts: `docs/development/M8_IMPLEMENTATION_EVIDENCE.md`.

O-004 OPEN; O-006 OPEN pending implementation acceptance. ACTIVE CSV and unapproved account/role operations remain closed. Branch/worktree retained. No Owner acceptance environment or Owner PASS; no merge/push/tag/release/deploy. STOP.
