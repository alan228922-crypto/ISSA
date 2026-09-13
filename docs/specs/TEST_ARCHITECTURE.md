# TEST_ARCHITECTURE.md

## 0. 文件狀態

- 文件角色：Mechanics unit/benchmark、Django integration、permission、purge、contract 與 Future Frame regression 測試策略。
- 階段：Truss-first P0。
- 核心原則：**Mechanics correctness 必須先於 UI polish，Benchmark 是 gate，不是 demo。**
- Source of Truth：MASTER_SPEC.md v1.3；本 Test Architecture 已完成 reconciliation。

---

## 1. Test Pyramid for This PoC

【Recommended】

```text
Few browser/manual acceptance checks
            ▲
Django integration / permission / flow tests
            ▲
Pure domain + application unit tests
            ▲
Mechanics unit tests + benchmark tests
```

不為了「完整 E2E 自動化」導入大型 browser farm。P0 最重要的是 mechanics、permission、purge 可重現。

【Confirmed】未来 UI、Teaching copy 与用户可见 validation message 的测试使用简体中文（zh-CN）。Mechanics machine-readable code 不中文化；例如 `ZERO_LENGTH_MEMBER` 与 `SINGULAR_GLOBAL_STIFFNESS` 保持英文稳定 identifier。

---

## 2. Tooling Baseline

【Recommended】

- `pytest`
- `pytest-django`
- NumPy testing utilities / `math.isclose`
- Django test client
- fixtures/factories 採最小自建 helper 或 pytest fixtures

不強制導入大型 factory framework、property-based framework；若後續測試價值明確再加。

---

## 3. Test Directory Structure

```text
tests/
├── mechanics/
│   ├── unit/
│   ├── benchmarks/
│   │   ├── truss2d/
│   │   ├── sections/
│   │   └── stability/
│   └── fixtures/
├── idealization/
├── application/
├── permissions/
├── purge/
├── contracts/
└── integration/
```

【Future】

```text
tests/mechanics/benchmarks/frame2d/
```

Frame benchmarks 不與 Truss 混成同一 expected-output file。

---

## 4. Mechanics Unit Tests

【Confirmed / Recommended】

至少涵蓋：

### Geometry / element

- member length
- direction cosine
- zero length rejection

### Stiffness

- known 2D truss element stiffness matrix
- symmetry of element stiffness
- scaling with E / A / L

### Assembly

- deterministic DOF ordering
- correct contribution to global K
- repeated nodes/members handling per validation policy

### Restraints / load

- restrained DOF mapping
- load vector assembly

### Solve / recovery

- displacement solve
- reaction recovery
- axial force recovery
- tension positive / compression negative

### Postprocess

- stress = N/A
- member mass = density A L
- total mass sum
- Euler `Pcr` with explicit K

---

## 5. Benchmark Suite — P0 Gate

【Confirmed】Truss-first baseline：

### B/T01 — 單杆軸向拉壓

Reference：解析解。

驗證：

- `δ = PL/EA`
- support reaction
- axial force
- stress
- sign convention

### B/T02 — 簡單三角桁架

Reference：教材/手算。

驗證：

- reactions
- selected member axial forces
- displacement
- equilibrium

### B/T03 — 對稱平面桁架

驗證：

- symmetric reactions
- symmetric member forces
- symmetric displacements where expected

### B/T04 — 簡單超靜定桁架

Reference：可信 hand calculation / trusted software/reference implementation。

驗證：

- global assembly
- constraints
- displacement
- member force

### B/S01 — Composite Section

驗證：

- A
- centroid
- Ix
- Iy
- mass/length

至少包括：

- simple rectangle
- symmetric composite
- asymmetric composite

### B/E01 — Euler with explicit K

Reference：解析公式。

驗證：

- `Pcr = π²EI/(KL)²`

【MECHANICS REVIEW REQUIRED】產品 K policy 未核定，但 explicit-K formula test 可先完成。

