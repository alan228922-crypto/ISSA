# M8 — Approved participant qualification management contract

Owner approved D-M8-001..004 and native sequential Tasks1–9, including three bounded amendments, on 2026-10-18. Baseline main fa9c000ddbff89adc41a34711bf44a0b509d19fe. This is the binding scoped contract; implementation completion is not Owner acceptance.

## Authority and lifecycle

Authenticated active global DEVELOPER, or authenticated active global MANAGER with the exact Event active MANAGER Membership only. USER plus MANAGER Membership is not an administrator. Active PARTICIPANT plus active MANAGER in that Event fails closed, including for Developer. Inactive historical Memberships grant no authority, do not constitute current mixed identity and are preserved.

DRAFT supports existing CSV plus single CREATE_USER / JOIN_EXISTING / REACTIVATE / DEACTIVATE. ACTIVE permits only those single operations before purge_at; ACTIVE CSV remains denied. FINISHED_GRACE permits authorized read-only roster/history, no qualification mutation. PURGED refuses participant operational access. Confirm must reload actor, Event, target and Membership after Event serialization, never rely on preview-time permissions or stale objects.

## Identity and transitions

New accounts retain date+normalized01..99 username, Django-hashed captain initial credential and forced first password change. Existing targets must be active USER, explicitly verified same team, without active management-role conflict. Exact username only, no fuzzy discovery or prefix-based identity inference. Joining never overwrites credentials/global flags or other Event rows. Reactivate original PARTICIPANT row; deactivate changes only that Event row.is_active. No deletion, ownership change, Project/Draft/history/resource mutation. Next server authorization loses access after deactivation. Inactive global User recovery is out of scope (O-004 OPEN).

## Opaque credential preview

Client gets only random opaque reference. Trusted state is actor/Event/operation/target/expiry bound in separate default-DB Django Session rows, TTL600. Hash immediately; never serialize plaintext/raw CSV to Session, HTML, response, signed token, log or audit. Entire old signed credential-bearing token contract is retired, no fallback. One-time consumption and sanitized audit share the mutation transaction. Retry reauthorizes and returns the historical receipt without repeating effects or undoing later qualification changes.

600 seconds is SERVICE ACCESS CUTOFF, not automatic DB deletion. Encountered expired owned preview must immediately lose its credential hashes (physical delete or hash-free tombstone), even though confirm refuses. Abandoned expired Session cleanup uses Django clearsessions; tests must prove physical removal. No new preview model, scheduler, worker or workflow aggregate.

## Business receipts and migration

Only approved AddField: BulkImportBatch.operation_details_json JSONField(default=dict, blank=True). Legacy {} remains summary-only; no invented details/backfill. Fixed versioned allowlist, business operations CREATE_USER / JOIN_EXISTING / REACTIVATE / DEACTIVATE; outcome SUCCESS / NOOP only. DRAFT CSV uses CREATE_USER with controlled multi-target list, while internal DRAFT_CSV_CREATE channel preserves lifecycle restriction. Audit is atomic with User/Membership mutation and credential-free preview consumption. No DENIED business receipt for unauthorized, malformed, expired, conflict or invalid-ref requests. Any security logging excludes password/hash/ref/CSV/body/Session/traceback. Audit never contains credentials, raw request, arbitrary free text or bearer reference.

## Transactions, unchanged boundaries and gates

SQLite application paths serialize with no-op Event UPDATE, fresh reads and bounded whole-transaction busy retry. No schema additions beyond the one audit field. Same-ref replay, competing references, target changes and role/lifecycle revocation require real dedicated file-SQLite evidence. M7 projects/creation.py and self-create remain unchanged; provisioning creates no Project/resources/Run/snapshot. User/EventMembership/Project schemas, Draft, Node-as-Joint, Delete Impact, historical snapshots, Solver, Mechanics and mm/N/MPa/g unchanged.

At the implementation gate, O-006 remained OPEN / FAIL CLOSED until complete implementation and explicit Owner acceptance; automated evidence alone never declared Owner PASS. On 2026-10-20 (Asia/Shanghai), the Owner formally declared M8 OWNER MANUAL PRODUCT ACCEPTANCE: PASS for accepted implementation 5eea16eff337ca458dd5f2a8803571f08c8d2de0. D-M8-001..004 are RESOLVED and O-006 is RESOLVED — APPROVED SCOPE ONLY: DRAFT CSV and DRAFT/ACTIVE single CREATE_USER, JOIN_EXISTING, REACTIVATE, DEACTIVATE. ACTIVE CSV, public signup/join code, Manager assignment/revoke/participant-to-manager promotion, impersonation, administrator password reset, global User recovery, Event-transition UI/scheduler and automatic Project provisioning stay denied/out of scope. O-004 remains OPEN. Mandatory Task4/6/9 evidence is retained; local ff-only integration, fresh post-merge verification and cleanup are separately Owner-authorized closeout, not new product scope. No push/tag/release/deploy.