---

### Event provisioning policy tests

【Open Decision — Master O-006】测试必须区分产品政策与临时安全 fallback：

- DRAFT provisioning 必须成功。
- PURGED provisioning 必须拒绝。
- ACTIVE provisioning 在 O-006 未关闭时，必须验证 fail-closed / PROVISIONING_STATUS_POLICY_GAP 行为。

测试名称不得暗示 ACTIVE 的当前阻断是永久产品规则。Product Owner 决策 O-006 后，测试必须随最终政策更新。

## 6. Stage 2 Benchmarks

【Confirmed Deferred / Future】

舊研究計畫中的以下案例移到 Frame Stage 2：

- cantilever beam end load
- simply supported beam point load
- simply supported beam UDL
- portal frame
- Fixed support frame behavior
- N/V/M
- bending deformation

P0 CI 不因缺少這些測試判定 failure。

---

## 7. Numerical Comparison Rule

【Recommended】

不要使用字串化/顯示小數判斷 mechanics 正確性。

標準形式：

```text
abs(actual - expected) <= atol + rtol * abs(expected)
```

### Baseline policy

- 每個 benchmark fixture 明確寫自己的 `atol` / `rtol`。
- 對解析且尺度良好的簡單案例，可從 `rtol ~ 1e-8` 作起點。
- 接近 0 的反力/位移必須靠 meaningful `atol`，不可只看 relative error。
- 若模型 conditioning 造成合理 tolerance 差異，應由 benchmark 註明，不可任意放寬全局門檻。

這些是推薦測試策略，不是工程設計安全係數。

---

## 8. Equilibrium / Invariant Tests

【Recommended】除 expected value 外，建立 invariants：

- global ΣFx residual small
- global ΣFy residual small
- stiffness symmetry where expected
- same input + same solver version → deterministic result
- node/member input ordering不應改變依 ID 回傳之 physical result
- scaling E upward → displacement inverse scaling in適用線性案例
- scaling A upward → axial stiffness change consistent with theory

這些可補強單一 benchmark 的盲點。

---

## 9. Sign Convention Tests

【Required】

至少明確測：

- tension member → `N > 0`
- compression member → `N < 0`
- stress sign matches axial force
- reaction global axes +x right / +y up

任何 sign convention 改動需更新 solver version/contract 與 benchmark，不得只改 UI label。

---

## 10. Validation / Failure Tests

至少：

- empty model
- unknown node reference
- duplicate node/member ID
- zero length member
- E <= 0
- A <= 0
- NaN / Inf
- no support
- insufficient restraint
- singular mechanism
- unsupported P0 feature
- load target missing

Expected：stable machine code，不依賴 stack trace。

---

## 11. Section Engine Tests

【Confirmed】Section Designer 為跨 Truss/Frame 共用核心。

Tests：

- rectangle known A/I
- translated rectangle centroid/parallel-axis theorem
- composite symmetric section
- composite asymmetric section
- strip overlap policy（若產品允許/禁止需規格化）
- strong/weak axis tie case
- mass/length with density
- invalid zero/negative dimensions

【Open Decision】自由 composite strip 是否允許幾何重疊，若尚未產品確認，測試先標 pending，不自行猜。

---

## 12. Idealization Tests

這是防止 Physical Model 與 Solver 混掉的關鍵 test layer。

必測：

1. crossing members without Connection → **不**共用 analysis node。
2. explicit Connection at crossing → 產生共同 analysis node。
3. PhysicalMember with intermediate Connection → split into multiple analysis members。
4. mapping `physical_member → analysis_members[]` 正確。
5. material/section numeric properties 被 resolve/freeze。
6. invalid target support/load 被拒絕。
7. two visually coincident nodes 不被 solver 自動 merge，除非 idealization rule 明確建立共同 node。

---

## 13. ModelRevision Tests

必測：

- Analyze creates/reuses revision per hash policy。
- Revision immutable。
- editing Material after run 不改舊 revision snapshot。
- editing Section after run 不改舊 input/result。
- same canonical snapshot → same model_hash。
- reordered non-semantic JSON keys → same canonical hash。
- changed geometry/load/E/A → different input/model hash as defined。

---

## 14. AnalysisRun Tests

- Run points to ModelRevision。
- Run records SolverVersion。
- success persists result schema/version。
- mechanics validation failure persists stable failure status/code。
- unexpected error returns safe `SOLVER_FAILED` behavior。
- TeachingInsight does not mutate stored result JSON。
- repeated same input + solver version produces numerically equivalent result。

---

## 15. Application Flow Integration Tests

### M4A Prediction / reveal

- owner-only Prediction DRAFT/create/complete, CSRF and JSON error mapping;
- exact all-member `TENSION|COMPRESSION|ZERO_FORCE|UNSURE` coverage, `prediction-v1`, PhysicalPointRef and alternating-path topology;
- completed immutability, stale-draft history, nullable Analyze and same-draft repeated Run link;
- owner SUCCESS result read creates one reveal record; Manager/Developer and failed Run reads do not;
- completion/reveal race serializes on Project and cannot accept a late pre-result Prediction;
- mechanics, idealization and `truss2d-result-v1` remain unchanged; O-007 is not implemented.

### Save

- valid own project draft saves and increments version。
- stale expected version → 409 / `STALE_DRAFT`。
- client cannot alter owner/event through JSON。

### Model Check

- reads current saved version。
- returns machine code + beginner-facing message。
- does not create false successful AnalysisRun。

### Analyze

- ACTIVE Event 依 server-side 權限可 Analyze；PURGED 不可操作已 purge 的 Project Operational Data。FINISHED_GRACE 依 Master O-003 保持未決，不建立永久 allow/deny edit/analyze assertions。
- current draft version required。
- successful flow creates immutable revision + run。
- result endpoint maps analysis IDs back to physical IDs。

### Section preview

- server pure engine result returned。
- preview does not silently save Section。

---

## 16. Permission Test Matrix

【Required】

### User isolation

- User A list excludes User B project。
- guessed `/projects/B/` denied。
- save/check/analyze/result endpoints for B denied。

### Manager scope

- assigned Event project readable。
- unassigned Event denied。
- student project write denied。
- cannot create Manager/Developer。

### Developer

- global authorized operations allowed。

### Forced password change

- `must_change_password=True` direct project URL blocked。
- change succeeds → normal access restored。

### Event lifecycle

- 已核定的 DRAFT/PURGED 限制須 server-side 驗證；FINISHED_GRACE 的 view/edit/analyze 規則等待 Master O-003，read-only 僅為 Recommended。

---

## 17. Bulk Provisioning Tests

必測：

- username generation `YYYYMMDD + TT`
- team number padding
- duplicate in file
- duplicate against DB
- missing captain student ID
- unauthorized Manager event
- Manager cannot create elevated role
- confirm revalidates, not trust preview
- one bad row → zero accounts created
- successful batch → all accounts + memberships created
- password check works through Django hash
- plaintext captain student ID not persisted in audit/import result
- `must_change_password=True`

---

## 18. Purge Tests

【Required】

### Eligibility

- before purge_at → no purge
- at/after purge_at → eligible

### Deletion

- Project raw data removed
- Physical model removed
- ModelRevision snapshot removed
- AnalysisRun raw input/result removed
- raw Validation context removed
- raw Reflection/Prediction text removed per retention policy

### Research retention

- approved derived metric remains
- no username/captain ID remains in research data
- no full model topology remains
- identity → research key mapping removed

### Idempotency

- second purge = safe no-op
- retained metric not duplicated
- audit remains coherent

### Transaction failure

- injected failure before commit does not leave Event falsely marked PURGED with half-deleted operational state。

---

## 19. Research Logging Tests

若 research module enabled：

- Analysis count derived correctly。
- Modeling error count derives from stable codes。
- first-pass success definition deterministic。
- task duration uses defined timestamps，不由 browser text猜測。
- deleted raw data cannot be reconstructed from retained metric payload。

研究統計方法本身不屬於 application unit test；資料抽取 correctness 才是。

---

## 20. Teaching Layer Tests

【Recommended】deterministic rule tests：

- max displacement insight points to correct source metric/entity。
- tension/compression message matches force sign。
- singular error maps to beginner message without claiming exact mechanism certainty。
- buckling language uses「screening/risk/needs attention」，不宣稱確定 failure。
- report completeness identifies missing fields accurately。

Teaching tests 不能取代 mechanics benchmarks。

---

## 21. API Contract Tests

至少固定：

- JSON schema version present。
- save response draft_version。
- stale draft error code。
- analyze response revision/run IDs。
- result payload uses unit-suffixed fields。
- unsupported fields/features are rejected rather than silently ignored when they could alter mechanics meaning。

P0 不需建立 external OpenAPI spec，除非後續真的有外部 client。

---

## 22. CI / Merge Gates

【Recommended】Codex/Developer 完成功能前至少：

### Gate A — Mechanics

- all mechanics unit tests pass
- all P0 benchmarks pass

### Gate B — Domain

- idealization/revision/hash tests pass

### Gate C — Security/Data

- permission tests pass
- purge tests pass

### Gate D — Integration

- save → check → analyze → result happy path pass

UI cosmetic test failure 不應被拿來掩蓋 mechanics gate failure。

---

## 23. Regression Strategy for Future Frame

【Future】

加入 Frame2D 時：

- Truss benchmark suite **原封保留**。
- Frame 有自己的 unit/benchmark fixtures。
- shared Section Engine tests 同時服務 Truss/Frame。
- common geometry/numeric utility 改動必須跑兩套 mechanics regression。
- 不把 Frame expected result 塞到 Truss result schema。

成功標準：新增 Frame 不造成任何已通過 Truss benchmark drift，除非有明確 bug fix + version/change record。

---

## 24. Manual Acceptance Checks

自動測試外，P0 發佈前最少人工走一次：

```text
Login
→ forced password change
→ own Event/Project
→ build simple truss
→ Model Check
→ Predict
→ Analyze
→ understand System View
→ inspect detail
→ modify
→ Compare
→ Reflect
→ Report
```

另以 Manager 帳號確認 read-only 與 bulk provisioning。

---

## 25. Open Test Decisions

### OD-TEST-01 — Euler K product policy

【MECHANICS REVIEW REQUIRED】explicit K formula可測；自動 screening acceptance test 等老師確認。

### Resolved — Roller orientation（Master O-002）

Support fixture 必须覆盖 PINNED/null、ROLLER/X、ROLLER/Y 和无效组合。

### OD-TEST-03 — Composite strip overlap

若自由拼接可能重疊，需 Section spec 明確決定合法性與 property calculation semantics。

---

## 26. What Not to Test/Build Yet

P0 不因「測試完整」而先建：

- 3D test suite
- Frame bending test suite
- microservice contract test
- async queue test
- WebSocket test
- load/performance farm
- multi-browser realtime collaboration test
- optimization correctness test

測試架構服務於已批准 scope，不用測試推動 scope creep。

---

## Approved reconciliation — Master O-001

**MECHANICS REVIEW REQUIRED**: Master O-001 includes effective length factor K, default/automatic K inference, controlling I / weak-axis selection policy, final risk bands and related beginner-facing wording. None is implicitly approved. M1 may verify `Pcr = π² E I / (K L)²` using explicit E, I, L and K; numerical section properties do not authorize automatic buckling-axis selection. Automatic product behavior remains blocked.
